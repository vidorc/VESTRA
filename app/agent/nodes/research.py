"""Research agent node.

Enriches a market event with research context *before* strategy runs:
sentiment, relevant news, sector impact, historical context, and overall market
conditions. News/quote come from the Phase-0 market-data provider
(``app.data.market``); the LLM summarizes them into a structured
:class:`~app.models.schemas.ResearchContext`.

Design notes
------------
* **Data completeness signal.** The node records how much *real* data backed the
  research (live provider news/quote vs. static fallback vs. nothing). The
  confidence node consumes this -- a decision built on thin data should not be
  presented as high-confidence.
* **Graceful degradation.** Provider failures and LLM/parse failures never raise;
  the node returns a neutral, low-completeness context so the graph keeps moving.
  This is what lets the pipeline run even when live data or the LLM is down.
"""

from typing import List

from app.agent.llm import ainvoke_text, extract_json_object
from app.agent.sectors import get_sector
from app.data.market.provider import get_market_data_provider
from app.models.schemas import MarketEvent, ResearchContext, SignalAssessment

_VALID_SENTIMENT = {"bullish", "bearish", "neutral"}


def _build_prompt(
    event: MarketEvent,
    signal: SignalAssessment,
    sector: str,
    news_titles: List[str],
    quote_live: bool,
) -> str:
    news_block = "\n".join(f"- {t}" for t in news_titles) or "- (no live headlines available)"
    return f"""
You are a sell-side equity research analyst covering Indian markets (NSE/BSE).
Analyze the event below and return ONLY a JSON object.

MARKET EVENT
Ticker: {event.ticker}
Price move: {event.price_change_percent}%
Headline: {event.breaking_news_summary}

SIGNAL
Event type: {signal.event_type}
Severity: {signal.severity}
Sector: {sector}

RECENT HEADLINES
{news_block}

Quote source: {"live market feed" if quote_live else "reference/static (no live feed)"}

Return JSON with exactly these keys:
{{
  "sentiment": "bullish | bearish | neutral",
  "relevant_news": ["concise bullet", "..."],
  "sector_impact": "one sentence on how this affects the {sector} sector",
  "historical_context": "one sentence of relevant historical precedent",
  "market_conditions": "one sentence on broader Indian market conditions"
}}
Be concise and factual. Do not invent specific figures you are unsure of.
"""


async def generate_research_context(
    event: MarketEvent, signal: SignalAssessment
) -> ResearchContext:
    """Produce a :class:`ResearchContext` for an event. Never raises."""
    provider = get_market_data_provider()
    sector = get_sector(event.ticker)

    # Gather live data (best-effort). Each call already falls back internally.
    news_titles: List[str] = []
    quote_live = False
    try:
        news = await provider.get_news(event.ticker)
        news_titles = [n.get("title") for n in news if n.get("title")][:5]
    except Exception:
        news_titles = []
    try:
        quote = await provider.get_quote(event.ticker)
        quote_live = bool(quote.get("live"))
    except Exception:
        quote_live = False

    # Data completeness: blend of "did we get live news" and "live quote".
    completeness = 0.0
    if news_titles:
        completeness += 0.6
    if quote_live:
        completeness += 0.4
    # Even with no live data we always have the event headline itself.
    completeness = max(completeness, 0.15)

    # Always seed relevant_news with the event headline so context is non-empty.
    seeded_news = [event.breaking_news_summary, *news_titles]

    try:
        text = await ainvoke_text(
            _build_prompt(event, signal, sector, news_titles, quote_live)
        )
        parsed = extract_json_object(text) or {}
    except Exception:
        parsed = {}

    sentiment = str(parsed.get("sentiment", "")).lower().strip()
    if sentiment not in _VALID_SENTIMENT:
        # Fall back to a rule-of-thumb from the price move.
        sentiment = (
            "bearish"
            if event.price_change_percent <= -2
            else "bullish"
            if event.price_change_percent >= 2
            else "neutral"
        )

    relevant_news = parsed.get("relevant_news")
    if not isinstance(relevant_news, list) or not relevant_news:
        relevant_news = seeded_news

    return ResearchContext(
        sentiment=sentiment,
        relevant_news=[str(n) for n in relevant_news][:6],
        sector_impact=str(parsed.get("sector_impact", f"Impacts the {sector} sector.")),
        historical_context=str(parsed.get("historical_context", "")),
        market_conditions=str(parsed.get("market_conditions", "")),
        data_completeness=round(completeness, 2),
    )


__all__ = ["generate_research_context"]
