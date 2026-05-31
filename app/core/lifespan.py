"""Application lifespan: validate config at boot, ensure DB indexes.

Replaces the deprecated ``@app.on_event("startup")`` hook with a lifespan
context manager. Config validation fails fast (a misconfigured fintech app must
not start). Index creation is best-effort: a transient Mongo hiccup at boot
should not take the whole API down, since indexes are idempotent and can be
created on the next start or via the standalone script.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_settings
from app.data.indexes import create_indexes

logger = logging.getLogger("vestra")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast if required configuration is missing/invalid.
    get_settings()

    # Best-effort index creation (idempotent). Don't crash the app on a
    # transient DB error at boot.
    try:
        names = await create_indexes()
        logger.info("Ensured %d MongoDB indexes.", len(names))
    except Exception as exc:  # pragma: no cover - depends on live DB
        logger.warning("Index creation skipped (will retry next boot): %s", exc)

    yield


__all__ = ["lifespan"]
