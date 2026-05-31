"""Vestra FastAPI application.

Doors:
* ``/auth/*``                    -- register / login / me (JWT).
* ``/webhook/market-alert``      -- machine-to-machine ingest, authorized by a
  shared API key (NOT user auth -- the market feed has no user). It records the
  event and fans the workflow out to every impacted tenant.
* ``/portfolio`` / ``/audit``    -- user-facing, JWT-scoped to the caller.

Hardening vs. the original:
* No hardcoded ``user_001`` -- the webhook fans out per impacted user, and
  user-facing endpoints derive identity from the verified JWT.
* CORS + rate limiting installed; config validated + indexes ensured on startup
  via a lifespan context manager (not the deprecated ``on_event``).
"""

import asyncio
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.agent.graph import run_vestra_workflow
from app.agent.nodes.risk import RiskAssessmentError
from app.agent.nodes.signal import classify_market_event
from app.auth.deps import get_current_user_id, require_webhook_key
from app.auth.routes import router as auth_router
from app.approvals.routes import router as approvals_router
from app.config import ConfigError
from app.core.lifespan import lifespan
from app.core.security import install_security, limiter
from app.data.repository import (
    create_goal,
    delete_goal,
    find_impacted_user_ids,
    get_audit_logs,
    get_digital_twin,
    get_market_exposure,
    get_profile,
    get_recent_market_events,
    list_goals,
    list_reasoning_traces,
    list_simulations,
    record_market_event,
    update_goal,
    upsert_digital_twin,
)
from app.models.schemas import DigitalTwin, Goal, MarketEvent
from app.services.portfolio_health import compute_portfolio_health
from app.services.rebalancer import preview_rebalance
from app.agent.nodes.regime import aggregate_regime

logger = logging.getLogger("vestra")

app = FastAPI(title="Vestra", version="0.2.0", lifespan=lifespan)
install_security(app)
app.include_router(auth_router)
app.include_router(approvals_router)


@app.get("/")
def root():
    return {"status": "Vestra X running"}


@app.post("/webhook/market-alert", dependencies=[Depends(require_webhook_key)])
@limiter.limit("60/minute")
async def market_alert(request: Request, event: MarketEvent):
    """Ingest a market event and fan the workflow out to impacted users.

    Authorized by the ``X-API-Key`` header (see ``require_webhook_key``). The
    fan-out is synchronous for now; a queue replaces it at scale (see roadmap).
    """
    try:
        # Classify once to resolve broader impacted assets (e.g. macro -> indices).
        signal = classify_market_event(event)

        await record_market_event(
            {**event.model_dump(), "impacted_assets": signal.impacted_assets}
        )

        user_ids = await find_impacted_user_ids(event.ticker, signal.impacted_assets)
        if not user_ids:
            return {"status": "no_impacted_users", "ticker": event.ticker.upper()}

        results = await asyncio.gather(
            *[run_vestra_workflow(uid, event) for uid in user_ids],
            return_exceptions=True,
        )

        summary = []
        for uid, res in zip(user_ids, results):
            if isinstance(res, Exception):
                logger.warning("Workflow failed for %s: %s", uid, res)
                summary.append({"user_id": uid, "status": "error"})
            else:
                summary.append({"user_id": uid, "status": res.get("status"), "result": res})

        return {"status": "processed", "impacted_users": len(user_ids), "results": summary}

    except RiskAssessmentError as exc:
        return JSONResponse(
            status_code=422,
            content={"status": "error", "detail": str(exc)},
        )
    except ConfigError as exc:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "detail": str(exc)},
        )
    except Exception:
        logger.exception("Unhandled error processing market alert")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "detail": "Internal error while processing market alert.",
            },
        )


@app.get("/portfolio")
async def portfolio(user_id: str = Depends(get_current_user_id)):
    """Return the authenticated user's profile + computed market exposure."""
    profile = await get_profile(user_id)
    if isinstance(profile, dict) and "error" in profile:
        return JSONResponse(status_code=404, content={"status": "error", "detail": profile["error"]})
    exposure = await get_market_exposure(user_id)
    return {"profile": profile, "exposure": exposure}


@app.get("/portfolio/health")
async def portfolio_health(user_id: str = Depends(get_current_user_id)):
    """Return the authenticated user's 0-100 portfolio health score + factors."""
    profile = await get_profile(user_id)
    if isinstance(profile, dict) and "error" in profile:
        return JSONResponse(status_code=404, content={"status": "error", "detail": profile["error"]})
    goals = await list_goals(user_id)
    health = await compute_portfolio_health(
        holdings=profile.get("holdings", {}),
        cash_balance=profile.get("cash_balance", 0.0),
        target_allocation=profile.get("target_allocation", {}),
        goals=goals,
    )
    return health.model_dump()


@app.get("/audit")
async def audit(user_id: str = Depends(get_current_user_id), limit: int = 100):
    """Return the authenticated user's recent agent audit-log entries."""
    return {"logs": await get_audit_logs(user_id, limit=min(limit, 500))}


@app.get("/market/regime")
async def market_regime(user_id: str = Depends(get_current_user_id)):
    """Return the current market-wide regime aggregated from recent events."""
    events = await get_recent_market_events(limit=25)
    return aggregate_regime(events).model_dump()


@app.get("/simulations")
async def simulations(user_id: str = Depends(get_current_user_id), limit: int = 50):
    """Return the authenticated user's recent scenario-simulation results."""
    return {"simulations": await list_simulations(user_id, limit=min(limit, 200))}


@app.get("/reasoning")
async def reasoning(user_id: str = Depends(get_current_user_id), limit: int = 50):
    """Return the authenticated user's recent agent reasoning traces.

    Each trace is the full chain produced for one decision: signal, research,
    risk, strategy decision, reflection, confidence, and validation outputs.
    """
    return {"traces": await list_reasoning_traces(user_id, limit=min(limit, 200))}


@app.post("/rebalance/preview")
async def rebalance_preview(
    user_id: str = Depends(get_current_user_id), drift_threshold_pct: float = 5.0
):
    """Preview a rebalance plan correcting drift vs. the user's target allocation."""
    profile = await get_profile(user_id)
    if isinstance(profile, dict) and "error" in profile:
        return JSONResponse(status_code=404, content={"status": "error", "detail": profile["error"]})
    plan = await preview_rebalance(
        holdings=profile.get("holdings", {}),
        target_allocation=profile.get("target_allocation", {}),
        drift_threshold_pct=max(0.0, min(drift_threshold_pct, 100.0)),
    )
    return plan.model_dump()


# --- Digital twin & goals (Phase 4) --------------------------------------


@app.get("/digital-twin")
async def get_twin(user_id: str = Depends(get_current_user_id)):
    """Return the authenticated user's financial digital twin (or null if unset)."""
    twin = await get_digital_twin(user_id)
    return {"digital_twin": twin}


@app.put("/digital-twin")
async def put_twin(twin: DigitalTwin, user_id: str = Depends(get_current_user_id)):
    """Create or update the authenticated user's digital twin."""
    stored = await upsert_digital_twin(user_id, twin.model_dump())
    return {"digital_twin": stored}


@app.get("/goals")
async def get_goals(user_id: str = Depends(get_current_user_id)):
    """List the authenticated user's financial goals."""
    return {"goals": await list_goals(user_id)}


@app.post("/goals", status_code=201)
async def post_goal(goal: Goal, user_id: str = Depends(get_current_user_id)):
    """Create a financial goal for the authenticated user."""
    # The repository assigns the goal_id; ignore any client-supplied one.
    payload = goal.model_dump(exclude={"goal_id"})
    created = await create_goal(user_id, payload)
    created.pop("_id", None)
    return {"goal": created}


@app.put("/goals/{goal_id}")
async def put_goal(goal_id: str, updates: dict, user_id: str = Depends(get_current_user_id)):
    """Update a goal owned by the authenticated user."""
    updated = await update_goal(user_id, goal_id, updates)
    if not updated:
        return JSONResponse(status_code=404, content={"status": "error", "detail": "Goal not found."})
    return {"goal": updated}


@app.delete("/goals/{goal_id}")
async def remove_goal(goal_id: str, user_id: str = Depends(get_current_user_id)):
    """Delete a goal owned by the authenticated user."""
    ok = await delete_goal(user_id, goal_id)
    if not ok:
        return JSONResponse(status_code=404, content={"status": "error", "detail": "Goal not found."})
    return {"status": "deleted", "goal_id": goal_id}
