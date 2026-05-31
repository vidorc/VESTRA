"""MongoDB client/database factories for Vestra.

The Motor client is created lazily on first use (inside the running event loop,
which Motor requires) and cached process-wide. A ``set_client`` seam lets the
test suite inject a fake client (e.g. mongomock) without real configuration.

This module is the single home of the Mongo connection so that the repository
layer, the FastAPI lifespan (index creation), and the optional MCP transport
all share one client instead of each constructing their own.
"""

from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config import get_settings

_client: Optional[AsyncIOMotorClient] = None


def get_client() -> AsyncIOMotorClient:
    """Return the process-wide Motor client, creating it lazily on first use."""
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_settings().MONGODB_URI)
    return _client


def get_db() -> AsyncIOMotorDatabase:
    """Return the configured Mongo database handle."""
    return get_client()[get_settings().DATABASE_NAME]


def set_client(client: Optional[AsyncIOMotorClient]) -> None:
    """Test seam: inject a client (e.g. mongomock) or reset the cache with ``None``."""
    global _client
    _client = client


__all__ = ["get_client", "get_db", "set_client"]
