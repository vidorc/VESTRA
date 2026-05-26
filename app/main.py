from fastapi import FastAPI
from app.models.schemas import MarketEvent
from app.agent.graph import run_vestra_workflow

app = FastAPI()


@app.get("/")
def root():
    return {"status": "Vestra X running"}


@app.post("/webhook/market-alert")
async def market_alert(event: MarketEvent):
    result = await run_vestra_workflow(
        user_id="user_001",
        event=event
    )

    return result
