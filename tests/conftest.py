"""Pytest fixtures and hermetic test environment for Vestra.

Sets dummy required env vars BEFORE any ``app.*`` module is imported. Several
modules (``app.config``, ``app.mcp.server``, ``app.agent.nodes.strategy``)
resolve settings and construct clients at import time, so the environment must
be populated first. Environment variables take precedence over the ``.env`` file
in pydantic-settings, so this runs hermetically regardless of a developer's
local ``.env`` and never depends on real secrets. All DB/LLM calls are mocked in
the tests themselves.
"""

import os

os.environ.setdefault("GROQ_API_KEY", "test-groq-key")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("DATABASE_NAME", "vestra_test")
os.environ.setdefault(
    "JWT_SECRET", "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
)
os.environ.setdefault("WEBHOOK_API_KEY", "test-webhook-key")

import pytest

from app.models.schemas import MarketEvent, RiskAssessment, TradeDecision


@pytest.fixture
def market_event() -> MarketEvent:
    return MarketEvent(
        ticker="RELIANCE",
        price_change_percent=-12.0,
        breaking_news_summary="Supply chain shock rattles equities",
    )


@pytest.fixture
def risk() -> RiskAssessment:
    return RiskAssessment(
        concentration_risk="medium",
        cash_available=100000.0,
        safe_trade_limit=10,
        notes="Moderate concentration risk.",
    )


@pytest.fixture
def profile() -> dict:
    return {
        "user_id": "user_001",
        "risk_tolerance": "moderate",
        "cash_balance": 100000.0,
        "holdings": {"RELIANCE": 20, "INFY": 15},
        "target_allocation": {"RELIANCE": 30, "INFY": 20},
    }


def make_decision(action="SELL", ticker="RELIANCE", quantity=5, reasoning="x"):
    return TradeDecision(
        action=action, ticker=ticker, quantity=quantity, reasoning=reasoning
    )


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeLLM:
    """A stand-in for ChatGroq: returns a fixed payload from ``ainvoke``.

    Inject via ``app.agent.llm.set_llm(FakeLLM(...))``. Set ``raises=True`` to
    simulate an LLM failure and exercise a node's graceful-degradation path.
    """

    def __init__(self, payload: str = "{}", raises: bool = False):
        self.payload = payload
        self.raises = raises
        self.calls = 0

    async def ainvoke(self, prompt):
        self.calls += 1
        if self.raises:
            raise RuntimeError("simulated LLM failure")
        return _FakeMessage(self.payload)


@pytest.fixture
def fake_llm():
    """Install a FakeLLM into the shared seam and clean up afterwards."""
    from app.agent import llm as llm_mod

    installed = {}

    def _install(payload: str = "{}", raises: bool = False) -> FakeLLM:
        f = FakeLLM(payload, raises=raises)
        llm_mod.set_llm(f)
        installed["f"] = f
        return f

    yield _install
    llm_mod.set_llm(None)

