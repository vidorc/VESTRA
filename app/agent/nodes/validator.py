from typing import Optional

from app.agent.pricing import get_reference_price
from app.models.schemas import TradeDecision, RiskAssessment, ValidationResult


def validate_trade_decision(
    decision: TradeDecision,
    risk: RiskAssessment,
    current_holdings: dict = None,
    price: Optional[float] = None
) -> ValidationResult:

    if current_holdings is None:
        current_holdings = {}

    if price is None:
        price = get_reference_price(decision.ticker)

    if decision.action == "HOLD":
        return ValidationResult(
            approved=True,
            reason="Hold decision requires no execution."
        )

    if decision.quantity <= 0:
        return ValidationResult(
            approved=False,
            reason="Trade quantity must be greater than zero."
        )

    if decision.quantity > risk.safe_trade_limit:
        return ValidationResult(
            approved=False,
            reason="Trade exceeds safe trade limit."
        )

    if decision.action == "BUY":
        estimated_cost = decision.quantity * price

        if estimated_cost > risk.cash_available:
            return ValidationResult(
                approved=False,
                reason="Insufficient cash balance."
            )

    if decision.action == "SELL":
        owned = current_holdings.get(decision.ticker, 0)

        if decision.quantity > owned:
            return ValidationResult(
                approved=False,
                reason="Cannot sell more than owned holdings."
            )

    return ValidationResult(
        approved=True,
        reason="Trade approved."
    )