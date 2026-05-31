"""Sector classification for Indian equities and concentration analysis.

Replaces the previous US-only ``tech_names`` heuristic that left
``concentration_risk`` permanently "low" for the Indian tickers Vestra actually
handles. Concentration is computed from the largest single sector's share of the
portfolio, so it is meaningful for any holdings mix rather than one hardcoded
sector.
"""

# Ticker -> sector for the Indian instruments Vestra currently handles.
# Extend as coverage grows; unknown tickers fall into "other".
_SECTOR_MAP = {
    # IT
    "INFY": "it",
    "TCS": "it",
    "WIPRO": "it",
    "HCLTECH": "it",
    # Banking / financials
    "HDFCBANK": "banking",
    "ICICIBANK": "banking",
    "SBIN": "banking",
    "KOTAKBANK": "banking",
    "AXISBANK": "banking",
    "BANKNIFTY": "banking",
    # Energy / conglomerate
    "RELIANCE": "energy",
    "ONGC": "energy",
    "ADANIENT": "energy",
    "ADANIGREEN": "energy",
    # FMCG
    "ITC": "fmcg",
    "HINDUNILVR": "fmcg",
    "NESTLEIND": "fmcg",
    # Infra / industrials
    "LT": "infrastructure",
    # Broad index
    "NIFTY50": "index",
}

DEFAULT_SECTOR = "other"


def get_sector(ticker: str) -> str:
    """Return the sector for ``ticker`` (``"other"`` if unknown)."""
    return _SECTOR_MAP.get(ticker.upper(), DEFAULT_SECTOR)


def sector_breakdown(holdings: dict) -> dict:
    """Aggregate position quantities by sector.

    Args:
        holdings: mapping of ticker -> quantity.

    Returns:
        Mapping of sector -> total quantity in that sector.
    """
    breakdown: dict = {}
    for ticker, qty in holdings.items():
        sector = get_sector(ticker)
        breakdown[sector] = breakdown.get(sector, 0) + qty
    return breakdown


def assess_concentration(holdings: dict) -> dict:
    """Classify portfolio concentration by largest-sector share.

    Returns a dict with ``concentration_risk`` ("low"/"medium"/"high"),
    ``largest_sector``, ``largest_sector_exposure`` (quantity), and the full
    ``sector_breakdown``.
    """
    breakdown = sector_breakdown(holdings)
    total = sum(breakdown.values())

    concentration = "low"
    largest_sector = None
    largest_exposure = 0

    if total > 0:
        largest_sector, largest_exposure = max(
            breakdown.items(), key=lambda kv: kv[1]
        )
        ratio = largest_exposure / total
        if ratio > 0.6:
            concentration = "high"
        elif ratio > 0.3:
            concentration = "medium"

    return {
        "concentration_risk": concentration,
        "largest_sector": largest_sector,
        "largest_sector_exposure": largest_exposure,
        "sector_breakdown": breakdown,
    }


__all__ = [
    "get_sector",
    "sector_breakdown",
    "assess_concentration",
    "DEFAULT_SECTOR",
]
