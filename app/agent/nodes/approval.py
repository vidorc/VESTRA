"""Approval agent node — the human-in-the-loop gate.

Sits between the validator and execution. It decides, per the investor's
approval policy, whether a validated trade may auto-execute or must be approved
by a human. When human approval is required it:

1. idempotently writes a ``pending`` ``approval_requests`` document,
2. notifies the human exactly once (Telegram, best-effort), and
3. calls LangGraph ``interrupt()`` to pause the run.

The run resumes later via ``resume_workflow(thread_id, approved)`` (driven by the
approvals API or a Telegram callback), at which point ``interrupt()`` returns the
human's decision and the node records it.

Re-execution safety
--------------------
``interrupt()`` causes LangGraph to *re-run the node body from the top* on
resume. Everything before the ``interrupt()`` call therefore executes twice. We
keep that safe by (a) using an idempotent upsert for the approval doc and (b)
gating the notification on the upsert's ``created`` flag, so the human is pinged
exactly once across the original run and the resume.

Policies (from the investor profile's ``approval_policy``, else config default):
* ``manual``               -- always require approval.
* ``approval_required``    -- require approval for any non-HOLD trade.
* ``auto_below_threshold`` -- auto-execute only when confidence is high enough
                              and concentration risk is below the configured cap.
* ``autonomous_sandbox``   -- never interrupt (execution-mode enforcement, i.e.
                              paper/demo only, lands with OpenClaw in a later phase).
"""

from typing import Any, Dict, Optional

from langgraph.types import interrupt

from app.agent.nodes.notifier import notify_approval_request
from app.config import get_settings
from app.data.repository import create_approval_request, update_approval_status
from app.models.schemas import ConfidenceScore, RiskAssessment, TradeDecision

_RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def needs_human_approval(
    policy: str,
    decision: TradeDecision,
    confidence: Optional[ConfidenceScore],
    risk: Optional[RiskAssessment],
) -> bool:
    """Pure policy evaluation: does this decision require human sign-off?

    Deterministic and side-effect free so it can be unit-tested directly.
    """
    # A HOLD executes nothing, so it never needs approval.
    if decision.action == "HOLD":
        return False

    if policy == "autonomous_sandbox":
        return False
    if policy == "manual":
        return True
    if policy == "approval_required":
        return True
    if policy == "auto_below_threshold":
        settings = get_settings()
        conf_ok = (confidence is not None) and (
            confidence.overall >= settings.CONFIDENCE_THRESHOLD
        )
        risk_level = risk.concentration_risk if risk else "high"
        cap = settings.RISK_THRESHOLD
        risk_ok = _RISK_ORDER.get(risk_level, 2) < _RISK_ORDER.get(cap, 2)
        # Auto-execute (no approval) only when BOTH confidence and risk are fine.
        return not (conf_ok and risk_ok)

    # Unknown policy -> fail safe by requiring approval.
    return True


def _parse_resume(value: Any) -> bool:
    """Interpret the resume value from ``Command(resume=...)`` as approved/rejected."""
    if isinstance(value, bool):
        return value
    if isinstance(value, dict):
        if "approved" in value:
            return bool(value["approved"])
        if "decision" in value:
            return str(value["decision"]).lower() in {"approve", "approved", "true", "yes"}
    if isinstance(value, str):
        return value.lower() in {"approve", "approved", "true", "yes"}
    return bool(value)


async def resolve_policy(user_id: str) -> str:
    """Return the investor's approval policy, falling back to the config default."""
    from app.data.repository import get_profile

    try:
        profile = await get_profile(user_id)
        if isinstance(profile, dict) and "error" not in profile:
            policy = profile.get("approval_policy")
            if policy:
                return str(policy)
    except Exception:
        pass
    return get_settings().APPROVAL_POLICY_DEFAULT


async def run_approval(
    user_id: str,
    thread_id: str,
    decision: TradeDecision,
    confidence: Optional[ConfidenceScore],
    risk: Optional[RiskAssessment],
    reflection: Optional[Dict[str, Any]] = None,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate the policy and, if needed, persist + notify + interrupt.

    Returns an ``approval`` dict describing the outcome:
    ``{"required": bool, "status": "auto_approved"|"approved"|"rejected",
       "approval_id": str|None, "policy": str}``.
    """
    policy = await resolve_policy(user_id)

    if not needs_human_approval(policy, decision, confidence, risk):
        return {
            "required": False,
            "status": "auto_approved",
            "approval_id": None,
            "policy": policy,
        }

    # Idempotent: created=True only on the first pass (not on resume re-run).
    approval_id, created = await create_approval_request(
        thread_id=thread_id,
        user_id=user_id,
        decision=decision.model_dump(),
        confidence=confidence.model_dump() if confidence else None,
        reflection=reflection,
        event_id=event_id,
    )

    if created:
        # Best-effort, fire exactly once; failures never break the graph.
        try:
            await notify_approval_request(user_id, approval_id, decision, confidence)
        except Exception:
            pass

    # Pause here. On resume, interrupt() returns the human's decision.
    human_decision = interrupt(
        {
            "approval_id": approval_id,
            "thread_id": thread_id,
            "decision": decision.model_dump(),
            "confidence": confidence.model_dump() if confidence else None,
        }
    )

    approved = _parse_resume(human_decision)
    status = "approved" if approved else "rejected"
    await update_approval_status(
        approval_id, status, reason=None if approved else "Rejected by human reviewer."
    )

    return {
        "required": True,
        "status": status,
        "approval_id": approval_id,
        "policy": policy,
    }


__all__ = ["needs_human_approval", "resolve_policy", "run_approval"]
