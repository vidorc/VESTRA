from app.models.schemas import MarketEvent, SignalAssessment


def classify_market_event(event: MarketEvent) -> SignalAssessment:
    summary = event.breaking_news_summary.lower()
    ticker = event.ticker.upper()
    move = abs(event.price_change_percent)

    event_type = "company"
    severity = "medium"
    impacted_assets = [ticker]

    if any(keyword in summary for keyword in [
        "rbi",
        "inflation",
        "repo rate",
        "budget",
        "tax",
        "sebi",
        "rupee",
        "crude",
        "war",
        "sanctions"
    ]):
        event_type = "macro"
        impacted_assets = ["NIFTY50", "BANKNIFTY"]

    elif "earnings" in summary:
        event_type = "earnings"

    elif any(keyword in summary for keyword in [
        "china",
        "middle east",
        "oil",
        "supply chain"
    ]):
        event_type = "geopolitical"

    if move >= 15:
        severity = "critical"
    elif move >= 8:
        severity = "high"
    elif move >= 4:
        severity = "medium"
    else:
        severity = "low"

    return SignalAssessment(
        event_type=event_type,
        severity=severity,
        impacted_assets=impacted_assets
    )