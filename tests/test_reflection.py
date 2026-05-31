"""Tests for the reflection agent node (LLM mocked via the shared seam)."""

import pytest

from app.agent.nodes.reflection import reflect_on_decision
from app.models.schemas import (
    MarketEvent,
    ResearchContext,
    RiskAssessment,
    SignalAssessment,
    TradeDecision,
)


@pytest.fixture
def ctx():
    event = MarketEvent(
        ticker="RELIANCE", price_change_percent=-12.0, breaking_news_summary="Crude shock"
    )
    signal = SignalAssessment(event_type="company", severity="high", impacted_assets=["RELIANCE"])
    risk = RiskAssessment(
        concentration_risk="high", cash_available=100000.0, safe_trade_limit=10, notes="x"
    )
    decision = TradeDecision(action="SELL", ticker="RELIANCE", quantity=5, reasoning="reduce risk")
    research = ResearchContext(sentiment="bearish", data_completeness=0.6)
    return event, signal, risk, decision, research


async def test_reflection_parses_structured_verdict(fake_llm, ctx):
    fake_llm(
        '{"is_logical":true,"assumptions":["crude stays high"],'
        '"missing_data":["volume"],"better_alternative":null,"verdict":"sound"}'
    )
    event, signal, risk, decision, research = ctx
    r = await reflect_on_decision(event, signal, risk, decision, research)
    assert r.verdict == "sound"
    assert r.is_logical is True
    assert r.missing_data == ["volume"]
    assert r.better_alternative is None


async def test_reflection_normalizes_null_alternative_string(fake_llm, ctx):
    fake_llm('{"is_logical":false,"better_alternative":"none","verdict":"questionable"}')
    event, signal, risk, decision, research = ctx
    r = await reflect_on_decision(event, signal, risk, decision, research)
    assert r.verdict == "questionable"
    assert r.is_logical is False
    assert r.better_alternative is None


async def test_reflection_invalid_verdict_defaults_acceptable(fake_llm, ctx):
    fake_llm('{"verdict":"banana"}')
    event, signal, risk, decision, research = ctx
    r = await reflect_on_decision(event, signal, risk, decision, research)
    assert r.verdict == "acceptable"


async def test_reflection_llm_failure_returns_safe_default(fake_llm, ctx):
    fake_llm(raises=True)
    event, signal, risk, decision, research = ctx
    r = await reflect_on_decision(event, signal, risk, decision, research)
    # Non-HOLD with no LLM -> conservative "acceptable", never raises.
    assert r.verdict == "acceptable"
    assert "reflection unavailable" in r.missing_data


async def test_reflection_hold_is_sound_without_llm(fake_llm, ctx):
    fake_llm(raises=True)
    event, signal, risk, _, research = ctx
    hold = TradeDecision(action="HOLD", ticker="RELIANCE", quantity=0, reasoning="hold")
    r = await reflect_on_decision(event, signal, risk, hold, research)
    assert r.verdict == "sound"
