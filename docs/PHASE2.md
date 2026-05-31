# Phase 2 — Portfolio Intelligence

Phase 2 adds the portfolio-intelligence layer: a portfolio **health score**, a
**market regime** read, **scenario simulation**, and a **rebalancer**. Three of
these slot into the LangGraph pipeline as new nodes; health and rebalancing are
standalone services exposed via the API and (later) the dashboard.

All four are **deterministic and rule-based** — the same inputs always yield the
same output — which keeps them cheap, reproducible, and auditable. Each follows
the same shape: a **pure core** (prices/values passed in, no I/O, fully unit-tested)
plus a thin async wrapper that resolves prices from the Phase-0 market provider.

## Updated pipeline

```
signal → research → regime → risk → strategy → reflection → confidence
       → simulation → validate → approval → execute | reject
```

New nodes: `regime` (after research, before risk) and `simulation` (after
confidence, before validate). Both read upstream context with `.get()` and never
hard-fail, preserving incremental-phase safety. The simulation result is persisted
to `simulation_results`; the regime read flows in state and powers scenario sizing.

## Components

### Portfolio Health Engine — `app/services/portfolio_health.py`
A 0-100 "credit score" for a portfolio with the factors that produced it:

| Factor | Weight | Basis |
|---|---|---|
| diversification | 0.30 | Herfindahl index across sectors (more, more-even sectors score higher) |
| concentration | 0.25 | inverse of single-sector dominance (reuses `sectors.assess_concentration`) |
| liquidity | 0.20 | cash as a share of total portfolio value (rewards a ~10–40% buffer) |
| volatility | 0.15 | neutral default until price history is wired; accepts an override |
| goal_alignment | 0.10 | neutral until goals exist (Phase 4) |

Bands: `poor` (<40), `fair` (<60), `good` (<80), `excellent` (≥80).
Endpoint: `GET /portfolio/health` (JWT).

### Market Regime — `app/agent/nodes/regime.py`
Classifies `bull` / `bear` / `sideways` / `high_volatility` / `crisis`.
`detect_regime` reads a single event (severity + move + research sentiment);
`aggregate_regime` combines recent `market_events` into a market-wide read.
Endpoint: `GET /market/regime` (JWT).

### Scenario Simulation — `app/agent/nodes/simulation.py`
Projects **best / base / worst** outcomes for a proposed trade, with per-scenario
INR impact, expected return, expected drawdown, upside, and a 0-1 risk score. The
regime drives the scenario band and probability skew (crisis widens the band and
weights the downside; sideways is tight). `HOLD` yields an empty result.
Endpoint: `GET /simulations` (JWT, lists persisted results).

### Rebalancer — `app/services/rebalancer.py`
Detects allocation **drift** between `target_allocation` and current holdings
(holdings × price) and emits corrective BUY/SELL actions sized to restore target
weights. Targets are normalized over named tickers; a held ticker absent from the
target is sold off. Default drift threshold is 5 percentage points.
Endpoint: `POST /rebalance/preview?drift_threshold_pct=5` (JWT).

## New collections / persistence
- `simulation_results` — per-run scenario projections (indexed `{user_id, ts}`).
- `market_events` — now read back by the regime endpoint (`get_recent_market_events`).

(Both collections + indexes were already defined in `app/data/indexes.py`.)

## API summary (Phase 2 additions)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/portfolio/health` | JWT | 0-100 health score + factors |
| `GET` | `/market/regime` | JWT | current market-wide regime |
| `GET` | `/simulations` | JWT | recent scenario simulations |
| `POST` | `/rebalance/preview` | JWT | drift-correction plan |

## Tests
- `tests/test_portfolio_health.py` — scoring (diversified > concentrated, weights
  sum to 1, clamping, bands) + endpoint auth/shape.
- `tests/test_regime.py` — `detect_regime` per band, `aggregate_regime`, endpoint.
- `tests/test_simulation.py` — ordering, probability sum, crisis vs bull risk,
  concentration bump, notional scaling, HOLD empty, endpoint.
- `tests/test_rebalancer.py` — overweight→SELL, underweight→BUY, orphan→SELL,
  balanced→no-op, unpriced→no-op, endpoint.

127 tests passing, ruff clean, ~81% coverage.
