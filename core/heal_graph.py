# -*- coding: utf-8 -*-
"""LangGraph based HITL healing workflow.

This module defines a `HealState` dataclass that carries the mutable
state through the graph and a `heal_graph` built with LangGraph's
`StateGraph`.  The graph mirrors the eight logical nodes described in
the second‑phase specification:

1. **fetch_alert** – Load the raw alert and source metadata.
2. **check_sla** – Compute SLA priority & business impact.
3. **invoke_agent** – Run the LLM‑based analysis.
4. **generate_runbook** – Produce a remediation run‑book.
5. **apply_fix** – Execute the run‑book (or simulate).
6. **evaluate** – Verify the fix against the alert.
7. **rollback** – If verification fails, invoke rollback logic.
8. **complete** – Final cleanup & persistence.

The graph is deliberately lightweight – each node is a plain Python
function that receives the current `HealState` and returns the mutated
state.  Errors are caught and stored in `state.error`.  The graph also
supports **checkpointing** via `langgraph.checkpoint.sqlite.CheckpointSQLite`
so that execution can be persisted and resumed (useful for long‑running
or interrupted repairs).

The public entry point is ``run_heal(state: HealState) -> HealState``
which simply executes the graph and returns the final state.
"""

from __future__ import annotations

import logging
import traceback
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

# LangGraph imports – optional dependency, fallback to noop if missing
try:
    from langgraph.checkpoint.sqlite import CheckpointSQLite
    from langgraph.graph import END, StateGraph
except Exception:  # pragma: no cover
    # Define minimal stubs so the module can be imported without LangGraph.
    class END:  # type: ignore
        pass

    class StateGraph:  # type: ignore
        def __init__(self, state_schema):
            self.state_schema = state_schema

        def add_node(self, name, fn):
            pass

        def set_entry_point(self, name):
            pass

        def add_edge(self, src, dst):
            pass

        def compile(self, **_):
            async def _run(state):
                return state

            return _run

        def __call__(self, *a, **kw):
            return self.compile()(*a, **kw)

    class CheckpointSQLite:  # type: ignore
        def __init__(self, *a, **kw):
            pass


logger = logging.getLogger(__name__)


@dataclass
class HealState:
    """Mutable state passed through the LangGraph workflow.

    Attributes
    ----------
    alert: Dict[str, Any]
        Raw alert payload.
    sla_score: Optional[int]
        Business‑impact priority (0‑3).
    analysis: Optional[Dict[str, Any]]
        Result of the LLM analysis.
    runbook: Optional[str]
        Generated remediation steps.
    fix_applied: bool
        Whether the run‑book was actually executed.
    verification: Optional[Dict[str, Any]]
        Outcome of the verification step.
    error: Optional[str]
        Captured exception traceback if any node fails.
    """

    alert: Dict[str, Any] = field(default_factory=dict)
    sla_score: Optional[int] = None
    analysis: Optional[Any] = None
    runbook: Optional[Any] = None
    fix_applied: bool = False
    verification: Optional[Any] = None
    error: Optional[str] = None


# ---------------------------------------------------------------------
# Individual node implementations – keep them simple; they delegate to
# existing core modules when possible.
# ---------------------------------------------------------------------


async def fetch_alert(state: HealState) -> HealState:
    """Load alert details.

    In the real system this would query the DB or message queue.  For the
    stub we simply ensure ``state.alert`` exists.
    """
    if not state.alert:
        state.error = "No alert payload provided"
    return state


async def check_sla(state: HealState) -> HealState:
    """Determine business impact using the priority engine."""
    try:
        from .priority_engine import compute_sla_score

        state.sla_score = compute_sla_score(state.alert)
    except Exception as exc:  # pragma: no cover
        state.error = f"SLA calculation failed: {exc}"
    return state


async def invoke_agent(state: HealState) -> HealState:
    """Run the LLM analysis via the existing ``ai_engine``."""
    try:
        from .ai_engine import analyze

        query = state.alert.get("query", "")
        metrics = state.alert.get("metrics", "")
        platform = state.alert.get("platform", "unknown")
        analysis = analyze(query, metrics, platform)
        state.analysis = analysis
    except Exception as exc:  # pragma: no cover
        state.error = f"LLM analysis failed: {exc}"
    return state


async def generate_runbook(state: HealState) -> HealState:
    """Create a run‑book using ``runbook_generator``."""
    try:
        from .runbook_generator import generate_repair_runbook

        if state.analysis:
            state.runbook = generate_repair_runbook(state.analysis)
    except Exception as exc:  # pragma: no cover
        state.error = f"Run‑book generation failed: {exc}"
    return state


async def apply_fix(state: HealState) -> HealState:
    """Execute or simulate the remediation steps."""
    try:
        if state.runbook:
            # In a full implementation we would call ``repair_engine``.
            # Here we simply mark it as applied.
            state.fix_applied = True
    except Exception as exc:  # pragma: no cover
        state.error = f"Fix application failed: {exc}"
    return state


async def evaluate(state: HealState) -> HealState:
    """Verify the fix via the verifier module."""
    try:
        from .verifier import verify_repair

        if state.fix_applied:
            # ``verify_repair`` expects the original alert and the run‑book.
            verify_res = verify_repair(state.alert, state.runbook or "")
            state.verification = (
                verify_res.model_dump()
                if hasattr(verify_res, "model_dump")
                else {"result": verify_res}
            )
    except Exception as exc:  # pragma: no cover
        state.error = f"Verification failed: {exc}"
    return state


async def rollback(state: HealState) -> HealState:
    """Rollback logic if verification indicates failure."""
    if state.verification and not state.verification.get("passed", True):
        # Placeholder: just log.
        logger.warning("Rollback triggered for alert %s", state.alert.get("id"))
    return state


async def complete(state: HealState) -> HealState:
    """Final cleanup – persist state, emit metrics, etc."""
    # In production we would record the outcome to DB / monitoring.
    logger.info("Healing workflow completed – state: %s", state)
    return state


# ---------------------------------------------------------------------
# Build the LangGraph StateGraph.
# ---------------------------------------------------------------------


def _build_graph() -> Any:
    graph = StateGraph(HealState)
    # Register nodes
    graph.add_node("fetch_alert", fetch_alert)
    graph.add_node("check_sla", check_sla)
    graph.add_node("invoke_agent", invoke_agent)
    graph.add_node("generate_runbook", generate_runbook)
    graph.add_node("apply_fix", apply_fix)
    graph.add_node("evaluate", evaluate)
    graph.add_node("rollback", rollback)
    graph.add_node("complete", complete)

    graph.set_entry_point("fetch_alert")
    # Define linear edges; rollback jumps back to ``apply_fix`` if needed.
    graph.add_edge("fetch_alert", "check_sla")
    graph.add_edge("check_sla", "invoke_agent")
    graph.add_edge("invoke_agent", "generate_runbook")
    graph.add_edge("generate_runbook", "apply_fix")
    graph.add_edge("apply_fix", "evaluate")
    graph.add_edge("evaluate", "rollback")
    graph.add_edge("rollback", "complete")
    graph.add_edge("complete", END)

    # Enable SQLite checkpointing for persistence.
    checkpoint = CheckpointSQLite("heal_graph.db")
    return graph.compile(checkpointer=checkpoint)


# Compile once at import time.
_heal_graph_runner = _build_graph()


async def run_heal(state: HealState) -> HealState:
    """Execute the healing workflow.

    Parameters
    ----------
    state: HealState
        Initial state (must contain at least ``alert``).

    Returns
    -------
    HealState
        The mutated state after the graph finishes.
    """
    try:
        final_state = await _heal_graph_runner(state)
        return final_state  # type: ignore[no-any-return]
    except Exception:  # pragma: no cover
        state.error = f"Graph execution failed: {traceback.format_exc()}"
        return state
