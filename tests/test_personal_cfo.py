"""Tests for the Personal CFO layer: liquidity_pressure wired into the risk
node (biasing toward capital preservation) and surfaced in the strategy prompt.

The deterministic goals service (liquidity_need / liquidity_pressure) is already
covered in test_digital_twin_goals.py. These tests cover the *wiring*: the risk
node loading goals + twin, computing pressure, and tightening the safe trade
limit; and the strategy prompt exposing it to the LLM.
"""

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.agent.nodes.risk import assess_portfolio_risk
from app.agent.nodes.strategy import generate_trade_strategy
from app.data.mongo import set_client
from app.models.schemas import MarketEvent, RiskAssessment, SignalAssessment


@pytest.fixture
async def mongo():
    client = AsyncMongoMockClient()
    set_client(client)
    yield client["vestra_test"]
    set_client(None)


async def _seed_profile(db, user_id="u1", cash=100_000.0, holdings=None):
    await db.investor_profiles.insert_one(
        {
            "user_id": user_id,
            "risk_tolerance": "aggressive",  # high base safe_trade_limit (20)
            "cash_balance": cash,
            "holdings": holdings or {"RELIANCE": 10},
            "target_allocation": {},
        }
    )


# --- risk node wiring ----------------------------------------------------

async def test_risk_low_pressure_when_no_goals(mongo):
    await _seed_profile(mongo)
    risk = await assess_portfolio_risk("u1")
    assert risk.liquidity_pressure == "low"
    # Aggressive base limit preserved when there is no liquidity pressure.
    assert risk.safe_trade_limit == 20


async def test_high_liquidity_pressure_tightens_safe_trade_limit(mongo):
    await _seed_profile(mongo, cash=10_000.0, holdings={"RELIANCE": 1})
    # A large near-term goal relative to a small portfolio -> high pressure.
    await mongo.goals.insert_one(
        {
            "user_id": "u1",
            "goal_id": "g1",
            "type": "education",
            "name": "tuition",
            "target_amount": 1_000_000,
            "current_amount": 0,
            "target_date": "2026-09-01",
            "priority": "high",
        }
    )
    risk = await assess_portfolio_risk("u1")
    assert risk.liquidity_pressure == "high"
    # Preservation bias: the aggressive base limit (20) is cut.
    assert risk.safe_trade_limit < 20
    assert "liquidity" in (risk.notes or "").lower()


async def test_risk_tolerates_missing_twin_and_goals(mongo):
    """No goals collection entries + no twin must not raise; defaults to low."""
    await _seed_profile(mongo)
    risk = await assess_portfolio_risk("u1")
    assert isinstance(risk, RiskAssessment)
    assert risk.liquidity_pressure == "low"


# --- strategy prompt surfacing -------------------------------------------

class _CapturingLLM:
    """Captures the prompt it is invoked with, returns a fixed HOLD decision."""

    def __init__(self):
        self.prompt = None

    async def ainvoke(self, prompt):
        self.prompt = prompt

        class _Msg:
            content = '{"action":"HOLD","ticker":"RELIANCE","quantity":0,"reasoning":"x"}'

        return _Msg()


async def test_strategy_prompt_includes_liquidity_pressure():
    from app.agent import llm as llm_mod

    cap = _CapturingLLM()
    llm_mod.set_llm(cap)
    try:
        event = MarketEvent(ticker="RELIANCE", price_change_percent=-5.0, breaking_news_summary="x")
        signal = SignalAssessment(event_type="company", severity="medium", impacted_assets=["RELIANCE"])
        risk = RiskAssessment(
            concentration_risk="low",
            cash_available=50_000.0,
            safe_trade_limit=5,
            notes="x",
            liquidity_pressure="high",
        )
        await generate_trade_strategy(event, signal, risk)
        assert "liquidity" in cap.prompt.lower()
        assert "high" in cap.prompt.lower()
    finally:
        llm_mod.set_llm(None)
