# Vestra

An AI Wealth Operating System for Indian retail investors. Vestra ingests market
events and runs them through a LangGraph agent pipeline to produce disciplined,
auditable, per-user investment decisions — with research enrichment, market-regime
detection, scenario simulation, self-critique, confidence scoring, and a
human-in-the-loop approval gate. It also scores portfolio health and previews
rebalancing.

> Phases 0 (hardening), 1 (intelligence + approval), and 2 (portfolio
> intelligence) are complete. See `docs/ARCHITECTURE.md` (system as built),
> `docs/PHASE1.md` and `docs/PHASE2.md` (feature layers), `docs/BUILD_PROGRESS.md`
> (status), `DESIGN.md` (frontend design system), and
> `docs/VESTRA_V2_MASTER_PROMPT.md` (full vision + roadmap).

## Architecture

```
POST /webhook/market-alert  (API-key)        Authenticated user (JWT)
        │                                          │
        ▼                                          ▼
  classify + record event           /portfolio /audit /auth/* /approvals
        │ fan-out per impacted user
        ▼
  run_vestra_workflow(user_id, event)   ──►  LangGraph StateGraph
    signal → research → risk → strategy → reflection → confidence → validate
      validate ─(ok)→ approval ─(approved|auto)→ execute → END
               └(no)→ reject                    └(human reject)→ reject
```

The `approval` node may pause the run for human sign-off (Telegram / REST) per
the investor's approval policy; see `docs/PHASE1.md`.

- **API layer** — FastAPI (`app/main.py`), JWT auth + rate limiting + CORS.
- **Orchestration** — LangGraph (`app/agent/graph.py`), with `interrupt()`/resume
  for human approval.
- **LLM** — Groq `llama-3.3-70b-versatile` (strategy, research, reflection).
- **Data** — MongoDB (Motor), accessed via the repository layer
  (`app/data/repository.py`); the optional MCP transport shim is
  `app/mcp/server.py`.
- **Market data** — pluggable provider (`app/data/market/`); static reference
  table by default, optional yfinance live feed.
- **Approvals** — policy engine + Telegram bot (`app/integrations/telegram/`) +
  REST (`app/approvals/`).

## Requirements

- Python 3.11+
- MongoDB (local via Docker, or MongoDB Atlas)
- A Groq API key

## Configuration

Copy `.env.example` to `.env` and fill in values:

| Variable | Required | Notes |
|---|---|---|
| `GROQ_API_KEY` | yes | Groq LLM key. |
| `MONGODB_URI` | yes | Atlas `mongodb+srv://…` or `mongodb://localhost:27017`. |
| `JWT_SECRET` | yes | ≥32 chars. Generate: `openssl rand -hex 32`. |
| `WEBHOOK_API_KEY` | no* | Shared key for the market-alert webhook. **Unset ⇒ webhook rejects all calls (fail-closed).** |
| `DATABASE_NAME` | no | Defaults to `vestra`. |
| `GROQ_MODEL` | no | Defaults to `llama-3.3-70b-versatile`. |
| `MARKET_DATA_PROVIDER` | no | `static` (default) or `yfinance`. |
| `CORS_ORIGINS` | no | Comma-separated; defaults to `*` (lock down in prod). |

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Create indexes and seed demo users (needs MONGODB_URI reachable):
python -m app.scripts.create_indexes
python -m tests.seed_db          # prints demo credentials

uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for the interactive API.

### Auth quickstart

```bash
# Register (also creates a default investor profile)
curl -X POST localhost:8000/auth/register \
  -H 'content-type: application/json' \
  -d '{"email":"me@example.com","password":"supersecret1"}'
# -> {"access_token":"…","user_id":"…"}

curl localhost:8000/portfolio -H "Authorization: Bearer <token>"
```

### Triggering the workflow

```bash
curl -X POST localhost:8000/webhook/market-alert \
  -H "X-API-Key: $WEBHOOK_API_KEY" \
  -H 'content-type: application/json' \
  -d '{"ticker":"RELIANCE","price_change_percent":-6.0,"breaking_news_summary":"Selloff."}'
```

The webhook fans out to every user holding the impacted ticker/assets.

## Docker

```bash
# Brings up MongoDB + the API (API waits for Mongo healthcheck).
# Provide GROQ_API_KEY and JWT_SECRET via .env or the shell.
docker compose up --build
```

The image runs as a non-root user and honors `$PORT`. `.dockerignore` keeps
`.env`, `.git`, and the frontend out of the image.

## Deployment

- **Backend → Railway:** `railway.json` builds from the Dockerfile and
  health-checks `/`. Set all required env vars in the Railway dashboard. The
  start command honors Railway's injected `$PORT`.
- **Database → MongoDB Atlas:** set `MONGODB_URI` to the Atlas SRV string.
- **Frontend → Vercel:** the Next.js app lives in `web/` (scaffolded with the
  frontend phase); deploy with Vercel Root Directory = `web/`.

## Testing

```bash
pytest                 # unit + integration (no live DB/LLM needed)
```

Tests use `mongomock-motor` for an in-memory Mongo and inject a fake LLM via the
`strategy.set_llm` seam, so the suite runs fully offline. Manual integration
scripts (`tests/simulate_*.py`, `tests/seed_db.py`) hit a live stack and are not
collected by pytest.

## Security notes

- The market-alert webhook is machine-to-machine and authorized by
  `WEBHOOK_API_KEY` (not user JWT). It is fail-closed.
- User endpoints derive identity from the verified JWT `sub` claim — a caller
  can only ever act as themselves.
- Passwords are PBKDF2-HMAC-SHA256 hashed with a per-password salt.
- `execute_trade` is atomic (document-level guard) and idempotent
  (`idempotency_key`), preventing overspend under concurrency and double
  execution on retries.
