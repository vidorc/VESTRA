"""Centralized configuration and environment validation for Vestra.

Reads settings from the environment (and a local ``.env`` file) and fails fast
with a clear, actionable message when a required variable is missing, instead of
surfacing an opaque error deep inside the Mongo client or the LLM client later.
"""

from functools import lru_cache

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated application settings.

    Required:
        GROQ_API_KEY  -- API key for the Groq LLM used by the strategy node.
        MONGODB_URI   -- MongoDB connection string (Atlas ``mongodb+srv://`` or local).

    Optional:
        DATABASE_NAME -- Mongo database name (defaults to ``vestra``).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    GROQ_API_KEY: str = Field(min_length=1)
    MONGODB_URI: str = Field(min_length=1)
    DATABASE_NAME: str = "vestra"

    # Model id kept here so it is configurable without touching node code.
    GROQ_MODEL: str = "llama-3.3-70b-versatile"

    # --- Auth / security --------------------------------------------------
    # Secret used to sign JWTs for user-facing endpoints. Required, and at least
    # 32 chars: a fintech system must not run with a default or weak signing key
    # (HS256 needs >= 32 bytes per RFC 7518). Generate with `openssl rand -hex 32`.
    JWT_SECRET: str = Field(min_length=32)
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24h access tokens

    # Shared secret for the machine-to-machine market-alert webhook. This door
    # is NOT user-authenticated (the feed has no user), so it carries its own
    # API key. Optional: when unset, the webhook rejects all calls (fail-closed).
    WEBHOOK_API_KEY: str = ""

    # --- Market data ------------------------------------------------------
    # "static" (default, no I/O) or "yfinance" (live; falls back to static).
    MARKET_DATA_PROVIDER: str = "static"

    # --- CORS -------------------------------------------------------------
    # Comma-separated list of allowed origins for the browser frontend.
    # Default "*" is fine for local dev; lock down in production.
    CORS_ORIGINS: str = "*"

    # --- Phase 1: approval / intelligence ---------------------------------
    # Default human-approval policy applied when an investor profile does not
    # specify one. One of: manual | approval_required | auto_below_threshold |
    # autonomous_sandbox.
    APPROVAL_POLICY_DEFAULT: str = "approval_required"

    # Thresholds for the auto_below_threshold policy. A trade auto-executes only
    # when overall confidence >= CONFIDENCE_THRESHOLD and risk is not "high".
    CONFIDENCE_THRESHOLD: float = 0.7
    RISK_THRESHOLD: str = "high"  # concentration level at/above which to interrupt

    # Telegram approval bot (optional). When unset, the notifier no-ops and
    # approvals remain actionable via the API / frontend.
    TELEGRAM_BOT_TOKEN: str = ""
    # Default chat id for notifications when a profile has no telegram_chat_id.
    TELEGRAM_DEFAULT_CHAT_ID: str = ""
    # Optional shared secret enforced on the Telegram webhook (set the same value
    # when registering the webhook via setWebhook's secret_token).
    TELEGRAM_WEBHOOK_SECRET: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the validated settings singleton.

    Raises:
        ConfigError: if any required environment variable is missing/empty,
            with a message naming the offending variables.
    """
    try:
        return Settings()  # type: ignore[call-arg]
    except ValidationError as exc:
        missing = sorted(
            ".".join(str(p) for p in err["loc"]) for err in exc.errors()
        )
        raise ConfigError(
            "Invalid or missing configuration for: "
            + ", ".join(missing)
            + ". Set these in your environment or .env file "
            "(see .env.example)."
        ) from exc


__all__ = ["Settings", "ConfigError", "get_settings"]
