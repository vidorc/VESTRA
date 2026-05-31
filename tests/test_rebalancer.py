"""Tests for the Portfolio Rebalancer (pure plan computation + endpoint)."""

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.data.mongo import get_client, set_client
from app.main import app
from app.services.rebalancer import compute_rebalance_plan

_PRICES = {"RELIANCE": 1450.0, "INFY": 1550.0, "HDFCBANK": 1650.0, "TCS": 3900.0}
_TARGET = {"RELIANCE": 30, "INFY": 20, "HDFCBANK": 20}


# --- pure plan computation ----------------------------------------------

def test_no_target_means_no_plan():
    plan = compute_rebalance_plan({"RELIANCE": 10}, {}, _PRICES)
    assert plan.drift_detected is False
    assert plan.actions == []


def test_overweight_position_is_sold():
    # Heavily overweight RELIANCE.
    plan = compute_rebalance_plan({"RELIANCE": 50, "INFY": 5, "HDFCBANK": 5}, _TARGET, _PRICES)
    assert plan.drift_detected is True
    actions = {a.ticker: a.action for a in plan.actions}
    assert actions["RELIANCE"] == "SELL"


def test_underweight_positions_are_bought():
    plan = compute_rebalance_plan({"RELIANCE": 50, "INFY": 5, "HDFCBANK": 5}, _TARGET, _PRICES)
    actions = {a.ticker: a.action for a in plan.actions}
    assert actions.get("INFY") == "BUY"
    assert actions.get("HDFCBANK") == "BUY"


def test_held_ticker_absent_from_target_is_fully_sold():
    plan = compute_rebalance_plan({"RELIANCE": 10, "TCS": 10}, {"RELIANCE": 100}, _PRICES)
    tcs = [a for a in plan.actions if a.ticker == "TCS"]
    assert tcs and tcs[0].action == "SELL"


def test_balanced_within_threshold_has_no_actions():
    # Roughly on target (42.9 / 28.6 / 28.6 after normalization), small drift.
    holdings = {"RELIANCE": 30, "INFY": 19, "HDFCBANK": 18}
    plan = compute_rebalance_plan(holdings, _TARGET, _PRICES, drift_threshold_pct=15.0)
    assert plan.drift_detected is False


def test_unpriced_holdings_yield_no_plan():
    plan = compute_rebalance_plan({"RELIANCE": 10}, _TARGET, {})  # no prices
    assert plan.drift_detected is False


def test_all_quantities_positive():
    plan = compute_rebalance_plan({"RELIANCE": 50, "INFY": 1}, _TARGET, _PRICES)
    for a in plan.actions:
        assert a.quantity > 0


# --- endpoint ------------------------------------------------------------

@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_rebalance_requires_auth(client):
    r = await client.post("/rebalance/preview")
    assert r.status_code == 401


async def test_rebalance_preview_returns_plan(client):
    reg = await client.post(
        "/auth/register", json={"email": "rb@b.com", "password": "supersecret1"}
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.investor_profiles.update_one(
        {"user_id": uid},
        {"$set": {"holdings": {"RELIANCE": 50, "INFY": 5, "HDFCBANK": 5}, "target_allocation": _TARGET}},
    )
    r = await client.post("/rebalance/preview", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["drift_detected"] is True
    assert len(body["actions"]) >= 1
