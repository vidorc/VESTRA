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


def memory_analytics(memories: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Roll up a list of agent memories into executive-dashboard analytics.

    Pure/deterministic. Produces overall tallies (total / completed / losses /
    pending), a win rate over *decided* trades only, and a per-ticker breakdown.
    Drives the memory-analytics charts.
    """
    total = len(memories or [])
    completed = losses = pending = 0
    per_ticker: Dict[str, Dict[str, int]] = {}

    for m in memories or []:
        outcome = m.get("outcome") or {}
        result = outcome.get("result")
        if result == "completed":
            completed += 1
        elif result == "loss":
            losses += 1
        else:
            pending += 1

        ticker = (m.get("ticker") or "—").upper()
        bucket = per_ticker.setdefault(ticker, {"total": 0, "completed": 0, "losses": 0})
        bucket["total"] += 1
        if result == "completed":
            bucket["completed"] += 1
        elif result == "loss":
            bucket["losses"] += 1

    decided = completed + losses
    win_rate = round(completed / decided, 4) if decided else 0.0

    by_ticker = [
        {"ticker": t, **counts}
        for t, counts in sorted(per_ticker.items(), key=lambda kv: -kv[1]["total"])
    ]

    return {
        "total": total,
        "completed": completed,
        "losses": losses,
        "pending": pending,
        "win_rate": win_rate,
        "by_ticker": by_ticker,
    }


__all__ = ["save_decision_memory", "recall_memory", "recent_loss_streak", "memory_analytics"]
