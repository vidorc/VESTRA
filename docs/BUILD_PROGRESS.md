# Vestra Build Progress

Living status of the V2 build. Updated at each checkpoint. See
`docs/VESTRA_V2_MASTER_PROMPT.md` for the full vision and `docs/ARCHITECTURE.md`
for the system as built.

_Last updated: Phase 2 complete._

## ✅ Completed

### Phase 0 — Hardening & Foundation
- Lazy client/LLM factories (no import-time side effects); fixed a latent Motor
  event-loop binding bug.
- JWT auth (PBKDF2 passwords, ≥32-char secret) + fail-closed webhook API key.
- DAL formalized (`app/data/repository.py`); `execute_trade` made **atomic** +
  **idempotent** (proven: concurrent buys cannot overspend; retries don't double-execute).
- Market-data provider seam (static fallback + optional yfinance), non-blocking hot path.
- `main.py` hardened: removed hardcoded `user_001`, multi-tenant webhook fan-out,
  CORS, rate limiting, lifespan + index creation, JWT-scoped `/portfolio` + `/audit`.
- Indexes for all collections; multi-user seed script.
- Deploy hardening: non-root Dockerfile (`$PORT`), `.dockerignore`, compose
  healthchecks, `railway.json`, README.
- CI (GitHub Actions): ruff + pytest with coverage gate.
- Next.js 15 frontend shell (dark Bloomberg-terminal theme per DESIGN.md): auth
  flow, app shell, live Dashboard + Audit, route placeholders. Production build passes.

### Phase 1 — Intelligence & Approval
- **Research agent** (`research.py`) → `ResearchContext` with `data_completeness`.
- **Reflection agent** (`reflection.py`) → `ReflectionResult` self-critique.
- **Confidence agent** (`confidence.py`) → rule-based `ConfidenceScore`.
- **Approval system**: policy engine + LangGraph `interrupt()`/resume +
  `approval_requests` collection + Telegram bot + notifier; REST approvals API.
- Graph rewired with checkpointer; legacy result contract preserved
  (`pending_approval` additive). 89 tests, ruff clean, ~79% coverage.

### Phase 2 — Portfolio Intelligence
- **Portfolio Health Engine** (`services/portfolio_health.py`) → 0–100 score
  (diversification, concentration, liquidity, volatility, goal alignment) +
  `GET /portfolio/health`.
- **Market Regime agent** (`nodes/regime.py`) → bull/bear/sideways/high-vol/crisis;
  wired pre-strategy (research→regime→risk); `GET /market/regime`.
- **Scenario Simulation agent** (`nodes/simulation.py`) → best/base/worst,
  drawdown, expected return, risk score; persisted; `GET /simulations`.
- **Rebalancer** (`services/rebalancer.py`) → drift detection + corrective plan;
  `POST /rebalance/preview`.
- 127 tests, ruff clean, ~81% coverage (past the 80% target).

## 🚧 In Progress
- _None_ — Phase 2 closed. Ready for Phase 3.

## ⛔ Blocked / Needs human input
- **Rotate leaked credentials.** The original `.env` held a live Groq key +
  MongoDB Atlas password (now gitignored, code uses proper secret handling).
  These must be rotated in the Groq console + Atlas — a manual operator step.
- **Optional, not blocking:** persistent LangGraph checkpointer. In-process
  `MemorySaver` is used today (sufficient single-process); a durable saver can be
  injected via `app/agent/checkpoint.set_checkpointer` when multi-process scaling
  is needed. (The heavy `langgraph-checkpoint-mongodb` dep was evaluated and
  rejected — it downgraded pymongo and pulled numpy/sqlalchemy.)

## ⏭️ Next (per master prompt roadmap)

### Phase 3 — Autonomous Execution
- OpenClaw `browser_executor.py` (demo + paper modes, screenshots, audit evidence).

### Phase 4 — Wealth OS
- Digital Twin (income/expenses/loans/SIPs/emergency fund/goals), Goal-Based
  Investing, Personal CFO layer.

### Phase 5 — Institutional Intelligence
- CIO agent (final authority), multi-strategy council, Memory agent, Learning agent,
  Decision Review.

### Cross-cutting
- Frontend screens for Phase 1–2 (Market Intelligence, Agent Reasoning, Execution
  Center, Portfolio health/regime/simulation views, Settings).
- Maintain the 80%+ coverage target as agents land.
