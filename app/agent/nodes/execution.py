from typing import Optional

from app.agent.nodes.browser_executor import execute_via_browser
from app.agent.pricing import get_reference_price
from app.config import get_settings
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

    result = await execute_trade(
        user_id=user_id,
        action=action,
        ticker=ticker,
        quantity=quantity,
        price=price
    )

    # Attach browser execution evidence (Phase 3). Paper mode by default: a
    # deterministic synthetic confirmation for the audit trail, never a
    # real-money order. The mode is configurable but never "live" here.
    if isinstance(result, dict) and "error" not in result:
        mode = getattr(get_settings(), "EXECUTION_MODE", "paper")
        try:
            result["evidence"] = await execute_via_browser(
                ticker, action, quantity, price, mode=mode
            )
        except Exception:
            # Evidence capture must never break the actual trade result.
            pass

    return result
