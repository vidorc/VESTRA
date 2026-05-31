# Vestra Build Progress

Living status of the V2 build. Updated at each checkpoint. See
`docs/VESTRA_V2_MASTER_PROMPT.md` for the full vision and `docs/ARCHITECTURE.md`
for the system as built.

_Last updated: Phases 0–5 complete (full master-prompt roadmap)._

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

### Phase 4 (partial) — Digital Twin & Goal-Based Investing
- **Digital Twin** (`DigitalTwin` schema, `digital_twins` collection): income,
  expenses, EMIs, SIPs, emergency fund, tax bracket, risk profile; computed
  `monthly_surplus` + `recommended_emergency_fund`. `GET`/`PUT /digital-twin`.
- **Goals** (`Goal` schema, `goals` collection): retirement/house/education/
  emergency_fund/wealth_growth; ownership-scoped CRUD (`/goals`, `/goals/{id}`).
- **Goals service** (`services/goals.py`): `goal_alignment_score`,
  `liquidity_need`, `liquidity_pressure` (deterministic). The alignment score now
  powers the Health Engine's previously-stubbed `goal_alignment` factor.
- 137 tests, ruff clean, ~83% coverage. See `docs/PHASE4_DIGITAL_TWIN.md`.

### Frontend screens + Agent Reasoning
- **Phase 1–2 screens wired to live data**: Market Intelligence (regime +
  simulations), Execution Center (pending approvals, approve/reject HITL),
  Portfolio (health gauge, factors, holdings, sectors, rebalance preview),
  Settings (Digital Twin + goals CRUD); new `web/components/ui` primitives.
- **Agent Reasoning** (new `reasoning_traces` collection + `GET /reasoning`):
  the validator node persists one full trace per decision — signal, research,
  risk, strategy decision, reflection, confidence, validation — and the
  `/reasoning` screen renders each as the 7-stage pipeline in graph order.
- 144 tests, ruff clean. Frontend typecheck + production build pass (12 routes).

### Phase 4 — Personal CFO layer
- `liquidity_pressure` (deterministic, from goals + digital twin) now wired into
  the **risk node**: it estimates portfolio value (cash + holdings at reference
  price), computes pressure, and tightens `safe_trade_limit` (×0.5 medium, ×0.25
  high) toward capital preservation. DB loads degrade gracefully to "low".
- Surfaced in the **strategy prompt** (preserve-capital rule) and the reasoning
  screen (liquidity badge on the Risk step).

### Phase 5 — Institutional Intelligence
- **Memory** (`services/memory.py` + `agent_memories`): recall past decisions /
  outcomes per ticker.
- **Council** (`nodes/council.py`): four deterministic strategy seats (momentum,
  contrarian, risk_averse, macro) → consensus action + dissent score.
- **CIO** (`nodes/cio.py`): the final authority. Passes through, downsizes
  (clamp to safe limit; cut after a losing streak via memory), vetoes (low
  confidence) or overrides (against council) — but only for BUYs. Risk-reducing
  SELLs are never blocked; governance gates capital deployment, not de-risking.
- **Learning** (`nodes/learning.py`): writes execution outcomes back to memory
  from the execute node, closing the loop the CIO reads next time.
- Graph rewired `confidence → council → cio → simulation`; trace + reasoning
  screen show council, CIO verdict, and an analyst→final governance banner.

### Phase 3 — Autonomous Execution (paper/demo)
- `nodes/browser_executor.py`: **paper** mode (deterministic simulation, default,
  no browser — synthetic reproducible confirmation id) and **demo** mode (lazy
  headless Playwright screenshot as audit evidence, degrades to paper if the
  library is absent). **Live** real-money execution is deliberately refused.
- Execution node attaches evidence (mode from `EXECUTION_MODE`, default paper);
  Audit screen surfaces it. Real broker integration remains out of scope.
- 169 tests, ruff clean. Frontend typecheck + production build pass (12 routes).

## 🚧 In Progress
- _None_ — all roadmap phases (0–5) have landed in this environment.

## ⛔ Blocked / Needs human input
- **Rotate leaked credentials.** The original `.env` held a live Groq key +
  MongoDB Atlas password (now gitignored, code uses proper secret handling).
  These must be rotated in the Groq console + Atlas — a manual operator step.
- **Real-money execution (Phase 3 live mode)** is intentionally unbuilt and
  refused by the executor. A vetted broker integration, credential handling, and
  explicit operator opt-in are prerequisites — out of scope to build blind. Paper
  + demo modes are fully implemented. (Playwright is referenced lazily; install
  it + browser binaries to exercise demo-mode screenshots.)
- **Optional, not blocking:** persistent LangGraph checkpointer. In-process
  `MemorySaver` is used today (sufficient single-process); a durable saver can be
  injected via `app/agent/checkpoint.set_checkpointer` when multi-process scaling
  is needed. (The heavy `langgraph-checkpoint-mongodb` dep was evaluated and
  rejected — it downgraded pymongo and pulled numpy/sqlalchemy.)

## ⏭️ Next (post-roadmap)

The master-prompt roadmap (Phases 0–5) is complete. Remaining enhancements:
- **Decision Review** UI — a richer per-decision drill-down beyond the reasoning
  trace (outcome attribution, memory timeline per ticker).
- **Live execution** once a broker integration is provisioned (see Blocked).
- Maintain the 80%+ coverage target as features land.
