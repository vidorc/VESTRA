"""Tests for the Decision Review service + /review endpoint.

``review_decisions`` is a pure/deterministic roll-up over agent memory (past
decisions + outcomes) into a "what worked / what failed / why" report with a
chronological investor timeline. The endpoint is owner-scoped and authed.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.data.mongo import get_client, set_client
from app.main import app
from app.services.review import review_decisions


def _mem(ticker, action, result, *, ts="2026-01-01T00:00:00Z", quantity=1):
    outcome = None if result is None else {"result": result, "status": result}
    return {"ticker": ticker, "action": action, "quantity": quantity, "ts": ts, "outcome": outcome}


# --- pure service: tallies ----------------------------------------------


def test_tallies_worked_failed_pending():
    review = review_decisions(
        [
            _mem("RELIANCE", "SELL", "completed"),
            _mem("RELIANCE", "BUY", "loss"),
            _mem("INFY", "BUY", "completed"),
            _mem("INFY", "BUY", None),  # pending
        ]
    )
    assert review.total == 4
    assert review.completed == 2
    assert review.losses == 1
    assert review.pending == 1
    # Win rate over decided trades only: 2 of 3.
    assert review.win_rate == pytest.approx(2 / 3, abs=0.001)


def test_hold_counts_as_decision_but_not_toward_win_rate():
    review = review_decisions(
        [
            _mem("RELIANCE", "HOLD", "no_action", quantity=0),
            _mem("RELIANCE", "SELL", "completed"),
        ]
    )
    assert review.total == 2
    assert review.completed == 1
    assert review.losses == 0
    assert review.pending == 0  # the HOLD is no_action, not pending
    assert review.win_rate == 1.0  # only the decided SELL counts


def test_empty_memory_yields_zeroed_review_with_friendly_highlight():
    review = review_decisions([])
    assert review.total == 0
    assert review.win_rate == 0.0
    assert review.by_ticker == []
    assert review.timeline == []
    assert review.highlights and "No decisions recorded" in review.highlights[0]


# --- per-ticker attribution ---------------------------------------------


def test_per_ticker_entries_busiest_first_with_win_rate():
    review = review_decisions(
        [
            _mem("RELIANCE", "BUY", "completed"),
            _mem("RELIANCE", "BUY", "completed"),
            _mem("RELIANCE", "SELL", "loss"),
            _mem("INFY", "BUY", "completed"),
        ]
    )
    # RELIANCE has more decisions -> first.
    assert review.by_ticker[0].ticker == "RELIANCE"
    assert review.by_ticker[0].decisions == 3
    assert review.by_ticker[0].worked == 2
    assert review.by_ticker[0].failed == 1
    assert review.by_ticker[0].win_rate == pytest.approx(2 / 3, abs=0.001)
    assert "hit rate" in review.by_ticker[0].note


def test_clean_record_note():
    review = review_decisions([_mem("TCS", "BUY", "completed")])
    assert "clean record" in review.by_ticker[0].note


def test_all_losses_note_flags_caution():
    review = review_decisions(
        [_mem("YESBANK", "BUY", "loss"), _mem("YESBANK", "BUY", "loss")]
    )
    assert "cautious" in review.by_ticker[0].note.lower()


# --- timeline -----------------------------------------------------------


def test_timeline_is_oldest_first_and_describes_each_decision():
    # Memories arrive newest-first (as the DAL returns them).
    review = review_decisions(
        [
            _mem("INFY", "BUY", "completed", ts="2026-02-01T00:00:00Z", quantity=4),
            _mem("RELIANCE", "SELL", "loss", ts="2026-01-01T00:00:00Z", quantity=3),
        ]
    )
    # Re-ordered oldest-first for narrative reading.
    assert review.timeline[0].ticker == "RELIANCE"
    assert review.timeline[0].ts == "2026-01-01T00:00:00Z"
    assert review.timeline[0].status == "failed"
    assert review.timeline[0].description == "Sold 3 RELIANCE"
    assert review.timeline[1].description == "Bought 4 INFY"
    assert review.timeline[1].status == "worked"


def test_hold_timeline_description_omits_quantity():
    review = review_decisions([_mem("RELIANCE", "HOLD", "no_action", quantity=0)])
    assert review.timeline[0].description == "Held RELIANCE"
    assert review.timeline[0].status == "no_action"


# --- highlights ---------------------------------------------------------


def test_highlights_name_best_and_weakest_eligible_tickers():
    review = review_decisions(
        [
            # WINNER: 2/2 worked (eligible, >= 2 decided).
            _mem("WINNER", "BUY", "completed"),
            _mem("WINNER", "BUY", "completed"),
            # LOSER: 0/2 worked (eligible).
            _mem("LOSER", "BUY", "loss"),
            _mem("LOSER", "BUY", "loss"),
        ]
    )
    joined = " ".join(review.highlights)
    assert "WINNER" in joined
    assert "LOSER" in joined


def test_determinism_same_memory_same_review():
    memories = [
        _mem("RELIANCE", "BUY", "completed"),
        _mem("INFY", "SELL", "loss"),
    ]
    assert review_decisions(memories).model_dump() == review_decisions(memories).model_dump()


# --- /review endpoint ---------------------------------------------------


@pytest.fixture
async def client():
    set_client(AsyncMongoMockClient())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    set_client(None)


async def test_review_endpoint_requires_auth(client):
    r = await client.get("/review")
    assert r.status_code == 401


async def test_review_endpoint_returns_report(client):
    reg = await client.post("/auth/register", json={"email": "r@b.com", "password": "supersecret1"})
    token, uid = reg.json()["access_token"], reg.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.agent_memories.insert_many(
        [
            {"user_id": uid, "ticker": "RELIANCE", "action": "SELL", "quantity": 3,
             "ts": "2026-01-01T00:00:00Z", "outcome": {"result": "completed"}},
            {"user_id": uid, "ticker": "INFY", "action": "BUY", "quantity": 2,
             "ts": "2026-02-01T00:00:00Z", "outcome": {"result": "loss"}},
        ]
    )
    r = await client.get("/review", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 2
    assert body["completed"] == 1
    assert body["losses"] == 1
    assert len(body["timeline"]) == 2
    assert {e["ticker"] for e in body["by_ticker"]} == {"RELIANCE", "INFY"}
    assert body["highlights"]


async def test_review_endpoint_is_owner_scoped(client):
    reg_a = await client.post("/auth/register", json={"email": "a2@b.com", "password": "supersecret1"})
    token_a, uid_a = reg_a.json()["access_token"], reg_a.json()["user_id"]
    reg_b = await client.post("/auth/register", json={"email": "b2@b.com", "password": "supersecret1"})
    uid_b = reg_b.json()["user_id"]
    db = get_client()["vestra_test"]
    await db.agent_memories.insert_one(
        {"user_id": uid_a, "ticker": "RELIANCE", "action": "BUY", "outcome": {"result": "completed"}}
    )
    await db.agent_memories.insert_one(
        {"user_id": uid_b, "ticker": "INFY", "action": "BUY", "outcome": {"result": "loss"}}
    )
    r = await client.get("/review", headers={"Authorization": f"Bearer {token_a}"})
    assert r.status_code == 200
    assert r.json()["total"] == 1
    assert r.json()["completed"] == 1
