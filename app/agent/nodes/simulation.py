"""Scenario Simulation agent node.

Projects best / base / worst-case outcomes for a proposed trade *before* it is
validated, so the system (and the user) can see the risk envelope, not just a
point decision. Rule-based and deterministic for the same reasons as the
confidence and regime nodes: cheap, reproducible, auditable.

The market **regime** drives the scenario parameters — a crisis regime widens
the band and skews probability toward the downside; a calm sideways regime
produces a tight band. Outputs a :class:`~app.models.schemas.SimulationResult`
with per-scenario INR portfolio impact plus aggregate expected return, expected
drawdown, upside, and a 0-1 risk score.

The pure core (:func:`simulate`) takes a resolved price so it never does I/O and
is trivially testable; :func:`run_simulation` resolves the price from the market
provider and delegates.
"""

from typing import Optional

from app.models.schemas import (
    MarketRegime,
    RiskAssessment,
    ScenarioOutcome,
    SimulationResult,
    TradeDecision,
)

# regime -> (base_move_pct, band_pct, (p_best, p_base, p_worst))
_REGIME_PARAMS = {
    "bull": (3.0, 5.0, (0.40, 0.45, 0.15)),
    "bear": (-3.0, 5.0, (0.15, 0.45, 0.40)),
    "sideways": (0.0, 3.0, (0.25, 0.50, 0.25)),
    "high_volatility": (0.0, 10.0, (0.30, 0.40, 0.30)),
    "crisis": (-5.0, 15.0, (0.10, 0.35, 0.55)),
}
_DEFAULT_PARAMS = (0.0, 5.0, (0.25, 0.50, 0.25))


def simulate(
    decision: TradeDecision,
    price: float,
    regime: Optional[MarketRegime] = None,
    risk: Optional[RiskAssessment] = None,
) -> SimulationResult:
    """Project best/base/worst outcomes for ``decision``. Pure/deterministic.

    Returns an empty/zeroed result for HOLD (nothing is traded).
    """
    if decision.action == "HOLD" or decision.quantity <= 0:
        return SimulationResult(
            scenarios=[], expected_return_pct=0.0, expected_drawdown_pct=0.0,
            risk_score=0.0, upside_pct=0.0,
        )

    base_move, band, (p_best, p_base, p_worst) = _REGIME_PARAMS.get(
        regime.regime if regime else "", _DEFAULT_PARAMS
    )

    # Forward return of the position under each scenario (in %).
    best_ret = base_move + band
    base_ret = base_move
    worst_ret = base_move - band

    # A SELL exits/avoids exposure, so the P&L sign of a price move flips: a
    # worst-case price drop becomes a positive "avoided loss" for the seller.
    direction = 1.0 if decision.action == "BUY" else -1.0
    best_ret, base_ret, worst_ret = (
        direction * best_ret,
        direction * base_ret,
        direction * worst_ret,
    )
    # After flipping, best should be the max; reorder so labels stay meaningful.
    hi, mid, lo = sorted([best_ret, base_ret, worst_ret], reverse=True)

    notional = decision.quantity * price

    def _impact(ret_pct: float) -> float:
        return round(notional * ret_pct / 100.0, 2)

    scenarios = [
        ScenarioOutcome(name="best", probability=p_best, expected_return_pct=round(hi, 2), portfolio_impact=_impact(hi)),
        ScenarioOutcome(name="base", probability=p_base, expected_return_pct=round(mid, 2), portfolio_impact=_impact(mid)),
        ScenarioOutcome(name="worst", probability=p_worst, expected_return_pct=round(lo, 2), portfolio_impact=_impact(lo)),
    ]

    expected_return = round(p_best * hi + p_base * mid + p_worst * lo, 2)
    expected_drawdown = round(abs(min(lo, 0.0)), 2)  # magnitude of worst-case loss
    upside = round(max(hi, 0.0), 2)

    # Risk score (0-1): blend of downside magnitude and band width, nudged by a
    # high concentration read. Scaled so a crisis-sized 20% drawdown approaches 1.
    risk_score = min(1.0, expected_drawdown / 20.0 + band / 40.0)
    if risk and risk.concentration_risk == "high":
        risk_score = min(1.0, risk_score + 0.1)
    risk_score = round(risk_score, 2)

    return SimulationResult(
        scenarios=scenarios,
        expected_return_pct=expected_return,
        expected_drawdown_pct=expected_drawdown,
        risk_score=risk_score,
        upside_pct=upside,
    )


async def run_simulation(
    decision: TradeDecision,
    regime: Optional[MarketRegime] = None,
    risk: Optional[RiskAssessment] = None,
    price: Optional[float] = None,
) -> SimulationResult:
    """Resolve a price (if not given) and simulate. Never raises."""
    if price is None:
        try:
            from app.agent.pricing import get_reference_price

            price = get_reference_price(decision.ticker)
        except Exception:
            price = 0.0
    return simulate(decision, price, regime=regime, risk=risk)


__all__ = ["simulate", "run_simulation"]
