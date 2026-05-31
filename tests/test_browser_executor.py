"""Tests for Phase 3 autonomous execution (paper/demo browser executor).

The browser executor produces *execution evidence* (a confirmation record, and in
demo mode a screenshot) for a decision. Two safe modes:

* **paper** (default): pure deterministic simulation. No browser, no I/O, fully
  reproducible. This is what runs in tests and CI.
* **demo**: lazily drives a headless browser to capture a screenshot as audit
  evidence. Degrades gracefully to a paper-style record if the browser library
  is unavailable -- so it never crashes the execution path.

A real-money / live broker mode is deliberately NOT implemented: the executor
refuses it. Autonomous execution against real funds is out of scope and unsafe to
build blind.
"""

import pytest


# --- paper mode ----------------------------------------------------------

async def test_paper_mode_returns_deterministic_evidence():
    from app.agent.nodes.browser_executor import execute_via_browser

    ev = await execute_via_browser("RELIANCE", "SELL", 3, 2500.0, mode="paper")
    assert ev["mode"] == "paper"
    assert ev["status"] == "simulated"
    assert ev["ticker"] == "RELIANCE"
    assert ev["action"] == "SELL"
    assert ev["quantity"] == 3
    assert ev["price"] == 2500.0
    assert ev["notional"] == 7500.0
    assert ev["confirmation_id"]  # a synthetic broker confirmation ref
    assert ev["screenshot"] is None  # paper mode never touches a browser


async def test_paper_mode_is_reproducible():
    from app.agent.nodes.browser_executor import execute_via_browser

    a = await execute_via_browser("INFY", "BUY", 5, 1500.0, mode="paper")
    b = await execute_via_browser("INFY", "BUY", 5, 1500.0, mode="paper")
    # Same inputs -> same synthetic confirmation (deterministic, auditable).
    assert a["confirmation_id"] == b["confirmation_id"]


async def test_paper_mode_hold_is_no_action():
    from app.agent.nodes.browser_executor import execute_via_browser

    ev = await execute_via_browser("RELIANCE", "HOLD", 0, 2500.0, mode="paper")
    assert ev["status"] == "no_action"


# --- demo mode (graceful degradation) ------------------------------------

async def test_demo_mode_degrades_when_browser_unavailable():
    """Playwright isn't installed in this env; demo must degrade, not crash."""
    from app.agent.nodes.browser_executor import execute_via_browser

    ev = await execute_via_browser("RELIANCE", "SELL", 2, 2500.0, mode="demo")
    # Still returns usable evidence; flags that the browser path was skipped.
    assert ev["ticker"] == "RELIANCE"
    assert ev["status"] in ("simulated", "captured")
    assert "note" in ev or ev["screenshot"] is not None


# --- safety: live mode refused -------------------------------------------

async def test_live_mode_is_refused():
    from app.agent.nodes.browser_executor import execute_via_browser

    ev = await execute_via_browser("RELIANCE", "BUY", 1, 2500.0, mode="live")
    assert ev["status"] == "refused"
    assert "error" in ev


# --- integration: execution node attaches evidence -----------------------

@pytest.fixture
async def mongo():
    from mongomock_motor import AsyncMongoMockClient

    from app.data.mongo import set_client

    client = AsyncMongoMockClient()
    set_client(client)
    db = client["vestra_test"]
    await db.investor_profiles.insert_one(
        {
            "user_id": "u1",
            "risk_tolerance": "moderate",
            "cash_balance": 100000.0,
            "holdings": {"RELIANCE": 20},
            "target_allocation": {},
        }
    )
    yield db
    set_client(None)


async def test_execute_trade_decision_includes_browser_evidence(mongo):
    from app.agent.nodes.execution import execute_trade_decision

    result = await execute_trade_decision("u1", "SELL", "RELIANCE", 3, price=2500.0)
    assert result["status"] == "success"
    assert "evidence" in result
    assert result["evidence"]["mode"] == "paper"
    assert result["evidence"]["confirmation_id"]
