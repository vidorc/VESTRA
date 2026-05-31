"""Risk Stress Testing -- named macro shocks applied to the whole portfolio.

Before (and alongside) any trade, an institutional risk desk asks "what if the
market falls 15%? what if the RBI surprises? what if our biggest sector cracks?"
This module answers that for a retail book: it applies a fixed set of named
shocks to current holdings using per-sector sensitivities and reports the
projected loss under each, plus an overall resilience read.

Deterministic and rule-based (like the simulation/confidence/regime nodes): the
same holdings + prices always yield the same stress test, so the risk report is
reproducible and auditable. The pure core (:func:`stress_test`) takes a resolved
``prices`` map and never does I/O; :func:`run_stress_test` resolves prices from
the market provider and delegates.

Sector sensitivities are deliberately simple, transparent betas keyed to the
Indian-equity sectors in ``app.agent.sectors``. They are a planning tool, not a
forecast -- the point is to show the *shape* of the risk, not to be precise.
"""

from typing import Dict, List, Optional

from app.agent.sectors import get_sector
from app.models.schemas import StressScenario, StressTestResult

# Per-sector beta to a broad market move (1.0 == moves with the market).
# Defensives (FMCG) dampen; rate-/cycle-sensitive sectors (banking, infra) amplify.
_MARKET_BETA = {
    "banking": 1.3,
    "infrastructure": 1.2,
    "energy": 1.1,
    "it": 1.0,
    "index": 1.0,
    "fmcg": 0.6,
    "other": 1.0,
}

# Per-sector shock from an RBI rate surprise (a hawkish surprise hurts rate- and
# capital-intensive sectors most; exporters/defensives are relatively insulated).
_RBI_SHOCK_PCT = {
    "banking": -8.0,
    "infrastructure": -6.0,
    "energy": -4.0,
    "other": -3.0,
    "index": -3.0,
    "fmcg": -2.0,
    "it": -1.0,
}

# A single-sector crash: the worst-hit sector loses this; spillover hits the rest.
_SECTOR_CRASH_PCT = -30.0
_SECTOR_CRASH_SPILLOVER_PCT = -3.0

# Resilience thresholds on worst-case loss as a share of total portfolio value.
_FRAGILE_LOSS_PCT = 25.0
_MODERATE_LOSS_PCT = 12.0


def _sector_values(holdings: Dict[str, int], prices: Dict[str, float]) -> Dict[str, float]:
    """Aggregate INR position value by sector."""
    by_sector: Dict[str, float] = {}
    for ticker, qty in (holdings or {}).items():
        if qty <= 0:
            continue
        price = prices.get(ticker.upper(), prices.get(ticker, 0.0)) or 0.0
        value = qty * price
        sector = get_sector(ticker)
        by_sector[sector] = by_sector.get(sector, 0.0) + value
    return by_sector


def _apply_uniform_move(sector_values: Dict[str, float], move_pct: float) -> Dict[str, float]:
    """Apply a broad market move scaled by each sector's beta. Returns loss per sector."""
    losses: Dict[str, float] = {}
    for sector, value in sector_values.items():
        beta = _MARKET_BETA.get(sector, 1.0)
        losses[sector] = value * (move_pct / 100.0) * beta
    return losses


def _scenario_from_losses(
    name: str,
    label: str,
    invested: float,
    portfolio_value: float,
    sector_losses: Dict[str, float],
    note: str,
) -> StressScenario:
    """Build a StressScenario from per-sector signed losses (negative == loss)."""
    total_change = sum(sector_losses.values())
    loss = round(-total_change, 2)  # positive == loss
    value_after = round(portfolio_value + total_change, 2)
    loss_pct = round(100.0 * loss / portfolio_value, 2) if portfolio_value > 0 else 0.0

    # Worst-hit sector (largest negative change).
    worst_sector = None
    if sector_losses:
        worst_sector, worst_change = min(sector_losses.items(), key=lambda kv: kv[1])
        if worst_change >= 0:  # nothing actually lost
            worst_sector = None

    return StressScenario(
        name=name,
        label=label,
        value_before=round(portfolio_value, 2),
        value_after=value_after,
        loss=loss,
        loss_pct=loss_pct,
        worst_sector=worst_sector,
        note=note,
    )


def stress_test(
    holdings: Dict[str, int],
    prices: Dict[str, float],
    cash: float = 0.0,
) -> StressTestResult:
    """Stress the portfolio against named macro shocks. Pure/deterministic.

    ``holdings`` maps ticker -> quantity; ``prices`` maps ticker -> INR price;
    ``cash`` is uninvested balance (shocked sectors don't touch it).
    """
    sector_values = _sector_values(holdings, prices)
    invested = round(sum(sector_values.values()), 2)
    portfolio_value = round(invested + max(0.0, cash), 2)

    scenarios: List[StressScenario] = []

    # Empty/cash-only book: nothing at market risk.
    if invested <= 0:
        return StressTestResult(
            portfolio_value=portfolio_value,
            invested_value=invested,
            scenarios=[],
            worst_case_loss_pct=0.0,
            resilience="robust",
            note="No invested positions — nothing exposed to market shocks.",
        )

    # 1) Broad market falls 5%.
    scenarios.append(
        _scenario_from_losses(
            "market_drop_5", "Market falls 5%", invested, portfolio_value,
            _apply_uniform_move(sector_values, -5.0),
            "Broad sell-off; losses scaled by each sector's market beta.",
        )
    )

    # 2) Broad market falls 15%.
    scenarios.append(
        _scenario_from_losses(
            "market_drop_15", "Market falls 15%", invested, portfolio_value,
            _apply_uniform_move(sector_values, -15.0),
            "Sharp drawdown; high-beta sectors (banking, infra) lead the fall.",
        )
    )

    # 3) RBI rate surprise -- per-sector shock, rate-sensitive sectors hit hardest.
    rbi_losses = {
        sector: value * (_RBI_SHOCK_PCT.get(sector, -3.0) / 100.0)
        for sector, value in sector_values.items()
    }
    scenarios.append(
        _scenario_from_losses(
            "rbi_surprise", "RBI rate surprise", invested, portfolio_value, rbi_losses,
            "Hawkish surprise; banks and capital-intensive sectors repriced down.",
        )
    )

    # 4) Single-sector crash -- the largest sector craters, modest spillover elsewhere.
    largest_sector = max(sector_values.items(), key=lambda kv: kv[1])[0]
    crash_losses = {}
    for sector, value in sector_values.items():
        move = _SECTOR_CRASH_PCT if sector == largest_sector else _SECTOR_CRASH_SPILLOVER_PCT
        crash_losses[sector] = value * (move / 100.0)
    scenarios.append(
        _scenario_from_losses(
            "sector_crash", f"{largest_sector.title()} sector crash",
            invested, portfolio_value, crash_losses,
            f"Your largest sector ({largest_sector}) drops {abs(_SECTOR_CRASH_PCT):.0f}%; others see spillover.",
        )
    )

    worst_case_loss_pct = round(max((s.loss_pct for s in scenarios), default=0.0), 2)

    if worst_case_loss_pct >= _FRAGILE_LOSS_PCT:
        resilience = "fragile"
        note = "Worst-case loss is severe — the book is concentrated and exposed. Consider diversifying or raising cash."
    elif worst_case_loss_pct >= _MODERATE_LOSS_PCT:
        resilience = "moderate"
        note = "The book absorbs mild shocks but a sharp move or sector crash would sting."
    else:
        resilience = "robust"
        note = "The book holds up well across the tested shocks."

    return StressTestResult(
        portfolio_value=portfolio_value,
        invested_value=invested,
        scenarios=scenarios,
        worst_case_loss_pct=worst_case_loss_pct,
        resilience=resilience,
        note=note,
    )


async def run_stress_test(
    holdings: Dict[str, int],
    cash: float = 0.0,
    prices: Optional[Dict[str, float]] = None,
) -> StressTestResult:
    """Resolve prices (if not given) and stress-test the book. Never raises."""
    if prices is None:
        prices = {}
        try:
            from app.agent.pricing import get_reference_price

            for ticker in (holdings or {}):
                prices[ticker.upper()] = get_reference_price(ticker)
        except Exception:
            prices = {}
    return stress_test(holdings or {}, prices, cash=cash)


__all__ = ["stress_test", "run_stress_test"]
