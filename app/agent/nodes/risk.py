from app.models.schemas import RiskAssessment
from app.mcp.server import get_profile, get_market_exposure


async def assess_portfolio_risk(user_id: str) -> RiskAssessment:
    profile = await get_profile(user_id)
    exposure = await get_market_exposure(user_id)

    if "error" in profile:
        raise Exception(profile["error"])

    if "error" in exposure:
        raise Exception(exposure["error"])

    risk_tolerance = profile["risk_tolerance"]
    cash = exposure["cash_balance"]
    concentration = exposure["concentration_risk"]

    safe_trade_limit = 5

    if risk_tolerance == "aggressive":
        safe_trade_limit = 20
    elif risk_tolerance == "moderate":
        safe_trade_limit = 10
    elif risk_tolerance == "conservative":
        safe_trade_limit = 5

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