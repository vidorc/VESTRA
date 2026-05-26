import asyncio
from app.agent.graph import run_agent


async def main():
    await run_agent(
        user_id="user_001",
        market_event={
            "ticker": "AAPL",
            "price_change_percent": -12.0,
            "breaking_news_summary": "Semiconductor supply chain collapse."
        }
    )


asyncio.run(main())