import os
import json
import re
from typing import TypedDict, Optional, Dict, Any

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq

from app.mcp.server import (
    get_profile,
    execute_trade,
    log_reasoning
)

load_dotenv()

console = Console()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.2,
    api_key=os.getenv("GROQ_API_KEY")
)


class AgentState(TypedDict):
    user_id: str
    market_event: Dict[str, Any]
    investor_profile: Optional[Dict[str, Any]]
    reasoning: Optional[str]
    trade_decision: Optional[Dict[str, Any]]


async def ingest_node(state: AgentState):
    event = state["market_event"]

    console.print(
        Panel.fit(
            f"[bold red]🔴 MARKET EVENT INGESTED[/bold red]\n\n"
            f"Ticker: {event['ticker']}\n"
            f"Move: {event['price_change_percent']}%\n"
            f"News: {event['breaking_news_summary']}"
        )
    )

    return state


async def retrieve_context_node(state: AgentState):
    console.print(
        "[bold green]🟢 MCP TOOL EXECUTED:[/bold green] get_profile()"
    )

    profile = await get_profile(state["user_id"])

    state["investor_profile"] = profile

    console.print(
        Panel.fit(
            f"[bold yellow]🟡 INVESTOR CONTEXT RETRIEVED[/bold yellow]\n\n"
            f"{profile}"
        )
    )

    return state


async def analyze_and_trade_node(state: AgentState):
    prompt = f"""
You are Vestra, an autonomous fiduciary investment agent.

STRICT RULES:
- Respect investor risk tolerance.
- Conservative investors avoid aggressive risk.
- Moderate investors balance preservation and opportunity.
- Aggressive investors can take calculated risk.

You MUST first explain reasoning.

Then output EXACT JSON.

FORMAT:
{{
  "action": "BUY" or "SELL" or "HOLD",
  "ticker": "AAPL",
  "quantity": 10,
  "reasoning": "..."
}}

Investor profile:
{state["investor_profile"]}

Market event:
{state["market_event"]}
"""

    response = await llm.ainvoke(prompt)
    content = response.content

    console.print(
        Panel.fit(
            f"[bold cyan]🧠 AGENT REASONING[/bold cyan]\n\n{content}"
        )
    )

    state["reasoning"] = content

    match = re.search(r"\{.*\}", content, re.DOTALL)

    if match:
        try:
            decision = json.loads(match.group())
        except Exception:
            decision = {
                "action": "HOLD",
                "ticker": state["market_event"]["ticker"],
                "quantity": 0,
                "reasoning": "JSON parsing failed"
            }
    else:
        decision = {
            "action": "HOLD",
            "ticker": state["market_event"]["ticker"],
            "quantity": 0,
            "reasoning": "No structured decision found"
        }

    state["trade_decision"] = decision

    return state


async def execute_trade_node(state: AgentState):
    decision = state["trade_decision"]

    if decision["action"] == "HOLD":
        console.print(
            "[yellow]No trade executed (HOLD decision)[/yellow]"
        )
        return state

    console.print(
        f"[bold green]🟢 MCP TOOL EXECUTED:[/bold green] execute_trade("
        f"{state['user_id']}, "
        f"{decision['ticker']}, "
        f"{decision['action']}, "
        f"{decision['quantity']}, "
        f"100.0)"
    )

    trade_result = await execute_trade(
        user_id=state["user_id"],
        ticker=decision["ticker"],
        action=decision["action"],
        quantity=decision["quantity"],
        price=100.0
    )

    console.print(
        f"[bold green]🟢 MCP TOOL EXECUTED:[/bold green] log_reasoning()"
    )

    await log_reasoning(
        user_id=state["user_id"],
        ticker=decision["ticker"],
        action=decision["action"],
        reasoning=decision["reasoning"]
    )

    table = Table(title="TRADE EXECUTION RESULT")
    table.add_column("Field")
    table.add_column("Value")

    for k, v in trade_result.items():
        table.add_row(str(k), str(v))

    console.print(table)

    return state


builder = StateGraph(AgentState)

builder.add_node("ingest", ingest_node)
builder.add_node("retrieve", retrieve_context_node)
builder.add_node("analyze", analyze_and_trade_node)
builder.add_node("execute", execute_trade_node)

builder.set_entry_point("ingest")

builder.add_edge("ingest", "retrieve")
builder.add_edge("retrieve", "analyze")
builder.add_edge("analyze", "execute")
builder.add_edge("execute", END)

graph = builder.compile()


async def run_agent(user_id: str, market_event: Dict[str, Any]):
    state = {
        "user_id": user_id,
        "market_event": market_event,
        "investor_profile": None,
        "reasoning": None,
        "trade_decision": None
    }

    return await graph.ainvoke(state)