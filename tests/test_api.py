"""Integration tests for the hardened FastAPI surface (app/main.py).

Exercises auth-scoping on /portfolio and /audit, and API-key enforcement +
multi-tenant fan-out on /webhook/market-alert. Mongo is mongomock; the strategy
LLM is replaced via the set_llm seam so no network/LLM is touched. The app is
driven over ASGITransport (lifespan not run -- we inject the client directly).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.agent.nodes import strategy as strategy_mod
from app.config import get_settings
from app.data.mongo import set_client
from app.main import app


class _FakeMessage:
    def __init__(self, content):
        self.content = content


class _FakeLLM:
    """Returns a fixed HOLD decision so the workflow is deterministic + offline."""

    async def ainvoke(self, prompt):
        return _FakeMessage(
            '{"action": "HOLD", "ticker": "RELIANCE", "quantity": 0, '
            '"reasoning": "Holding through volatility."}'
        )


@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    strategy_mod.set_llm(_FakeLLM())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    strategy_mod.set_llm(None)
    set_client(None)


async def _register(client, email="user@b.com"):
    r = await client.post("/auth/register", json={"email": email, "password": "supersecret1"})
    assert r.status_code == 201, r.text
    return r.json()["access_token"], r.json()["user_id"]


# --- auth scoping --------------------------------------------------------

async def test_portfolio_requires_auth(client):
    r = await client.get("/portfolio")
    assert r.status_code == 401


async def test_portfolio_returns_scoped_profile(client):
    token, uid = await _register(client)
    r = await client.get("/portfolio", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["user_id"] == uid
    assert "exposure" in body


async def test_audit_requires_auth(client):
    r = await client.get("/audit")
    assert r.status_code == 401


# --- webhook API-key enforcement ----------------------------------------

async def test_webhook_rejects_without_api_key(client):
    r = await client.post(
        "/webhook/market-alert",
        json={"ticker": "RELIANCE", "price_change_percent": -5.0, "breaking_news_summary": "x"},
    )
    assert r.status_code == 401


async def test_webhook_rejects_wrong_api_key(client):
    r = await client.post(
        "/webhook/market-alert",
        headers={"X-API-Key": "wrong"},
        json={"ticker": "RELIANCE", "price_change_percent": -5.0, "breaking_news_summary": "x"},
    )
    assert r.status_code == 401


# --- multi-tenant fan-out (no hardcoded user_001) ------------------------

async def test_webhook_fans_out_to_impacted_users(client):
    key = get_settings().WEBHOOK_API_KEY

    # Two users: one holds RELIANCE (impacted), one holds only INFY (not).
    t1, u1 = await _register(client, "holder@b.com")
    t2, u2 = await _register(client, "other@b.com")
    # Give u1 a RELIANCE position; u2 an INFY position. mongomock via the client.
    from app.data.mongo import get_client

    db = get_client()["vestra_test"]
    await db.investor_profiles.update_one(
        {"user_id": u1}, {"$set": {"holdings": {"RELIANCE": 10}, "cash_balance": 100000.0}}
    )
    await db.investor_profiles.update_one(
        {"user_id": u2}, {"$set": {"holdings": {"INFY": 10}, "cash_balance": 100000.0}}
    )

    r = await client.post(
        "/webhook/market-alert",
        headers={"X-API-Key": key},
        json={
            "ticker": "RELIANCE",
            "price_change_percent": -6.0,
            "breaking_news_summary": "Company-specific selloff.",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "processed"
    # Only the RELIANCE holder is impacted (company event -> ticker only).
    assert body["impacted_users"] == 1
    assert body["results"][0]["user_id"] == u1


async def test_webhook_no_impacted_users(client):
    key = get_settings().WEBHOOK_API_KEY
    r = await client.post(
        "/webhook/market-alert",
        headers={"X-API-Key": key},
        json={
            "ticker": "ZZZNOHOLDERS",
            "price_change_percent": -6.0,
            "breaking_news_summary": "Nobody holds this.",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "no_impacted_users"
