"""Data-access layer (repository) for Vestra.

This is the real persistence logic. It used to live in ``app/mcp/server.py``
decorated as MCP tools, but the FastAPI request path never spoke MCP -- it
imported and awaited those functions directly. So the "MCP server" was really a
DAL wearing an MCP hat. This module is that DAL, made explicit; ``app/mcp/server``
is now a thin transport shim that re-exports these functions (and only actually
runs as an MCP server under ``__main__``).

Concurrency & safety notes
---------------------------
``execute_trade`` previously did a read-modify-write (find_one -> mutate in
Python -> update_one) with no atomicity. Two concurrent trades could both read
the same balance and both "succeed", corrupting cash/holdings; a retried request
double-executed. It is now:

* **Atomic** -- a single ``find_one_and_update`` whose *filter* carries the
  affordability guard (``cash_balance >= cost`` for BUY, ``holdings.TICKER >=
  qty`` for SELL). MongoDB applies the match-and-update as one document-level
  atomic operation, so the guard cannot be bypassed by interleaving. This needs
  no multi-document transaction (works on standalone Mongo and mongomock).
* **Idempotent** -- when an ``idempotency_key`` is supplied, the first call
  claims it via an insert against the implicit unique ``_id`` index; a duplicate
  call returns the stored result instead of executing again.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.agent.sectors import assess_concentration
from app.data.mongo import get_db


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_profile(user_id: str) -> Dict[str, Any]:
    try:
        db = get_db()
        profile = await db.investor_profiles.find_one({"user_id": user_id})
        if not profile:
            return {"error": "Profile not found"}
        profile.pop("_id", None)
        return profile
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


async def get_market_exposure(user_id: str) -> Dict[str, Any]:
    try:
        db = get_db()
        profile = await db.investor_profiles.find_one({"user_id": user_id})
        if not profile:
            return {"error": "Profile not found"}

        holdings = profile.get("holdings", {})
        cash = profile.get("cash_balance", 0)
        total_positions = sum(holdings.values())
        concentration = assess_concentration(holdings)

        return {
            "cash_balance": cash,
            "total_positions": total_positions,
            "concentration_risk": concentration["concentration_risk"],
            "largest_sector": concentration["largest_sector"],
            "largest_sector_exposure": concentration["largest_sector_exposure"],
            "sector_breakdown": concentration["sector_breakdown"],
        }
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


async def _claim_idempotency_key(db, user_id: str, key: str) -> Optional[Dict[str, Any]]:
    """Try to claim ``key``. Returns the stored result if already claimed, else None.

    Uses the implicit unique ``_id`` index: the first caller inserts and gets
    None (proceed); a concurrent/retried caller hits DuplicateKeyError and gets
    back whatever result the winner stored.
    """
    try:
        await db.trade_idempotency.insert_one(
            {"_id": key, "user_id": user_id, "status": "pending"}
        )
        return None
    except DuplicateKeyError:
        existing = await db.trade_idempotency.find_one({"_id": key})
        if existing and "result" in existing:
            return existing["result"]
        # Winner is still in-flight; surface a benign duplicate marker.
        return {"status": "duplicate", "message": "Trade already in progress."}


async def execute_trade(
    user_id: str,
    ticker: str,
    action: str,
    quantity: int,
    price: float,
    idempotency_key: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        db = get_db()
        ticker = ticker.upper()
        action = action.upper()

        if action not in ("BUY", "SELL"):
            return {"error": "Invalid action"}
        if quantity <= 0:
            return {"error": "Quantity must be greater than zero"}

        # Idempotency: a retried request must not execute twice.
        if idempotency_key:
            cached = await _claim_idempotency_key(db, user_id, idempotency_key)
            if cached is not None:
                return cached

        total = quantity * price
        holdings_field = f"holdings.{ticker}"

        if action == "BUY":
            # Guard (cash >= cost) lives in the filter -> match-and-update is
            # one atomic op. Concurrent BUYs cannot both overspend.
            updated = await db.investor_profiles.find_one_and_update(
                {"user_id": user_id, "cash_balance": {"$gte": total}},
                {"$inc": {"cash_balance": -total, holdings_field: quantity}},
                return_document=ReturnDocument.AFTER,
            )
        else:  # SELL
            updated = await db.investor_profiles.find_one_and_update(
                {"user_id": user_id, holdings_field: {"$gte": quantity}},
                {"$inc": {"cash_balance": total, holdings_field: -quantity}},
                return_document=ReturnDocument.AFTER,
            )

        if updated is None:
            # Disambiguate: missing profile vs. failed affordability guard.
            exists = await db.investor_profiles.find_one(
                {"user_id": user_id}, {"_id": 1}
            )
            if not exists:
                result: Dict[str, Any] = {"error": "Profile not found"}
            elif action == "BUY":
                result = {"error": "Insufficient balance"}
            else:
                result = {"error": "Insufficient holdings"}
        else:
            result = {
                "status": "success",
                "ticker": ticker,
                "action": action,
                "quantity": quantity,
                "updated_cash": updated.get("cash_balance"),
            }

        # Record the outcome against the idempotency key so retries replay it.
        if idempotency_key:
            await db.trade_idempotency.update_one(
                {"_id": idempotency_key},
                {"$set": {"status": "done", "result": result}},
            )

        return result
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


async def reject_trade(user_id: str, ticker: str, reason: str) -> Dict[str, Any]:
    try:
        db = get_db()
        result = await db.rejected_trades.insert_one(
            {"user_id": user_id, "ticker": ticker, "reason": reason}
        )
        return {"status": "rejected_logged", "id": str(result.inserted_id)}
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


async def log_reasoning(
    user_id: str, agent_name: str, action: str, payload: dict
) -> Dict[str, Any]:
    try:
        db = get_db()
        result = await db.agent_audit_logs.insert_one(
            {
                "user_id": user_id,
                "agent_name": agent_name,
                "action": action,
                "payload": payload,
            }
        )
        return {"status": "logged", "id": str(result.inserted_id)}
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


# --- User accounts -------------------------------------------------------

async def create_user(email: str, password_hash: str) -> Dict[str, Any]:
    """Create a user account + a minimal investor profile, scoped by user_id.

    Returns ``{"error": "Email already registered"}`` if the email is taken.
    The investor profile is seeded with conservative defaults so the workflow
    and portfolio endpoints work immediately after sign-up.
    """
    import uuid

    db = get_db()
    email = email.strip().lower()
    try:
        existing = await db.users.find_one({"email": email})
        if existing:
            return {"error": "Email already registered"}

        user_id = uuid.uuid4().hex
        try:
            await db.users.insert_one(
                {
                    "user_id": user_id,
                    "email": email,
                    "password_hash": password_hash,
                }
            )
        except DuplicateKeyError:
            # Lost a race against the unique email index.
            return {"error": "Email already registered"}

        # Seed a default investor profile (one per user, keyed by user_id).
        await db.investor_profiles.update_one(
            {"user_id": user_id},
            {
                "$setOnInsert": {
                    "user_id": user_id,
                    "risk_tolerance": "conservative",
                    "cash_balance": 0.0,
                    "holdings": {},
                    "target_allocation": {},
                }
            },
            upsert=True,
        )
        return {"user_id": user_id, "email": email}
    except Exception as e:  # pragma: no cover - defensive
        return {"error": str(e)}


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    user = await db.users.find_one({"email": email.strip().lower()})
    if user:
        user["_id"] = str(user["_id"])
    return user


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    user = await db.users.find_one({"user_id": user_id})
    if user:
        user["_id"] = str(user["_id"])
    return user


async def get_audit_logs(user_id: str, limit: int = 100) -> list:
    """Return recent audit-log entries for a user, newest first."""
    db = get_db()
    cursor = (
        db.agent_audit_logs.find({"user_id": user_id})
        .sort("_id", -1)
        .limit(limit)
    )
    out = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out


# --- Market events / fan-out ---------------------------------------------

async def record_market_event(event: Dict[str, Any]) -> str:
    """Persist an incoming market event (the global ingest record). Returns its id."""
    db = get_db()
    result = await db.market_events.insert_one(dict(event))
    return str(result.inserted_id)


async def find_impacted_user_ids(ticker: str, impacted_assets: Optional[list] = None) -> list:
    """Return user_ids whose portfolios are exposed to this event.

    A user is impacted if they hold the event ticker (or any of the broader
    impacted_assets a macro event resolves to, e.g. NIFTY50/BANKNIFTY). This
    replaces the previous hardcoded ``user_001`` -- the webhook fans out to every
    affected tenant. Holdings are stored as a ``holdings.<TICKER>`` sub-document,
    so existence of that key means a non-zero position.
    """
    db = get_db()
    tickers = {ticker.upper()}
    for a in impacted_assets or []:
        tickers.add(str(a).upper())

    # Match a profile if any of the relevant holdings.<TICKER> keys exist.
    or_clauses = [{f"holdings.{t}": {"$exists": True}} for t in tickers]
    cursor = db.investor_profiles.find({"$or": or_clauses}, {"user_id": 1, "_id": 0})
    return [doc["user_id"] async for doc in cursor]


async def get_recent_market_events(limit: int = 25) -> List[Dict[str, Any]]:
    """Return the most recent market events (newest first) for regime aggregation."""
    db = get_db()
    cursor = db.market_events.find().sort("_id", -1).limit(limit)
    out = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out


# --- Simulation results --------------------------------------------------

async def save_simulation_result(
    user_id: str, simulation: Dict[str, Any], event_id: Optional[str] = None
) -> str:
    """Persist a scenario-simulation result for a user/event. Returns its id."""
    db = get_db()
    doc = {"user_id": user_id, "event_id": event_id, "ts": _utcnow(), **simulation}
    result = await db.simulation_results.insert_one(doc)
    return str(result.inserted_id)


async def list_simulations(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """List a user's simulation results, newest first."""
    db = get_db()
    cursor = db.simulation_results.find({"user_id": user_id}).sort("ts", -1).limit(limit)
    out = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out


# --- Digital twin --------------------------------------------------------

async def upsert_digital_twin(user_id: str, twin: Dict[str, Any]) -> Dict[str, Any]:
    """Create or update the user's financial digital twin (one per user)."""
    db = get_db()
    await db.digital_twins.update_one(
        {"user_id": user_id},
        {"$set": {**twin, "user_id": user_id, "updated_at": _utcnow()}},
        upsert=True,
    )
    doc = await db.digital_twins.find_one({"user_id": user_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc or {}


async def get_digital_twin(user_id: str) -> Optional[Dict[str, Any]]:
    """Return the user's digital twin, or None if not yet set."""
    db = get_db()
    doc = await db.digital_twins.find_one({"user_id": user_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


# --- Goals ---------------------------------------------------------------

async def create_goal(user_id: str, goal: Dict[str, Any]) -> Dict[str, Any]:
    """Create a financial goal for a user. Returns the stored goal (with goal_id)."""
    import uuid

    db = get_db()
    goal_id = uuid.uuid4().hex
    doc = {**goal, "goal_id": goal_id, "user_id": user_id, "ts": _utcnow()}
    await db.goals.insert_one(doc)
    doc["_id"] = str(doc["_id"]) if "_id" in doc else None
    return doc


async def list_goals(user_id: str) -> List[Dict[str, Any]]:
    """List a user's goals, newest first."""
    db = get_db()
    cursor = db.goals.find({"user_id": user_id}).sort("ts", -1)
    out = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out


async def update_goal(
    user_id: str, goal_id: str, updates: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Update a user's goal (ownership-scoped). Returns the updated goal or None."""
    db = get_db()
    # Never allow the caller to move the goal to another user / change its id.
    updates = {k: v for k, v in updates.items() if k not in ("user_id", "goal_id", "_id")}
    doc = await db.goals.find_one_and_update(
        {"user_id": user_id, "goal_id": goal_id},
        {"$set": updates},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def delete_goal(user_id: str, goal_id: str) -> bool:
    """Delete a user's goal (ownership-scoped). Returns True if one was removed."""
    db = get_db()
    result = await db.goals.delete_one({"user_id": user_id, "goal_id": goal_id})
    return result.deleted_count > 0


# --- Research context ----------------------------------------------------

async def save_research_context(
    user_id: str, research: Dict[str, Any], event_id: Optional[str] = None
) -> str:
    """Persist a research-context document for a user/event. Returns its id."""
    db = get_db()
    doc = {"user_id": user_id, "event_id": event_id, "ts": _utcnow(), **research}
    result = await db.research_context.insert_one(doc)
    return str(result.inserted_id)


# --- Agent memories (Phase 5) --------------------------------------------

async def save_agent_memory(user_id: str, memory: Dict[str, Any]) -> str:
    """Persist one agent memory (a past decision + optional outcome). Returns its id."""
    db = get_db()
    doc = {"user_id": user_id, "ts": _utcnow(), **memory}
    result = await db.agent_memories.insert_one(doc)
    return str(result.inserted_id)


async def list_agent_memories(
    user_id: str, ticker: Optional[str] = None, limit: int = 20
) -> List[Dict[str, Any]]:
    """List a user's agent memories (newest first), optionally scoped to a ticker."""
    db = get_db()
    query: Dict[str, Any] = {"user_id": user_id}
    if ticker:
        query["ticker"] = ticker.upper()
    cursor = db.agent_memories.find(query).sort([("ts", -1), ("_id", -1)]).limit(limit)
    out = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out


# --- Reasoning traces ----------------------------------------------------
async def save_reasoning_trace(
    user_id: str, trace: Dict[str, Any], event_id: Optional[str] = None
) -> str:
    """Persist a full agent reasoning trace for a user/decision. Returns its id.

    A trace is the complete chain produced for one decision (signal, research,
    risk, decision, reflection, confidence, validation). Captured once per run by
    the validator node so every decision is inspectable afterwards.
    """
    db = get_db()
    doc = {"user_id": user_id, "event_id": event_id, "ts": _utcnow(), **trace}
    result = await db.reasoning_traces.insert_one(doc)
    return str(result.inserted_id)


async def list_reasoning_traces(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """List a user's reasoning traces, newest first.

    Sorts by ``ts`` then ``_id`` (both descending) so traces written within the
    same clock tick still order deterministically by insertion (ObjectId is
    monotonic).
    """
    db = get_db()
    cursor = (
        db.reasoning_traces.find({"user_id": user_id})
        .sort([("ts", -1), ("_id", -1)])
        .limit(limit)
    )
    out = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out


# --- Agent observability (node execution spans) --------------------------
async def save_agent_event(user_id: str, event: Dict[str, Any]) -> str:
    """Persist one node-execution span for observability. Returns its id.

    A span records a single graph node's run: its name, duration, status, and an
    optional error. Written best-effort by the instrumented node wrapper — it
    must never break the workflow.
    """
    db = get_db()
    doc = {"user_id": user_id, "ts": _utcnow(), **event}
    result = await db.agent_events.insert_one(doc)
    return str(result.inserted_id)


async def list_agent_events(user_id: str, limit: int = 500) -> List[Dict[str, Any]]:
    """List a user's recent node-execution spans, newest first."""
    db = get_db()
    cursor = (
        db.agent_events.find({"user_id": user_id})
        .sort([("ts", -1), ("_id", -1)])
        .limit(limit)
    )
    out = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out


# --- Approval requests ---------------------------------------------------

async def create_approval_request(
    thread_id: str,
    user_id: str,
    decision: Dict[str, Any],
    confidence: Optional[Dict[str, Any]] = None,
    reflection: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> tuple[str, bool]:
    """Idempotently create (or refresh) a pending approval request.

    Keyed by ``thread_id``: LangGraph's ``interrupt()`` re-runs the approval node
    on resume, so a plain insert would create duplicates. We upsert instead, and
    only (re)set pending state on first insert via ``$setOnInsert`` -- a request
    already decided by a human is never silently reverted to pending.

    Returns ``(approval_id, created)`` where ``created`` is True only on the first
    insert. The approval node uses ``created`` to send the human notification
    exactly once, even though the node body re-executes on resume.
    """
    db = get_db()
    now = _utcnow()
    result = await db.approval_requests.update_one(
        {"thread_id": thread_id},
        {
            "$set": {
                "user_id": user_id,
                "event_id": event_id,
                "decision": decision,
                "confidence": confidence,
                "reflection": reflection,
                "updated_at": now,
            },
            "$setOnInsert": {
                "thread_id": thread_id,
                "status": "pending",
                "ts": now,
            },
        },
        upsert=True,
    )
    created = result.upserted_id is not None
    if created:
        return str(result.upserted_id), True
    doc = await db.approval_requests.find_one({"thread_id": thread_id}, {"_id": 1})
    return (str(doc["_id"]) if doc else thread_id), False


async def get_approval(approval_id: str) -> Optional[Dict[str, Any]]:
    """Fetch an approval by its document id (string ObjectId)."""
    db = get_db()
    try:
        oid = ObjectId(approval_id)
    except (InvalidId, TypeError):
        return None
    doc = await db.approval_requests.find_one({"_id": oid})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def get_approval_by_thread(thread_id: str) -> Optional[Dict[str, Any]]:
    db = get_db()
    doc = await db.approval_requests.find_one({"thread_id": thread_id})
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


async def list_approvals(
    user_id: str, status: Optional[str] = None, limit: int = 100
) -> List[Dict[str, Any]]:
    """List a user's approval requests, newest first, optionally filtered by status."""
    db = get_db()
    query: Dict[str, Any] = {"user_id": user_id}
    if status:
        query["status"] = status
    cursor = db.approval_requests.find(query).sort("ts", -1).limit(limit)
    out = []
    async for doc in cursor:
        doc["_id"] = str(doc["_id"])
        out.append(doc)
    return out


async def update_approval_status(
    approval_id: str, status: str, reason: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Set an approval's status (approved/rejected) atomically, only if pending.

    Returns the updated document, or ``None`` if not found / not pending (so a
    double-decision is a no-op rather than flipping an already-decided request).
    """
    db = get_db()
    try:
        oid = ObjectId(approval_id)
    except (InvalidId, TypeError):
        return None
    doc = await db.approval_requests.find_one_and_update(
        {"_id": oid, "status": "pending"},
        {"$set": {"status": status, "reason": reason, "decided_at": _utcnow()}},
        return_document=ReturnDocument.AFTER,
    )
    if doc:
        doc["_id"] = str(doc["_id"])
    return doc


__all__ = [
    "get_profile",
    "get_market_exposure",
    "execute_trade",
    "reject_trade",
    "log_reasoning",
    "create_user",
    "get_user_by_email",
    "get_user_by_id",
    "get_audit_logs",
    "record_market_event",
    "find_impacted_user_ids",
    "get_recent_market_events",
    "save_simulation_result",
    "list_simulations",
    "save_research_context",
    "save_agent_memory",
    "list_agent_memories",
    "save_reasoning_trace",
    "list_reasoning_traces",
    "save_agent_event",
    "list_agent_events",
    "create_approval_request",
    "get_approval",
    "get_approval_by_thread",
    "list_approvals",
    "update_approval_status",
    "upsert_digital_twin",
    "get_digital_twin",
    "create_goal",
    "list_goals",
    "update_goal",
    "delete_goal",
]
