"""Market Regime agent node.

Classifies the prevailing market regime — ``bull`` / ``bear`` / ``sideways`` /
``high_volatility`` / ``crisis`` — so downstream agents (and the dashboard) can
adapt. Like the confidence node it is **rule-based and deterministic**: the same
event/signal/research always yields the same regime, which keeps it cheap,
reproducible, and testable. (LLM refinement is a possible future enhancement;
kept out for now to preserve determinism.)

Sits between research and risk in the pipeline
(``signal → research → regime → risk``) so the regime read can inform later
phases. It also backs the ``GET /market/regime`` endpoint, which aggregates the
most recent market events into a current market-wide read.
"""

from typing import List, Optional

from app.models.schemas import (
    MarketEvent,
    MarketRegime,
    ResearchContext,
    SignalAssessment,
)


def detect_regime(
    event: MarketEvent,
    signal: SignalAssessment,
    research: Optional[ResearchContext] = None,
) -> MarketRegime:
    """Classify the regime implied by a single event. Pure/deterministic.

    A single event is only a sample of the broader market, so this is a directional
    read rather than a definitive market state; :func:`aggregate_regime` combines
    several events for a steadier signal.
    """
    move = event.price_change_percent
    abs_move = abs(move)
    sentiment = research.sentiment if research else None

    # Crisis: a critical-severity event with a large adverse move.
    if signal.severity == "critical" and move <= -10:
        return MarketRegime(
            regime="crisis",
            confidence=0.85,
            rationale=f"Critical event with a {move:.1f}% move signals crisis conditions.",
        )

    # High volatility: large move in either direction, or high severity.
    if abs_move >= 6 or signal.severity in ("high", "critical"):
        return MarketRegime(
            regime="high_volatility",
            confidence=0.7,
            rationale=f"Large/severe move ({move:.1f}%, {signal.severity}) indicates elevated volatility.",
        )

    # Directional reads for moderate moves, corroborated by sentiment.
    if move <= -2 or sentiment == "bearish":
        return MarketRegime(
            regime="bear",
            confidence=0.6,
            rationale=f"Negative move ({move:.1f}%)" + (" with bearish sentiment." if sentiment == "bearish" else "."),
        )
    if move >= 2 or sentiment == "bullish":
        return MarketRegime(
            regime="bull",
            confidence=0.6,
            rationale=f"Positive move ({move:.1f}%)" + (" with bullish sentiment." if sentiment == "bullish" else "."),
        )

    return MarketRegime(
        regime="sideways",
        confidence=0.55,
        rationale=f"Small move ({move:.1f}%) with no strong directional signal.",
    )


def aggregate_regime(events: List[dict]) -> MarketRegime:
    """Derive a current market-wide regime from recent market-event docs.

    Each doc carries ``price_change_percent`` (and optionally ``severity``). We
    look at the average move and the worst single move to decide between crisis,
    high-volatility, directional, and sideways regimes. Returns ``sideways`` with
    low confidence when there is no data.
    """
    moves = [e.get("price_change_percent", 0.0) for e in events if "price_change_percent" in e]
    if not moves:
        return MarketRegime(regime="sideways", confidence=0.3, rationale="No recent market events.")

    avg = sum(moves) / len(moves)
    worst = min(moves)
    spread = max(moves) - min(moves)
    n = len(moves)

    if worst <= -10:
        return MarketRegime(
            regime="crisis",
            confidence=0.8,
            rationale=f"Worst recent move {worst:.1f}% across {n} events.",
        )
    if spread >= 8 or any(abs(m) >= 6 for m in moves):
        return MarketRegime(
            regime="high_volatility",
            confidence=0.7,
            rationale=f"Wide move spread ({spread:.1f} pts) across {n} events.",
        )
    if avg <= -1.5:
        return MarketRegime(regime="bear", confidence=0.6, rationale=f"Average move {avg:.1f}% across {n} events.")
    if avg >= 1.5:
        return MarketRegime(regime="bull", confidence=0.6, rationale=f"Average move {avg:.1f}% across {n} events.")
    return MarketRegime(regime="sideways", confidence=0.55, rationale=f"Average move {avg:.1f}% across {n} events.")


__all__ = ["detect_regime", "aggregate_regime"]
