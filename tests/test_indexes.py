"""Test that index creation runs cleanly and is idempotent.

Uses mongomock (which accepts create_index calls). Verifies the unique
constraints we depend on actually reject duplicates, since those back
multi-tenant safety (one profile/email per user).
"""

import pytest
from mongomock_motor import AsyncMongoMockClient
from pymongo.errors import DuplicateKeyError

from app.data.indexes import create_indexes
from app.data.mongo import get_client, set_client


@pytest.fixture(autouse=True)
def _mongo():
    set_client(AsyncMongoMockClient())
    yield
    set_client(None)


async def test_create_indexes_returns_names_and_is_idempotent():
    first = await create_indexes()
    assert len(first) > 0
    # Running again must not raise.
    second = await create_indexes()
    assert first == second
    # Spot-check a couple of expected index identifiers.
    assert "users.uq_email" in first
    assert "investor_profiles.uq_user_id" in first


async def test_unique_email_index_rejects_duplicates():
    await create_indexes()
    db = get_client()["vestra_test"]
    await db.users.insert_one({"user_id": "a", "email": "dup@x.com"})
    with pytest.raises(DuplicateKeyError):
        await db.users.insert_one({"user_id": "b", "email": "dup@x.com"})
