import os
from typing import Any, Dict

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from mcp.server.fastmcp import FastMCP

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "vestra")

client = AsyncIOMotorClient(MONGODB_URI)
db = client[DATABASE_NAME]

mcp = FastMCP("vestra-mcp")


@mcp.tool()
async def get_profile(user_id: str) -> Dict[str, Any]:
    """
    Fetch investor profile and holdings.
    """
    try:
        profile = await db.investor_profiles.find_one({"user_id": user_id})

        if not profile:
            return {
                "error": f"No investor profile found for user_id={user_id}"
            }

        profile.pop("_id", None)
        return profile

    except Exception as e:
        return {
            "error": f"Database error in get_profile: {str(e)}"
        }


@mcp.tool()
async def execute_trade(
    user_id: str,
    ticker: str,
    action: str,
    quantity: int,
    price: float
) -> Dict[str, Any]:
    """
    Execute a simulated trade.
    """
    try:
        profile = await db.investor_profiles.find_one({"user_id": user_id})

        if not profile:
            return {
                "error": f"No profile found for user_id={user_id}"
            }

        holdings = profile.get("holdings", {})
        cash_balance = profile.get("cash_balance", 0)

        trade_value = quantity * price
        ticker = ticker.upper()
        action = action.upper()

        if action == "BUY":
            if cash_balance < trade_value:
                return {
                    "error": "Insufficient cash balance"
                }

            holdings[ticker] = holdings.get(ticker, 0) + quantity
            cash_balance -= trade_value

        elif action == "SELL":
            current_qty = holdings.get(ticker, 0)

            if current_qty < quantity:
                return {
                    "error": "Insufficient holdings to sell"
                }

            holdings[ticker] -= quantity
            cash_balance += trade_value

        else:
            return {
                "error": "Action must be BUY or SELL"
            }

        await db.investor_profiles.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "cash_balance": cash_balance,
                    "holdings": holdings
                }
            }
        )

        return {
            "status": "success",
            "user_id": user_id,
            "ticker": ticker,
            "action": action,
            "quantity": quantity,
            "price": price,
            "cash_balance": cash_balance
        }

    except Exception as e:
        return {
            "error": f"Database error in execute_trade: {str(e)}"
        }


@mcp.tool()
async def log_reasoning(
    user_id: str,
    ticker: str,
    action: str,
    reasoning: str
) -> Dict[str, Any]:
    """
    Store immutable audit logs.
    """
    try:
        log_doc = {
            "user_id": user_id,
            "ticker": ticker.upper(),
            "action": action.upper(),
            "reasoning": reasoning
        }

        result = await db.trade_audit_logs.insert_one(log_doc)

        return {
            "status": "logged",
            "log_id": str(result.inserted_id)
        }

    except Exception as e:
        return {
            "error": f"Database error in log_reasoning: {str(e)}"
        }


if __name__ == "__main__":
    mcp.run()