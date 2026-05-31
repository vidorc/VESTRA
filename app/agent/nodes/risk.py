from app.models.schemas import DigitalTwin, Goal, RiskAssessment
from app.mcp.server import get_profile, get_market_exposure
from app.agent.pricing import get_reference_price
from app.data.repository import get_digital_twin, list_goals
from app.services.goals import liquidity_pressure


class RiskAssessmentError(RuntimeError):
    """Raised when portfolio risk cannot be assessed (e.g. missing profile)."""


# Safe trade limits by declared risk tolerance.
_SAFE_TRADE_LIMITS = {
    "aggressive": 20,
    "moderate": 10,
    "conservative": 5,
}
_DEFAULT_SAFE_TRADE_LIMIT = 5

# How hard each liquidity-pressure band cuts the safe trade limit. The Personal
# CFO principle: when the investor needs cash soon, preserve capital -- shrink how
# much the agent may trade in one move.
_LIQUIDITY_LIMIT_FACTOR = {"low": 1.0, "medium": 0.5, "high": 0.25}


def _portfolio_value(cash: float, holdings: dict) -> float:
    """Estimate total portfolio value (INR): cash + holdings at reference price.

    Uses the synchronous, non-blocking reference-price seam so the hot path never
    does network I/O.
    """
    value = float(cash or 0.0)
    for ticker, qty in (holdings or {}).items():
        value += float(qty or 0) * get_reference_price(ticker)
    return value


async def _load_liquidity_pressure(user_id: str, portfolio_value: float) -> str:
    """Compute the investor's near-term liquidity pressure (low/medium/high).

    Best-effort: a missing twin or goals collection must never break risk
    assessment, so any error degrades to ``"low"``.
    """
    try:
        goal_docs = await list_goals(user_id)
        goals = [Goal(**{k: v for k, v in g.items() if k in Goal.model_fields}) for g in goal_docs]
        twin_doc = await get_digital_twin(user_id)
        twin = (
            DigitalTwin(**{k: v for k, v in twin_doc.items() if k in DigitalTwin.model_fields})
            if twin_doc
            else None
        )
        return liquidity_pressure(goals, twin, portfolio_value=portfolio_value)
    except Exception:
        return "low"


async def assess_portfolio_risk(user_id: str) -> RiskAssessment:
    profile = await get_profile(user_id)
    exposure = await get_market_exposure(user_id)

    if isinstance(profile, dict) and "error" in profile:
        raise RiskAssessmentError(
            f"Could not load profile for {user_id}: {profile['error']}"
        )

    if isinstance(exposure, dict) and "error" in exposure:
        raise RiskAssessmentError(
            f"Could not load exposure for {user_id}: {exposure['error']}"
        )

    # Default to the most conservative interpretation when fields are absent.
    risk_tolerance = profile.get("risk_tolerance", "conservative")
    cash = exposure.get("cash_balance", 0)
    concentration = exposure.get("concentration_risk", "low")

    base_limit = _SAFE_TRADE_LIMITS.get(risk_tolerance, _DEFAULT_SAFE_TRADE_LIMIT)

    # Personal CFO: bias toward preservation when near-term cash needs are large
    # relative to the portfolio. High pressure shrinks the safe trade limit.
    portfolio_value = _portfolio_value(cash, profile.get("holdings", {}))
    pressure = await _load_liquidity_pressure(user_id, portfolio_value)
    safe_trade_limit = max(1, int(base_limit * _LIQUIDITY_LIMIT_FACTOR.get(pressure, 1.0)))

    if concentration == "high":
        notes = "Investor heavily concentrated; reduce exposure carefully."
    elif concentration == "medium":
        notes = "Moderate concentration risk."
    else:
        notes = "Portfolio diversified."

    if pressure == "high":
        notes += " High near-term liquidity pressure; preserve capital and limit new exposure."
    elif pressure == "medium":
        notes += " Moderate liquidity pressure; size positions conservatively."

    return RiskAssessment(
        concentration_risk=concentration,
        cash_available=cash,
        safe_trade_limit=safe_trade_limit,
        notes=notes,
        liquidity_pressure=pressure,
    )