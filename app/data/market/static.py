"""Static reference-price market-data provider.

This is the guaranteed-available fallback. It holds the order-of-magnitude INR
reference prices that used to live directly in ``app/agent/pricing.py`` and does
no network I/O, so it is always safe to call from the synchronous validator /
execution hot path. Live providers (e.g. yfinance) fall back to this one on any
failure or timeout.
"""

from typing import Any, Dict, List

# Approximate INR reference prices. Order-of-magnitude realistic so cash/limit
# checks behave sensibly without a live feed.
_REFERENCE_PRICES: Dict[str, float] = {
    "RELIANCE": 1450.0,
    "INFY": 1550.0,
    "HDFCBANK": 1650.0,
    "ADANIENT": 2400.0,
    "TCS": 3900.0,
    "ICICIBANK": 1250.0,
    "SBIN": 820.0,
    "ITC": 460.0,
    "HINDUNILVR": 2350.0,
    "LT": 3600.0,
}

# Used when a ticker is unknown. Documented and intentionally conservative.
DEFAULT_REFERENCE_PRICE = 1000.0


class StaticReferenceProvider:
    """Market-data provider backed by a static table. Never does I/O."""

    name = "static"

    def get_cached_price(self, ticker: str) -> float:
        """Synchronous, non-blocking price lookup. Always returns a value."""
        return _REFERENCE_PRICES.get(ticker.upper(), DEFAULT_REFERENCE_PRICE)

    async def get_price(self, ticker: str) -> float:
        return self.get_cached_price(ticker)

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        return {
            "ticker": ticker.upper(),
            "price": self.get_cached_price(ticker),
            "source": self.name,
            "live": False,
        }

    async def get_history(self, ticker: str, period: str = "1mo") -> List[Dict[str, Any]]:
        # No historical data without a live feed.
        return []

    async def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        return {}

    async def get_news(self, ticker: str) -> List[Dict[str, Any]]:
        return []


__all__ = ["StaticReferenceProvider", "DEFAULT_REFERENCE_PRICE", "_REFERENCE_PRICES"]
