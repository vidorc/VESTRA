"""Agent Observability -- roll up node-execution spans into a monitoring report.

Each graph node, when it runs, records a span (node name, duration, ok/error)
via the instrumented wrapper in ``app.agent.graph``. This service aggregates a
window of those spans into an :class:`~app.models.schemas.ObservabilityReport`:
per-node run counts, error rates, and latency (avg / max), plus overall totals
and the slowest node.

Pure and deterministic -- the same spans always yield the same report -- so the
agent-monitoring dashboard is reproducible and the service is trivially testable.
"""

from typing import Any, Dict, List

from app.models.schemas import NodeStat, ObservabilityReport


def build_observability_report(events: List[Dict[str, Any]]) -> ObservabilityReport:
    """Aggregate node-execution spans into an :class:`ObservabilityReport`.

    ``events`` is expected newest-first (as the DAL returns it); ``last_status``
    per node therefore reflects the most recent run.
    """
    events = events or []
    if not events:
        return ObservabilityReport()

    # node -> accumulator
    acc: Dict[str, Dict[str, Any]] = {}
    total_runs = 0
    total_errors = 0
    total_ms = 0.0

    for ev in events:
        node = ev.get("node") or "unknown"
        duration = float(ev.get("duration_ms") or 0.0)
        is_error = ev.get("status") == "error"

        bucket = acc.setdefault(
            node,
            {"runs": 0, "errors": 0, "sum_ms": 0.0, "max_ms": 0.0, "last_status": None},
        )
        bucket["runs"] += 1
        bucket["sum_ms"] += duration
        bucket["max_ms"] = max(bucket["max_ms"], duration)
        if is_error:
            bucket["errors"] += 1
        # Events are newest-first, so the FIRST one seen for a node is its latest run.
        if bucket["last_status"] is None:
            bucket["last_status"] = "error" if is_error else "ok"

        total_runs += 1
        total_errors += 1 if is_error else 0
        total_ms += duration

    nodes: List[NodeStat] = []
    for node, b in acc.items():
        runs = b["runs"]
        nodes.append(
            NodeStat(
                node=node,
                runs=runs,
                errors=b["errors"],
                error_rate=round(b["errors"] / runs, 4) if runs else 0.0,
                avg_ms=round(b["sum_ms"] / runs, 2) if runs else 0.0,
                max_ms=round(b["max_ms"], 2),
                last_status=b["last_status"] or "ok",
            )
        )

    # Busiest nodes first; ties broken by slower average (more interesting).
    nodes.sort(key=lambda n: (-n.runs, -n.avg_ms))

    slowest_node = max(nodes, key=lambda n: n.avg_ms).node if nodes else None

    return ObservabilityReport(
        total_runs=total_runs,
        total_errors=total_errors,
        error_rate=round(total_errors / total_runs, 4) if total_runs else 0.0,
        avg_ms=round(total_ms / total_runs, 2) if total_runs else 0.0,
        slowest_node=slowest_node,
        nodes=nodes,
    )


__all__ = ["build_observability_report"]
