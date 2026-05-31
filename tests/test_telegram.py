"""Tests for the Telegram integration: callback parsing + webhook resume.

The Telegram Bot API (network) is mocked by patching the bot module's send/answer
seams; the webhook's resume path is exercised against a real paused workflow.
"""

import pytest
from langgraph.checkpoint.memory import MemorySaver
from mongomock_motor import AsyncMongoMockClient

from app.agent.checkpoint import set_checkpointer
from app.config import get_settings
from app.data.mongo import get_client, set_client
from app.integrations.telegram import bot
from app.models.schemas import MarketEvent

_SELL = '{"action":"SELL","ticker":"RELIANCE","quantity":3,"reasoning":"reduce risk"}'
_EVENT = MarketEvent(ticker="RELIANCE", price_change_percent=-12.0, breaking_news_summary="shock")


# --- pure callback parsing ----------------------------------------------

def test_parse_callback_approve():
    update = {"callback_query": {"id": "cq1", "data": "approve:abc123"}}
    assert bot.parse_callback(update) == ("approve", "abc123", "cq1")


def test_parse_callback_reject():
    update = {"callback_query": {"id": "cq2", "data": "reject:xyz"}}
    assert bot.parse_callback(update) == ("reject", "xyz", "cq2")


def test_parse_callback_ignores_non_button_updates():
    assert bot.parse_callback({"message": {"text": "hi"}}) is None
    assert bot.parse_callback({"callback_query": {"id": "c", "data": "garbage"}}) is None
    assert bot.parse_callback({"callback_query": {"id": "c", "data": "approve:"}}) is None


async def test_send_is_noop_without_token(monkeypatch):
    # No TELEGRAM_BOT_TOKEN configured (default test env) -> skipped, no network.
    res = await bot.send_message("123", "hello")
    assert res.get("skipped")


# --- webhook resume ------------------------------------------------------

@pytest.fixture
async def webhook_client(fake_llm, monkeypatch):
    from httpx import ASGITransport, AsyncClient
    from app.main import app

    set_client(AsyncMongoMockClient())
    set_checkpointer(MemorySaver())
    fake_llm(_SELL)
    # Avoid real network on answerCallbackQuery.
    async def _fake_answer(cq_id, text=""):
        return {"ok": True}
    monkeypatch.setattr(bot, "answer_callback", _fake_answer)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_checkpointer(None)
    set_client(None)


async def _seed_pending(user_id="u1"):
    from app.agent.graph import run_vestra_workflow

    db = get_client()["vestra_test"]
    await db.investor_profiles.insert_one(
        {
            "user_id": user_id,
            "risk_tolerance": "moderate",
            "cash_balance": 100000.0,
            "holdings": {"RELIANCE": 20},
            "target_allocation": {},
            "approval_policy": "approval_required",
        }
    )
    res = await run_vestra_workflow(user_id, _EVENT, event_id="tg-1")
    return res["approval_request_id"]


async def test_webhook_approve_resumes_and_executes(webhook_client):
    approval_id = await _seed_pending()
    update = {"callback_query": {"id": "cq", "data": f"approve:{approval_id}"}}
    r = await webhook_client.post("/telegram/webhook", json=update)
    assert r.status_code == 200
    assert r.json()["ok"] is True
    db = get_client()["vestra_test"]
    doc = await db.approval_requests.find_one({"thread_id": "u1:tg-1"})
    assert doc["status"] == "approved"


async def test_webhook_ignores_unknown_update(webhook_client):
    r = await webhook_client.post("/telegram/webhook", json={"message": {"text": "hi"}})
    assert r.status_code == 200
    assert r.json().get("ignored") is True


async def test_webhook_secret_enforced(webhook_client, monkeypatch):
    # When a secret is configured, a wrong/missing header is rejected.
    get_settings.cache_clear()
    monkeypatch.setenv("TELEGRAM_WEBHOOK_SECRET", "s3cret")
    get_settings.cache_clear()
    try:
        r = await webhook_client.post(
            "/telegram/webhook",
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
            json={"callback_query": {"id": "c", "data": "approve:x"}},
        )
        assert r.status_code == 401
    finally:
        monkeypatch.delenv("TELEGRAM_WEBHOOK_SECRET", raising=False)
        get_settings.cache_clear()
