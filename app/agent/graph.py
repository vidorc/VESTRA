r"""Vestra agent orchestration (LangGraph).

Phase 1 expands the pipeline with the intelligence + human-approval layer while
preserving the public entry point and the legacy result contract.

Flow::

    signal -> research -> risk -> strategy -> reflection -> confidence -> validate
        validate --(approved)--> approval --(approved|auto)--> execute --> END
                 \--(rejected)-> reject  --(human reject)----> reject  --> END

The ``approval`` node may call LangGraph ``interrupt()`` to pause for human
sign-off (per the investor's approval policy). The run is resumed later by
``resume_workflow(thread_id, approved)``.

Backward compatibility
-----------------------
* Runs that do NOT interrupt return the exact legacy shape:
  ``{"status": "rejected", "reason": ...}`` or
  ``{"status": "success"|"failed", "decision": {...}, "execution": {...}}``.
* Runs that DO interrupt return the additive shape
  ``{"status": "pending_approval", "thread_id": ..., "approval_request_id": ...}``.
  Consumers that only branch on ``success``/``rejected``/``failed`` are unaffected.
* ``run_vestra_workflow(user_id, event)`` keeps its signature (``event_id`` added
  as an optional third arg); it generates the ``thread_id`` and checkpointer config.

Audit logging happens inside the terminal nodes (``execute``/``reject``), as before.
"""

import time
import uuid
from typing import Awaitable, Callable, Optional, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.types import Command

from app.models.schemas import (
    CIODecision,
    ConfidenceScore,
    CouncilOpinion,
    Explanation,
    MarketEvent,
    MarketRegime,
    ReflectionResult,
    ResearchContext,
    RiskAssessment,
    SignalAssessment,
    SimulationResult,
    TradeDecision,
    ValidationResult,
)
from app.mcp.server import get_profile
from app.agent.checkpoint import get_checkpointer
from app.agent.nodes.signal import classify_market_event
from app.agent.nodes.research import generate_research_context
from app.agent.nodes.regime import detect_regime
from app.agent.nodes.risk import assess_portfolio_risk
from app.agent.nodes.strategy import generate_trade_strategy
from app.agent.nodes.reflection import reflect_on_decision
from app.agent.nodes.confidence import compute_confidence
from app.agent.nodes.council import convene_council
from app.agent.nodes.cio import cio_review
from app.agent.nodes.simulation import run_simulation
from app.agent.nodes.validator import validate_trade_decision
from app.agent.nodes.approval import run_approval
from app.agent.nodes.execution import execute_trade_decision
from app.agent.nodes.learning import learn_from_execution
from app.services.memory import recall_memory
from app.services.explanation import explain_decision
from app.agent.nodes.audit import audit_agent_action
from app.data.repository import (
    save_agent_event,
    save_reasoning_trace,
    save_research_context,
    save_simulation_result,
)


class AgentState(TypedDict, total=False):
    user_id: str
    event: MarketEvent
    event_id: Optional[str]
    thread_id: str
    holdings: dict
    signal: SignalAssessment
    research_context: ResearchContext
    regime: MarketRegime
    risk: RiskAssessment
    decision: TradeDecision
    analyst_decision: TradeDecision
    reflection: ReflectionResult
    confidence: ConfidenceScore
    council: CouncilOpinion
    cio: CIODecision
    simulation: SimulationResult
    validation: ValidationResult
    explanation: Explanation
    approval: dict
    execution_result: dict
    status: str
    reason: Optional[str]


# --- Observability -------------------------------------------------------

def _instrument(name: str, fn: Callable[["AgentState"], Awaitable[dict]]):
    """Wrap a node so each execution records a timing/status span.

    Times the node, records one ``agent_events`` span (node, duration, ok/error),
    and preserves behaviour exactly: the node's result is returned on success; on
    error the span is recorded and the exception re-raised so the graph's own
    error handling is unchanged. Span persistence is best-effort and never breaks
    the run (a failed write is swallowed).
    """

    async def wrapped(state: "AgentState") -> dict:
        user_id = state.get("user_id", "")
        start = time.perf_counter()
        status = "ok"
        error = None
        try:
            return await fn(state)
        except Exception as exc:  # record then re-raise — behaviour unchanged
            status = "error"
            error = f"{type(exc).__name__}: {exc}"
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            try:
                await save_agent_event(
                    user_id,
                    {
                        "node": name,
                        "duration_ms": duration_ms,
                        "status": status,
                        "error": error,
                        "event_id": state.get("event_id"),
                        "thread_id": state.get("thread_id"),
                    },
                )
            except Exception:
                pass  # observability must never break the workflow

    return wrapped


# --- Nodes ---------------------------------------------------------------

async def signal_node(state: AgentState) -> AgentState:
    signal = classify_market_event(state["event"])
    return {"signal": signal}


async def research_node(state: AgentState) -> AgentState:
    research = await generate_research_context(state["event"], state["signal"])
    # Persist the research context (best-effort; never break the run).
    try:
        await save_research_context(
            state["user_id"], research.model_dump(), event_id=state.get("event_id")
        )
    except Exception:
        pass
    return {"research_context": research}


async def regime_node(state: AgentState) -> AgentState:
    regime = detect_regime(
        state["event"], state["signal"], state.get("research_context")
    )
    return {"regime": regime}


async def risk_node(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    risk = await assess_portfolio_risk(user_id)

    # Real holdings for the validator's oversell check. Tolerate a missing/errored
    # profile gracefully.
    profile = await get_profile(user_id)
    if isinstance(profile, dict) and "error" not in profile:
        holdings = profile.get("holdings", {})
    else:
        holdings = {}

    return {"risk": risk, "holdings": holdings}


async def strategy_node(state: AgentState) -> AgentState:
    decision = await generate_trade_strategy(
        state["event"],
        state["signal"],
        state["risk"],
    )
    return {"decision": decision}


async def reflection_node(state: AgentState) -> AgentState:
    reflection = await reflect_on_decision(
        state["event"],
        state["signal"],
        state["risk"],
        state["decision"],
        state.get("research_context"),
    )
    return {"reflection": reflection}


async def confidence_node(state: AgentState) -> AgentState:
    confidence = compute_confidence(
        state["decision"],
        state["risk"],
        state["signal"],
        state.get("reflection"),
        state.get("research_context"),
    )
    return {"confidence": confidence}


async def council_node(state: AgentState) -> AgentState:
    """Convene the multi-strategy council on the analyst's proposed decision."""
    council = convene_council(
        state["decision"],
        state["signal"],
        state["risk"],
        state.get("regime") or MarketRegime(),
    )
    return {"council": council}


async def cio_node(state: AgentState) -> AgentState:
    """CIO renders the final, authoritative verdict over the analyst decision.

    The analyst's proposal is preserved as ``analyst_decision``; ``decision`` is
    replaced by the CIO's final call, which the rest of the pipeline (simulation,
    validation, approval, execution) acts on.
    """
    analyst = state["decision"]
    try:
        memory = await recall_memory(state["user_id"], analyst.ticker)
    except Exception:
        memory = []

    verdict = cio_review(
        analyst,
        state["risk"],
        state.get("confidence") or compute_confidence(
            analyst, state["risk"], state["signal"], state.get("reflection"), state.get("research_context")
        ),
        state["council"],
        memory,
    )
    return {
        "analyst_decision": analyst,
        "decision": verdict.final_decision,
        "cio": verdict,
    }


async def simulation_node(state: AgentState) -> AgentState:
    simulation = await run_simulation(
        state["decision"],
        regime=state.get("regime"),
        risk=state.get("risk"),
    )
    # Persist the simulation (best-effort; never break the run).
    try:
        await save_simulation_result(
            state["user_id"], simulation.model_dump(), event_id=state.get("event_id")
        )
    except Exception:
        pass
    return {"simulation": simulation}


async def validator_node(state: AgentState) -> AgentState:
    validation = validate_trade_decision(
        state["decision"],
        state["risk"],
        state.get("holdings", {}),
    )

    # Trust layer: narrate the finished decision into a plain-English explanation
    # with evidence + why-not counterfactuals. Deterministic and post-hoc -- reads
    # already-computed state, never alters the decision. Best-effort.
    explanation = None
    try:
        explanation = explain_decision(
            state["decision"],
            confidence=state.get("confidence"),
            signal=state.get("signal"),
            research=state.get("research_context"),
            regime=state.get("regime"),
            risk=state.get("risk"),
            council=state.get("council"),
            cio=state.get("cio"),
            reflection=state.get("reflection"),
        )
    except Exception:
        explanation = None

    # Persist the full reasoning trace (best-effort; never break the run). The
    # validator is the last node always reached before branching and is not
    # re-run on resume, so exactly one trace is captured per decision. Maps each
    # AgentState output to a plain dict for storage.
    def _dump(key):
        value = state.get(key)
        return value.model_dump() if value is not None else None

    try:
        trace = {
            "signal": _dump("signal"),
            "research": _dump("research_context"),
            "regime": _dump("regime"),
            "risk": _dump("risk"),
            "analyst_decision": _dump("analyst_decision"),
            "council": _dump("council"),
            "cio": _dump("cio"),
            "decision": _dump("decision"),
            "reflection": _dump("reflection"),
            "confidence": _dump("confidence"),
            "explanation": explanation.model_dump() if explanation is not None else None,
            "validation": validation.model_dump(),
        }
        await save_reasoning_trace(
            state["user_id"], trace, event_id=state.get("event_id")
        )
    except Exception:
        pass

    out = {"validation": validation}
    if explanation is not None:
        out["explanation"] = explanation
    return out


def route_after_validation(state: AgentState) -> str:
    return "approval" if state["validation"].approved else "reject"


async def approval_node(state: AgentState) -> AgentState:
    reflection = state.get("reflection")
    approval = await run_approval(
        user_id=state["user_id"],
        thread_id=state["thread_id"],
        decision=state["decision"],
        confidence=state.get("confidence"),
        risk=state.get("risk"),
        reflection=reflection.model_dump() if reflection else None,
        event_id=state.get("event_id"),
    )
    return {"approval": approval}


def route_after_approval(state: AgentState) -> str:
    approval = state.get("approval", {})
    return "execute" if approval.get("status") in ("approved", "auto_approved") else "reject"


async def execute_node(state: AgentState) -> AgentState:
    user_id = state["user_id"]
    decision = state["decision"]

    execution = await execute_trade_decision(
        user_id,
        decision.action,
        decision.ticker,
        decision.quantity,
    )

    # Audit truthfully: only "trade_executed" when the layer did not return an
    # error; otherwise record the failure rather than masking it as success.
    failed = isinstance(execution, dict) and "error" in execution
    await audit_agent_action(
        user_id,
        "execution",
        "trade_failed" if failed else "trade_executed",
        {"decision": decision.model_dump(), "execution": execution},
    )

    # Learning agent: write the outcome back to memory so the CIO can weigh this
    # ticker's track record on future decisions. Closes the institutional loop.
    await learn_from_execution(user_id, decision, execution)

    return {
        "execution_result": execution,
        "status": "failed" if failed else "success",
    }


async def reject_node(state: AgentState) -> AgentState:
    decision = state["decision"]
    approval = state.get("approval")
    validation = state.get("validation")

    # A rejection can come from the validator (rule failure) or from a human via
    # the approval node. Record the relevant reason.
    if approval and approval.get("status") == "rejected":
        reason = "Rejected by human reviewer."
        agent_name = "approval"
    elif validation is not None and not validation.approved:
        reason = validation.reason
        agent_name = "validator"
    else:
        reason = "Trade rejected."
        agent_name = "validator"

    await audit_agent_action(
        state["user_id"],
        agent_name,
        "trade_rejected",
        {"decision": decision.model_dump(), "reason": reason},
    )

    return {"status": "rejected", "reason": reason}


# --- Graph assembly ------------------------------------------------------

def _build_graph(checkpointer):
    builder = StateGraph(AgentState)

    builder.add_node("signal", _instrument("signal", signal_node))
    builder.add_node("research", _instrument("research", research_node))
    builder.add_node("regime", _instrument("regime", regime_node))
    builder.add_node("risk", _instrument("risk", risk_node))
    builder.add_node("strategy", _instrument("strategy", strategy_node))
    builder.add_node("reflection", _instrument("reflection", reflection_node))
    builder.add_node("confidence", _instrument("confidence", confidence_node))
    builder.add_node("council", _instrument("council", council_node))
    builder.add_node("cio", _instrument("cio", cio_node))
    builder.add_node("simulation", _instrument("simulation", simulation_node))
    builder.add_node("validate", _instrument("validate", validator_node))
    builder.add_node("approval", _instrument("approval", approval_node))
    builder.add_node("execute", _instrument("execute", execute_node))
    builder.add_node("reject", _instrument("reject", reject_node))

    builder.set_entry_point("signal")
    builder.add_edge("signal", "research")
    builder.add_edge("research", "regime")
    builder.add_edge("regime", "risk")
    builder.add_edge("risk", "strategy")
    builder.add_edge("strategy", "reflection")
    builder.add_edge("reflection", "confidence")
    # Institutional layer: the council debates the analyst's call, then the CIO
    # renders the final decision the rest of the pipeline executes.
    builder.add_edge("confidence", "council")
    builder.add_edge("council", "cio")
    builder.add_edge("cio", "simulation")
    builder.add_edge("simulation", "validate")
    builder.add_conditional_edges(
        "validate",
        route_after_validation,
        {"approval": "approval", "reject": "reject"},
    )
    builder.add_conditional_edges(
        "approval",
        route_after_approval,
        {"execute": "execute", "reject": "reject"},
    )
    builder.add_edge("execute", END)
    builder.add_edge("reject", END)

    return builder.compile(checkpointer=checkpointer)


# Cache the compiled graph, rebuilding only if the checkpointer instance changes
# (e.g. a test injects a fresh MemorySaver).
_graph = None
_graph_checkpointer = None


def get_graph():
    """Return the compiled workflow graph, (re)building it with the active checkpointer."""
    global _graph, _graph_checkpointer
    cp = get_checkpointer()
    if _graph is None or _graph_checkpointer is not cp:
        _graph = _build_graph(cp)
        _graph_checkpointer = cp
    return _graph


# --- Public entry points -------------------------------------------------

def _finalize(result: dict) -> dict:
    """Map a completed graph state to the legacy result contract."""
    if result.get("status") == "rejected":
        return {"status": "rejected", "reason": result.get("reason")}
    decision = result.get("decision")
    return {
        "status": result.get("status", "success"),
        "decision": decision.model_dump() if decision else None,
        "execution": result.get("execution_result"),
    }


def _interrupt_payload(result: dict):
    """Return the interrupt payload if the run paused for approval, else None."""
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    return getattr(first, "value", first)


async def run_vestra_workflow(
    user_id: str, event: MarketEvent, event_id: Optional[str] = None
) -> dict:
    """Run the Vestra decision workflow for a single market event.

    Returns the legacy contract on completion, or an additive
    ``{"status": "pending_approval", ...}`` shape if the run pauses for human
    approval (resume later with :func:`resume_workflow`).
    """
    thread_id = f"{user_id}:{event_id or uuid.uuid4().hex}"
    config = {"configurable": {"thread_id": thread_id}}

    result = await get_graph().ainvoke(
        {
            "user_id": user_id,
            "event": event,
            "event_id": event_id,
            "thread_id": thread_id,
        },
        config=config,
    )

    payload = _interrupt_payload(result)
    if payload is not None:
        return {
            "status": "pending_approval",
            "thread_id": thread_id,
            "approval_request_id": (payload or {}).get("approval_id")
            if isinstance(payload, dict)
            else None,
        }

    return _finalize(result)


async def resume_workflow(thread_id: str, approved: bool) -> dict:
    """Resume a paused workflow with a human approve/reject decision.

    Continues from the ``approval`` interrupt into execute/reject and returns the
    legacy result contract.
    """
    config = {"configurable": {"thread_id": thread_id}}
    result = await get_graph().ainvoke(Command(resume=bool(approved)), config=config)

    # Defensive: if somehow still interrupted, report still-pending.
    payload = _interrupt_payload(result)
    if payload is not None:
        return {"status": "pending_approval", "thread_id": thread_id}

    return _finalize(result)
