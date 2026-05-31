"""Tests for Risk Stress Testing (pure shock projection + endpoint).

``stress_test`` applies named macro shocks (broad market drops, an RBI rate
surprise, a largest-sector crash) to a portfolio using per-sector sensitivities.
Deterministic: same holdings + prices always yield the same result.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.data.mongo import get_client, set_client
from app.main import app
from app.services.stress import stress_test

# RELIANCE -> energy, INFY -> it, HDFCBANK -> banking, ITC -> fmcg.
_PRICES = {"RELIANCE": 1400.0, "INFY": 1500.0, "HDFCBANK": 1600.0, "ITC": 450.0}


# --- pure shock projection ----------------------------------------------


def test_empty_book_has_no_exposure():
    result = stress_test({}, _PRICES, cash=50000.0)
    assert result.invested_value == 0.0
    assert result.portfolio_value == 50000.0
    assert result.scenarios == []
    assert result.resilience == "robust"


def test_cash_only_book_is_robust():
    result = stress_test({"RELIANCE": 0}, _PRICES, cash=100000.0)
    assert result.invested_value == 0.0
    assert result.scenarios == []


def test_produces_the_four_named_scenarios():
    result = stress_test({"RELIANCE": 10, "INFY": 10}, _PRICES)
    names = {s.name for s in result.scenarios}
    assert names == {"market_drop_5", "market_drop_15", "rbi_surprise", "sector_crash"}


def test_invested_value_excludes_cash():
    result = stress_test({"RELIANCE": 10}, _PRICES, cash=20000.0)
    assert result.invested_value == pytest.approx(14000.0)  # 10 * 1400
    assert result.portfolio_value == pytest.approx(34000.0)  # + cash


def test_bigger_market_drop_loses_more():
    result = stress_test({"HDFCBANK": 10}, _PRICES)
    by_name = {s.name: s for s in result.scenarios}
    assert by_name["market_drop_15"].loss > by_name["market_drop_5"].loss


def test_market_beta_makes_banking_fall_more_than_fmcg():
    # Equal INR exposure: banking (beta 1.3) should lose more than fmcg (beta 0.6).
    # HDFCBANK 10 * 1600 = 16000 ; ITC ~35.5 * 450 ≈ 16000.
    bank = stress_test({"HDFCBANK": 10}, _PRICES)
    fmcg = stress_test({"ITC": 36}, _PRICES)
    bank_drop = next(s for s in bank.scenarios if s.name == "market_drop_15")
    fmcg_drop = next(s for s in fmcg.scenarios if s.name == "market_drop_15")
    assert bank_drop.loss_pct > fmcg_drop.loss_pct


def test_rbi_surprise_hits_banking_hardest():
    result = stress_test({"HDFCBANK": 10, "INFY": 10}, _PRICES)
    rbi = next(s for s in result.scenarios if s.name == "rbi_surprise")
    assert rbi.worst_sector == "banking"


def test_sector_crash_targets_the_largest_sector():
    # Energy is the largest sector by value here (RELIANCE 50 * 1400 = 70000).
    result = stress_test({"RELIANCE": 50, "INFY": 1}, _PRICES)
    crash = next(s for s in result.scenarios if s.name == "sector_crash")
    assert crash.worst_sector == "energy"
    assert "energy" in crash.label.lower()


def test_loss_is_positive_and_value_after_is_lower():
    result = stress_test({"RELIANCE": 10}, _PRICES)
    for s in result.scenarios:
        assert s.loss >= 0
        assert s.value_after <= s.value_before


def test_concentrated_book_is_more_fragile_than_diversified():
    # Single-sector concentration -> a sector crash bites the whole book.
    concentrated = stress_test({"RELIANCE": 100}, _PRICES)
    diversified = stress_test(
        {"RELIANCE": 25, "INFY": 25, "HDFCBANK": 25, "ITC": 80}, _PRICES
    )
    assert concentrated.worst_case_loss_pct > diversified.worst_case_loss_pct


def test_resilience_band_reflects_worst_case():
    result = stress_test({"RELIANCE": 100}, _PRICES)
    assert result.resilience in ("robust", "moderate", "fragile")
    if result.worst_case_loss_pct >= 25.0:
        assert result.resilience == "fragile"


def test_determinism_same_inputs_same_result():
    h, p = {"RELIANCE": 10, "INFY": 5}, _PRICES
    assert stress_test(h, p).model_dump() == stress_test(h, p).model_dump()


def test_unknown_ticker_priced_at_zero_adds_no_risk():
    # No price entry -> valued at 0, contributes nothing.
    result = stress_test({"UNKNOWNX": 10}, _PRICES)
    assert result.invested_value == 0.0


# --- /risk/stress endpoint ----------------------------------------------


@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_stress_endpoint_requires_auth(client):
    r = await client.get("/risk/stress")
    assert r.status_code == 401


async def test_stress_endpoint_default_empty_book_has_no_exposure(client):
    # Registration seeds a default profile (empty holdings, 0 cash), so a fresh
    # user has nothing at market risk.
    reg = await client.post("/auth/register", json={"email": "s@b.com", "password": "supersecret1"})
    token = reg.json()["access_token"]
    r = await client.get("/risk/stress", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["invested_value"] == 0.0
    assert body["scenarios"] == []
    assert body["resilience"] == "robust"


async def test_stress_endpoint_returns_result_for_a_book(client):
    reg = await client.post("/auth/register", json={"email": "s2@b.com", "password": "supersecret1"})
    token, uid = reg.json()["access_token"], reg.json()["user_id"]
    db = get_client()["vestra_test"]
    # Registration already seeded a default profile; update it with a real book.
    await db.investor_profiles.update_one(
        {"user_id": uid},
        {"$set": {"cash_balance": 50000.0, "holdings": {"RELIANCE": 20, "HDFCBANK": 10}}},
    )
    r = await client.get("/risk/stress", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["invested_value"] > 0
    assert len(body["scenarios"]) == 4
    assert body["resilience"] in ("robust", "moderate", "fragile")
    assert body["worst_case_loss_pct"] >= 0
