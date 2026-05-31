from app.models.schemas import RiskAssessment
from app.mcp.server import get_profile, get_market_exposure


class RiskAssessmentError(RuntimeError):
    """Raised when portfolio risk cannot be assessed (e.g. missing profile)."""


# Safe trade limits by declared risk tolerance.
_SAFE_TRADE_LIMITS = {
    "aggressive": 20,
    "moderate": 10,
    "conservative": 5,
}
_DEFAULT_SAFE_TRADE_LIMIT = 5


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

    safe_trade_limit = _SAFE_TRADE_LIMITS.get(
        risk_tolerance, _DEFAULT_SAFE_TRADE_LIMIT
    )

    if concentration == "high":
        notes = "Investor heavily concentrated; reduce exposure carefully."
    elif concentration == "medium":
        notes = "Moderate concentration risk."
    else:
        notes = "Portfolio diversified."

    return RiskAssessment(
        concentration_risk=concentration,
        cash_available=cash,
        safe_trade_limit=safe_trade_limit,
        notes=notes
    )