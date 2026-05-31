"""Tests for Phase 5 Institutional Intelligence.

A deterministic institutional loop layered over the existing analyst pipeline:

* Memory service  -- recall past decisions/outcomes per ticker.
* Council node     -- multiple rule-based strategy viewpoints + consensus/dissent.
* CIO node         -- FINAL authority: synthesizes strategy + council + confidence
                      + memory into the decision that actually gets executed. May
                      downsize, veto (-> HOLD), or pass through.
* Learning node    -- writes execution outcomes back to memory, closing the loop.

The council and CIO are deterministic (no LLM) so governance is predictable,
reproducible, and fully auditable -- the right property for a "final authority".
"""

import pytest
from mongomock_motor import AsyncMongoMockClient

from app.data.mongo import set_client
from app.models.schemas import (
    CIODecision,
    ConfidenceScore,
    CouncilOpinion,
    MarketRegime,
    RiskAssessment,
    SignalAssessment,
    TradeDecision,
)


@pytest.fixture
async def mongo():
    client = AsyncMongoMockClient()
    set_client(client)
    yield client["vestra_test"]
    set_client(None)


def _decision(action="BUY", ticker="RELIANCE", qty=10):
    return TradeDecision(action=action, ticker=ticker, quantity=qty, reasoning="analyst view")


def _signal(severity="medium"):
    return SignalAssessment(event_type="company", severity=severity, impacted_assets=["RELIANCE"])


def _risk(limit=20, pressure="low", concentration="low"):
    return RiskAssessment(
        concentration_risk=concentration,
        cash_available=1_000_000.0,
        safe_trade_limit=limit,
        notes="x",
        liquidity_pressure=pressure,
    )


def _conf(overall=0.8):
    return ConfidenceScore(
        decision_confidence=overall, risk_confidence=overall, data_completeness=overall, overall=overall
    )


# --- Memory service ------------------------------------------------------

async def test_memory_recall_empty_for_new_ticker(mongo):
    from app.services.memory import recall_memory

    assert await recall_memory("u1", "RELIANCE") == []


async def test_memory_save_and_recall_per_ticker(mongo):
    from app.services.memory import recall_memory, save_decision_memory

    await save_decision_memory("u1", _decision(ticker="RELIANCE"), outcome=None)
    await save_decision_memory("u1", _decision(ticker="INFY"), outcome=None)
    recalled = await recall_memory("u1", "RELIANCE")
    assert len(recalled) == 1
    assert recalled[0]["ticker"] == "RELIANCE"


async def test_memory_is_owner_and_ticker_scoped(mongo):
    from app.services.memory import recall_memory, save_decision_memory

    await save_decision_memory("u1", _decision(ticker="RELIANCE"))
    await save_decision_memory("u2", _decision(ticker="RELIANCE"))
    assert len(await recall_memory("u1", "RELIANCE")) == 1


# --- Council node --------------------------------------------------------

def test_council_produces_multiple_views_with_consensus():
    from app.agent.nodes.council import convene_council

    opinion = convene_council(_decision("BUY"), _signal(), _risk(), MarketRegime(regime="bull"))
    assert isinstance(opinion, CouncilOpinion)
    assert len(opinion.views) >= 3
    assert opinion.consensus_action in ("BUY", "SELL", "HOLD")
    assert 0.0 <= opinion.dissent <= 1.0


def test_council_dissent_high_when_views_split():
    from app.agent.nodes.council import convene_council

    # A crisis regime should split the council (some defensive, some opportunistic).
    opinion = convene_council(_decision("BUY"), _signal("critical"), _risk(), MarketRegime(regime="crisis"))
    assert opinion.dissent > 0.0


# --- CIO node (final authority) ------------------------------------------

def test_cio_passes_through_strong_aligned_decision():
    from app.agent.nodes.cio import cio_review

    council = CouncilOpinion(
        views=[], consensus_action="BUY", dissent=0.0, rationale="aligned"
    )
    verdict = cio_review(_decision("BUY", qty=10), _risk(limit=20), _conf(0.85), council, memory=[])
    assert isinstance(verdict, CIODecision)
    assert verdict.final_decision.action == "BUY"
    assert verdict.vetoed is False
    assert verdict.final_decision.quantity == 10


def test_cio_vetoes_low_confidence_to_hold():
    from app.agent.nodes.cio import cio_review

    council = CouncilOpinion(views=[], consensus_action="BUY", dissent=0.0)
    verdict = cio_review(_decision("BUY"), _risk(), _conf(0.2), council, memory=[])
    assert verdict.vetoed is True
    assert verdict.final_decision.action == "HOLD"


def test_cio_does_not_veto_sell_on_low_confidence():
    """Low confidence never blocks risk reduction -- a SELL still passes."""
    from app.agent.nodes.cio import cio_review

    council = CouncilOpinion(views=[], consensus_action="HOLD", dissent=0.5)
    verdict = cio_review(_decision("SELL", qty=5), _risk(limit=20), _conf(0.2), council, memory=[])
    assert verdict.vetoed is False
    assert verdict.final_decision.action == "SELL"


def test_cio_holds_when_council_consensus_opposes():
    from app.agent.nodes.cio import cio_review

    council = CouncilOpinion(views=[], consensus_action="HOLD", dissent=0.7)
    verdict = cio_review(_decision("BUY"), _risk(), _conf(0.8), council, memory=[])
    # Strong council opposition overrides the analyst's BUY.
    assert verdict.overrode is True
    assert verdict.final_decision.action == "HOLD"


def test_cio_allows_sell_even_when_council_says_hold():
    """Risk reduction is never blocked: a SELL passes even against a HOLD consensus."""
    from app.agent.nodes.cio import cio_review

    council = CouncilOpinion(views=[], consensus_action="HOLD", dissent=0.5)
    verdict = cio_review(_decision("SELL", qty=5), _risk(limit=20), _conf(0.8), council, memory=[])
    assert verdict.overrode is False
    assert verdict.final_decision.action == "SELL"


def test_cio_clamps_quantity_to_safe_trade_limit():
    from app.agent.nodes.cio import cio_review

    council = CouncilOpinion(views=[], consensus_action="BUY", dissent=0.0)
    verdict = cio_review(_decision("BUY", qty=100), _risk(limit=10), _conf(0.85), council, memory=[])
    assert verdict.final_decision.quantity <= 10


def test_cio_downsizes_after_repeated_recent_losses():
    from app.agent.nodes.cio import cio_review

    council = CouncilOpinion(views=[], consensus_action="BUY", dissent=0.0)
    losing_memory = [{"ticker": "RELIANCE", "outcome": {"result": "loss"}} for _ in range(3)]
    verdict = cio_review(_decision("BUY", qty=10), _risk(limit=20), _conf(0.85), council, memory=losing_memory)
    # A losing streak makes the CIO cautious: smaller size than the analyst asked.
    assert verdict.final_decision.quantity < 10
    assert verdict.final_decision.action == "BUY"


def test_cio_does_not_resurrect_hold_into_a_trade():
    """A HOLD must stay quantity 0 even with a losing streak (downsizing must not floor to 1)."""
    from app.agent.nodes.cio import cio_review

    council = CouncilOpinion(views=[], consensus_action="HOLD", dissent=0.0)
    losing_memory = [{"ticker": "RELIANCE", "outcome": {"result": "loss"}} for _ in range(3)]
    verdict = cio_review(_decision("HOLD", qty=0), _risk(limit=20), _conf(0.85), council, memory=losing_memory)
    assert verdict.final_decision.action == "HOLD"
    assert verdict.final_decision.quantity == 0


# --- Learning node -------------------------------------------------------

async def test_learning_records_outcome_to_memory(mongo):
    from app.agent.nodes.learning import learn_from_execution
    from app.services.memory import recall_memory

    decision = _decision("BUY", ticker="RELIANCE", qty=5)
    execution = {"status": "success", "ticker": "RELIANCE", "updated_cash": 95000.0}
    await learn_from_execution("u1", decision, execution)

    recalled = await recall_memory("u1", "RELIANCE")
    assert len(recalled) == 1
    assert recalled[0]["outcome"]["status"] == "success"


async def test_learning_hold_is_not_counted_as_a_win(mongo):
    """A HOLD (no_action execution) must not be recorded as a completed/won trade."""
    from app.agent.nodes.learning import learn_from_execution
    from app.services.memory import memory_analytics, recall_memory

    await learn_from_execution(
        "u1", _decision("HOLD", ticker="RELIANCE", qty=0), {"status": "no_action"}
    )
    recalled = await recall_memory("u1", "RELIANCE")
    assert len(recalled) == 1
    # A no-action HOLD is neither a win nor a loss — it must not inflate the win rate.
    assert recalled[0]["outcome"]["result"] != "completed"
    assert memory_analytics(recalled)["completed"] == 0


# --- graph integration ---------------------------------------------------

@pytest.fixture
async def workflow_env(fake_llm):
    from langgraph.checkpoint.memory import MemorySaver

    from app.agent.checkpoint import set_checkpointer

    set_client(AsyncMongoMockClient())
    set_checkpointer(MemorySaver())
    yield
    set_checkpointer(None)
    set_client(None)


async def _seed(policy="autonomous_sandbox", holdings=None):
    from app.data.mongo import get_client

    db = get_client()["vestra_test"]
    await db.investor_profiles.insert_one(
        {
            "user_id": "u1",
            "risk_tolerance": "moderate",
            "cash_balance": 100000.0,
            "holdings": holdings if holdings is not None else {"RELIANCE": 20},
            "target_allocation": {},
            "approval_policy": policy,
        }
    )


async def test_workflow_persists_council_and_cio_in_trace(workflow_env, fake_llm):
    """A full run records the council opinion + CIO verdict into the reasoning trace."""
    from app.agent.graph import run_vestra_workflow
    from app.data.repository import list_reasoning_traces
    from app.models.schemas import MarketEvent

    fake_llm('{"action":"SELL","ticker":"RELIANCE","quantity":3,"reasoning":"reduce risk"}')
    await _seed()
    event = MarketEvent(ticker="RELIANCE", price_change_percent=-12.0, breaking_news_summary="shock")
    await run_vestra_workflow("u1", event, event_id="ev-inst")

    traces = await list_reasoning_traces("u1")
    assert len(traces) == 1
    trace = traces[0]
    assert trace["council"] and "consensus_action" in trace["council"]
    assert trace["cio"] and "final_decision" in trace["cio"]


async def test_workflow_executes_then_learns(workflow_env, fake_llm):
    """After an autonomous execution, the outcome is written to memory."""
    from app.agent.graph import run_vestra_workflow
    from app.models.schemas import MarketEvent
    from app.services.memory import recall_memory

    fake_llm('{"action":"SELL","ticker":"RELIANCE","quantity":3,"reasoning":"reduce risk"}')
    await _seed()
    event = MarketEvent(ticker="RELIANCE", price_change_percent=-12.0, breaking_news_summary="shock")
    r = await run_vestra_workflow("u1", event, event_id="ev-learn")
    assert r["status"] == "success"

    mem = await recall_memory("u1", "RELIANCE")
    assert len(mem) == 1
    assert mem[0]["outcome"]["result"] == "completed"
