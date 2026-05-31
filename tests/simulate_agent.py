"""Manual integration script: run the full Vestra workflow in-process.

NOT collected by pytest (see pytest.ini — only ``test_*.py`` is collected, and
this is ``simulate_*``). It hits the live LLM and live MongoDB, so run it by
hand against a configured stack:

    python tests/simulate_agent.py

Requires GROQ_API_KEY + MONGODB_URI in the environment / .env, and a seeded
investor profile (see tests/seed_db.py).
"""

import asyncio

from app.agent.graph import run_vestra_workflow
from app.models.schemas import MarketEvent


async def main() -> None:
    result = await run_vestra_workflow(
        user_id="user_001",
        event=MarketEvent(
            ticker="RELIANCE",
            price_change_percent=-12.0,
            breaking_news_summary="Semiconductor supply chain collapse.",
        ),
    )
    print(result)


if __name__ == "__main__":
    asyncio.run(main())
