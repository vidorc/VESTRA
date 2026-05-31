"""Trust layer -- plain-English explanation + why-not counterfactuals.

Most AI finance tools hand the user a verdict and a number. Vestra's trust layer
turns the *already-computed* reasoning chain into something a non-expert can read:
a one-line summary, the concrete evidence that backed the call (each tagged as
supporting or cautioning), the confidence it carries, and -- crucially -- *why
the two actions we didn't take were rejected* ("Why not BUY? Why not HOLD?").

This module is deterministic and strictly post-hoc. It reads the signal, research,
regime, risk, council, CIO, confidence, and reflection that earlier nodes produced
and narrates them. It never changes the decision or the graph flow, so it can be
attached at the end of a run (and recomputed from a stored trace) without risk.
Keeping it rule-based -- not another LLM call -- makes the trust layer itself
auditable: the same chain always yields the same explanation.
"""

from typing import List, Optional

from app.models.schemas import (
    CIODecision,
    ConfidenceScore,
    CouncilOpinion,
    Evidence,
    Explanation,
    MarketRegime,
    ReflectionResult,
    ResearchContext,
    RiskAssessment,
    SignalAssessment,
    TradeDecision,
    WhyNot,
)

_ACTIONS = ("BUY", "SELL", "HOLD")
_DEFENSIVE_REGIMES = {"bear", "crisis", "high_volatility"}
# A risk-reducing action: SELL trims exposure, HOLD deploys no capital.
_ACTION_VERB = {"BUY": "add exposure", "SELL": "trim the position", "HOLD": "stand pat"}


def _signal_evidence(signal: Optional[SignalAssessment]) -> Optional[Evidence]:
    if signal is None:
        return None
    assets = ", ".join(signal.impacted_assets) if signal.impacted_assets else "the portfolio"
    stance = "cautions" if signal.severity in ("high", "critical") else "neutral"
    return Evidence(
        source="Signal",
        detail=f"A {signal.severity}-severity {signal.event_type} event affecting {assets}.",
        stance=stance,
    )


def _research_evidence(research: Optional[ResearchContext]) -> Optional[Evidence]:
    if research is None:
        return None
    pct = int(round(research.data_completeness * 100))
    stance = {"bullish": "supports", "bearish": "cautions", "neutral": "neutral"}[research.sentiment]
    backing = f"{pct}% data-backed" if pct else "thin data backing"
    return Evidence(
        source="Research",
        detail=f"Market sentiment reads {research.sentiment} ({backing}).",
        stance=stance,
    )


def _regime_evidence(regime: Optional[MarketRegime], action: str) -> Optional[Evidence]:
    if regime is None:
        return None
    defensive = regime.regime in _DEFENSIVE_REGIMES
    # A defensive regime supports de-risking (SELL/HOLD) and cautions adding (BUY).
    if defensive:
        stance = "cautions" if action == "BUY" else "supports"
    else:
        stance = "supports" if action == "BUY" else "neutral"
    return Evidence(
        source="Market regime",
        detail=f"Regime is {regime.regime.replace('_', ' ')} (confidence {regime.confidence:.0%}).",
        stance=stance,
    )


def _risk_evidence(risk: Optional[RiskAssessment], action: str) -> Optional[Evidence]:
    if risk is None:
        return None
    bits = [f"concentration {risk.concentration_risk}"]
    if risk.liquidity_pressure != "low":
        bits.append(f"{risk.liquidity_pressure} liquidity pressure")
    pressured = risk.concentration_risk == "high" or risk.liquidity_pressure == "high"
    # High risk cautions adding capital, supports holding/trimming.
    if pressured:
        stance = "cautions" if action == "BUY" else "supports"
    else:
        stance = "neutral"
    return Evidence(
        source="Risk",
        detail=f"Risk desk: {', '.join(bits)}; safe limit {risk.safe_trade_limit} units.",
        stance=stance,
    )


def _council_evidence(council: Optional[CouncilOpinion], action: str) -> Optional[Evidence]:
    if council is None:
        return None
    agree = council.consensus_action == action
    return Evidence(
        source="Council",
        detail=f"{council.rationale} Dissent {council.dissent:.0%}.",
        stance="supports" if agree else "cautions",
    )


def _cio_evidence(cio: Optional[CIODecision]) -> Optional[Evidence]:
    if cio is None:
        return None
    if cio.vetoed:
        stance = "cautions"
    elif cio.overrode:
        stance = "cautions"
    else:
        stance = "supports"
    return Evidence(source="CIO", detail=cio.rationale, stance=stance)


def _gather_evidence(
    action: str,
    signal: Optional[SignalAssessment],
    research: Optional[ResearchContext],
    regime: Optional[MarketRegime],
    risk: Optional[RiskAssessment],
    council: Optional[CouncilOpinion],
    cio: Optional[CIODecision],
) -> List[Evidence]:
    candidates = [
        _signal_evidence(signal),
        _research_evidence(research),
        _regime_evidence(regime, action),
        _risk_evidence(risk, action),
        _council_evidence(council, action),
        _cio_evidence(cio),
    ]
    return [e for e in candidates if e is not None]


def _why_not_buy(
    chosen: str,
    confidence: Optional[ConfidenceScore],
    council: Optional[CouncilOpinion],
    risk: Optional[RiskAssessment],
    regime: Optional[MarketRegime],
    cio: Optional[CIODecision],
) -> str:
    if cio is not None and cio.vetoed:
        return "Conviction was below the bar to deploy capital, so adding was off the table."
    if cio is not None and cio.overrode:
        return "The investment committee would not endorse adding here, so a buy was declined."
    if council is not None and council.consensus_action != "BUY":
        return f"The strategy desk did not back buying ({council.rationale})."
    if risk is not None and (risk.concentration_risk == "high" or risk.liquidity_pressure == "high"):
        return "Risk limits (concentration / liquidity) ruled out taking on more exposure."
    if regime is not None and regime.regime in _DEFENSIVE_REGIMES:
        return f"A {regime.regime.replace('_', ' ')} regime is no backdrop for adding risk."
    if confidence is not None and confidence.overall < 0.6:
        return f"Confidence ({confidence.overall:.0%}) was too modest to justify new capital."
    return "Nothing in the read argued for committing fresh capital right now."


def _why_not_sell(
    chosen: str,
    signal: Optional[SignalAssessment],
    research: Optional[ResearchContext],
    risk: Optional[RiskAssessment],
) -> str:
    if research is not None and research.sentiment == "bullish":
        return "Sentiment is constructive, so trimming would have left upside on the table."
    if signal is not None and signal.severity in ("low", "medium"):
        return "The catalyst wasn't severe enough to warrant cutting the position."
    if risk is not None and risk.concentration_risk == "low":
        return "Exposure is already well-contained, so there was no risk reason to sell."
    return "No risk trigger or broken thesis called for reducing the position."


def _why_not_hold(
    chosen: str,
    signal: Optional[SignalAssessment],
    confidence: Optional[ConfidenceScore],
    council: Optional[CouncilOpinion],
) -> str:
    verb = _ACTION_VERB.get(chosen, "act")
    if signal is not None and signal.severity in ("high", "critical"):
        return f"The catalyst was material enough that sitting still was the wrong call; better to {verb}."
    if council is not None and council.consensus_action == chosen:
        return f"The desk's consensus was to {verb}, not to wait."
    if confidence is not None and confidence.overall >= 0.6:
        return f"Conviction ({confidence.overall:.0%}) was high enough to {verb} rather than wait."
    return f"The evidence pointed clearly enough to {verb} that holding added no value."


def _build_summary(
    action: str,
    decision: TradeDecision,
    confidence: Optional[ConfidenceScore],
    evidence: List[Evidence],
) -> str:
    conf = f"{confidence.overall:.0%} confidence" if confidence is not None else "the available read"
    supports = sum(1 for e in evidence if e.stance == "supports")
    cautions = sum(1 for e in evidence if e.stance == "cautions")
    if action == "HOLD":
        head = f"Holding {decision.ticker} on {conf}"
    else:
        head = f"{action.title()}ing {decision.quantity} {decision.ticker} on {conf}"
    return f"{head}: {supports} signal(s) in favour, {cautions} urging caution."


def explain_decision(
    decision: TradeDecision,
    *,
    confidence: Optional[ConfidenceScore] = None,
    signal: Optional[SignalAssessment] = None,
    research: Optional[ResearchContext] = None,
    regime: Optional[MarketRegime] = None,
    risk: Optional[RiskAssessment] = None,
    council: Optional[CouncilOpinion] = None,
    cio: Optional[CIODecision] = None,
    reflection: Optional[ReflectionResult] = None,
) -> Explanation:
    """Narrate a finished decision into a trust-layer :class:`Explanation`.

    Pure and deterministic: it reads already-computed state and produces evidence,
    a summary, and ``why_not`` reasons for the two actions that were not chosen.
    """
    action = decision.action
    evidence = _gather_evidence(action, signal, research, regime, risk, council, cio)

    # Reflection's acknowledged blind spots become explicit caution evidence so the
    # trust panel never hides what the system knew it was missing.
    if reflection is not None and reflection.missing_data:
        evidence.append(
            Evidence(
                source="Reflection",
                detail="Acknowledged gaps: " + "; ".join(reflection.missing_data) + ".",
                stance="cautions",
            )
        )

    why_not: List[WhyNot] = []
    for alt in _ACTIONS:
        if alt == action:
            continue
        if alt == "BUY":
            reason = _why_not_buy(action, confidence, council, risk, regime, cio)
        elif alt == "SELL":
            reason = _why_not_sell(action, signal, research, risk)
        else:
            reason = _why_not_hold(action, signal, confidence, council)
        why_not.append(WhyNot(action=alt, reason=reason))

    return Explanation(
        action=action,
        summary=_build_summary(action, decision, confidence, evidence),
        confidence=confidence.overall if confidence is not None else 0.0,
        evidence=evidence,
        why_not=why_not,
    )


__all__ = ["explain_decision"]
