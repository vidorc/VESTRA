"""Index definitions and creation for Vestra's MongoDB collections.

Single source of truth used by both the FastAPI lifespan (create indexes on
startup) and the standalone ``app/scripts/create_indexes.py`` script. Index
creation is idempotent in MongoDB, so running it repeatedly is safe.

Covers collections in use today plus the reserved V2 collections, so queries are
index-backed from the start instead of full-collection scans as data grows.
"""

from typing import List, Tuple

from pymongo import ASCENDING, DESCENDING

from app.data.mongo import get_db

# Each entry: (collection, keys, options). ``keys`` is a pymongo key spec.
_INDEXES: List[Tuple[str, List[Tuple[str, int]], dict]] = [
    # Accounts.
    ("users", [("email", ASCENDING)], {"unique": True, "name": "uq_email"}),
    ("users", [("user_id", ASCENDING)], {"unique": True, "name": "uq_user_id"}),
    # One profile per user.
    ("investor_profiles", [("user_id", ASCENDING)], {"unique": True, "name": "uq_user_id"}),
    # Audit / logs, newest-first per user.
    ("agent_audit_logs", [("user_id", ASCENDING), ("_id", DESCENDING)], {"name": "user_recent"}),
    ("rejected_trades", [("user_id", ASCENDING), ("_id", DESCENDING)], {"name": "user_recent"}),
    # Observability events (Phase 1).
    ("agent_events", [("user_id", ASCENDING), ("ts", DESCENDING)], {"name": "user_ts"}),
    # Reserved V2 collections — index now so later phases inherit fast queries.
    ("market_events", [("ticker", ASCENDING), ("ts", DESCENDING)], {"name": "ticker_ts"}),
    ("research_context", [("user_id", ASCENDING), ("ts", DESCENDING)], {"name": "user_ts"}),
    ("trade_decisions", [("user_id", ASCENDING), ("ts", DESCENDING)], {"name": "user_ts"}),
    ("trade_executions", [("user_id", ASCENDING), ("ts", DESCENDING)], {"name": "user_ts"}),
    ("portfolio_snapshots", [("user_id", ASCENDING), ("ts", DESCENDING)], {"name": "user_ts"}),
    ("agent_memories", [("user_id", ASCENDING), ("ticker", ASCENDING), ("ts", DESCENDING)], {"name": "user_ticker_ts"}),
    ("simulation_results", [("user_id", ASCENDING), ("ts", DESCENDING)], {"name": "user_ts"}),
    (
        "approval_requests",
        [("user_id", ASCENDING), ("status", ASCENDING), ("ts", DESCENDING)],
        {"name": "user_status_ts"},
    ),
    # Phase 4: digital twin (one per user) + goals.
    ("digital_twins", [("user_id", ASCENDING)], {"unique": True, "name": "uq_user_id"}),
    ("goals", [("user_id", ASCENDING), ("ts", DESCENDING)], {"name": "user_ts"}),
    ("goals", [("user_id", ASCENDING), ("goal_id", ASCENDING)], {"name": "user_goal"}),
]


async def create_indexes() -> List[str]:
    """Create all defined indexes (idempotent). Returns the index names created/ensured."""
    db = get_db()
    created: List[str] = []
    for collection, keys, options in _INDEXES:
        await db[collection].create_index(keys, **options)
        created.append(f"{collection}.{options.get('name')}")
    return created


__all__ = ["create_indexes"]
