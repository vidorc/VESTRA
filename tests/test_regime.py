"""Tests for the Market Regime agent (pure detection + aggregation + endpoint)."""

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.agent.nodes.regime import aggregate_regime, detect_regime
from app.agent.nodes.signal import classify_market_event
from app.data.mongo import get_client, set_client
from app.main import app
from app.models.schemas import MarketEvent, ResearchContext


def _event(move: float, news: str = "update") -> MarketEvent:
    return MarketEvent(ticker="RELIANCE", price_change_percent=move, breaking_news_summary=news)


# --- detect_regime (single event) ---------------------------------------

def test_crisis_on_critical_large_drop():
    ev = _event(-16.0, "market collapse")
    r = detect_regime(ev, classify_market_event(ev))
    assert r.regime == "crisis"


def test_high_volatility_on_large_move():
    ev = _event(7.0)
    r = detect_regime(ev, classify_market_event(ev))
    assert r.regime == "high_volatility"


def test_bear_on_moderate_drop():
    ev = _event(-3.0)
    r = detect_regime(ev, classify_market_event(ev))
    assert r.regime == "bear"


def test_bull_on_moderate_rise():
    ev = _event(3.0)
    r = detect_regime(ev, classify_market_event(ev))
    assert r.regime == "bull"


def test_sideways_on_small_move():
    ev = _event(0.5)
    r = detect_regime(ev, classify_market_event(ev))
    assert r.regime == "sideways"


def test_sentiment_can_tip_direction():
    ev = _event(0.0)
    research = ResearchContext(sentiment="bearish")
    r = detect_regime(ev, classify_market_event(ev), research)
    assert r.regime == "bear"


# --- aggregate_regime (many events) --------------------------------------

def test_aggregate_empty_is_sideways():
    r = aggregate_regime([])
    assert r.regime == "sideways"
    assert r.confidence < 0.5


def test_aggregate_crisis_on_worst_move():
    r = aggregate_regime(
        [{"price_change_percent": -12.0}, {"price_change_percent": 1.0}]
    )
    assert r.regime == "crisis"


def test_aggregate_bear_on_negative_average():
    r = aggregate_regime(
        [{"price_change_percent": -2.0}, {"price_change_percent": -3.0}]
    )
    assert r.regime == "bear"


def test_aggregate_bull_on_positive_average():
    r = aggregate_regime(
        [{"price_change_percent": 2.0}, {"price_change_percent": 3.0}]
    )
    assert r.regime == "bull"


# --- endpoint ------------------------------------------------------------

@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_regime_endpoint_requires_auth(client):
    r = await client.get("/market/regime")
    assert r.status_code == 401


async def test_regime_endpoint_returns_regime(client):
    reg = await client.post(
        "/auth/register", json={"email": "r@b.com", "password": "supersecret1"}
    )
    token = reg.json()["access_token"]
    db = get_client()["vestra_test"]
    await db.market_events.insert_many(
        [
            {"ticker": "RELIANCE", "price_change_percent": -12.0},
            {"ticker": "INFY", "price_change_percent": 1.0},
        ]
    )
    r = await client.get("/market/regime", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["regime"] in ("bull", "bear", "sideways", "high_volatility", "crisis")
    assert 0.0 <= body["confidence"] <= 1.0
