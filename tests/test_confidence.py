"""Tests for the confidence agent node (rule-based, deterministic — no LLM)."""

from app.agent.nodes.confidence import compute_confidence
from app.models.schemas import (
    ConfidenceScore,
    ReflectionResult,
    ResearchContext,
    RiskAssessment,
    SignalAssessment,
    TradeDecision,
)


def _sig(severity="medium"):
    return SignalAssessment(event_type="company", severity=severity, impacted_assets=["RELIANCE"])


def _risk(level="low"):
    return RiskAssessment(
        concentration_risk=level, cash_available=100000.0, safe_trade_limit=10, notes="x"
    )


def _sell(qty=3):
    return TradeDecision(action="SELL", ticker="RELIANCE", quantity=qty, reasoning="x")


def test_high_confidence_when_sound_low_risk_full_data():
    conf = compute_confidence(
        _sell(),
        _risk("low"),
        _sig("medium"),
        ReflectionResult(is_logical=True, verdict="sound"),
        ResearchContext(data_completeness=1.0),
    )
    # sound=0.9 decision, low-risk=0.9, data=1.0 -> all high.
    assert conf.decision_confidence == 0.9
    assert conf.risk_confidence == 0.9
    assert conf.data_completeness == 1.0
    # 0.45*0.9 + 0.35*0.9 + 0.20*1.0 = 0.92
    assert conf.overall == 0.92


def test_questionable_verdict_lowers_decision_confidence():
    conf = compute_confidence(
        _sell(),
        _risk("low"),
        _sig("low"),
        ReflectionResult(is_logical=True, verdict="questionable"),
        ResearchContext(data_completeness=0.5),
    )
    assert conf.decision_confidence == 0.4


def test_missing_data_and_illogical_penalize_confidence():
    conf = compute_confidence(
        _sell(),
        _risk("low"),
        _sig("low"),
        ReflectionResult(
            is_logical=False, verdict="sound", missing_data=["a", "b"], better_alternative="HOLD"
        ),
        ResearchContext(data_completeness=0.0),
    )
    # 0.9 - 0.25(illogical) - 0.10(2 missing) - 0.10(alt) = 0.45
    assert conf.decision_confidence == 0.45


def test_critical_severity_lowers_risk_confidence():
    conf = compute_confidence(
        _sell(), _risk("low"), _sig("critical"), ReflectionResult(verdict="sound"), ResearchContext()
    )
    # low-risk 0.9 - 0.2 critical = 0.7
    assert conf.risk_confidence == 0.7


def test_hold_floors_decision_confidence():
    hold = TradeDecision(action="HOLD", ticker="RELIANCE", quantity=0, reasoning="hold")
    conf = compute_confidence(
        hold, _risk("high"), _sig("low"), ReflectionResult(verdict="questionable"), ResearchContext()
    )
    # questionable would be 0.4, but HOLD floors decision confidence at 0.7.
    assert conf.decision_confidence == 0.7


def test_works_without_reflection_or_research():
    conf = compute_confidence(_sell(), _risk("medium"), _sig("low"))
    assert isinstance(conf, ConfidenceScore)
    assert 0.0 <= conf.overall <= 1.0
    assert conf.data_completeness == 0.0  # no research provided


def test_all_scores_clamped_to_unit_interval():
    conf = compute_confidence(
        _sell(99),
        _risk("high"),
        _sig("critical"),
        ReflectionResult(is_logical=False, verdict="questionable", missing_data=["a"] * 10),
        ResearchContext(data_completeness=0.0),
    )
    for v in (conf.decision_confidence, conf.risk_confidence, conf.data_completeness, conf.overall):
        assert 0.0 <= v <= 1.0
