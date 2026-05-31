"""Memory agent service (Phase 5).

The Memory agent gives Vestra institutional recall: before the CIO rules on a
trade, it looks up what the system decided about this ticker before and how those
decisions turned out. A losing streak makes the CIO more cautious; a winning
track record lets it act with normal conviction.

Thin domain layer over the ``agent_memories`` DAL functions. A memory is a past
decision plus an optional outcome (filled in later by the Learning agent once the
trade executes).
"""

from typing import Any, Dict, List, Optional

from app.data.repository import list_agent_memories, save_agent_memory
from app.models.schemas import TradeDecision


async def save_decision_memory(
    user_id: str,
    decision: TradeDecision,
    outcome: Optional[Dict[str, Any]] = None,
) -> str:
    """Record a decision (and optional outcome) the agent made for a ticker."""
    return await save_agent_memory(
        user_id,
        {
            "ticker": decision.ticker.upper(),
            "action": decision.action,
            "quantity": decision.quantity,
            "reasoning": decision.reasoning,
            "outcome": outcome,
        },
    )


async def recall_memory(user_id: str, ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Recall the agent's recent memories for a ticker (newest first)."""
    return await list_agent_memories(user_id, ticker=ticker, limit=limit)


def recent_loss_streak(memory: List[Dict[str, Any]]) -> int:
    """Count consecutive recent losses at the head of a (newest-first) memory list.

    A memory counts as a loss when its outcome marks ``result == "loss"``. Used by
    the CIO to downsize after a losing run on a ticker.
    """
    streak = 0
    for m in memory or []:
        outcome = m.get("outcome") or {}
        if outcome.get("result") == "loss":
            streak += 1
        else:
            break
    return streak


__all__ = ["save_decision_memory", "recall_memory", "recent_loss_streak"]
