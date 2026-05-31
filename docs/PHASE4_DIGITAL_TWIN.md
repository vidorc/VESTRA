# Phase 4 (partial) — Digital Twin & Goal-Based Investing

The master prompt calls the Digital Twin "probably the biggest upgrade": it makes
Vestra reason about *the investor*, not just the ticker. This slice lands the
twin + goals foundation. (The Personal CFO layer and wiring `liquidity_pressure`
into CIO/risk reasoning remain for a later Phase 4/5 pass.)

## Digital Twin — `DigitalTwin` schema + `digital_twins` collection

A financial model of the investor: `age`, `annual_income`, `monthly_expenses`,
`monthly_emi`, `monthly_sip`, `emergency_fund`, `tax_bracket`, `risk_profile`.
Computed properties:
- `monthly_surplus` = income/12 − expenses − EMI − SIP
- `recommended_emergency_fund` = 6 × (expenses + EMI)

One twin per user (unique index). Endpoints: `GET /digital-twin`, `PUT /digital-twin`.

## Goals — `Goal` schema + `goals` collection

Types: `retirement`, `house`, `education`, `emergency_fund`, `wealth_growth`.
Fields: `target_amount`, `current_amount`, `target_date`, `priority`, plus a
computed `progress_pct`. CRUD endpoints, all **ownership-scoped** (a user can only
see/modify their own goals):
`GET /goals`, `POST /goals`, `PUT /goals/{id}`, `DELETE /goals/{id}`.

## Goals service — `app/services/goals.py` (deterministic)

- `goal_alignment_score(goals)` → 0-100 priority-weighted funding progress.
  Neutral 50 with no goals. **Now powers the Portfolio Health Engine's
  `goal_alignment` factor** (previously a stub), so health reflects goal funding.
- `liquidity_need(goals, twin)` → near-term cash requirement: unfunded goals due
  within 12 months + any emergency-fund shortfall.
- `liquidity_pressure(...)` → low/medium/high vs. portfolio value. (Ready to bias
  CIO/risk reasoning toward preservation; wiring is a later step.)

## Tests
`tests/test_digital_twin_goals.py` — alignment weighting, liquidity math, bad-date
tolerance, health-engine integration, twin PUT/GET, goals CRUD + ownership (403→404
on cross-user access).

137 tests passing, ruff clean, ~83% coverage.
