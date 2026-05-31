"""Multi-strategy council node (Phase 5).

An institutional desk doesn't bet on one analyst -- it convenes seats with
different mandates and weighs the room. This node runs four deterministic
strategy "seats", each voting an action on the analyst's proposed trade given the
market regime and risk. Their plurality vote is the ``consensus_action`` and the
fraction disagreeing with it is ``dissent`` -- a measure of how split the desk is,
which the CIO uses to gauge conviction.

Rule-based (no LLM) so the council is reproducible and auditable: the same inputs
always seat the same votes.
"""

from collections import Counter

from app.models.schemas import (
    CouncilOpinion,
    CouncilView,
    MarketRegime,
    RiskAssessment,
    SignalAssessment,
    TradeDecision,
)

# Regimes where defensive seats turn cautious regardless of the analyst view.
_DEFENSIVE_REGIMES = {"bear", "crisis", "high_volatility"}
_BULLISH_REGIMES = {"bull"}


def _momentum_seat(decision: TradeDecision, regime: MarketRegime) -> CouncilView:
    """Trend-follower: trades with the regime, sits out chop."""
    if regime.regime in _BULLISH_REGIMES:
        action = "BUY" if decision.action != "SELL" else "HOLD"
        return CouncilView(strategy="momentum", action=action, rationale="Bullish trend supports adding.")
    if regime.regime in _DEFENSIVE_REGIMES:
        return CouncilView(strategy="momentum", action="SELL" if decision.action == "SELL" else "HOLD",
                           rationale="Downtrend; no new longs.")
    return CouncilView(strategy="momentum", action="HOLD", rationale="No clear trend.")


def _contrarian_seat(decision: TradeDecision, signal: SignalAssessment, regime: MarketRegime) -> CouncilView:
    """Mean-reverter: leans against severe moves, buys fear, fades euphoria."""
    if regime.regime in _DEFENSIVE_REGIMES and signal.severity in ("high", "critical"):
        return CouncilView(strategy="contrarian", action="BUY",
                           rationale="Capitulation; fade the panic.")
    if regime.regime in _BULLISH_REGIMES:
        return CouncilView(strategy="contrarian", action="HOLD", rationale="Euphoria; avoid chasing.")
    return CouncilView(strategy="contrarian", action=decision.action, rationale="No edge; defer to analyst.")


def _risk_averse_seat(decision: TradeDecision, risk: RiskAssessment) -> CouncilView:
    """Capital-preservation seat: vetoes risk when pressure or concentration is high."""
    if risk.liquidity_pressure == "high" or risk.concentration_risk == "high":
        return CouncilView(strategy="risk_averse", action="HOLD",
                           rationale="High liquidity/concentration risk; preserve capital.")
    if decision.action == "BUY" and risk.liquidity_pressure == "medium":
        return CouncilView(strategy="risk_averse", action="HOLD", rationale="Moderate pressure; no new exposure.")
    return CouncilView(strategy="risk_averse", action=decision.action, rationale="Risk within tolerance.")


def _macro_seat(signal: SignalAssessment, regime: MarketRegime) -> CouncilView:
    """Top-down seat: defensive in stressed regimes, constructive otherwise."""
    if regime.regime == "crisis":
        return CouncilView(strategy="macro", action="SELL", rationale="Crisis regime; de-risk.")
    if regime.regime in _DEFENSIVE_REGIMES:
        return CouncilView(strategy="macro", action="HOLD", rationale="Defensive macro backdrop.")
    return CouncilView(strategy="macro", action="BUY" if regime.regime == "bull" else "HOLD",
                       rationale="Supportive macro backdrop.")


def convene_council(
    decision: TradeDecision,
    signal: SignalAssessment,
    risk: RiskAssessment,
    regime: MarketRegime,
) -> CouncilOpinion:
    """Seat four strategy views and aggregate into a consensus + dissent score."""
    views = [
        _momentum_seat(decision, regime),
        _contrarian_seat(decision, signal, regime),
        _risk_averse_seat(decision, risk),
        _macro_seat(signal, regime),
    ]

    counts = Counter(v.action for v in views)
    # Plurality vote; ties break toward the more conservative action (HOLD > SELL > BUY).
    top = max(counts.values())
    tied = [a for a, c in counts.items() if c == top]
    consensus_action = min(tied, key=lambda a: {"HOLD": 0, "SELL": 1, "BUY": 2}[a])

    agreeing = counts[consensus_action]
    dissent = round(1.0 - agreeing / len(views), 2)

    rationale = f"{agreeing}/{len(views)} seats favour {consensus_action}."
    return CouncilOpinion(
        views=views,
        consensus_action=consensus_action,
        dissent=dissent,
        rationale=rationale,
    )


__all__ = ["convene_council"]
