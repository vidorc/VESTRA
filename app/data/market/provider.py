"""Market-data provider interface and factory.

A ``MarketDataProvider`` abstracts where price / quote / news data comes from so
the rest of Vestra never hardcodes a feed. The static table
(:class:`~app.data.market.static.StaticReferenceProvider`) is the guaranteed
fallback; live providers (yfinance now, NSE/broker later) layer on top and
degrade to static on any failure.

Hot-path safety
---------------
``app/agent/pricing.get_reference_price`` is *synchronous* and runs inside the
validator / execution path, which must never block on network I/O. Providers
therefore expose ``get_cached_price`` -- a synchronous, non-blocking lookup that
returns a cached or static value immediately -- in addition to the async methods
the Research agent uses for live fetching.
"""

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from app.config import get_settings
from app.data.market.static import StaticReferenceProvider


@runtime_checkable
class MarketDataProvider(Protocol):
    """Protocol every market-data source implements."""

    name: str

    def get_cached_price(self, ticker: str) -> float:
        """Synchronous, non-blocking price lookup. Must always return a value."""
        ...

    async def get_price(self, ticker: str) -> float: ...
    async def get_quote(self, ticker: str) -> Dict[str, Any]: ...
    async def get_history(self, ticker: str, period: str = "1mo") -> List[Dict[str, Any]]: ...
    async def get_fundamentals(self, ticker: str) -> Dict[str, Any]: ...
    async def get_news(self, ticker: str) -> List[Dict[str, Any]]: ...


_provider: Optional[MarketDataProvider] = None


def get_market_data_provider() -> MarketDataProvider:
    """Return the configured provider singleton (lazy).

    Selected by ``MARKET_DATA_PROVIDER`` config (default ``static``). Unknown or
    unavailable selections fall back to the static provider so the system always
    has a working price source.
    """
    global _provider
    if _provider is None:
        choice = getattr(get_settings(), "MARKET_DATA_PROVIDER", "static").lower()
        if choice == "yfinance":
            # Lazy import: yfinance is heavy and optional. If it (or its deps)
            # are missing, fall back to static rather than crashing the app.
            try:
                from app.data.market.yfinance_provider import YFinanceProvider

                _provider = YFinanceProvider()
            except Exception:
                _provider = StaticReferenceProvider()
        else:
            _provider = StaticReferenceProvider()
    return _provider


def set_provider(provider: Optional[MarketDataProvider]) -> None:
    """Test seam: inject a provider or reset the cache with ``None``."""
    global _provider
    _provider = provider


__all__ = [
    "MarketDataProvider",
    "get_market_data_provider",
    "set_provider",
]
