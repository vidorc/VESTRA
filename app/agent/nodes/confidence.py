"""Confidence agent node.

Computes, rule-based (no LLM), how much the system should trust a decision
*before* it reaches validation/approval. It aggregates three signals into a
:class:`~app.models.schemas.ConfidenceScore`:

* **decision_confidence** -- driven by the reflection verdict and logic flag.
* **risk_confidence** -- driven by portfolio concentration and cash adequacy.
* **data_completeness** -- carried through from the research node (how much real
  data backed the analysis).

``overall`` is a weighted blend. Keeping this deterministic (rather than another
LLM call) makes it cheap, fully testable, and reproducible -- the same inputs
always yield the same score, which matters for an auditable fintech decision and
for the ``auto_below_threshold`` approval policy that gates on it.
"""

from typing import Optional

from app.models.schemas import (
    ConfidenceScore,
    ReflectionResult,
    ResearchContext,
    RiskAssessment,
    SignalAssessment,
    TradeDecision,
)

# Reflection verdict -> base decision confidence.
_VERDICT_CONFIDENCE = {"sound": 0.9, "acceptable": 0.7, "questionable": 0.4}
# Concentration level -> base risk confidence (lower concentration == safer).
_CONCENTRATION_CONFIDENCE = {"low": 0.9, "medium": 0.7, "high": 0.4}


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, round(x, 2)))


def compute_confidence(
    decision: TradeDecision,
    risk: RiskAssessment,
    signal: SignalAssessment,
    reflection: Optional[ReflectionResult] = None,
    research: Optional[ResearchContext] = None,
) -> ConfidenceScore:
    """Aggregate upstream signals into a :class:`ConfidenceScore`. Pure/deterministic."""

    # --- decision confidence ---------------------------------------------
    if reflection is not None:
        decision_conf = _VERDICT_CONFIDENCE.get(reflection.verdict, 0.6)
        if not reflection.is_logical:
            decision_conf -= 0.25
        # Each piece of acknowledged missing data chips away at confidence.
        decision_conf -= 0.05 * len(reflection.missing_data)
        # A flagged better alternative means the chosen action is less certain.
        if reflection.better_alternative:
            decision_conf -= 0.1
    else:
        decision_conf = 0.6  # no reflection available -> neutral-low

    # A HOLD carries no execution risk, so floor its decision confidence higher.
    if decision.action == "HOLD":
        decision_conf = max(decision_conf, 0.7)

    # --- risk confidence -------------------------------------------------
    risk_conf = _CONCENTRATION_CONFIDENCE.get(risk.concentration_risk, 0.6)
    # Critical-severity events inject uncertainty into any risk read.
    if signal.severity == "critical":
        risk_conf -= 0.2
    elif signal.severity == "high":
        risk_conf -= 0.1
    # Cash adequacy: a BUY that would consume most available cash is riskier.
    if decision.action == "BUY" and risk.cash_available > 0:
        # We don't have price here; use quantity vs. safe limit as a proxy.
        if risk.safe_trade_limit and decision.quantity >= risk.safe_trade_limit:
            risk_conf -= 0.1

    # --- data completeness ----------------------------------------------
    data_completeness = research.data_completeness if research else 0.0

    decision_conf = _clamp(decision_conf)
    risk_conf = _clamp(risk_conf)
    data_completeness = _clamp(data_completeness)

    # Weighted blend: the decision itself matters most, then risk, then data.
    overall = _clamp(
        0.45 * decision_conf + 0.35 * risk_conf + 0.20 * data_completeness
    )

    return ConfidenceScore(
        decision_confidence=decision_conf,
        risk_confidence=risk_conf,
        data_completeness=data_completeness,
        overall=overall,
    )


__all__ = ["compute_confidence"]
