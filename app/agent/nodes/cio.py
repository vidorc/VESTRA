"""CIO node (Phase 5) -- the final decision authority.

In the analyst pipeline the strategy node (LLM) proposes a trade. The CIO is the
institution's last word over that proposal: a deterministic governor that weighs
the proposal against the multi-strategy council, the confidence score, the risk
limits, and the agent's memory of how this ticker played out before. It can:

* **pass through** -- proposal is strong and aligned;
* **override** -- the council consensus opposes the analyst, so defer to the desk
  (conservative: drop to HOLD);
* **veto** -- confidence is too low to act at all (drop to HOLD);
* **downsize** -- clamp to the safe trade limit, and cut size further after a
  recent losing streak on this ticker.

Deterministic by design: an auditable "final authority" must be reproducible.
"""

from typing import Any, Dict, List

from app.models.schemas import (
    CIODecision,
    ConfidenceScore,
    CouncilOpinion,
    RiskAssessment,
    TradeDecision,
)
from app.services.memory import recent_loss_streak

# Below this overall confidence the CIO will not act -- it vetoes to HOLD.
_CONFIDENCE_VETO_THRESHOLD = 0.4
# A losing streak at/above this length triggers position downsizing.
_LOSS_STREAK_TRIGGER = 2
# Each step of the streak (from the trigger) removes this fraction of size.
_LOSS_DOWNSIZE_STEP = 0.25


def _hold(ticker: str, reasoning: str) -> TradeDecision:
    return TradeDecision(action="HOLD", ticker=ticker, quantity=0, reasoning=reasoning)


def cio_review(
    decision: TradeDecision,
    risk: RiskAssessment,
    confidence: ConfidenceScore,
    council: CouncilOpinion,
    memory: List[Dict[str, Any]],
) -> CIODecision:
    """Render the CIO's final, authoritative verdict over the analyst decision."""
    ticker = decision.ticker

    # 1) Confidence veto -- too uncertain to *deploy capital*. A BUY is killed to
    #    HOLD below the threshold; a SELL (risk reduction) is never vetoed.
    if decision.action == "BUY" and confidence.overall < _CONFIDENCE_VETO_THRESHOLD:
        return CIODecision(
            final_decision=_hold(ticker, "CIO veto: confidence below threshold."),
            vetoed=True,
            rationale=f"Overall confidence {confidence.overall:.2f} < {_CONFIDENCE_VETO_THRESHOLD}.",
        )

    # 2) Council override -- the desk consensus opposes deploying capital. We only
    #    override a BUY (don't buy into a trade the desk won't endorse); a SELL is
    #    risk reduction and is never blocked, even against a HOLD consensus.
    if decision.action == "BUY" and council.consensus_action != "BUY":
        return CIODecision(
            final_decision=_hold(ticker, "CIO defers to council: no consensus to deploy capital."),
            overrode=True,
            rationale=council.rationale,
        )

    # 3) Pass through, but governed: clamp to the safe trade limit ...
    quantity = decision.quantity
    notes = []
    if risk.safe_trade_limit and quantity > risk.safe_trade_limit:
        quantity = risk.safe_trade_limit
        notes.append(f"clamped to safe limit {risk.safe_trade_limit}")

    # ... and downsize after a recent losing streak on this ticker.
    streak = recent_loss_streak(memory)
    if streak >= _LOSS_STREAK_TRIGGER:
        factor = max(0.25, 1.0 - _LOSS_DOWNSIZE_STEP * streak)
        quantity = max(1, int(quantity * factor))
        notes.append(f"downsized after {streak} recent losses")

    final = TradeDecision(
        action=decision.action,
        ticker=ticker,
        quantity=quantity,
        reasoning=decision.reasoning,
    )
    rationale = "CIO approved" + (f" ({'; '.join(notes)})" if notes else " as proposed") + "."
    return CIODecision(final_decision=final, rationale=rationale)


__all__ = ["cio_review"]
