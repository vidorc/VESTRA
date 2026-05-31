"""Decision Review service -- periodic "what worked / what failed / why" + timeline.

The master prompt asks for a review loop: *every period, look back over the
decisions the agent made -- which worked, which failed, and why -- and turn that
into a report the investor can read.* This is that report.

It is a deterministic roll-up over the agent's memory (the same ``agent_memories``
the Memory/Learning agents write and the CIO reads). For each ticker it tallies
the track record and writes a plain-English attribution; it lays the decisions out
as a chronological investor timeline ("Jan 10: Bought RELIANCE -- worked"); and it
surfaces a few highlights (best/worst names, current run). No LLM call -- the same
memory always yields the same review, which keeps the trust report auditable.

Outcome vocabulary (set by the Learning node):
* ``completed`` -> the trade worked (capital deployed / de-risked as intended);
* ``loss``      -> the trade failed (execution blocked/errored);
* ``no_action`` -> a HOLD: neither win nor loss, excluded from the win rate;
* missing       -> still pending (executed but not yet classified).
"""

from typing import Any, Dict, List

from app.models.schemas import (
    DecisionReview,
    DecisionReviewEntry,
    TimelineEvent,
)

# Minimum decided trades before a ticker is eligible to be a best/worst highlight.
_HIGHLIGHT_MIN_DECISIONS = 2

_RESULT_TO_STATUS = {
    "completed": "worked",
    "loss": "failed",
    "no_action": "no_action",
}


def _status_of(memory: Dict[str, Any]) -> str:
    """Map a memory's stored outcome to a timeline status."""
    outcome = memory.get("outcome") or {}
    return _RESULT_TO_STATUS.get(outcome.get("result"), "pending")


def _format_action(action: str, quantity: int, ticker: str) -> str:
    verb = {"BUY": "Bought", "SELL": "Sold", "HOLD": "Held"}.get(action, action.title())
    if action == "HOLD" or not quantity:
        return f"{verb} {ticker}"
    return f"{verb} {quantity} {ticker}"


def _ticker_note(ticker: str, worked: int, failed: int, pending: int) -> str:
    """Plain-English attribution for one ticker's record."""
    decided = worked + failed
    if decided == 0:
        return f"{ticker}: no decided trades yet ({pending} pending)."
    if failed == 0:
        return f"{ticker}: {worked}/{decided} worked — a clean record so far."
    if worked == 0:
        return f"{ticker}: {failed}/{decided} went against us — the desk is cautious here."
    rate = round(100 * worked / decided)
    return f"{ticker}: {worked} worked, {failed} failed ({rate}% hit rate)."


def _build_highlights(
    total: int,
    completed: int,
    losses: int,
    entries: List[DecisionReviewEntry],
) -> List[str]:
    highlights: List[str] = []
    decided = completed + losses
    if total == 0:
        return ["No decisions recorded yet — the review fills in as the agent acts."]

    if decided:
        rate = round(100 * completed / decided)
        highlights.append(
            f"{rate}% of decided trades worked ({completed} of {decided})."
        )
    else:
        highlights.append("No trades have resolved yet — all decisions are still pending.")

    eligible = [e for e in entries if (e.worked + e.failed) >= _HIGHLIGHT_MIN_DECISIONS]
    if eligible:
        best = max(eligible, key=lambda e: (e.win_rate, e.worked))
        worst = min(eligible, key=lambda e: (e.win_rate, -e.failed))
        if best.win_rate >= 0.5:
            highlights.append(
                f"Best track record: {best.ticker} at {round(best.win_rate * 100)}% over {best.worked + best.failed} decided."
            )
        if worst.ticker != best.ticker and worst.win_rate < 0.5:
            highlights.append(
                f"Weakest: {worst.ticker} at {round(worst.win_rate * 100)}% — review the thesis."
            )

    if losses and losses >= completed:
        highlights.append("Losses outweigh wins this period — the desk should tighten risk.")
    return highlights


def review_decisions(memories: List[Dict[str, Any]]) -> DecisionReview:
    """Roll up agent memories into a :class:`DecisionReview`. Pure/deterministic.

    ``memories`` is expected newest-first (as the DAL returns it); the timeline is
    re-ordered oldest-first so it reads as a narrative.
    """
    memories = memories or []
    total = len(memories)
    completed = losses = pending = 0
    per_ticker: Dict[str, Dict[str, int]] = {}

    for m in memories:
        status = _status_of(m)
        ticker = (m.get("ticker") or "—").upper()
        bucket = per_ticker.setdefault(
            ticker, {"decisions": 0, "worked": 0, "failed": 0, "pending": 0}
        )
        bucket["decisions"] += 1

        if status == "worked":
            completed += 1
            bucket["worked"] += 1
        elif status == "failed":
            losses += 1
            bucket["failed"] += 1
        elif status == "pending":
            pending += 1
            bucket["pending"] += 1
        # "no_action" (HOLD) counts as a decision but never as worked/failed/pending-trade.

    decided_total = completed + losses
    win_rate = round(completed / decided_total, 4) if decided_total else 0.0

    # Per-ticker entries, busiest first.
    entries: List[DecisionReviewEntry] = []
    for ticker, c in sorted(per_ticker.items(), key=lambda kv: -kv[1]["decisions"]):
        decided = c["worked"] + c["failed"]
        entries.append(
            DecisionReviewEntry(
                ticker=ticker,
                decisions=c["decisions"],
                worked=c["worked"],
                failed=c["failed"],
                pending=c["pending"],
                win_rate=round(c["worked"] / decided, 4) if decided else 0.0,
                note=_ticker_note(ticker, c["worked"], c["failed"], c["pending"]),
            )
        )

    # Timeline, oldest-first so it reads as a story.
    timeline: List[TimelineEvent] = []
    for m in reversed(memories):
        ticker = (m.get("ticker") or "—").upper()
        action = m.get("action") or "HOLD"
        quantity = int(m.get("quantity") or 0)
        status = _status_of(m)
        timeline.append(
            TimelineEvent(
                ts=m.get("ts", ""),
                ticker=ticker,
                action=action,
                quantity=quantity,
                status=status,
                description=_format_action(action, quantity, ticker),
            )
        )

    return DecisionReview(
        total=total,
        completed=completed,
        losses=losses,
        pending=pending,
        win_rate=win_rate,
        by_ticker=entries,
        timeline=timeline,
        highlights=_build_highlights(total, completed, losses, entries),
    )


__all__ = ["review_decisions"]
