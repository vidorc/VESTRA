"""Telegram Bot API client for the human-approval workflow.

Uses the HTTP Bot API directly via ``httpx`` (already a project dependency)
rather than ``python-telegram-bot``'s polling runner: the approval callbacks
arrive through our own FastAPI webhook (``/telegram/webhook``), so we only need
outbound ``sendMessage`` / ``answerCallbackQuery`` calls plus callback parsing.
This keeps the integration small and easy to mock in tests.

Everything is **config-gated**: when ``TELEGRAM_BOT_TOKEN`` is unset, all sends
become no-ops (returning ``{"skipped": ...}``) so the system runs fully without
Telegram -- approvals stay actionable via the REST API. ``send_message`` is the
single network seam; tests patch it.

Inline-button callback data is encoded as ``"<action>:<approval_id>"`` where
action is ``approve`` or ``reject``.
"""

from typing import Any, Dict, Optional, Tuple

import httpx

from app.config import get_settings

_API_BASE = "https://api.telegram.org/bot{token}/{method}"
_TIMEOUT = 8.0


def is_configured() -> bool:
    """True when a bot token is present (Telegram features are enabled)."""
    return bool(get_settings().TELEGRAM_BOT_TOKEN)


async def _call(method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Call a Telegram Bot API method. Returns the parsed JSON or an error dict.

    No-ops (without error) when the bot is not configured. Network failures are
    swallowed into an error dict so notification problems never break the graph.
    """
    settings = get_settings()
    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return {"skipped": "telegram not configured"}
    url = _API_BASE.format(token=token, method=method)
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            return resp.json()
    except Exception as exc:  # pragma: no cover - network failure path
        return {"error": str(exc)}


async def send_message(
    chat_id: str,
    text: str,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Send a Markdown message, optionally with an inline keyboard. The seam tests patch."""
    if not chat_id:
        return {"skipped": "no chat_id"}
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return await _call("sendMessage", payload)


def _approval_keyboard(approval_id: str) -> Dict[str, Any]:
    return {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve:{approval_id}"},
                {"text": "❌ Reject", "callback_data": f"reject:{approval_id}"},
            ]
        ]
    }


async def send_approval_request(
    chat_id: str,
    approval_id: str,
    *,
    ticker: str,
    action: str,
    quantity: int,
    reasoning: str,
    confidence: Optional[float] = None,
) -> Dict[str, Any]:
    """Send a trade-approval message with Approve/Reject inline buttons."""
    conf_line = f"\n*Confidence:* {round(confidence * 100)}%" if confidence is not None else ""
    text = (
        f"*Vestra — Trade Approval*\n\n"
        f"*{action} {quantity} {ticker}*{conf_line}\n\n"
        f"_{reasoning}_\n\n"
        f"Approve or reject below."
    )
    return await send_message(chat_id, text, reply_markup=_approval_keyboard(approval_id))


async def send_alert(chat_id: str, title: str, body: str) -> Dict[str, Any]:
    """Send a plain risk/alert/summary message (no buttons)."""
    return await send_message(chat_id, f"*Vestra — {title}*\n\n{body}")


async def answer_callback(callback_query_id: str, text: str = "") -> Dict[str, Any]:
    """Acknowledge a button press so Telegram stops showing the loading spinner."""
    return await _call(
        "answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text}
    )


def parse_callback(update: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    """Parse a Telegram webhook update into ``(action, approval_id, callback_query_id)``.

    Returns ``None`` if the update is not a recognized approve/reject button press.
    """
    cq = update.get("callback_query")
    if not isinstance(cq, dict):
        return None
    data = cq.get("data", "")
    cq_id = cq.get("id", "")
    if ":" not in data:
        return None
    action, _, approval_id = data.partition(":")
    if action not in ("approve", "reject") or not approval_id:
        return None
    return action, approval_id, cq_id


__all__ = [
    "is_configured",
    "send_message",
    "send_approval_request",
    "send_alert",
    "answer_callback",
    "parse_callback",
]
