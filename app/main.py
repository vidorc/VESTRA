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
    find_impacted_user_ids,
    get_audit_logs,
    get_market_exposure,
    get_profile,
    record_market_event,
)
from app.models.schemas import MarketEvent

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


@app.get("/audit")
async def audit(user_id: str = Depends(get_current_user_id), limit: int = 100):
    """Return the authenticated user's recent agent audit-log entries."""
    return {"logs": await get_audit_logs(user_id, limit=min(limit, 500))}
