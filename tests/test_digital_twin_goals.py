"""Tests for Phase 4 Digital Twin + Goal-Based Investing.

Covers the deterministic goals service (alignment, liquidity) and the
twin/goals REST endpoints (auth + ownership scoping), plus the goal_alignment
factor now flowing into the Portfolio Health Engine.
"""

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.data.mongo import set_client
from app.main import app
from app.models.schemas import DigitalTwin, Goal
from app.services.goals import goal_alignment_score, liquidity_need, liquidity_pressure
from app.services.portfolio_health import score_portfolio_health


# --- goals service (pure) ------------------------------------------------

def test_alignment_neutral_without_goals():
    assert goal_alignment_score([]) == 50.0


def test_alignment_priority_weighted():
    high = Goal(type="house", target_amount=2_000_000, current_amount=500_000, priority="high")  # 25%
    low = Goal(type="wealth_growth", target_amount=1_000_000, current_amount=1_000_000, priority="low")  # 100%
    # (3*25 + 1*100) / 4 = 43.75 -> 43.8
    assert goal_alignment_score([high, low]) == 43.8


def test_liquidity_need_near_term_goal_plus_emergency_shortfall():
    today = date(2026, 1, 1)
    near = Goal(type="education", target_amount=300_000, current_amount=100_000, target_date="2026-07-01")
    far = Goal(type="retirement", target_amount=10_000_000, current_amount=0, target_date="2050-01-01")
    twin = DigitalTwin(monthly_expenses=80_000, monthly_emi=30_000, emergency_fund=300_000)
    # near shortfall 200k + emergency shortfall (660k - 300k) = 560k
    assert liquidity_need([near, far], twin, today=today) == 560_000.0


def test_liquidity_pressure_bands():
    today = date(2026, 1, 1)
    near = Goal(type="education", target_amount=300_000, current_amount=100_000, target_date="2026-07-01")
    twin = DigitalTwin(monthly_expenses=80_000, monthly_emi=30_000, emergency_fund=300_000)
    assert liquidity_pressure([near], twin, portfolio_value=2_000_000, today=today) in ("medium", "high")
    assert liquidity_pressure([], None, portfolio_value=1_000_000, today=today) == "low"


def test_bad_target_date_is_ignored_not_raised():
    today = date(2026, 1, 1)
    g = Goal(type="house", target_amount=100_000, current_amount=0, target_date="not-a-date")
    # Unparseable date -> not counted as near-term; no exception.
    assert liquidity_need([g], None, today=today) == 0.0


# --- health engine integration ------------------------------------------

def test_goals_flow_into_health_score():
    prices = {"INFY": 1550.0, "HDFCBANK": 1650.0}
    holdings = {"INFY": 10, "HDFCBANK": 10}
    well_funded = [Goal(type="retirement", target_amount=100, current_amount=100, priority="high")]
    underfunded = [Goal(type="retirement", target_amount=100, current_amount=0, priority="high")]
    h_good = score_portfolio_health(holdings, 20000.0, prices, goals=well_funded)
    h_bad = score_portfolio_health(holdings, 20000.0, prices, goals=underfunded)
    assert h_good.score > h_bad.score
    # Dict goals (as stored in Mongo) are coerced too.
    h_dict = score_portfolio_health(holdings, 20000.0, prices, goals=[{"type": "house", "target_amount": 100, "current_amount": 100}])
    align = next(f for f in h_dict.factors if f.name == "goal_alignment")
    assert align.score == 100.0


# --- endpoints -----------------------------------------------------------

@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def _register(client, email="t@b.com"):
    r = await client.post("/auth/register", json={"email": email, "password": "supersecret1"})
    assert r.status_code == 201
    return r.json()["access_token"], r.json()["user_id"]


async def test_twin_requires_auth(client):
    assert (await client.get("/digital-twin")).status_code == 401
    assert (await client.put("/digital-twin", json={})).status_code == 401


async def test_twin_put_then_get(client):
    token, _ = await _register(client)
    h = {"Authorization": f"Bearer {token}"}
    r = await client.put(
        "/digital-twin",
        headers=h,
        json={"age": 35, "annual_income": 2_400_000, "monthly_expenses": 80_000, "risk_profile": "moderate"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["digital_twin"]["age"] == 35
    got = await client.get("/digital-twin", headers=h)
    assert got.json()["digital_twin"]["annual_income"] == 2_400_000


async def test_goals_crud_and_ownership(client):
    token_a, _ = await _register(client, "a@b.com")
    token_b, _ = await _register(client, "b@b.com")
    ha = {"Authorization": f"Bearer {token_a}"}
    hb = {"Authorization": f"Bearer {token_b}"}

    # create
    r = await client.post(
        "/goals", headers=ha,
        json={"type": "house", "name": "Down payment", "target_amount": 2_000_000, "current_amount": 500_000, "priority": "high"},
    )
    assert r.status_code == 201, r.text
    goal_id = r.json()["goal"]["goal_id"]
    assert goal_id

    # list (owner sees it; other user does not)
    assert len((await client.get("/goals", headers=ha)).json()["goals"]) == 1
    assert len((await client.get("/goals", headers=hb)).json()["goals"]) == 0

    # update (owner ok)
    upd = await client.put(f"/goals/{goal_id}", headers=ha, json={"current_amount": 800_000})
    assert upd.status_code == 200
    assert upd.json()["goal"]["current_amount"] == 800_000

    # update by other user -> 404 (ownership-scoped)
    assert (await client.put(f"/goals/{goal_id}", headers=hb, json={"current_amount": 1})).status_code == 404

    # delete by other user -> 404; by owner -> ok
    assert (await client.delete(f"/goals/{goal_id}", headers=hb)).status_code == 404
    assert (await client.delete(f"/goals/{goal_id}", headers=ha)).status_code == 200
    assert len((await client.get("/goals", headers=ha)).json()["goals"]) == 0


async def test_health_endpoint_reflects_goals(client):
    token, uid = await _register(client, "hg@b.com")
    h = {"Authorization": f"Bearer {token}"}
    from app.data.mongo import get_client

    db = get_client()["vestra_test"]
    await db.investor_profiles.update_one(
        {"user_id": uid}, {"$set": {"holdings": {"INFY": 10, "HDFCBANK": 10}, "cash_balance": 20000.0}}
    )
    await client.post(
        "/goals", headers=h,
        json={"type": "retirement", "target_amount": 100, "current_amount": 100, "priority": "high"},
    )
    r = await client.get("/portfolio/health", headers=h)
    assert r.status_code == 200
    align = next(f for f in r.json()["factors"] if f["name"] == "goal_alignment")
    assert align["score"] == 100.0
