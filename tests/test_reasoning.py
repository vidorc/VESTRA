"""Tests for the Agent Reasoning trace: persistence, the GET /reasoning endpoint,
and the graph capturing a full 7-output trace per decision.

A reasoning trace is the complete chain the agent produced for one decision:
signal -> research -> risk -> strategy(decision) -> reflection -> confidence ->
validation. It is persisted once per run by the validator node (the last node
always reached before branching), so every decision is inspectable afterwards.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver
from mongomock_motor import AsyncMongoMockClient

from app.agent.checkpoint import set_checkpointer
from app.data import repository as repo
from app.data.mongo import get_client, set_client
from app.main import app
from app.models.schemas import MarketEvent

_SELL = '{"action":"SELL","ticker":"RELIANCE","quantity":3,"reasoning":"reduce risk"}'
_EVENT = MarketEvent(ticker="RELIANCE", price_change_percent=-12.0, breaking_news_summary="shock")

# The seven outputs a reasoning trace must surface.
_TRACE_KEYS = ("signal", "research", "risk", "decision", "reflection", "confidence", "validation")


# --- repository layer ----------------------------------------------------

@pytest.fixture
async def mongo():
    client = AsyncMongoMockClient()
    set_client(client)
    yield client["vestra_test"]
    set_client(None)


async def test_save_and_list_reasoning_trace(mongo):
    trace = {k: {"k": i} for i, k in enumerate(_TRACE_KEYS)}
    await repo.save_reasoning_trace("u1", trace, event_id="ev-1")

    traces = await repo.list_reasoning_traces("u1")
    assert len(traces) == 1
    stored = traces[0]
    assert stored["event_id"] == "ev-1"
    assert stored["user_id"] == "u1"
    assert "ts" in stored
    for k in _TRACE_KEYS:
        assert stored[k] == trace[k]


async def test_list_reasoning_traces_is_owner_scoped(mongo):
    await repo.save_reasoning_trace("u1", {"signal": {}}, event_id="a")
    await repo.save_reasoning_trace("u2", {"signal": {}}, event_id="b")
    assert len(await repo.list_reasoning_traces("u1")) == 1
    assert len(await repo.list_reasoning_traces("u2")) == 1


async def test_list_reasoning_traces_newest_first_and_limited(mongo):
    for i in range(5):
        await repo.save_reasoning_trace("u1", {"n": i}, event_id=f"ev-{i}")
    traces = await repo.list_reasoning_traces("u1", limit=3)
    assert len(traces) == 3
    # Newest first: the last-written event_id leads.
    assert traces[0]["event_id"] == "ev-4"


# --- endpoint ------------------------------------------------------------

@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_reasoning_endpoint_requires_auth(client):
    r = await client.get("/reasoning")
    assert r.status_code == 401


async def test_reasoning_endpoint_lists_traces(client):
    reg = await client.post(
        "/auth/register", json={"email": "r@b.com", "password": "supersecret1"}
    )
    token = reg.json()["access_token"]
    uid = reg.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.reasoning_traces.insert_one(
        {"user_id": uid, "event_id": "e1", "ts": "2026-01-01", "signal": {"severity": "high"}}
    )
    r = await client.get("/reasoning", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    traces = r.json()["traces"]
    assert len(traces) == 1
    assert traces[0]["signal"]["severity"] == "high"


async def test_reasoning_endpoint_only_returns_own_traces(client):
    reg_a = await client.post(
        "/auth/register", json={"email": "a@b.com", "password": "supersecret1"}
    )
    token_a, uid_a = reg_a.json()["access_token"], reg_a.json()["user_id"]
    reg_b = await client.post(
        "/auth/register", json={"email": "b@b.com", "password": "supersecret1"}
    )
    uid_b = reg_b.json()["user_id"]

    db = get_client()["vestra_test"]
    await db.reasoning_traces.insert_one({"user_id": uid_a, "event_id": "mine", "signal": {}})
    await db.reasoning_traces.insert_one({"user_id": uid_b, "event_id": "theirs", "signal": {}})

    r = await client.get("/reasoning", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200
    events = [t["event_id"] for t in r.json()["traces"]]
    assert events == ["mine"]


# --- graph integration ---------------------------------------------------

@pytest.fixture
async def graph_client(fake_llm):
    set_client(AsyncMongoMockClient())
    set_checkpointer(MemorySaver())
    fake_llm(_SELL)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_checkpointer(None)
    set_client(None)


async def test_workflow_persists_full_reasoning_trace(graph_client):
    """Running a decision through the graph persists a trace with all 7 outputs."""
    from app.agent.graph import run_vestra_workflow

    reg = await graph_client.post(
        "/auth/register", json={"email": "g@b.com", "password": "supersecret1"}
    )
    uid = reg.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.investor_profiles.update_one(
        {"user_id": uid},
        {"$set": {"holdings": {"RELIANCE": 20}, "cash_balance": 100000.0}},
    )

    await run_vestra_workflow(uid, _EVENT, event_id="ev-trace")

    traces = await repo.list_reasoning_traces(uid)
    assert len(traces) == 1
    trace = traces[0]
    assert trace["event_id"] == "ev-trace"
    for k in _TRACE_KEYS:
        assert k in trace and trace[k], f"missing reasoning output: {k}"
    # Spot-check the strategy decision flowed through from the fake LLM.
    assert trace["decision"]["action"] == "SELL"
