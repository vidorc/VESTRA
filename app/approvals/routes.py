"""Approvals API + Telegram approval webhook.

Two surfaces drive the human-in-the-loop resume of a paused workflow:

* ``GET /approvals`` / ``POST /approvals/{id}/decision`` -- JWT-scoped. A user can
  only see and decide their *own* approval requests (ownership is enforced from
  the verified token, never from the path/body). Deciding resumes the paused
  LangGraph run via ``resume_workflow``.
* ``POST /telegram/webhook`` -- receives inline-button callbacks from the Telegram
  bot. Not JWT-authed (Telegram calls it), so it is hardened with Telegram's
  ``X-Telegram-Bot-Api-Secret-Token`` header when ``TELEGRAM_WEBHOOK_SECRET`` is
  configured, and it only resumes runs for requests that are still ``pending``.

Both paths are idempotent against double-decisions: an already-decided approval
returns 409 (API) or is silently ignored (Telegram), because the underlying
``update_approval_status`` only transitions ``pending`` requests.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel

from app.agent.graph import resume_workflow
from app.auth.deps import get_current_user_id
from app.config import get_settings
from app.data.repository import get_approval, list_approvals
from app.integrations.telegram import bot

router = APIRouter(tags=["approvals"])


class DecisionRequest(BaseModel):
    approved: bool
    reason: Optional[str] = None


@router.get("/approvals")
async def get_approvals(
    status: Optional[str] = None,
    limit: int = 100,
    user_id: str = Depends(get_current_user_id),
):
    """List the authenticated user's approval requests (optionally by status)."""
    approvals = await list_approvals(user_id, status=status, limit=min(limit, 500))
    return {"approvals": approvals}


@router.post("/approvals/{approval_id}/decision")
async def decide_approval(
    approval_id: str,
    body: DecisionRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Approve or reject a pending request and resume the paused workflow.

    Enforces ownership (caller must own the request) and idempotency (an
    already-decided request returns 409).
    """
    approval = await get_approval(approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval not found.")
    if approval.get("user_id") != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your approval request.")
    if approval.get("status") != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Approval already {approval.get('status')}.",
        )

    result = await resume_workflow(approval["thread_id"], body.approved)
    return {"approval_id": approval_id, "decision": "approved" if body.approved else "rejected", "result": result}


def _verify_telegram_secret(secret_header: Optional[str]) -> None:
    """When TELEGRAM_WEBHOOK_SECRET is configured, require the matching header."""
    configured = getattr(get_settings(), "TELEGRAM_WEBHOOK_SECRET", "")
    if configured and secret_header != configured:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret.")


@router.post("/telegram/webhook")
async def telegram_webhook(
    update: dict,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    """Handle a Telegram inline-button callback (approve/reject) and resume the run.

    Always returns 200 with ``{"ok": true}`` for recognized updates so Telegram
    does not retry; non-button updates are ignored.
    """
    _verify_telegram_secret(x_telegram_bot_api_secret_token)

    parsed = bot.parse_callback(update)
    if not parsed:
        return {"ok": True, "ignored": True}

    action, approval_id, cq_id = parsed
    approval = await get_approval(approval_id)
    if approval and approval.get("status") == "pending":
        await resume_workflow(approval["thread_id"], action == "approve")
        ack = "Approved ✅" if action == "approve" else "Rejected ❌"
    else:
        ack = "Already handled."

    if cq_id:
        try:
            await bot.answer_callback(cq_id, ack)
        except Exception:
            pass
    return {"ok": True}


__all__ = ["router"]
