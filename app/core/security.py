"""Security middleware: CORS and rate limiting.

A single ``Limiter`` instance is shared across the app (routes reference it via
``app.state.limiter``). CORS origins are configurable; the default is permissive
for local dev but should be locked down in production via ``CORS_ORIGINS``.

CORS origins are read directly from the environment (not via the full ``Settings``
model) so installing security does not force config validation at import time --
that stays in the lifespan, the single fail-fast point.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Shared limiter keyed by client IP. Routes opt in with @limiter.limit("N/unit").
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])


def _cors_origins_from_env() -> list[str]:
    raw = os.environ.get("CORS_ORIGINS", "*")
    return [o.strip() for o in raw.split(",") if o.strip()] or ["*"]


def install_security(app: FastAPI, cors_origins: list[str] | None = None) -> None:
    """Attach the rate limiter and CORS middleware to ``app``."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or _cors_origins_from_env(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


__all__ = ["limiter", "install_security"]
