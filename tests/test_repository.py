"""Tests for the data-access layer: the atomic + idempotent execute_trade fix.

These use an in-memory async Mongo (mongomock-motor) injected via the
``set_client`` seam, so no real database is required. The focus is the
concurrency-safety guarantees that the previous read-modify-write lacked.
"""

import asyncio

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.data import repository as repo
from app.data.mongo import set_client


@pytest.fixture
async def mongo():
    """Inject a fresh in-memory Mongo client and seed one profile."""
    client = AsyncMongoMockClient()
    set_client(client)
    db = client["vestra_test"]
    # Patch the repository's get_db to point at this test database. get_db()
    # reads DATABASE_NAME from settings; conftest sets it to "vestra_test".
    await db.investor_profiles.insert_one(
        {
            "user_id": "u1",
            "risk_tolerance": "moderate",
            "cash_balance": 10000.0,
            "holdings": {"RELIANCE": 10},
            "target_allocation": {},
        }
    )
    yield db
    set_client(None)


async def _cash(db, user_id="u1"):
    p = await db.investor_profiles.find_one({"user_id": user_id})
    return p["cash_balance"]


async def _holding(db, ticker, user_id="u1"):
    p = await db.investor_profiles.find_one({"user_id": user_id})
    return p.get("holdings", {}).get(ticker, 0)


async def test_buy_success_decrements_cash_and_adds_holding(mongo):
    res = await repo.execute_trade("u1", "RELIANCE", "BUY", 2, 1000.0)
    assert res["status"] == "success"
    assert await _cash(mongo) == 8000.0
    assert await _holding(mongo, "RELIANCE") == 12


async def test_sell_success_increments_cash_and_reduces_holding(mongo):
    res = await repo.execute_trade("u1", "RELIANCE", "SELL", 5, 1000.0)
    assert res["status"] == "success"
    assert await _cash(mongo) == 15000.0
    assert await _holding(mongo, "RELIANCE") == 5


async def test_buy_insufficient_cash_rejected(mongo):
    res = await repo.execute_trade("u1", "RELIANCE", "BUY", 100, 1000.0)
    assert res.get("error") == "Insufficient balance"
    assert await _cash(mongo) == 10000.0  # unchanged


async def test_sell_more_than_owned_rejected(mongo):
    res = await repo.execute_trade("u1", "RELIANCE", "SELL", 50, 1000.0)
    assert res.get("error") == "Insufficient holdings"
    assert await _holding(mongo, "RELIANCE") == 10  # unchanged


async def test_missing_profile_rejected(mongo):
    res = await repo.execute_trade("ghost", "RELIANCE", "BUY", 1, 1000.0)
    assert res.get("error") == "Profile not found"


async def test_concurrent_buys_cannot_overspend(mongo):
    """10 concurrent BUYs of 1000 each against 10000 cash: at most 10 succeed,
    cash never goes negative. The atomic filter guard is what enforces this."""
    results = await asyncio.gather(
        *[repo.execute_trade("u1", "RELIANCE", "BUY", 1, 1000.0) for _ in range(15)]
    )
    successes = [r for r in results if r.get("status") == "success"]
    assert len(successes) == 10
    cash = await _cash(mongo)
    assert cash == 0.0
    assert cash >= 0  # never oversold


async def test_idempotency_key_executes_only_once(mongo):
    key = "order-abc-123"
    first = await repo.execute_trade("u1", "RELIANCE", "BUY", 2, 1000.0, idempotency_key=key)
    second = await repo.execute_trade("u1", "RELIANCE", "BUY", 2, 1000.0, idempotency_key=key)
    assert first["status"] == "success"
    # Second call replays the stored result instead of executing again.
    assert second == first
    # Cash only decremented once.
    assert await _cash(mongo) == 8000.0
    assert await _holding(mongo, "RELIANCE") == 12
