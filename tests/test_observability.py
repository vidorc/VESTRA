"""Tests for Agent Observability (span aggregation + workflow instrumentation).

``build_observability_report`` rolls up node-execution spans into per-node timing
and error rates. The graph's node wrapper records one span per node run without
changing behaviour. The /observability endpoint is authed + owner-scoped.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from langgraph.checkpoint.memory import MemorySaver
from mongomock_motor import AsyncMongoMockClient

from app.agent.checkpoint import set_checkpointer
from app.data.mongo import get_client, set_client
from app.main import app
from app.models.schemas import MarketEvent
from app.services.observability import build_observability_report


def _span(node, duration_ms, status="ok"):
    return {"node": node, "duration_ms": duration_ms, "status": status}


# --- pure aggregation ---------------------------------------------------


def test_empty_events_yield_zeroed_report():
    report = build_observability_report([])
    assert report.total_runs == 0
    assert report.total_errors == 0
    assert report.nodes == []
    assert report.slowest_node is None


def test_aggregates_runs_and_latency_per_node():
    report = build_observability_report(
        [
            _span("signal", 5.0),
            _span("signal", 15.0),
            _span("risk", 100.0),
        ]
    )
    by = {n.node: n for n in report.nodes}
    assert by["signal"].runs == 2
    assert by["signal"].avg_ms == 10.0
    assert by["signal"].max_ms == 15.0
    assert by["risk"].runs == 1
    assert report.total_runs == 3


def test_error_rate_overall_and_per_node():
    report = build_observability_report(
        [
            _span("execute", 20.0, status="error"),
            _span("execute", 20.0, status="ok"),
            _span("signal", 5.0, status="ok"),
        ]
    )
    by = {n.node: n for n in report.nodes}
    assert by["execute"].errors == 1
    assert by["execute"].error_rate == 0.5
    assert report.total_errors == 1
    assert report.error_rate == pytest.approx(1 / 3, abs=0.001)


def test_last_status_reflects_most_recent_run():
    # Events are newest-first: the first 'execute' seen is its latest run.
    report = build_observability_report(
        [
            _span("execute", 10.0, status="error"),  # newest
            _span("execute", 10.0, status="ok"),  # older
        ]
    )
    execute = next(n for n in report.nodes if n.node == "execute")
    assert execute.last_status == "error"


def test_slowest_node_is_highest_average():
    report = build_observability_report(
        [_span("fast", 1.0), _span("slow", 500.0)]
    )
    assert report.slowest_node == "slow"


def test_nodes_sorted_busiest_first():
    report = build_observability_report(
        [_span("a", 1.0), _span("b", 1.0), _span("b", 1.0), _span("b", 1.0), _span("a", 1.0)]
    )
    # b has 3 runs, a has 2 -> b first.
    assert report.nodes[0].node == "b"


def test_determinism_same_spans_same_report():
    spans = [_span("signal", 5.0), _span("risk", 50.0, status="error")]
    assert build_observability_report(spans).model_dump() == build_observability_report(spans).model_dump()


# --- workflow records spans ---------------------------------------------


@pytest.fixture
async def workflow_env(fake_llm):
    set_client(AsyncMongoMockClient())
    set_checkpointer(MemorySaver())
    fake_llm('{"action":"SELL","ticker":"RELIANCE","quantity":3,"reasoning":"reduce risk"}')
    yield
    set_checkpointer(None)
    set_client(None)


async def test_workflow_records_node_spans(workflow_env):
    from app.agent.graph import run_vestra_workflow
    from app.data.repository import list_agent_events

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
    await run_vestra_workflow("u1", MarketEvent(
        ticker="RELIANCE", price_change_percent=-12.0, breaking_news_summary="shock"
    ), event_id="ev-obs")

    events = await list_agent_events("u1")
    nodes_seen = {e["node"] for e in events}
    # Core pipeline nodes should each have recorded a span.
    assert {"signal", "research", "risk", "strategy", "validate"} <= nodes_seen
    assert all("duration_ms" in e and e["status"] in ("ok", "error") for e in events)


# --- /observability endpoint --------------------------------------------


@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_observability_endpoint_requires_auth(client):
    r = await client.get("/observability")
    assert r.status_code == 401


async def test_observability_endpoint_returns_report(client):
    reg = await client.post("/auth/register", json={"email": "o@b.com", "password": "supersecret1"})
    token, uid = reg.json()["access_token"], reg.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.agent_events.insert_many(
        [
            {"user_id": uid, "node": "signal", "duration_ms": 5.0, "status": "ok"},
            {"user_id": uid, "node": "risk", "duration_ms": 80.0, "status": "ok"},
            {"user_id": uid, "node": "execute", "duration_ms": 30.0, "status": "error"},
        ]
    )
    r = await client.get("/observability", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["total_runs"] == 3
    assert body["total_errors"] == 1
    assert {n["node"] for n in body["nodes"]} == {"signal", "risk", "execute"}


async def test_observability_endpoint_is_owner_scoped(client):
    reg_a = await client.post("/auth/register", json={"email": "oa@b.com", "password": "supersecret1"})
    token_a, uid_a = reg_a.json()["access_token"], reg_a.json()["user_id"]
    reg_b = await client.post("/auth/register", json={"email": "ob@b.com", "password": "supersecret1"})
    uid_b = reg_b.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.agent_events.insert_one({"user_id": uid_a, "node": "signal", "duration_ms": 5.0, "status": "ok"})
    await db.agent_events.insert_one({"user_id": uid_b, "node": "risk", "duration_ms": 5.0, "status": "ok"})
    r = await client.get("/observability", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200
    assert r.json()["total_runs"] == 1
    assert r.json()["nodes"][0]["node"] == "signal"
