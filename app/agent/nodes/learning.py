"""Learning node (Phase 5) -- closes the institutional feedback loop.

After a trade executes, the Learning agent records the outcome back into the
agent's memory for that ticker. That memory is what the Memory agent recalls and
the CIO weighs on the next decision -- so a losing run on a name makes the desk
progressively more cautious, and a clean record restores normal conviction.

Outcome classification is deliberately simple and deterministic: a successful
execution is recorded as a completed trade; a failed/blocked execution is marked
a loss (capital wasn't deployed as intended). Richer P&L-based outcomes can layer
on later once positions are marked to market.
"""

from typing import Any, Dict

from app.models.schemas import TradeDecision
from app.services.memory import save_decision_memory


def _classify_outcome(execution: Dict[str, Any]) -> Dict[str, Any]:
    """Map a raw execution result into a memory outcome record."""
    status = execution.get("status") if isinstance(execution, dict) else None
    failed = (isinstance(execution, dict) and "error" in execution) or status in ("failed", None)
    return {
        "status": status or "failed",
        "result": "loss" if failed else "completed",
        "detail": execution if isinstance(execution, dict) else {},
    }


async def learn_from_execution(
    user_id: str,
    decision: TradeDecision,
    execution: Dict[str, Any],
) -> None:
    """Record the executed decision + its outcome to memory (best-effort)."""
    try:
        await save_decision_memory(user_id, decision, outcome=_classify_outcome(execution))
    except Exception:
        # Learning must never break the execution path.
        pass


__all__ = ["learn_from_execution"]
