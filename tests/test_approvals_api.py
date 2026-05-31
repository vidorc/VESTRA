"""Integration tests for the approvals API + Telegram webhook (app/approvals)."""

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


@pytest.fixture
async def client(fake_llm):
    set_client(AsyncMongoMockClient())
    set_checkpointer(MemorySaver())
    fake_llm(_SELL)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_checkpointer(None)
    set_client(None)


async def _register(client, email="u@b.com"):
    r = await client.post("/auth/register", json={"email": email, "password": "supersecret1"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"], r.json()["user_id"]


async def _make_pending_approval(user_id: str):
    """Seed a profile requiring approval and run the workflow to a pending state."""
    from app.agent.graph import run_vestra_workflow

    db = get_client()["vestra_test"]
    await db.investor_profiles.update_one(
        {"user_id": user_id},
        {"$set": {"approval_policy": "approval_required", "holdings": {"RELIANCE": 20}, "cash_balance": 100000.0}},
    )
    res = await run_vestra_workflow(user_id, _EVENT, event_id="ev-1")
    assert res["status"] == "pending_approval"
    return res["approval_request_id"]


async def test_approvals_requires_auth(client):
    r = await client.get("/approvals")
    assert r.status_code == 401


async def test_list_and_approve_resumes_workflow(client):
    token, uid = await _register(client)
    approval_id = await _make_pending_approval(uid)

    # The pending approval is listed for its owner.
    r = await client.get("/approvals?status=pending", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    ids = [a["_id"] for a in r.json()["approvals"]]
    assert approval_id in ids

    # Approving resumes the workflow to execution.
    r = await client.post(
        f"/approvals/{approval_id}/decision",
        headers={"Authorization": f"Bearer {token}"},
        json={"approved": True},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["decision"] == "approved"
    assert body["result"]["status"] == "success"


async def test_double_decision_conflicts(client):
    token, uid = await _register(client)
    approval_id = await _make_pending_approval(uid)
    h = {"Authorization": f"Bearer {token}"}
    first = await client.post(f"/approvals/{approval_id}/decision", headers=h, json={"approved": True})
    assert first.status_code == 200
    second = await client.post(f"/approvals/{approval_id}/decision", headers=h, json={"approved": False})
    assert second.status_code == 409


async def test_cannot_decide_another_users_approval(client):
    token_a, uid_a = await _register(client, "a@b.com")
    approval_id = await _make_pending_approval(uid_a)
    token_b, _ = await _register(client, "b@b.com")
    r = await client.post(
        f"/approvals/{approval_id}/decision",
        headers={"Authorization": f"Bearer {token_b}"},
        json={"approved": True},
    )
    assert r.status_code == 403


async def test_decision_on_missing_approval_404(client):
    token, _ = await _register(client)
    r = await client.post(
        "/approvals/64b7f9aabbccddee00112233/decision",
        headers={"Authorization": f"Bearer {token}"},
        json={"approved": True},
    )
    assert r.status_code == 404
