"""Tests for the research agent node (LLM mocked via the shared seam)."""

import pytest

from app.agent.nodes.research import generate_research_context
from app.agent.nodes.signal import classify_market_event
from app.models.schemas import MarketEvent

_GOOD = (
    '{"sentiment":"bearish","relevant_news":["selloff deepens"],'
    '"sector_impact":"Energy pressured","historical_context":"Echoes 2020",'
    '"market_conditions":"Risk-off"}'
)


@pytest.fixture
def event() -> MarketEvent:
    return MarketEvent(
        ticker="RELIANCE",
        price_change_percent=-12.0,
        breaking_news_summary="Crude shock rattles energy names",
    )


async def test_research_parses_structured_output(fake_llm, event):
    fake_llm(_GOOD)
    signal = classify_market_event(event)
    rc = await generate_research_context(event, signal)
    assert rc.sentiment == "bearish"
    assert rc.sector_impact == "Energy pressured"
    # Static provider has no live news/quote -> low but non-zero completeness.
    assert 0.0 < rc.data_completeness <= 1.0
    # When the LLM supplies relevant_news, the node uses it.
    assert any("selloff" in n.lower() for n in rc.relevant_news)


async def test_research_falls_back_to_price_rule_when_llm_fails(fake_llm, event):
    fake_llm(raises=True)
    signal = classify_market_event(event)
    rc = await generate_research_context(event, signal)
    # -12% move -> bearish by the fallback rule; never raises.
    assert rc.sentiment == "bearish"
    assert rc.relevant_news  # seeded with the headline


async def test_research_neutral_on_small_move_without_llm(fake_llm):
    fake_llm(raises=True)
    ev = MarketEvent(ticker="INFY", price_change_percent=0.5, breaking_news_summary="minor update")
    rc = await generate_research_context(ev, classify_market_event(ev))
    assert rc.sentiment == "neutral"


async def test_research_invalid_sentiment_is_corrected(fake_llm, event):
    fake_llm('{"sentiment":"purple","relevant_news":[],"sector_impact":"x"}')
    rc = await generate_research_context(event, classify_market_event(event))
    # Invalid sentiment -> fall back to price-derived (-12% -> bearish).
    assert rc.sentiment == "bearish"
