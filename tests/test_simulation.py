"""Tests for the Scenario Simulation agent (pure simulate + endpoint)."""

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.agent.nodes.simulation import simulate
from app.data.mongo import get_client, set_client
from app.main import app
from app.models.schemas import MarketRegime, RiskAssessment, TradeDecision

_PRICE = 1450.0


def _buy(q=10):
    return TradeDecision(action="BUY", ticker="RELIANCE", quantity=q, reasoning="x")


def _sell(q=10):
    return TradeDecision(action="SELL", ticker="RELIANCE", quantity=q, reasoning="x")


def test_hold_produces_empty_simulation():
    hold = TradeDecision(action="HOLD", ticker="RELIANCE", quantity=0, reasoning="x")
    r = simulate(hold, _PRICE)
    assert r.scenarios == []
    assert r.risk_score == 0.0


def test_scenarios_are_ordered_best_to_worst():
    r = simulate(_buy(), _PRICE, MarketRegime(regime="bull"))
    rets = [s.expected_return_pct for s in r.scenarios]
    assert rets == sorted(rets, reverse=True)
    assert [s.name for s in r.scenarios] == ["best", "base", "worst"]


def test_probabilities_sum_to_one():
    r = simulate(_buy(), _PRICE, MarketRegime(regime="sideways"))
    assert abs(sum(s.probability for s in r.scenarios) - 1.0) < 1e-9


def test_crisis_is_riskier_than_bull():
    bull = simulate(_buy(), _PRICE, MarketRegime(regime="bull"))
    crisis = simulate(_buy(), _PRICE, MarketRegime(regime="crisis"))
    assert crisis.risk_score > bull.risk_score
    assert crisis.expected_drawdown_pct > bull.expected_drawdown_pct


def test_high_concentration_raises_risk_score():
    base = simulate(_buy(), _PRICE, MarketRegime(regime="sideways"))
    conc = simulate(
        _buy(),
        _PRICE,
        MarketRegime(regime="sideways"),
        RiskAssessment(concentration_risk="high", cash_available=1, safe_trade_limit=10),
    )
    assert conc.risk_score >= base.risk_score


def test_portfolio_impact_scales_with_notional():
    small = simulate(_buy(1), _PRICE, MarketRegime(regime="bull"))
    big = simulate(_buy(100), _PRICE, MarketRegime(regime="bull"))
    assert abs(big.scenarios[0].portfolio_impact) > abs(small.scenarios[0].portfolio_impact)


def test_risk_score_clamped_unit_interval():
    r = simulate(_buy(), _PRICE, MarketRegime(regime="crisis"))
    assert 0.0 <= r.risk_score <= 1.0


# --- endpoint ------------------------------------------------------------

@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_simulations_endpoint_requires_auth(client):
    r = await client.get("/simulations")
    assert r.status_code == 401


async def test_simulations_endpoint_lists_results(client):
    reg = await client.post(
        "/auth/register", json={"email": "s@b.com", "password": "supersecret1"}
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.simulation_results.insert_one(
        {"user_id": uid, "event_id": "e1", "ts": "2026-01-01", "risk_score": 0.5, "scenarios": []}
    )
    r = await client.get("/simulations", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert len(r.json()["simulations"]) == 1
