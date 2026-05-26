import asyncio
from typing import TypedDict

from app.models.schemas import MarketEvent
from app.agent.nodes.signal import classify_market_event
from app.agent.nodes.risk import assess_portfolio_risk
from app.agent.nodes.strategy import generate_trade_strategy
from app.agent.nodes.validator import validate_trade_decision
from app.agent.nodes.execution import execute_trade_decision
from app.agent.nodes.audit import audit_agent_action


class AgentState(TypedDict):
    user_id: str
    event: MarketEvent
    signal: dict
    risk: dict
    decision: dict
    validation: dict
    execution_result: dict


async def run_vestra_workflow(user_id: str, event: MarketEvent):
    signal = classify_market_event(event)

    risk = await assess_portfolio_risk(user_id)

    decision = await generate_trade_strategy(
        event,
        signal,
        risk
    )

    validation = validate_trade_decision(
        decision,
        risk,
        {event.ticker: 10}
    )

    if not validation.approved:
        await audit_agent_action(
            user_id,
            "validator",
            "trade_rejected",
            {
                "decision": decision.model_dump(),
                "reason": validation.reason
            }
        )

        return {
            "status": "rejected",
            "reason": validation.reason
        }

    execution = await execute_trade_decision(
        user_id,
        decision.action,
        decision.ticker,
        decision.quantity,
        1000.0
    )

    await audit_agent_action(
        user_id,
        "execution",
        "trade_executed",
        {
            "decision": decision.model_dump(),
            "execution": execution
        }
    )

    return {
        "status": "success",
        "decision": decision,
        "execution": execution
    }
