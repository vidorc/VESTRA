"""Reflection agent node.

Challenges the strategy decision *after* it is made and *before* validation/
approval. This is the system's self-critique layer: it asks whether the
recommendation is logical, what it assumed, what data is missing, and whether a
better alternative exists -- producing a structured
:class:`~app.models.schemas.ReflectionResult`.

The reflection ``verdict`` ("sound" / "acceptable" / "questionable") feeds the
confidence node, which lowers confidence for questionable decisions. Like the
other LLM nodes, this never raises: on any LLM/parse failure it returns a
conservative "acceptable" verdict so the pipeline proceeds (and the missing
self-critique is reflected in lower data completeness elsewhere).
"""

from typing import List, Optional

from app.agent.llm import ainvoke_text, extract_json_object
from app.models.schemas import (
    MarketEvent,
    ReflectionResult,
    ResearchContext,
    RiskAssessment,
    SignalAssessment,
    TradeDecision,
)

_VALID_VERDICT = {"sound", "acceptable", "questionable"}


def _build_prompt(
    event: MarketEvent,
    signal: SignalAssessment,
    risk: RiskAssessment,
    decision: TradeDecision,
    research: Optional[ResearchContext],
) -> str:
    research_block = (
        f"Sentiment: {research.sentiment}\n"
        f"Sector impact: {research.sector_impact}\n"
        f"Market conditions: {research.market_conditions}\n"
        f"Data completeness: {research.data_completeness}"
        if research
        else "(no research context available)"
    )
    return f"""
You are a risk-aware investment committee member reviewing a proposed trade for
an Indian retail investor. Critically challenge the recommendation. Return ONLY
a JSON object.

PROPOSED DECISION
Action: {decision.action} {decision.quantity} {decision.ticker}
Reasoning: {decision.reasoning}

CONTEXT
Event: {event.ticker} {event.price_change_percent}% — {event.breaking_news_summary}
Signal: {signal.event_type} / severity {signal.severity}
Risk: concentration {risk.concentration_risk}, cash ₹{risk.cash_available}, safe limit {risk.safe_trade_limit}
Research:
{research_block}

Ask yourself:
- Is this recommendation logical given the data?
- What assumptions does it rest on?
- What data is missing that would change the call?
- Is there a clearly better alternative action?

Return JSON with exactly these keys:
{{
  "is_logical": true | false,
  "assumptions": ["..."],
  "missing_data": ["..."],
  "better_alternative": "short description, or null",
  "verdict": "sound | acceptable | questionable"
}}
"""


async def reflect_on_decision(
    event: MarketEvent,
    signal: SignalAssessment,
    risk: RiskAssessment,
    decision: TradeDecision,
    research: Optional[ResearchContext] = None,
) -> ReflectionResult:
    """Produce a :class:`ReflectionResult` critiquing ``decision``. Never raises."""
    # A HOLD is the conservative default; reflection still runs but a HOLD is
    # inherently low-risk, so treat it as sound when the LLM is unavailable.
    try:
        text = await ainvoke_text(
            _build_prompt(event, signal, risk, decision, research)
        )
        parsed = extract_json_object(text) or {}
    except Exception:
        parsed = {}

    if not parsed:
        return ReflectionResult(
            is_logical=True,
            assumptions=[],
            missing_data=["reflection unavailable"],
            better_alternative=None,
            verdict="sound" if decision.action == "HOLD" else "acceptable",
        )

    verdict = str(parsed.get("verdict", "")).lower().strip()
    if verdict not in _VALID_VERDICT:
        verdict = "acceptable"

    def _as_list(v) -> List[str]:
        if isinstance(v, list):
            return [str(x) for x in v]
        if v:
            return [str(v)]
        return []

    alt = parsed.get("better_alternative")
    if isinstance(alt, str) and alt.strip().lower() in {"", "null", "none"}:
        alt = None

    return ReflectionResult(
        is_logical=bool(parsed.get("is_logical", True)),
        assumptions=_as_list(parsed.get("assumptions")),
        missing_data=_as_list(parsed.get("missing_data")),
        better_alternative=str(alt) if alt else None,
        verdict=verdict,
    )


__all__ = ["reflect_on_decision"]
