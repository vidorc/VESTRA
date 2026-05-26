from app.mcp.server import execute_trade


async def execute_trade_decision(
    user_id: str,
    action: str,
    ticker: str,
    quantity: int,
    price: float = 1000.0
):
    if action == "HOLD":
        return {
            "status": "no_action",
            "message": "No execution required."
        }

    return await execute_trade(
        user_id=user_id,
        action=action,
        ticker=ticker,
        quantity=quantity,
        price=price
    )
