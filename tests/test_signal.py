"""Unit tests for the signal classification node (pure, no I/O)."""

from app.agent.nodes.signal import classify_market_event
from app.models.schemas import MarketEvent


def _event(summary, move=5.0, ticker="RELIANCE"):
    return MarketEvent(
        ticker=ticker, price_change_percent=move, breaking_news_summary=summary
    )


def test_macro_keywords_set_macro_type_and_index_assets():
    sig = classify_market_event(_event("RBI hikes repo rate unexpectedly"))
    assert sig.event_type == "macro"
    assert sig.impacted_assets == ["NIFTY50", "BANKNIFTY"]


def test_earnings_keyword():
    sig = classify_market_event(_event("Company misses earnings estimates"))
    assert sig.event_type == "earnings"
    assert sig.impacted_assets == ["RELIANCE"]


def test_geopolitical_keyword():
    sig = classify_market_event(_event("Oil supply chain disruption in middle east"))
    assert sig.event_type == "geopolitical"


def test_default_company_type():
    sig = classify_market_event(_event("Board approves new product line"))
    assert sig.event_type == "company"


def test_severity_thresholds():
    assert classify_market_event(_event("x", move=-20)).severity == "critical"
    assert classify_market_event(_event("x", move=10)).severity == "high"
    assert classify_market_event(_event("x", move=5)).severity == "medium"
    assert classify_market_event(_event("x", move=1)).severity == "low"


def test_ticker_is_uppercased_in_assets():
    sig = classify_market_event(_event("product launch", ticker="infy"))
    assert sig.impacted_assets == ["INFY"]
