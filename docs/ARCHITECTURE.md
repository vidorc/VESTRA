# Vestra Architecture

Vestra is an **AI Wealth Operating System** for Indian retail investors (NSE/BSE/
ETFs/MFs). It ingests market events and runs them through a LangGraph agent
pipeline to produce disciplined, auditable, per-user investment decisions with a
human-in-the-loop approval gate.

This document describes the system as built through Phase 1. See
`docs/BUILD_PROGRESS.md` for status and `docs/PHASE1.md` for the approval layer.

## High-level shape

```
                         ┌──────────────────────────────────────────────┐
  POST /webhook/         │             FastAPI (app/main.py)             │
  market-alert  ───────► │  • API-key on webhook   • JWT on user routes  │
  (X-API-Key)            │  • CORS + rate limiting • lifespan + indexes  │
                         └───────┬───────────────────────┬──────────────┘
                                 │ fan-out per             │ JWT-scoped
                                 │ impacted user           ▼
                                 ▼                 /auth /portfolio /audit
                    run_vestra_workflow()          /approvals /telegram/webhook
                                 │
                                 ▼
        ┌──────────────── LangGraph StateGraph (app/agent/graph.py) ─────────────┐
        │ signal → research → risk → strategy → reflection → confidence → validate│
        │   validate ─(ok)→ approval ─(approved|auto)→ execute → audit → END      │
        │            └(no)→ reject                     └(human reject)→ reject     │
        └──────────────────────────────┬─────────────────────────────────────────┘
                                        ▼
                       Repository (app/data/repository.py)  ──► MongoDB (Motor)
                                        │
                       Market data provider (app/data/market) ──► static | yfinance
```

## Layers

### API — `app/main.py`, `app/auth`, `app/approvals`
- **Two doors.** The market-alert webhook is machine-to-machine, authorized by a
  shared `WEBHOOK_API_KEY` (fail-closed). User-facing endpoints derive identity
  from a verified JWT (`sub` claim) — a caller can only ever act as themselves.
- **Webhook fan-out.** One market event is classified, recorded to
  `market_events`, then dispatched to every user holding the impacted ticker/
  assets (no hardcoded user).
- **Cross-cutting.** CORS + rate limiting (`app/core/security.py`); config
  validation + index creation on startup via a lifespan (`app/core/lifespan.py`).

### Orchestration — `app/agent/graph.py`
- A compiled LangGraph `StateGraph`. `AgentState` is a flat `TypedDict` whose
  optional fields each node reads with `.get()`, so a missing upstream context
  never breaks a downstream node (incremental-phase safety).
- Compiled lazily with a checkpointer (`app/agent/checkpoint.py`) to support
  `interrupt()`-based human approval. `run_vestra_workflow` / `resume_workflow`
  are the public entry points; the legacy result contract is preserved (see
  `docs/PHASE1.md`).

### Agent nodes — `app/agent/nodes/`
| Node | Kind | Role |
|---|---|---|
| signal | rule-based | classify event type + severity |
| research | LLM | enrich with sentiment/news/sector/context |
| risk | data + rules | concentration + safe-trade limits |
| strategy | LLM (Groq) | propose BUY/SELL/HOLD |
| reflection | LLM | self-critique the decision |
| confidence | rule-based | aggregate confidence signals |
| validator | rule-based | hard constraints (cash, holdings, limits) |
| approval | policy + interrupt | human-in-the-loop gate |
| execution | data | atomic trade application |
| audit | data | truthful action logging |
| notifier | integration | Telegram notifications |

Shared LLM access + robust JSON parsing live in `app/agent/llm.py` (one
injectable client for all LLM nodes).

### Data — `app/data/`
- `mongo.py` — lazy Motor client/factory (test-injectable).
- `repository.py` — the real DAL. `execute_trade` is **atomic** (document-level
  `find_one_and_update` guard) and **idempotent** (optional `idempotency_key`).
- `indexes.py` — index definitions for all collections (created on startup +
  via `app/scripts/create_indexes.py`).
- `market/` — `MarketDataProvider` protocol; `StaticReferenceProvider` (always-on
  fallback) and `YFinanceProvider` (optional live feed). The synchronous price
  hot-path (`app/agent/pricing.py`) never blocks on network I/O.

### Integrations — `app/integrations/telegram`
- HTTP Bot API client (via `httpx`); approval messages with inline buttons;
  callback parsing. Fully config-gated (no-op without a token).

## Collections

`users`, `investor_profiles`, `agent_audit_logs`, `rejected_trades`,
`market_events`, `research_context`, `approval_requests`, `agent_events`,
plus reserved-and-indexed V2 collections (`trade_decisions`, `trade_executions`,
`portfolio_snapshots`, `agent_memories`, `simulation_results`). All scoped by
`user_id`; indexes defined in `app/data/indexes.py`.

## Security
JWT auth (PBKDF2-hashed passwords, ≥32-char signing secret), fail-closed webhook
API key, per-user data scoping, rate limiting, input validation (Pydantic),
secret management via env/config validation. See README “Security notes”.

## Testing
`pytest` + `pytest-asyncio`, fully offline: `mongomock-motor` for Mongo and an
injected fake LLM via `app.agent.llm.set_llm`. CI (`.github/workflows/ci.yml`)
runs ruff + pytest with a coverage gate.

## Deployment
Docker (non-root, `$PORT`-aware), `docker-compose` (Mongo + API w/ healthchecks),
Railway (`railway.json`), MongoDB Atlas, Next.js frontend on Vercel (`web/`).
