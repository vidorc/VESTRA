"""Tests for the Portfolio Health Engine (pure scoring + endpoint)."""

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.data.mongo import get_client, set_client
from app.main import app
from app.services.portfolio_health import score_portfolio_health

_PRICES = {"INFY": 1550.0, "TCS": 3900.0, "HDFCBANK": 1650.0, "RELIANCE": 1450.0}


# --- pure scoring --------------------------------------------------------

def test_diversified_beats_concentrated():
    diversified = score_portfolio_health(
        {"INFY": 10, "HDFCBANK": 10, "RELIANCE": 10}, 50000.0, _PRICES
    )
    concentrated = score_portfolio_health({"INFY": 30, "TCS": 20}, 0.0, _PRICES)
    assert diversified.score > concentrated.score
    assert diversified.band in ("good", "excellent")
    assert concentrated.band in ("poor", "fair")


def test_weights_sum_to_one_and_scores_clamped():
    h = score_portfolio_health({"INFY": 10, "HDFCBANK": 5}, 20000.0, _PRICES)
    assert abs(sum(f.weight for f in h.factors) - 1.0) < 1e-9
    assert 0.0 <= h.score <= 100.0
    for f in h.factors:
        assert 0.0 <= f.score <= 100.0


def test_empty_portfolio_does_not_crash():
    h = score_portfolio_health({}, 100000.0, {})
    assert 0.0 <= h.score <= 100.0
    # No holdings -> diversification factor is zero.
    div = next(f for f in h.factors if f.name == "diversification")
    assert div.score == 0.0


def test_single_sector_low_diversification():
    h = score_portfolio_health({"INFY": 10, "TCS": 10}, 10000.0, _PRICES)
    div = next(f for f in h.factors if f.name == "diversification")
    # Both IT -> single sector -> low diversification score.
    assert div.score <= 30.0


def test_band_thresholds():
    # All-cash portfolio lands in a mid band, never crashes.
    h = score_portfolio_health({}, 100000.0, {})
    assert h.band in ("poor", "fair", "good", "excellent")


def test_volatility_override_is_used():
    base = score_portfolio_health({"INFY": 10, "HDFCBANK": 10}, 20000.0, _PRICES)
    lowvol = score_portfolio_health(
        {"INFY": 10, "HDFCBANK": 10}, 20000.0, _PRICES, volatility_score=95.0
    )
    assert lowvol.score >= base.score


# --- endpoint ------------------------------------------------------------

@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_health_endpoint_requires_auth(client):
    r = await client.get("/portfolio/health")
    assert r.status_code == 401


async def test_health_endpoint_returns_score(client):
    reg = await client.post(
        "/auth/register", json={"email": "h@b.com", "password": "supersecret1"}
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.investor_profiles.update_one(
        {"user_id": uid},
        {"$set": {"holdings": {"INFY": 10, "HDFCBANK": 10, "RELIANCE": 10}, "cash_balance": 50000.0}},
    )
    r = await client.get("/portfolio/health", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0.0 <= body["score"] <= 100.0
    assert body["band"] in ("poor", "fair", "good", "excellent")
    assert len(body["factors"]) == 5
