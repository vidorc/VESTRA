from typing import Optional

from app.agent.pricing import get_reference_price
from app.mcp.server import execute_trade


async def execute_trade_decision(
    user_id: str,
    action: str,
    ticker: str,
    quantity: int,
    price: Optional[float] = None
):
    if action == "HOLD":
        return {
            "status": "no_action",
            "message": "No execution required."
        }

    if price is None:
        price = get_reference_price(ticker)

    return await execute_trade(
        user_id=user_id,
        action=action,
        ticker=ticker,
        quantity=quantity,
        price=price
    )
