"""Tests for the trust-layer explanation service (rule-based, deterministic — no LLM)."""

from app.models.schemas import (
    CIODecision,
    ConfidenceScore,
    CouncilOpinion,
    CouncilView,
    Explanation,
    MarketRegime,
    ReflectionResult,
    ResearchContext,
    RiskAssessment,
    SignalAssessment,
    TradeDecision,
)
from app.services.explanation import explain_decision


def _buy(qty=5):
    return TradeDecision(action="BUY", ticker="RELIANCE", quantity=qty, reasoning="add")


def _sell(qty=3):
    return TradeDecision(action="SELL", ticker="RELIANCE", quantity=qty, reasoning="trim")


def _hold():
    return TradeDecision(action="HOLD", ticker="RELIANCE", quantity=0, reasoning="wait")


def _sig(severity="medium", event="company"):
    return SignalAssessment(event_type=event, severity=severity, impacted_assets=["RELIANCE"])


def _risk(conc="low", liq="low"):
    return RiskAssessment(
        concentration_risk=conc, cash_available=100000.0, safe_trade_limit=10,
        notes="x", liquidity_pressure=liq,
    )


def _council(action="BUY", dissent=0.25):
    return CouncilOpinion(
        views=[CouncilView(strategy="momentum", action=action, rationale="r")],
        consensus_action=action, dissent=dissent, rationale=f"3/4 favour {action}.",
    )


def _conf(overall=0.8):
    return ConfidenceScore(
        decision_confidence=overall, risk_confidence=overall,
        data_completeness=overall, overall=overall,
    )


# --- structure ----------------------------------------------------------


def test_returns_explanation_with_two_why_not_for_the_unchosen_actions():
    exp = explain_decision(_buy(), confidence=_conf())
    assert isinstance(exp, Explanation)
    assert exp.action == "BUY"
    # Exactly the two actions that were NOT chosen, never the chosen one.
    assert {w.action for w in exp.why_not} == {"SELL", "HOLD"}
    assert len(exp.why_not) == 2
    assert all(w.reason for w in exp.why_not)  # every counterfactual has prose


def test_why_not_covers_each_alternative_for_a_sell():
    exp = explain_decision(_sell(), confidence=_conf())
    assert {w.action for w in exp.why_not} == {"BUY", "HOLD"}


def test_why_not_covers_each_alternative_for_a_hold():
    exp = explain_decision(_hold(), confidence=_conf())
    assert {w.action for w in exp.why_not} == {"BUY", "SELL"}


def test_works_with_no_optional_inputs():
    exp = explain_decision(_buy())
    assert isinstance(exp, Explanation)
    assert exp.confidence == 0.0
    assert exp.evidence == []  # nothing to draw on
    assert len(exp.why_not) == 2  # counterfactuals still produced


# --- evidence assembly --------------------------------------------------


def test_each_source_contributes_one_evidence_row():
    exp = explain_decision(
        _buy(),
        confidence=_conf(),
        signal=_sig("high"),
        research=ResearchContext(sentiment="bullish", data_completeness=0.8),
        regime=MarketRegime(regime="bull", confidence=0.7),
        risk=_risk("low"),
        council=_council("BUY"),
        cio=CIODecision(final_decision=_buy(), rationale="CIO approved as proposed."),
    )
    sources = {e.source for e in exp.evidence}
    assert {"Signal", "Research", "Market regime", "Risk", "Council", "CIO"} <= sources


def test_bullish_research_supports_and_bearish_cautions():
    bull = explain_decision(_buy(), research=ResearchContext(sentiment="bullish", data_completeness=0.5))
    bear = explain_decision(_buy(), research=ResearchContext(sentiment="bearish", data_completeness=0.5))
    assert any(e.source == "Research" and e.stance == "supports" for e in bull.evidence)
    assert any(e.source == "Research" and e.stance == "cautions" for e in bear.evidence)


def test_council_disagreement_is_a_caution():
    # Council favours SELL but the decision was BUY -> council cautions.
    exp = explain_decision(_buy(), council=_council("SELL"))
    council_ev = [e for e in exp.evidence if e.source == "Council"]
    assert council_ev and council_ev[0].stance == "cautions"


def test_council_agreement_supports():
    exp = explain_decision(_buy(), council=_council("BUY"))
    council_ev = [e for e in exp.evidence if e.source == "Council"]
    assert council_ev and council_ev[0].stance == "supports"


def test_defensive_regime_cautions_a_buy_but_supports_a_sell():
    buy = explain_decision(_buy(), regime=MarketRegime(regime="crisis", confidence=0.9))
    sell = explain_decision(_sell(), regime=MarketRegime(regime="crisis", confidence=0.9))
    assert any(e.source == "Market regime" and e.stance == "cautions" for e in buy.evidence)
    assert any(e.source == "Market regime" and e.stance == "supports" for e in sell.evidence)


def test_high_risk_cautions_a_buy():
    exp = explain_decision(_buy(), risk=_risk(conc="high"))
    risk_ev = [e for e in exp.evidence if e.source == "Risk"]
    assert risk_ev and risk_ev[0].stance == "cautions"


def test_vetoed_cio_is_a_caution():
    cio = CIODecision(final_decision=_hold(), vetoed=True, rationale="CIO veto: confidence below threshold.")
    exp = explain_decision(_hold(), cio=cio)
    cio_ev = [e for e in exp.evidence if e.source == "CIO"]
    assert cio_ev and cio_ev[0].stance == "cautions"


def test_reflection_missing_data_becomes_caution_evidence():
    exp = explain_decision(
        _buy(),
        reflection=ReflectionResult(missing_data=["earnings date", "peer multiples"]),
    )
    refl = [e for e in exp.evidence if e.source == "Reflection"]
    assert refl and refl[0].stance == "cautions"
    assert "earnings date" in refl[0].detail


# --- why-not reasoning --------------------------------------------------


def test_why_not_buy_cites_cio_veto():
    cio = CIODecision(final_decision=_hold(), vetoed=True, rationale="veto")
    exp = explain_decision(_hold(), confidence=_conf(0.3), cio=cio)
    why_buy = next(w for w in exp.why_not if w.action == "BUY")
    assert "capital" in why_buy.reason.lower()


def test_why_not_sell_cites_bullish_sentiment():
    exp = explain_decision(
        _buy(), research=ResearchContext(sentiment="bullish", data_completeness=0.6)
    )
    why_sell = next(w for w in exp.why_not if w.action == "SELL")
    assert "upside" in why_sell.reason.lower() or "constructive" in why_sell.reason.lower()


def test_why_not_hold_cites_material_catalyst():
    exp = explain_decision(_buy(), signal=_sig("critical"), confidence=_conf(0.8))
    why_hold = next(w for w in exp.why_not if w.action == "HOLD")
    assert "sitting still" in why_hold.reason.lower() or "wrong call" in why_hold.reason.lower()


# --- summary ------------------------------------------------------------


def test_summary_mentions_ticker_and_confidence():
    exp = explain_decision(_buy(7), confidence=_conf(0.8))
    assert "RELIANCE" in exp.summary
    assert "80%" in exp.summary
    assert "7" in exp.summary  # quantity surfaced for a real trade


def test_hold_summary_omits_quantity_phrasing():
    exp = explain_decision(_hold(), confidence=_conf(0.7))
    assert "Holding RELIANCE" in exp.summary


def test_determinism_same_inputs_same_explanation():
    args = dict(confidence=_conf(0.8), signal=_sig("high"), council=_council("BUY"))
    a = explain_decision(_buy(), **args)
    b = explain_decision(_buy(), **args)
    assert a.model_dump() == b.model_dump()
