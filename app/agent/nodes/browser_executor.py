"""Browser execution node (Phase 3) -- autonomous execution evidence.

The master prompt's Phase 3 is "OpenClaw" browser execution: the agent drives a
broker UI to place a trade and captures evidence (a confirmation, a screenshot)
for the audit trail. This module provides that seam in two SAFE modes:

* **paper** (default): a pure, deterministic simulation. It computes the notional
  and a synthetic, reproducible confirmation id from the order details -- no
  browser, no network, no real order. This is what runs in tests and CI and what
  backs the existing paper-trading execution path.
* **demo**: lazily drives a headless browser (Playwright) to open a page and
  capture a screenshot as audit evidence, then records a paper-style fill. If the
  browser library isn't installed, it DEGRADES to a paper record with a note --
  it never crashes the execution path.

A **live** / real-money broker mode is deliberately refused. Placing real orders
against a real brokerage autonomously is out of scope and unsafe to build without
a vetted broker integration, credentials handling, and explicit operator opt-in.
"""

import hashlib
from typing import Any, Dict, Optional

# A stable, non-secret demo target. Captured purely as audit evidence that the
# browser path ran; it is never a real broker order ticket.
_DEMO_URL = "https://example.com/"


def _confirmation_id(ticker: str, action: str, quantity: int, price: float) -> str:
    """A deterministic synthetic broker confirmation ref for an order.

    Derived from the order details so the same order always yields the same id --
    reproducible and auditable, and safe in tests (no randomness/clock).
    """
    raw = f"{ticker.upper()}:{action.upper()}:{quantity}:{price:.2f}"
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12].upper()
    return f"PAPER-{digest}"


def _paper_evidence(
    ticker: str, action: str, quantity: int, price: float, mode: str = "paper"
) -> Dict[str, Any]:
    """Build a deterministic paper-fill evidence record."""
    action = action.upper()
    if action == "HOLD" or quantity <= 0:
        return {
            "mode": mode,
            "status": "no_action",
            "ticker": ticker.upper(),
            "action": action,
            "quantity": quantity,
            "price": price,
            "notional": 0.0,
            "confirmation_id": None,
            "screenshot": None,
        }
    return {
        "mode": mode,
        "status": "simulated",
        "ticker": ticker.upper(),
        "action": action,
        "quantity": quantity,
        "price": price,
        "notional": round(quantity * price, 2),
        "confirmation_id": _confirmation_id(ticker, action, quantity, price),
        "screenshot": None,
    }


async def _capture_demo_screenshot() -> Optional[str]:
    """Drive a headless browser to capture a screenshot path; None if unavailable.

    Lazily imports Playwright so the dependency is optional. Any failure (library
    missing, no browser binary, launch error) returns None so the caller degrades
    to a paper record rather than crashing.
    """
    try:
        from playwright.async_api import async_playwright
    except Exception:
        return None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            try:
                page = await browser.new_page()
                await page.goto(_DEMO_URL, wait_until="domcontentloaded")
                path = "/tmp/vestra_demo_execution.png"
                await page.screenshot(path=path)
                return path
            finally:
                await browser.close()
    except Exception:
        return None


async def execute_via_browser(
    ticker: str,
    action: str,
    quantity: int,
    price: float,
    mode: str = "paper",
) -> Dict[str, Any]:
    """Produce execution evidence for an order in a SAFE mode.

    Modes: ``paper`` (deterministic simulation, default), ``demo`` (screenshot +
    paper fill, degrades gracefully), ``live`` (refused).
    """
    mode = (mode or "paper").lower()

    if mode == "live":
        return {
            "mode": "live",
            "status": "refused",
            "ticker": ticker.upper(),
            "action": action.upper(),
            "error": "Live real-money execution is not supported. Use paper or demo mode.",
            "screenshot": None,
        }

    if mode == "demo":
        evidence = _paper_evidence(ticker, action, quantity, price, mode="demo")
        if evidence["status"] == "no_action":
            return evidence
        screenshot = await _capture_demo_screenshot()
        if screenshot is not None:
            evidence["status"] = "captured"
            evidence["screenshot"] = screenshot
        else:
            evidence["note"] = "Browser unavailable; recorded a paper fill instead."
        return evidence

    # Default: paper.
    return _paper_evidence(ticker, action, quantity, price, mode="paper")


__all__ = ["execute_via_browser"]
