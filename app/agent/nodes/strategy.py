import os
import json
from dotenv import load_dotenv
from langchain_groq import ChatGroq

from app.models.schemas import (
    MarketEvent,
    SignalAssessment,
    RiskAssessment,
    TradeDecision
)

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.2
)


async def generate_trade_strategy(
    event: MarketEvent,
    signal: SignalAssessment,
    risk: RiskAssessment
) -> TradeDecision:

    prompt = f"""
You are an AI fiduciary investment advisor for Indian retail investors.

Your job is disciplined portfolio decision making.

MARKET EVENT:
Ticker: {event.ticker}
Move: {event.price_change_percent}%
News: {event.breaking_news_summary}

SIGNAL ANALYSIS:
Event Type: {signal.event_type}
Severity: {signal.severity}
Impacted Assets: {signal.impacted_assets}

RISK PROFILE:
Cash Available: ₹{risk.cash_available}
Concentration Risk: {risk.concentration_risk}
Safe Trade Limit: {risk.safe_trade_limit}
Notes: {risk.notes}

Rules:
- Conservative investors avoid aggressive trades
- Moderate investors reduce risk rationally
- Aggressive investors can take calculated opportunities
- NEVER exceed safe trade limit
- HOLD if uncertainty is high
- Think like a disciplined Indian portfolio manager
- Return ONLY JSON

Format:
{{
    "action": "BUY or SELL or HOLD",
    "ticker": "{event.ticker}",
    "quantity": integer,
    "reasoning": "short explanation"
}}
"""

    response = await llm.ainvoke(prompt)

    content = response.content

    if isinstance(content, list):
        content = content[0]

    parsed = json.loads(content)

    return TradeDecision(**parsed)