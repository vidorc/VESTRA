"""End-to-end workflow tests: interrupt, resume, and legacy-shape preservation.

Drives the real compiled LangGraph with an in-memory checkpointer (MemorySaver),
mongomock, and a fake LLM. These are the regression guard for the Phase 1
human-in-the-loop changes -- especially that the non-interrupt paths keep the
exact legacy result contract.
"""

import pytest
from langgraph.checkpoint.memory import MemorySaver
from mongomock_motor import AsyncMongoMockClient

from app.agent import graph as G
from app.agent.checkpoint import set_checkpointer
from app.data.mongo import get_client, set_client
from app.models.schemas import MarketEvent

_SELL = '{"action":"SELL","ticker":"RELIANCE","quantity":3,"reasoning":"reduce risk"}'
_HOLD = '{"action":"HOLD","ticker":"RELIANCE","quantity":0,"reasoning":"hold"}'
_OVERSELL = '{"action":"SELL","ticker":"RELIANCE","quantity":999,"reasoning":"x"}'

_EVENT = MarketEvent(
    ticker="RELIANCE", price_change_percent=-12.0, breaking_news_summary="shock"
)


@pytest.fixture
def workflow_env():
    """Fresh mongomock + a fresh MemorySaver (forces the graph to rebuild)."""
    set_client(AsyncMongoMockClient())
    # A new MemorySaver instance makes get_graph() rebuild against it.
    set_checkpointer(MemorySaver())
    yield
    set_checkpointer(None)
    set_client(None)


async def _seed_profile(policy: str, holdings=None):
    db = get_client()["vestra_test"]
    await db.investor_profiles.insert_one(
        {
            "user_id": "u1",
            "risk_tolerance": "moderate",
            "cash_balance": 100000.0,
            "holdings": holdings if holdings is not None else {"RELIANCE": 20},
            "target_allocation": {},
            "approval_policy": policy,
        }
    )


async def test_autonomous_sandbox_executes_with_legacy_shape(workflow_env, fake_llm):
    fake_llm(_SELL)
    await _seed_profile("autonomous_sandbox")
    r = await G.run_vestra_workflow("u1", _EVENT, event_id="e1")
    # Exact legacy success contract.
    assert r["status"] == "success"
    assert r["decision"]["action"] == "SELL"
    assert "execution" in r


async def test_approval_required_interrupts(workflow_env, fake_llm):
    fake_llm(_SELL)
    await _seed_profile("approval_required")
    r = await G.run_vestra_workflow("u1", _EVENT, event_id="e2")
    assert r["status"] == "pending_approval"
    assert r["thread_id"] == "u1:e2"
    assert r["approval_request_id"]
    # A pending approval row exists in Mongo.
    db = get_client()["vestra_test"]
    doc = await db.approval_requests.find_one({"thread_id": "u1:e2"})
    assert doc and doc["status"] == "pending"


async def test_resume_approve_executes(workflow_env, fake_llm):
    fake_llm(_SELL)
    await _seed_profile("approval_required")
    pending = await G.run_vestra_workflow("u1", _EVENT, event_id="e3")
    resumed = await G.resume_workflow(pending["thread_id"], True)
    assert resumed["status"] == "success"
    assert resumed["decision"]["action"] == "SELL"
    db = get_client()["vestra_test"]
    doc = await db.approval_requests.find_one({"thread_id": "u1:e3"})
    assert doc["status"] == "approved"


async def test_resume_reject_does_not_execute(workflow_env, fake_llm):
    fake_llm(_SELL)
    await _seed_profile("approval_required")
    pending = await G.run_vestra_workflow("u1", _EVENT, event_id="e4")
    resumed = await G.resume_workflow(pending["thread_id"], False)
    assert resumed["status"] == "rejected"
    assert "human" in resumed["reason"].lower()
    db = get_client()["vestra_test"]
    doc = await db.approval_requests.find_one({"thread_id": "u1:e4"})
    assert doc["status"] == "rejected"
    # Holdings unchanged (no execution).
    prof = await db.investor_profiles.find_one({"user_id": "u1"})
    assert prof["holdings"]["RELIANCE"] == 20


async def test_hold_never_interrupts(workflow_env, fake_llm):
    fake_llm(_HOLD)
    await _seed_profile("manual")  # strictest policy
    r = await G.run_vestra_workflow("u1", _EVENT, event_id="e5")
    # HOLD executes a no-op and returns the legacy success shape, no approval.
    assert r["status"] == "success"
    assert r["decision"]["action"] == "HOLD"


async def test_validator_rejection_is_legacy_shape(workflow_env, fake_llm):
    fake_llm(_OVERSELL)
    await _seed_profile("autonomous_sandbox", holdings={"RELIANCE": 5})
    r = await G.run_vestra_workflow("u1", _EVENT, event_id="e6")
    assert r["status"] == "rejected"
    assert r["reason"]  # validator reason, not a human one


async def test_research_context_persisted(workflow_env, fake_llm):
    fake_llm(_HOLD)
    await _seed_profile("autonomous_sandbox")
    await G.run_vestra_workflow("u1", _EVENT, event_id="e7")
    db = get_client()["vestra_test"]
    rc = await db.research_context.find_one({"user_id": "u1", "event_id": "e7"})
    assert rc is not None
    assert "sentiment" in rc
