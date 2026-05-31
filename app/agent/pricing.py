"""Reference price resolution for trade validation and execution.

This is the synchronous, non-blocking price seam used by the validator and
execution path -- it must never do network I/O. It delegates to the configured
:class:`~app.data.market.provider.MarketDataProvider` via its ``get_cached_price``
method, which returns a cached live price when one is fresh and otherwise the
static reference table.

The static table and ``DEFAULT_REFERENCE_PRICE`` now live in
``app/data/market/static.py``; they are re-exported here for backward
compatibility so existing imports (and tests) keep working unchanged. With the
default ``MARKET_DATA_PROVIDER=static`` config the values are identical to the
old hardcoded table.
"""

from app.data.market.provider import get_market_data_provider
from app.data.market.static import DEFAULT_REFERENCE_PRICE


def get_reference_price(ticker: str) -> float:
    """Return a reference execution price (INR) for ``ticker``.

    Non-blocking: returns a fresh cached live price if the active provider has
    one, otherwise the static fallback. Falls back to
    :data:`DEFAULT_REFERENCE_PRICE` for unknown tickers.
    """
    return get_market_data_provider().get_cached_price(ticker)


__all__ = ["get_reference_price", "DEFAULT_REFERENCE_PRICE"]
