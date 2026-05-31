import json
import re

from app.agent.llm import get_llm, set_llm  # noqa: F401  (set_llm re-exported)
from app.models.schemas import (
    MarketEvent,
    SignalAssessment,
    RiskAssessment,
    TradeDecision
)

# The LLM client/factory now lives in app.agent.llm so all LLM-backed nodes
# share one injectable instance. ``get_llm``/``set_llm`` are re-exported here so
# existing imports (``from app.agent.nodes.strategy import set_llm``) keep working
# and a single injection covers strategy + research + reflection.


def _content_to_text(content) -> str:
    """Normalize a LangChain message ``content`` into a plain string.

    ``content`` may be a string, or a list of content blocks where each block is
    either a string or a dict (e.g. ``{"type": "text", "text": "..."}``). The
    previous code did ``content[0]`` and fed a dict straight into ``json.loads``,
    which raised ``TypeError``.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                parts.append(block.get("text") or block.get("content") or "")
        return "".join(parts)

    return str(content)


def _extract_decision(text: str, ticker: str) -> dict:
    """Parse a trade decision dict from raw LLM text.

    Strips markdown code fences, extracts the first JSON object, and falls back
    to a safe HOLD if no valid JSON is found. Never raises.
    """
    cleaned = text.strip()

    # Strip ```json ... ``` or ``` ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    # Grab the first {...} block (handles leading/trailing prose).
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    candidate = match.group(0) if match else cleaned

    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict) and "action" in parsed:
            return parsed
    except (json.JSONDecodeError, ValueError):
        pass

    return {
        "action": "HOLD",
        "ticker": ticker,
        "quantity": 0,
        "reasoning": "Could not parse a structured decision; defaulting to HOLD.",
    }


async def generate_trade_strategy(
    event: MarketEvent,
    signal: SignalAssessment,
    risk: RiskAssessment
) -> TradeDecision:

    prompt = f"""
You are an AI fiduciary investment advisor for Indian retail investors.

Your job is disciplined portfolio decision making.

MARKET EVENT:
Ticker: {event.ticker}
Move: {event.price_change_percent}%
News: {event.breaking_news_summary}

SIGNAL ANALYSIS:
Event Type: {signal.event_type}
Severity: {signal.severity}
Impacted Assets: {signal.impacted_assets}

RISK PROFILE:
Cash Available: ₹{risk.cash_available}
Concentration Risk: {risk.concentration_risk}
Safe Trade Limit: {risk.safe_trade_limit}
Notes: {risk.notes}

Rules:
- Conservative investors avoid aggressive trades
- Moderate investors reduce risk rationally
- Aggressive investors can take calculated opportunities
- NEVER exceed safe trade limit
- HOLD if uncertainty is high
- Think like a disciplined Indian portfolio manager
- Return ONLY JSON

Format:
{{
    "action": "BUY or SELL or HOLD",
    "ticker": "{event.ticker}",
    "quantity": integer,
    "reasoning": "short explanation"
}}
"""

    response = await get_llm().ainvoke(prompt)

    text = _content_to_text(response.content)
    parsed = _extract_decision(text, event.ticker)

    try:
        return TradeDecision(**parsed)
    except Exception:
        # LLM returned structurally-parseable JSON but with invalid fields
        # (e.g. action outside BUY/SELL/HOLD). Fail safe to HOLD.
        return TradeDecision(
            action="HOLD",
            ticker=event.ticker,
            quantity=0,
            reasoning="Decision failed validation; defaulting to HOLD.",
        )