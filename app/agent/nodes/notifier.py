"""Notifier node — delivers human-facing notifications for the agent workflow.

Previously an empty stub. It now delegates to the Telegram integration
(``app.integrations.telegram.bot``) and is the single place the graph calls to
notify a human. It is intentionally tolerant: if Telegram is not configured, or
the user has no chat id, or the send fails, it returns a status dict and never
raises -- a notification problem must not break decision execution.

Chat-id resolution order: the investor profile's ``telegram_chat_id`` (per-user),
then the ``TELEGRAM_DEFAULT_CHAT_ID`` config fallback (useful for single-operator
/ demo setups).
"""

from typing import Any, Dict, Optional

from app.config import get_settings
from app.integrations.telegram import bot
from app.models.schemas import ConfidenceScore, TradeDecision


async def _resolve_chat_id(user_id: str) -> Optional[str]:
    """Return the Telegram chat id for a user, or the configured default."""
    # Imported here to avoid a circular import (repository -> sectors -> …).
    from app.data.repository import get_profile

    try:
        profile = await get_profile(user_id)
        if isinstance(profile, dict) and "error" not in profile:
            chat_id = profile.get("telegram_chat_id")
            if chat_id:
                return str(chat_id)
    except Exception:
        pass
    default = get_settings().TELEGRAM_DEFAULT_CHAT_ID
    return str(default) if default else None


async def notify_approval_request(
    user_id: str,
    approval_id: str,
    decision: TradeDecision,
    confidence: Optional[ConfidenceScore] = None,
) -> Dict[str, Any]:
    """Notify the user that a trade needs approval (Telegram inline buttons)."""
    if not bot.is_configured():
        return {"status": "skipped", "reason": "telegram not configured"}
    chat_id = await _resolve_chat_id(user_id)
    if not chat_id:
        return {"status": "skipped", "reason": "no chat id for user"}
    return await bot.send_approval_request(
        chat_id,
        approval_id,
        ticker=decision.ticker,
        action=decision.action,
        quantity=decision.quantity,
        reasoning=decision.reasoning,
        confidence=confidence.overall if confidence else None,
    )


async def notify_alert(user_id: str, title: str, body: str) -> Dict[str, Any]:
    """Send a risk alert / daily summary / portfolio summary to the user."""
    if not bot.is_configured():
        return {"status": "skipped", "reason": "telegram not configured"}
    chat_id = await _resolve_chat_id(user_id)
    if not chat_id:
        return {"status": "skipped", "reason": "no chat id for user"}
    return await bot.send_alert(chat_id, title, body)


__all__ = ["notify_approval_request", "notify_alert"]
