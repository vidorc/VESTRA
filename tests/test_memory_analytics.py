"""Tests for Phase 6 chart data sources.

Two backend additions that give the executive-analytics charts real data:

* ``regime`` persisted into the reasoning trace (it already lives in AgentState
  but wasn't being saved) -> powers the market-regime timeline.
* ``GET /memory`` + ``memory_analytics`` -> win/loss tallies, per-ticker
  breakdown, and a decision timeline from agent_memories.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver
from mongomock_motor import AsyncMongoMockClient

from app.agent.checkpoint import set_checkpointer
from app.data.mongo import get_client, set_client
from app.main import app
from app.models.schemas import MarketEvent

_SELL = '{"action":"SELL","ticker":"RELIANCE","quantity":3,"reasoning":"reduce risk"}'
_EVENT = MarketEvent(ticker="RELIANCE", price_change_percent=-12.0, breaking_news_summary="shock")


# --- regime in trace -----------------------------------------------------

@pytest.fixture
async def workflow_env(fake_llm):
    set_client(AsyncMongoMockClient())
    set_checkpointer(MemorySaver())
    fake_llm(_SELL)
    yield
    set_checkpointer(None)
    set_client(None)


async def test_workflow_persists_regime_in_trace(workflow_env):
    from app.agent.graph import run_vestra_workflow
    from app.data.repository import list_reasoning_traces

    db = get_client()["vestra_test"]
    await db.investor_profiles.insert_one(
        {
            "user_id": "u1",
            "risk_tolerance": "moderate",
            "cash_balance": 100000.0,
            "holdings": {"RELIANCE": 20},
            "target_allocation": {},
            "approval_policy": "autonomous_sandbox",
        }
    )
    await run_vestra_workflow("u1", _EVENT, event_id="ev-regime")

    traces = await list_reasoning_traces("u1")
    assert len(traces) == 1
    assert traces[0]["regime"] and "regime" in traces[0]["regime"]


# --- memory analytics service (pure) -------------------------------------

def test_memory_analytics_tallies_wins_losses():
    from app.services.memory import memory_analytics

    memories = [
        {"ticker": "RELIANCE", "action": "SELL", "outcome": {"result": "completed"}},
        {"ticker": "RELIANCE", "action": "BUY", "outcome": {"result": "loss"}},
        {"ticker": "INFY", "action": "BUY", "outcome": {"result": "completed"}},
        {"ticker": "INFY", "action": "BUY", "outcome": None},
    ]
    a = memory_analytics(memories)
    assert a["total"] == 4
    assert a["completed"] == 2
    assert a["losses"] == 1
    assert a["pending"] == 1
    # Per-ticker rollup.
    by = {t["ticker"]: t for t in a["by_ticker"]}
    assert by["RELIANCE"]["total"] == 2
    assert by["INFY"]["total"] == 2
    # Win rate over decided trades only (2 completed of 3 decided).
    assert a["win_rate"] == pytest.approx(2 / 3, abs=0.01)


def test_memory_analytics_empty():
    from app.services.memory import memory_analytics

    a = memory_analytics([])
    assert a["total"] == 0
    assert a["win_rate"] == 0.0
    assert a["by_ticker"] == []


# --- GET /memory endpoint ------------------------------------------------

@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_memory_endpoint_requires_auth(client):
    r = await client.get("/memory")
    assert r.status_code == 401


async def test_memory_endpoint_returns_timeline_and_analytics(client):
    reg = await client.post(
        "/auth/register", json={"email": "m@b.com", "password": "supersecret1"}
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.agent_memories.insert_many(
        [
            {"user_id": uid, "ticker": "RELIANCE", "action": "SELL", "outcome": {"result": "completed"}},
            {"user_id": uid, "ticker": "INFY", "action": "BUY", "outcome": {"result": "loss"}},
        ]
    )
    r = await client.get("/memory", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert len(body["memories"]) == 2
    assert body["analytics"]["total"] == 2
    assert body["analytics"]["completed"] == 1
    assert body["analytics"]["losses"] == 1


async def test_memory_endpoint_is_owner_scoped(client):
    reg_a = await client.post("/auth/register", json={"email": "a@b.com", "password": "supersecret1"})
    token_a, uid_a = reg_a.json()["access_token"], reg_a.json()["user_id"]
    reg_b = await client.post("/auth/register", json={"email": "b@b.com", "password": "supersecret1"})
    uid_b = reg_b.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.agent_memories.insert_one({"user_id": uid_a, "ticker": "RELIANCE", "outcome": None})
    await db.agent_memories.insert_one({"user_id": uid_b, "ticker": "INFY", "outcome": None})
    r = await client.get("/memory", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200
    assert r.json()["analytics"]["total"] == 1
