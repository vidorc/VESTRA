"""Portfolio Health Engine — a 0-100 score of overall portfolio health.

A "credit score" for a portfolio: a single, explainable number backed by the
factors that produced it. It is a sticky, user-facing feature (Executive
Dashboard) and is intentionally **deterministic and rule-based** — the same
inputs always yield the same score, which matters for auditability and for
explaining *why* the number moved.

The core scoring function is **pure**: it takes resolved prices as an argument so
it never does I/O and is trivially testable. A thin async wrapper
(:func:`compute_portfolio_health`) resolves prices from the market provider and
delegates to it.

Factors (weighted):
* diversification   -- how many sectors and how evenly spread (Herfindahl-based).
* concentration     -- inverse of single-sector dominance (reuses sectors module).
* liquidity         -- cash as a share of total portfolio value.
* volatility        -- best-effort; neutral default without price history.
* goal_alignment    -- neutral default until goals exist (Phase 4).
"""

from typing import Dict, List, Optional

from app.agent.sectors import assess_concentration
from app.models.schemas import Goal, HealthFactor, PortfolioHealth
from app.services.goals import goal_alignment_score


def _coerce_goals(goals: Optional[list]) -> List[Goal]:
    """Normalize raw goal dicts (from Mongo) into Goal models; drop invalid ones."""
    out: List[Goal] = []
    for g in goals or []:
        if isinstance(g, Goal):
            out.append(g)
            continue
        if isinstance(g, dict):
            try:
                out.append(Goal(**{k: v for k, v in g.items() if k not in ("_id",)}))
            except Exception:
                continue
    return out


# (factor name -> weight). Weights sum to 1.0.
_WEIGHTS = {
    "diversification": 0.30,
    "concentration": 0.25,
    "liquidity": 0.20,
    "volatility": 0.15,
    "goal_alignment": 0.10,
}

# Concentration tier -> score (inverse of risk).
_CONCENTRATION_SCORE = {"low": 90.0, "medium": 60.0, "high": 25.0}


def _clamp_score(x: float) -> float:
    return max(0.0, min(100.0, round(x, 1)))


def _band(score: float) -> str:
    if score >= 80:
        return "excellent"
    if score >= 60:
        return "good"
    if score >= 40:
        return "fair"
    return "poor"


def _diversification_score(sector_breakdown: Dict[str, float]) -> tuple[float, str]:
    """Score how spread the portfolio is across sectors (Herfindahl-based).

    HHI = sum of squared sector shares (1.0 == everything in one sector). We map
    a normalized HHI to 0-100 so more, more-even sectors score higher.
    """
    total = sum(sector_breakdown.values())
    if total <= 0 or not sector_breakdown:
        return 0.0, "No holdings."
    shares = [v / total for v in sector_breakdown.values()]
    hhi = sum(s * s for s in shares)
    n = len(sector_breakdown)
    # Best achievable HHI for n sectors is 1/n (perfectly even). Normalize so
    # an even spread scores ~100 and single-sector scores low.
    if n == 1:
        score = 20.0
    else:
        # Map hhi in [1/n, 1] -> score in [100, ~20].
        min_hhi = 1.0 / n
        norm = (hhi - min_hhi) / (1.0 - min_hhi)  # 0 (even) .. 1 (concentrated)
        score = 100.0 - 80.0 * norm
    return _clamp_score(score), f"{n} sector(s); HHI {hhi:.2f}."


def _liquidity_score(cash: float, invested_value: float) -> tuple[float, str]:
    """Score cash buffer as a share of total portfolio value.

    Too little cash (illiquid) and an enormous cash drag are both suboptimal; we
    reward a healthy buffer (~10-40%) and gently penalize extremes.
    """
    total = cash + invested_value
    if total <= 0:
        return 50.0, "No portfolio value."
    ratio = cash / total
    if ratio < 0.05:
        score = 40.0
    elif ratio <= 0.40:
        score = 90.0
    elif ratio <= 0.70:
        score = 65.0
    else:
        score = 45.0  # mostly cash -> capital not working
    return _clamp_score(score), f"Cash is {ratio * 100:.0f}% of portfolio."


def score_portfolio_health(
    holdings: Dict[str, int],
    cash_balance: float,
    prices: Dict[str, float],
    target_allocation: Optional[Dict[str, float]] = None,
    goals: Optional[list] = None,
    volatility_score: Optional[float] = None,
) -> PortfolioHealth:
    """Pure scoring: compute :class:`PortfolioHealth` from resolved inputs.

    ``prices`` maps TICKER -> price; ``volatility_score`` (0-100) may be supplied
    when price history is available, else a neutral default is used.
    """
    holdings = holdings or {}
    invested_value = sum(prices.get(t.upper(), 0.0) * q for t, q in holdings.items())

    concentration = assess_concentration(holdings)
    sector_breakdown = concentration["sector_breakdown"]

    div_score, div_note = _diversification_score(sector_breakdown)
    conc_score = _CONCENTRATION_SCORE.get(concentration["concentration_risk"], 50.0)
    liq_score, liq_note = _liquidity_score(cash_balance, invested_value)

    # Volatility: neutral default (no price history wired yet). Accepts override.
    vol_score = 60.0 if volatility_score is None else _clamp_score(volatility_score)

    # Goal alignment: real priority-weighted funding score (Phase 4). Neutral
    # 50 when no goals are set, so health is unchanged until the user adds goals.
    goal_objs = _coerce_goals(goals)
    goal_score = goal_alignment_score(goal_objs)
    goal_note = "no goals set" if not goal_objs else f"{len(goal_objs)} goal(s) tracked"

    factors: List[HealthFactor] = [
        HealthFactor(name="diversification", score=div_score, weight=_WEIGHTS["diversification"], note=div_note),
        HealthFactor(
            name="concentration",
            score=conc_score,
            weight=_WEIGHTS["concentration"],
            note=f"{concentration['concentration_risk']} concentration"
            + (f" in {concentration['largest_sector']}" if concentration["largest_sector"] else ""),
        ),
        HealthFactor(name="liquidity", score=liq_score, weight=_WEIGHTS["liquidity"], note=liq_note),
        HealthFactor(name="volatility", score=vol_score, weight=_WEIGHTS["volatility"], note="neutral default (no price history)"),
        HealthFactor(name="goal_alignment", score=goal_score, weight=_WEIGHTS["goal_alignment"], note=goal_note),
    ]

    overall = _clamp_score(sum(f.score * f.weight for f in factors))
    return PortfolioHealth(score=overall, band=_band(overall), factors=factors)


async def compute_portfolio_health(
    holdings: Dict[str, int],
    cash_balance: float,
    target_allocation: Optional[Dict[str, float]] = None,
    goals: Optional[list] = None,
) -> PortfolioHealth:
    """Resolve prices from the market provider and score health. Never raises."""
    from app.data.market.provider import get_market_data_provider

    provider = get_market_data_provider()
    prices: Dict[str, float] = {}
    for ticker in (holdings or {}):
        try:
            prices[ticker.upper()] = provider.get_cached_price(ticker)
        except Exception:
            prices[ticker.upper()] = 0.0

    return score_portfolio_health(
        holdings, cash_balance, prices, target_allocation=target_allocation, goals=goals
    )


__all__ = ["score_portfolio_health", "compute_portfolio_health"]
