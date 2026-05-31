"""Seed the database with demo users, profiles, and indexes (run manually).

NOT collected by pytest. Run against a configured stack:

    python -m tests.seed_db        # or: python tests/seed_db.py

Reuses the application layer so seeded data matches production shape:
* ``create_indexes()`` ensures all indexes exist (idempotent).
* ``create_user()`` creates a real, loginable account (PBKDF2-hashed password)
  plus a default investor profile, scoped by a generated ``user_id``.

Multi-tenant from the start: there is no hardcoded ``user_001``. Each demo user
gets a generated id; the printed credentials let you log in via /auth/login.
"""

import asyncio

# Ensure .env is loaded for standalone runs (pydantic-settings also reads it,
# but this keeps behavior obvious when run directly).
from dotenv import load_dotenv

load_dotenv()

from app.auth.jwt import hash_password  # noqa: E402
from app.data.indexes import create_indexes  # noqa: E402
from app.data.mongo import get_db  # noqa: E402
from app.data.repository import create_user  # noqa: E402

_DEMO_PASSWORD = "demo-password-123"

# Each demo user: email -> profile fields to apply after account creation.
_DEMO_USERS = {
    "moderate@vestra.dev": {
        "risk_tolerance": "moderate",
        "cash_balance": 100000.0,
        "holdings": {"RELIANCE": 20, "INFY": 15, "HDFCBANK": 10},
        "target_allocation": {"RELIANCE": 30, "INFY": 20, "HDFCBANK": 20},
    },
    "aggressive@vestra.dev": {
        "risk_tolerance": "aggressive",
        "cash_balance": 250000.0,
        "holdings": {"ADANIENT": 30, "TCS": 10},
        "target_allocation": {"ADANIENT": 40, "TCS": 30},
    },
    "conservative@vestra.dev": {
        "risk_tolerance": "conservative",
        "cash_balance": 50000.0,
        "holdings": {"ITC": 50, "HINDUNILVR": 5},
        "target_allocation": {"ITC": 50, "HINDUNILVR": 30},
    },
}


async def seed() -> None:
    names = await create_indexes()
    print(f"Ensured {len(names)} indexes.")

    db = get_db()
    for email, profile in _DEMO_USERS.items():
        result = await create_user(email, hash_password(_DEMO_PASSWORD))
        if "error" in result:
            # Already seeded — look up the existing user_id to apply profile.
            existing = await db.users.find_one({"email": email})
            user_id = existing["user_id"] if existing else None
            note = "(exists, updating profile)"
        else:
            user_id = result["user_id"]
            note = "(created)"

        if user_id:
            await db.investor_profiles.update_one(
                {"user_id": user_id}, {"$set": profile}
            )
            print(f"  {email}  ->  {user_id}  {note}")

    print(f"\nDemo password for all seeded users: {_DEMO_PASSWORD}")
    print("Log in via POST /auth/login to obtain a JWT.")


if __name__ == "__main__":
    asyncio.run(seed())
