"""yfinance-backed market-data provider.

Wraps Yahoo Finance for live quotes/history/news. yfinance is synchronous and
blocking, so every live call runs in a thread executor guarded by a timeout; any
failure or timeout falls back to the static provider. A short TTL cache holds the
last price per ticker so the synchronous hot-path lookup
(``get_cached_price``) never has to block on the network.

Indian tickers map to Yahoo's ``.NS`` (NSE) suffix.

yfinance is an optional, heavy dependency: it is imported lazily by
``get_market_data_provider`` and only when ``MARKET_DATA_PROVIDER=yfinance``.
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

import yfinance as yf

from app.data.market.static import StaticReferenceProvider

_PRICE_TTL_SECONDS = 60.0
_CALL_TIMEOUT_SECONDS = 4.0


def _to_yahoo_symbol(ticker: str) -> str:
    t = ticker.upper()
    # Already qualified (e.g. has an exchange suffix) -> leave as-is.
    if "." in t or t in {"NIFTY50", "BANKNIFTY"}:
        return t
    return f"{t}.NS"


class YFinanceProvider:
    """Live provider with TTL cache, per-call timeout, and static fallback."""

    name = "yfinance"

    def __init__(self) -> None:
        self._static = StaticReferenceProvider()
        # ticker -> (price, fetched_at)
        self._price_cache: Dict[str, Tuple[float, float]] = {}

    # --- synchronous hot-path lookup -------------------------------------

    def get_cached_price(self, ticker: str) -> float:
        """Non-blocking: return a fresh cached price, else the static fallback.

        Never does network I/O -- safe to call from the validator/execution path.
        """
        cached = self._price_cache.get(ticker.upper())
        if cached and (time.monotonic() - cached[1]) < _PRICE_TTL_SECONDS:
            return cached[0]
        return self._static.get_cached_price(ticker)

    # --- async live methods ----------------------------------------------

    async def _run(self, fn, *args):
        """Run a blocking yfinance call in a thread with a hard timeout."""
        return await asyncio.wait_for(
            asyncio.to_thread(fn, *args), timeout=_CALL_TIMEOUT_SECONDS
        )

    async def get_price(self, ticker: str) -> float:
        try:
            price = await self._run(self._fetch_price, ticker)
            if price is not None:
                self._price_cache[ticker.upper()] = (price, time.monotonic())
                return price
        except Exception:
            pass
        return self._static.get_cached_price(ticker)

    async def get_quote(self, ticker: str) -> Dict[str, Any]:
        price = await self.get_price(ticker)
        live = ticker.upper() in self._price_cache
        return {
            "ticker": ticker.upper(),
            "price": price,
            "source": self.name if live else self._static.name,
            "live": live,
        }

    async def get_history(self, ticker: str, period: str = "1mo") -> List[Dict[str, Any]]:
        try:
            return await self._run(self._fetch_history, ticker, period)
        except Exception:
            return []

    async def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        try:
            return await self._run(self._fetch_fundamentals, ticker)
        except Exception:
            return {}

    async def get_news(self, ticker: str) -> List[Dict[str, Any]]:
        try:
            return await self._run(self._fetch_news, ticker)
        except Exception:
            return []

    # --- blocking yfinance calls (run in thread) -------------------------

    def _fetch_price(self, ticker: str) -> Optional[float]:
        t = yf.Ticker(_to_yahoo_symbol(ticker))
        fast = getattr(t, "fast_info", None)
        if fast:
            price = fast.get("last_price") or fast.get("lastPrice")
            if price:
                return float(price)
        hist = t.history(period="1d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
        return None

    def _fetch_history(self, ticker: str, period: str) -> List[Dict[str, Any]]:
        hist = yf.Ticker(_to_yahoo_symbol(ticker)).history(period=period)
        out: List[Dict[str, Any]] = []
        for idx, row in hist.iterrows():
            out.append(
                {
                    "date": idx.isoformat(),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
            )
        return out

    def _fetch_fundamentals(self, ticker: str) -> Dict[str, Any]:
        info = yf.Ticker(_to_yahoo_symbol(ticker)).info or {}
        keys = (
            "sector",
            "industry",
            "marketCap",
            "trailingPE",
            "forwardPE",
            "dividendYield",
            "fiftyTwoWeekHigh",
            "fiftyTwoWeekLow",
        )
        return {k: info[k] for k in keys if k in info}

    def _fetch_news(self, ticker: str) -> List[Dict[str, Any]]:
        raw = yf.Ticker(_to_yahoo_symbol(ticker)).news or []
        out: List[Dict[str, Any]] = []
        for item in raw[:10]:
            content = item.get("content", item)
            out.append(
                {
                    "title": content.get("title"),
                    "publisher": (content.get("provider") or {}).get("displayName")
                    if isinstance(content.get("provider"), dict)
                    else content.get("publisher"),
                    "link": content.get("canonicalUrl", {}).get("url")
                    if isinstance(content.get("canonicalUrl"), dict)
                    else content.get("link"),
                }
            )
        return out


__all__ = ["YFinanceProvider"]
