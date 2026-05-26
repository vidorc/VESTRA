import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()


async def seed():
    client = AsyncIOMotorClient(os.getenv("MONGODB_URI"))
    db = client["vestra"]

    await db.investor_profiles.insert_one({
        "user_id": "user_001",
        "risk_tolerance": "moderate",
        "cash_balance": 100000,
        "target_allocation": {
            "AAPL": 30,
            "GOOGL": 20
        },
        "holdings": {
            "AAPL": 50
        }
    })

    print("Seeded test investor")


asyncio.run(seed())