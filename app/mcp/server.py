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
    try:
        profile = await db.investor_profiles.find_one({"user_id": user_id})

        if not profile:
            return {"error": "Profile not found"}

        profile.pop("_id", None)
        return profile

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def get_market_exposure(user_id: str):
    try:
        profile = await db.investor_profiles.find_one({"user_id": user_id})

        if not profile:
            return {"error": "Profile not found"}

        holdings = profile.get("holdings", {})
        cash = profile.get("cash_balance", 0)

        total_positions = sum(holdings.values())

        tech_names = {"AAPL", "MSFT", "GOOGL", "NVDA", "AMD"}
        tech_exposure = sum(
            qty for symbol, qty in holdings.items()
            if symbol in tech_names
        )

        concentration = "low"

        if total_positions > 0:
            ratio = tech_exposure / total_positions

            if ratio > 0.6:
                concentration = "high"
            elif ratio > 0.3:
                concentration = "medium"

        return {
            "cash_balance": cash,
            "total_positions": total_positions,
            "tech_exposure": tech_exposure,
            "concentration_risk": concentration
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def execute_trade(
    user_id: str,
    ticker: str,
    action: str,
    quantity: int,
    price: float
):
    try:
        profile = await db.investor_profiles.find_one({"user_id": user_id})

        if not profile:
            return {"error": "Profile not found"}

        holdings = profile.get("holdings", {})
        cash_balance = profile.get("cash_balance", 0)

        ticker = ticker.upper()
        action = action.upper()

        total = quantity * price

        if action == "BUY":
            if cash_balance < total:
                return {"error": "Insufficient balance"}

            holdings[ticker] = holdings.get(ticker, 0) + quantity
            cash_balance -= total

        elif action == "SELL":
            current = holdings.get(ticker, 0)

            if current < quantity:
                return {"error": "Insufficient holdings"}

            holdings[ticker] -= quantity
            cash_balance += total

        else:
            return {"error": "Invalid action"}

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
            "ticker": ticker,
            "action": action,
            "quantity": quantity,
            "updated_cash": cash_balance
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def reject_trade(
    user_id: str,
    ticker: str,
    reason: str
):
    try:
        result = await db.rejected_trades.insert_one({
            "user_id": user_id,
            "ticker": ticker,
            "reason": reason
        })

        return {
            "status": "rejected_logged",
            "id": str(result.inserted_id)
        }

    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
async def log_reasoning(
    user_id: str,
    agent_name: str,
    action: str,
    payload: dict
):
    try:
        result = await db.agent_audit_logs.insert_one({
            "user_id": user_id,
            "agent_name": agent_name,
            "action": action,
            "payload": payload
        })

        return {
            "status": "logged",
            "id": str(result.inserted_id)
        }

    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    mcp.run()
