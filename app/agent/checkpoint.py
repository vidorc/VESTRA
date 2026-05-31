"""Checkpointer factory for the LangGraph workflow.

LangGraph's ``interrupt()`` (used by the approval node) requires a checkpointer so
state can be persisted at the interrupt point and restored on resume. We use the
built-in in-process ``MemorySaver`` by default.

Why in-process is sufficient today: the webhook that starts a workflow and the
approvals endpoint that resumes it run in the *same* FastAPI process, so the
checkpoint is reachable for the resume. Crucially, the durable source of truth
for a pending approval is the ``approval_requests`` collection in MongoDB (written
by the approval node) -- the checkpoint only holds the transient graph state
needed to continue execution. If a horizontally-scaled / restart-durable
checkpointer is needed later (e.g. a Mongo or Postgres saver), inject it via
``set_checkpointer`` with no other code changes.

The checkpointer is a process-wide singleton so all runs + resumes share one
store; ``set_checkpointer`` is the test/override seam.
"""

from typing import Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

_checkpointer: Optional[BaseCheckpointSaver] = None


def get_checkpointer() -> BaseCheckpointSaver:
    """Return the process-wide checkpointer, creating a MemorySaver on first use."""
    global _checkpointer
    if _checkpointer is None:
        _checkpointer = MemorySaver()
    return _checkpointer


def set_checkpointer(checkpointer: Optional[BaseCheckpointSaver]) -> None:
    """Override the checkpointer (e.g. a persistent saver) or reset with ``None``.

    Resetting also invalidates any compiled graph that captured the old
    checkpointer; callers that cache a compiled graph should rebuild it.
    """
    global _checkpointer
    _checkpointer = checkpointer


__all__ = ["get_checkpointer", "set_checkpointer"]
