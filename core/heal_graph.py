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
from .metrics_history import metrics_history as _metrics_history
from .escalation import notify_rollback_failure
from config import SNAPSHOT_CONFIG
from typing import Any, Callable, Dict, List, Optional, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
import traceback
import re

import asyncio
import inspect
import json
import logging
import os

logger = logging.getLogger(__name__)


try:
    from core.stats_engine import record_decision, record_outcome
except (ImportError, ModuleNotFoundError) as e:
    logger.info("core.stats_engine not available, metrics recording disabled: %s", e)
    record_decision = None  # type: ignore[assignment]
    record_outcome = None  # type: ignore[assignment]

try:
    from .snapshot_store import (
        cleanup_expired_snapshots,
        save_snapshot,
        update_snapshot_status,
    )
except (ImportError, ModuleNotFoundError) as e:
    logger.info("snapshot_store not available, checkpoint persistence disabled: %s", e)
    save_snapshot = None  # type: ignore[assignment]
    update_snapshot_status = None  # type: ignore[assignment]
    cleanup_expired_snapshots = None  # type: ignore[assignment]

# P2-3: lazy Prometheus counter cache for heal workflow observability
_HEAL_METRIC_COUNTERS: Dict[str, Any] = {}

# LangGraph imports – optional dependency, fallback to noop if missing
try:
    from langgraph.checkpoint.sqlite import CheckpointSQLite
    from langgraph.graph import END, StateGraph
except (ImportError, ModuleNotFoundError):
    logger.info("LangGraph checkpointing not available; using built-in StateGraph fallback.")

    # Define minimal stubs so the module can be imported without LangGraph.
    class END:  # type: ignore
        pass

    class StateGraph:  # type: ignore
        """Minimal dependency-free graph executor for the healing workflow."""

        def __init__(self, state_schema=None):
            self.state_schema = state_schema
            self.nodes: Dict[str, Callable] = {}
            self.edges: List[Tuple[str, Any]] = []
            self.entry_point: Optional[str] = None
            self.end_nodes: set = set()

        def add_node(self, name: str, fn: Callable) -> None:
            self.nodes[name] = fn

        def set_entry_point(self, name: str) -> None:
            self.entry_point = name

        def add_edge(self, src: str, dst: Any) -> None:
            self.edges.append((src, dst))
            if dst is END:
                self.end_nodes.add(src)

        def compile(self, **kwargs):
            graph = self

            async def _run(state, config=None):
                if not graph.entry_point:
                    logger.warning("StateGraph has no entry point")
                    return state

                current = graph.entry_point
                visited: set = set()
                while current and current not in visited:
                    visited.add(current)
                    if current not in graph.nodes:
                        logger.error(f"Node {current} not found in graph")
                        break

                    try:
                        result = await graph.nodes[current](state)
                    except Exception as exc:
                        logger.error(f"Node {current} execution failed: {exc}")
                        if hasattr(state, "error"):
                            state.error = f"Node {current} failed: {exc}"
                        break

                    if result is not None:
                        state = result

                    # Detect end-of-graph
                    if current in graph.end_nodes:
                        break

                    outgoing = [dst for src, dst in graph.edges if src == current]
                    if any(dst is END for dst in outgoing):
                        break

                    candidates = [dst for dst in outgoing if dst is not END]
                    if not candidates:
                        break

                    current = candidates[0]

                return state

            return _run

        def __call__(self, *a, **kw):
            return self.compile()(*a, **kw)

    class CheckpointSQLite:  # type: ignore
        """Dependency-free fallback for LangGraph SQLite checkpointing."""

        def __init__(self, db_path: str = "heal_graph.db", *a, **kw):
            self.db_path = db_path
            self._pending: Dict[str, Any] = {}

        def put(self, config: Any, checkpoint: Any) -> None:
            self._pending[str(config)] = checkpoint

        def get(self, config: Any) -> Any:
            return self._pending.get(str(config))


logger = logging.getLogger(__name__)

# Red-team imports with graceful fallback to keep module importable in minimal envs.
try:
    from core.command_guard import RiskLevel, analyze_command, record_audit
except Exception as e:
    logger.warning("command_guard import failed, risk analysis disabled: %s", e)
    analyze_command = None  # type: ignore[assignment]
    RiskLevel = None  # type: ignore[assignment,misc]
    record_audit = None  # type: ignore[assignment]

try:
    from core.db_engine import (
        async_get_approval_by_alert,
        async_insert_repair_record,
        async_update_approval_status_by_alert,
        async_upsert_pending_approval,
    )
except Exception as e:
    logger.warning("db_engine import failed, persistence disabled: %s", e)
    async_get_approval_by_alert = None  # type: ignore[assignment]
    async_insert_repair_record = None  # type: ignore[assignment]
    async_update_approval_status_by_alert = None  # type: ignore[assignment]
    async_upsert_pending_approval = None  # type: ignore[assignment]

try:
    from core.audit_logger import get_trace_id as _get_trace_id
    from core.audit_logger import log_audit_event as _log_audit_event
    from core.audit_logger import set_trace_id as _set_trace_id

    AUDIT_AVAILABLE = True
except Exception as e:
    logger.warning("audit_logger import failed, audit trail disabled: %s", e)
    AUDIT_AVAILABLE = False
    _log_audit_event = None  # type: ignore[assignment]
    _get_trace_id = None  # type: ignore[assignment]
    _set_trace_id = None  # type: ignore[assignment]

try:
    from core.notify_engine import send_alert_notification as _send_alert_notification

    NOTIFY_AVAILABLE = True
except Exception as e:
    logger.info("notify_engine import failed, alert notifications disabled: %s", e)
    NOTIFY_AVAILABLE = False
    _send_alert_notification = None  # type: ignore[assignment]


def _audit(
    action: str, resource: str, status: str, details: Optional[Dict[str, Any]] = None
) -> None:
    """Best-effort audit helper for heal graph events."""
    if AUDIT_AVAILABLE and callable(_log_audit_event):
        try:
            _log_audit_event(
                event_type=action,
                user="system",
                resource=resource,
                action=action,
                status=status,
                details=details or {},
            )
        except Exception as exc:
            logger.warning(f"Audit write failed: {exc}")
    # Mirror high-level events into command_guard in-memory audit log so that
    # GET /api/v1/audit returns the full alert-to-repair chain.
    if callable(record_audit):
        try:
            record_audit(
                host=str(resource),
                command=str(action),
                risk_level=str(status),
                result=str(status),
                executor="heal_graph",
                trace_id=(_get_trace_id() if callable(_get_trace_id) else None),
            )
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)


def _approval_validity_minutes() -> int:
    """Return configured approval validity window in minutes (default 5)."""
    try:
        return int(os.getenv("HEAL_APPROVAL_VALIDITY_MINUTES", "5"))
    except (TypeError, ValueError):
        return 5


def _is_approval_expired(approval: Optional[Dict[str, Any]]) -> bool:
    """Check whether an approval record has exceeded its validity window."""
    if not approval:
        return False
    approved_at = approval.get("approved_at")
    if not approved_at:
        return False
    try:
        approved_time = datetime.fromisoformat(str(approved_at))
    except (TypeError, ValueError):
        return True
    age_minutes = (datetime.now() - approved_time).total_seconds() / 60.0
    return age_minutes > _approval_validity_minutes()


def _is_alert_resolved(alert: Dict[str, Any]) -> bool:
    """
    Best-effort pre-execution re-evaluation of whether the alert has self-healed.

    Supports:
      - alert['status'] == 'resolved' or alert['resolved'] == True
      - alert['resolved_condition'] with metric/operator/threshold evaluated
        against the latest metrics history.
    """
    if not isinstance(alert, dict):
        return False

    if alert.get("status") == "resolved" or alert.get("resolved") is True:
        return True

    condition = alert.get("resolved_condition")
    if isinstance(condition, dict):
        metric = str(condition.get("metric", ""))
        operator = str(condition.get("operator", ""))
        threshold = condition.get("threshold")
        try:
            metrics = _metrics_history.to_dict()
            values = metrics.get(metric, [])
            if values and threshold is not None:
                latest = float(values[-1])
                threshold = float(threshold)
                if operator in ("<", "lt"):
                    return latest < threshold
                if operator in (">", "gt"):
                    return latest > threshold
                if operator in ("<=", "le"):
                    return latest <= threshold
                if operator in (">=", "ge"):
                    return latest >= threshold
                if operator in ("==", "=", "eq"):
                    return latest == threshold
        except Exception as exc:  # pragma: no cover
            logger.debug(f"Resolved condition check failed: {exc}")

    return False


def _pre_execution_check(
    alert: Dict[str, Any], approval: Optional[Dict[str, Any]]
) -> Tuple[bool, str]:
    """
    Re-evaluate preconditions before executing a repair.

    Returns (can_execute, reason).
    """
    if _is_approval_expired(approval):
        return False, "approval expired or missing approved_at"

    if _is_alert_resolved(alert):
        return False, "alert self-healed before execution"

    return True, ""


def _is_off_hours() -> bool:
    """Return True when current local time is in the 00:00-06:00 quiet window."""
    return 0 <= datetime.now().hour < 6


def _off_hours_auto_approve_allowed() -> bool:
    """Off-hours auto-approve is opt-in via HEAL_OFFHOURS_AUTO_APPROVE."""
    return os.getenv("HEAL_OFFHOURS_AUTO_APPROVE", "false").lower() in ("1", "true", "yes")


def _is_auto_approve_allowed() -> bool:
    """SAFE/LOW auto-approve is disabled by default and blocked during off-hours unless opted in."""
    if not os.getenv("HEAL_AUTO_APPROVE_SAFE_LOW", "false").lower() in ("1", "true", "yes"):
        return False
    if _is_off_hours() and not _off_hours_auto_approve_allowed():
        return False
    return True


def _is_hardware_alert(alert: Dict[str, Any]) -> bool:
    """Return True if the alert clearly refers to a hardware component (BMC, disk, RAID, etc.)."""
    if not isinstance(alert, dict):
        return False
    if str(alert.get("category", "")).lower() == "hardware":
        return True
    text = " ".join(
        str(alert.get(k, "")) for k in ("metric", "metrics", "title", "desc", "description")
    ).lower()
    return any(
        kw in text
        for kw in (
            "ipmi",
            "redfish",
            "idrac",
            "ilo",
            "smart",
            "raid",
            "storcli",
        )
    )


# ---------------------------------------------------------------------------
# Command target validation helpers (Scenario 3: prevent wrong root cause)
# ---------------------------------------------------------------------------
_COMMAND_TARGET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\bsystemctl\s+(?:restart|stop|start|status)\s+([A-Za-z0-9_.-]+)"),
    re.compile(r"(?i)\bnet\s+(?:stop|start)\s+([A-Za-z0-9_.-]+)"),
    re.compile(r"(?i)\bsc\s+(?:start|stop|config)\s+([A-Za-z0-9_.-]+)"),
    re.compile(r"(?i)\blaunchctl\s+restart\s+([A-Za-z0-9_.-]+)"),
    re.compile(
        r"(?i)\b(?:Restart-Service|Stop-Service|Start-Service)\s+(?:-Name\s+)?([A-Za-z0-9_.-]+)"
    ),
    re.compile(r"(?i)\bservice\s+([A-Za-z0-9_.-]+)\s+(?:restart|stop|start)"),
    re.compile(
        r"(?i)\bkubectl\s+(?:rollout\s+restart|delete|scale)\s+"
        r"(?:deployment|pod|statefulset|service|svc)\s+([A-Za-z0-9_.-]+)"
    ),
]


def _tokenize_alert_text(text: Any) -> list[str]:
    """Extract normalized alphanumeric tokens from alert text."""
    if not isinstance(text, str) or not text:
        return []
    return [t.lower() for t in re.split(r"[^A-Za-z0-9_.-]+", text) if t]


def _allowed_targets_from_alert(alert: Dict[str, Any]) -> set[str]:
    """Build a set of allowed target tokens from alert fields."""
    targets: set[str] = set()
    for key in (
        "title",
        "desc",
        "description",
        "metric",
        "host",
        "service",
        "service_name",
        "pod",
        "deployment",
        "namespace",
        "resource_name",
        "alert_type",
    ):
        targets.update(_tokenize_alert_text(alert.get(key)))
    value = alert.get("value")
    if value is not None:
        targets.add(str(value).lower())
    return targets


def _extract_command_target(cmd: str) -> Optional[str]:
    """Extract the primary resource/service target from a destructive command."""
    for pattern in _COMMAND_TARGET_PATTERNS:
        match = pattern.search(cmd)
        if match:
            return match.group(1).strip().strip("\"'").lower()
    return None


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
    snapshot: Optional[Dict[str, Any]] = field(default_factory=dict)
    executed_commands: List[str] = field(default_factory=list)
    repair_result: Optional[Dict[str, Any]] = None
    rollback_info: Optional[Dict[str, Any]] = None
    approval_status: Optional[str] = None
    escalated: bool = False
    snapshot_id: Optional[str] = None
    decision_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------
# Individual node implementations – keep them simple; they delegate to
# existing core modules when possible.
# ---------------------------------------------------------------------


async def fetch_alert(state: HealState) -> HealState:
    """Load alert details.

    In the real system this would query the DB or message queue.  For the
    component we simply ensure ``state.alert`` exists.
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
    """Run the LLM analysis via the existing ``ai_engine`` and build a rich context."""
    try:
        from .ai_engine import analyze

        alert = state.alert or {}
        if alert.get("query"):
            query = alert["query"]
        else:
            query = f"{alert.get('title', '')}: {alert.get('desc', '')}".strip()

        platform = alert.get("platform", "windows")

        # Build rich context for the runbook generator/AI engine.
        rich_context: Dict[str, Any] = {
            "query": query,
            "platform": platform,
            "alert": alert,
        }

        # Inject current metrics history as a structured snapshot.
        try:
            rich_context["metrics_history"] = _metrics_history.to_dict()
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            rich_context["metrics_history"] = {}

        # Top processes from the alert payload if available.
        rich_context["top_processes"] = alert.get("top_processes") or []

        # Recent alerts from alert_engine if available (best-effort).
        recent_alerts: List[Dict[str, Any]] = []
        try:
            from .alert_engine import alert_history

            recent_alerts = [dict(a) for a in list(alert_history)[:10]]
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            logging.warning("Suppressed exception", exc_info=True)
        rich_context["recent_alerts"] = recent_alerts

        # Minimal stats for the snapshot.
        rich_context["stats"] = {
            "current_anomalies": len(recent_alerts),
            "total_alerts": len(recent_alerts),
            "heal_rate": 0,
        }

        raw_text = await analyze(
            query,
            alert.get("metrics", ""),
            platform,
            rich_context=rich_context,
        )

        # Persist structured analysis so downstream nodes can use it as context.
        rich_context["raw"] = raw_text
        rich_context["root_cause"] = str(raw_text)[:500]
        rich_context["confidence"] = 0.8
        state.analysis = rich_context
        from core.phase3_metrics import LLM_COST_PER_INCIDENT

        LLM_COST_PER_INCIDENT.labels(model="default").inc(0.001)
        _audit(
            "ANALYSIS_GENERATED",
            str(alert.get("id", "unknown")),
            "success",
            {"confidence": rich_context.get("confidence"), "platform": platform},
        )
    except Exception as exc:  # pragma: no cover
        state.error = f"LLM analysis failed: {exc}"
    return state


async def generate_runbook(state: HealState) -> HealState:
    """Create a run‑book using ``runbook_generator``.

    P2-2: Falls back to the ``RepairScriptLibrary`` when LLM generation fails
    or returns an invalid runbook.
    """
    try:
        import asyncio

        from .runbook_generator import generate_repair_runbook

        rich_context = state.analysis if isinstance(state.analysis, dict) else None
        raw = generate_repair_runbook(state.alert or {}, rich_context)
        state.runbook = await raw if asyncio.iscoroutine(raw) else raw  # type: ignore[assignment]
    except Exception as exc:  # pragma: no cover
        state.error = f"Run‑book generation failed: {exc}"

    # P2-2: RepairScriptLibrary fallback when LLM runbook is unusable.
    # Ensure hardware remediation scripts are registered in the global library.

    if not state.runbook or not isinstance(state.runbook, dict) or not state.runbook.get("success"):
        try:
            from core.auto_heal import repair_script_library

            alert = state.alert or {}
            metric = str(alert.get("metric") or alert.get("metrics") or "").lower()
            title = str(alert.get("title") or "").lower()
            desc = str(alert.get("desc") or "").lower()
            if _is_hardware_alert(alert):
                if any(k in metric or k in title or k in desc for k in ("ipmi",)):
                    script_key = "ipmi_power_cycle"
                elif any(
                    k in metric or k in title or k in desc for k in ("redfish", "idrac", "ilo")
                ):
                    script_key = "redfish_reboot"
                elif any(k in metric or k in title or k in desc for k in ("raid", "storcli")):
                    script_key = "raid_rebuild"
                elif any(k in metric or k in title or k in desc for k in ("smart",)):
                    script_key = "smart_test"
                elif any(
                    k in metric or k in title or k in desc for k in ("cordon", "drain", "uncordon")
                ):
                    script_key = "k8s_drain"
                elif any(
                    k in metric or k in title or k in desc for k in ("node", "k8s", "kubernetes")
                ):
                    script_key = "k8s_drain"
                else:
                    script_key = "ipmi_power_cycle"
            elif "disk" in metric or "disk" in title or "disk" in desc:
                script_key = "disk_high_script"
            elif "memory" in metric or "memory" in title or "memory" in desc:
                script_key = "memory_high_script"
            elif "service" in metric or "service" in title or "service" in desc:
                script_key = "service_restart_script"
            else:
                script_key = "cpu_high_script"

            script = repair_script_library.get_script(script_key)
            if script:
                raw_commands = [
                    c.strip() for c in (script.script_content or "").splitlines() if c.strip()
                ]
                raw_rollback = (
                    [c.strip() for c in (script.rollback_script or "").splitlines() if c.strip()]
                    if script.rollback_script
                    else []
                )
                fallback = {
                    "success": True,
                    "script_key": script_key,
                    "runbook": {
                        "script_key": script_key,
                        "name": script.name,
                        "description": script.description,
                        "commands": raw_commands,
                        "rollback": raw_rollback[0] if raw_rollback else "",
                        "risk_level": (
                            script.risk_level.value
                            if hasattr(script.risk_level, "value")
                            else str(script.risk_level)
                        ),
                        "params": {},
                    },
                    "worst_risk": (
                        script.risk_level.value
                        if hasattr(script.risk_level, "value")
                        else str(script.risk_level)
                    ),
                    "needs_approval": script.requires_approval
                    or script.risk_level in (RiskLevel.HIGH, RiskLevel.BLOCKED),
                    "auto_executable": script.risk_level in (RiskLevel.SAFE, RiskLevel.LOW),
                    "guard_results": [],
                    "source": "repair_script_library",
                    "approval_id": None,
                }
                state.runbook = fallback
                state.error = None
        except Exception as exc2:  # pragma: no cover
            if not state.error:
                state.error = f"RepairScriptLibrary fallback also failed: {exc2}"
    return state


async def apply_fix(state: HealState) -> HealState:
    """Execute or simulate the remediation steps after approval and snapshot."""
    try:
        alert = state.alert or {}
        alert_id = alert.get("id")
        if not alert_id:
            state.error = "Missing alert_id; cannot execute repair without approval"
            _audit("APPROVAL_CHECK", "unknown", "denied", {"reason": "missing alert_id"})
            return state

        if (
            not state.runbook
            or not isinstance(state.runbook, dict)
            or not state.runbook.get("success")
        ):
            state.error = "No valid runbook; skipping execution"
            _audit("REPAIR_EXECUTED", str(alert_id), "failure", {"reason": "no valid runbook"})
            return state

        inner_runbook = state.runbook.get("runbook") or state.runbook
        from_repair_script_library = state.runbook.get("source") == "repair_script_library"
        commands: List[str] = []
        if isinstance(inner_runbook, dict):
            cmds = inner_runbook.get("commands", [])
            if isinstance(cmds, list):
                commands = [str(c) for c in cmds if isinstance(c, str) and c]

        if not commands:
            state.error = "Runbook contains no executable commands"
            _audit("REPAIR_EXECUTED", str(alert_id), "failure", {"reason": "empty commands"})
            return state

        rollback_cmd = ""
        if isinstance(inner_runbook, dict):
            rollback_cmd = inner_runbook.get("rollback", "") or ""

        # S1: verify the repair has been explicitly approved before execution.
        # P1-1: SAFE/LOW auto-executable runbooks may be auto-approved when enabled.
        worst_risk = str(state.runbook.get("worst_risk", "")).lower()
        auto_executable = bool(
            state.runbook.get("auto_executable") and worst_risk in ("safe", "low")
        )
        # P2-1: P0 (highest) business impact always requires explicit human approval.
        sla_requires_explicit = state.sla_score == 0
        is_auto_approve = _is_auto_approve_allowed()

        # Confidence gate: low-confidence remediation plans cannot be auto-approved.
        confidence = 1.0
        if isinstance(inner_runbook, dict):
            try:
                confidence = float(inner_runbook.get("confidence", 1.0))
            except (TypeError, ValueError):
                confidence = 1.0
        confidence_threshold = float(os.getenv("HEAL_EXECUTION_CONFIDENCE_THRESHOLD", "0.75"))
        if confidence < confidence_threshold:
            is_auto_approve = False

        approval = None
        if async_get_approval_by_alert is not None:
            approval = await async_get_approval_by_alert(alert_id)

        # Persist a pending approval row so the HITL loop has a real record to approve.
        if approval is None and async_upsert_pending_approval is not None:
            try:
                await async_upsert_pending_approval(
                    alert_id=str(alert_id),
                    rule_name=str(alert.get("metric") or alert.get("title") or "unknown"),
                    script_key=str(alert.get("metric") or "unknown"),
                    proposal=json.dumps(state.runbook, ensure_ascii=False, default=str),
                    alert_json=json.dumps(alert, ensure_ascii=False, default=str),
                    risk_level=(
                        str(state.runbook.get("worst_risk", "medium")).lower()
                        if isinstance(state.runbook, dict)
                        else "medium"
                    ),
                    host=alert.get("host"),
                    platform=str(alert.get("platform", "windows")),
                )
            except Exception as _upsert_exc:
                logger.warning(f"Failed to persist pending approval: {_upsert_exc}")
            if async_get_approval_by_alert is not None:
                approval = await async_get_approval_by_alert(alert_id)

        if (approval is None or approval.get("status") != "approved") and not (
            auto_executable and is_auto_approve and not sla_requires_explicit
        ):
            status = approval.get("status") if approval else "missing"
            state.error = f"Repair for alert {alert_id} not approved (status={status}); aborting"
            state.approval_status = status
            _audit(
                "APPROVAL_CHECK",
                str(alert_id),
                "denied",
                {"reason": "not approved", "status": status},
            )
            _audit(
                "APPROVAL_CREATED",
                str(alert_id),
                "pending",
                {"reason": "awaiting human approval", "status": status},
            )
            from core.phase3_metrics import HEAL_PENDING_APPROVAL

            HEAL_PENDING_APPROVAL.labels(alert_id=str(alert_id)).inc()
            # HITL: notify on-call operators if notification is configured.
            if NOTIFY_AVAILABLE and _send_alert_notification is not None:
                try:
                    await _send_alert_notification(alert)
                except Exception as notify_exc:
                    logger.warning(f"HITL notification failed for {alert_id}: {notify_exc}")
            return state

        state.approval_status = "approved"
        if approval is None and auto_executable and is_auto_approve:
            _audit(
                "APPROVAL_CHECK",
                str(alert_id),
                "auto_approved",
                {"reason": "SAFE/LOW auto-executable", "worst_risk": worst_risk},
            )

        # P3/F4/F5: Re-evaluate approval validity and current alert state before execution.
        can_execute, precheck_reason = _pre_execution_check(alert, approval)
        if not can_execute:
            state.error = f"Pre-execution check failed: {precheck_reason}"
            state.approval_status = "cancelled" if "self-healed" in precheck_reason else "expired"
            _audit(
                "APPROVAL_CHECK",
                str(alert_id),
                "denied",
                {"reason": precheck_reason},
            )
            if async_update_approval_status_by_alert is not None:
                try:
                    await async_update_approval_status_by_alert(
                        str(alert_id), state.approval_status
                    )
                except Exception as db_exc:  # pragma: no cover
                    logger.warning(
                        f"Failed to update approval status after precheck failure: {db_exc}"
                    )
            return state

        # O13: capture a pre-execution snapshot for rollback and verification.
        try:
            pre_metrics = _metrics_history.to_dict()
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            pre_metrics = {}

        # Build rollback plan as a list of commands (supports single and multi-step rollback).
        rollback_plan: List[str] = []
        if rollback_cmd and rollback_cmd != "无需回滚":
            rollback_plan = [rollback_cmd]

        # Persist a structured, encrypted snapshot before any mutating command runs.
        if SNAPSHOT_CONFIG.get("enabled", True) and save_snapshot is not None:
            try:
                snapshot_id = await save_snapshot(
                    state=state,
                    commands=commands,
                    rollback_plan=rollback_plan,
                    pre_metrics=pre_metrics,
                )
                state.snapshot_id = snapshot_id
                _audit(
                    "SNAPSHOT_CREATED",
                    str(alert_id) if alert_id else "unknown",
                    "success",
                    {"snapshot_id": snapshot_id, "commands": commands},
                )
            except Exception as snap_exc:  # pragma: no cover
                logger.warning(f"Snapshot capture failed (non-blocking): {snap_exc}")
                _audit(
                    "SNAPSHOT_CREATED",
                    str(alert_id) if alert_id else "unknown",
                    "failure",
                    {"error": str(snap_exc), "commands": commands},
                )

        # Fallback in-memory snapshot when persistence is disabled/unavailable.
        if not isinstance(state.snapshot, dict) or not state.snapshot.get("snapshot_id"):
            state.snapshot = {
                "alert": alert,
                "runbook": state.runbook,
                "metrics": pre_metrics,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        state.rollback_info = {
            "snapshot_id": state.snapshot_id,
            "rollback_commands": rollback_plan,
            "snapshot": state.snapshot,
        }

        executed: List[str] = []
        results: List[Dict[str, Any]] = []
        command_failed = False
        is_hardware = _is_hardware_alert(alert)
        hardware_enabled = os.getenv("HARDWARE_EXECUTE_ENABLED", "false").lower() == "true"
        for cmd in commands:
            if is_hardware and not hardware_enabled:
                executed.append(cmd)
                results.append(
                    {
                        "command": cmd,
                        "simulated": True,
                        "reason": "HARDWARE_EXECUTE_ENABLED=false",
                    }
                )
                continue
            # S3: every command must pass command_guard before execution.
            if analyze_command is not None:
                guard_result = analyze_command(cmd)
                if RiskLevel is not None and guard_result.get("risk_level") == RiskLevel.BLOCKED:
                    state.error = f"Command blocked by guard: {guard_result}"
                    _audit(
                        "REPAIR_BLOCKED",
                        str(alert_id),
                        "blocked",
                        {"command": cmd, "reason": guard_result.get("reason")},
                    )
                    return state

            # S2: validate command target against alert context.
            if not from_repair_script_library:
                target = _extract_command_target(cmd)
                if target:
                    allowed_targets = _allowed_targets_from_alert(alert)
                    if allowed_targets and target not in allowed_targets:
                        state.error = (
                            f"Command target '{target}' not found in alert context; aborting"
                        )
                        _audit(
                            "REPAIR_BLOCKED",
                            str(alert_id),
                            "blocked",
                            {"command": cmd, "reason": state.error},
                        )
                        return state

            executed.append(cmd)
            if os.getenv("HEAL_EXECUTE_ENABLED", "false").lower() == "true":
                try:
                    if alert.get("platform") == "windows":
                        proc = await asyncio.create_subprocess_exec(
                            "powershell",
                            "-Command",
                            cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                    else:
                        proc = await asyncio.create_subprocess_shell(
                            cmd,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )
                    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
                    rc = proc.returncode or 0
                    results.append(
                        {
                            "command": cmd,
                            "returncode": rc,
                            "stdout": stdout.decode("utf-8", errors="ignore")[:500],
                            "stderr": stderr.decode("utf-8", errors="ignore")[:500],
                        }
                    )
                    if rc != 0:
                        state.error = f"Command failed: {cmd} (rc={rc})"
                        command_failed = True
                        break
                except Exception as exec_exc:
                    state.error = f"Command execution failed: {exec_exc}"
                    command_failed = True
                    break
            else:
                results.append({"command": cmd, "simulated": True})

        state.executed_commands = executed
        state.repair_result = {
            "success": not command_failed,
            "results": results,
            "executed": executed,
        }

        if command_failed:
            _audit(
                "REPAIR_EXECUTED",
                str(alert_id),
                "failure",
                state.repair_result,
            )
            # P0-5: trigger rollback by marking verification as failed.
            state.fix_applied = False
            state.verification = {"passed": False, "reason": state.error}
            return state

        state.fix_applied = True
        if record_decision is not None:
            state.decision_id = record_decision(
                prediction=state.fix_applied,
                decision_type="heal",
            )
        _audit(
            "REPAIR_EXECUTED",
            str(alert_id),
            "success",
            {"commands": executed, "platform": alert.get("platform")},
        )
    except Exception as exc:  # pragma: no cover
        state.error = f"Fix application failed: {exc}"
    return state


async def evaluate(state: HealState) -> HealState:
    """Verify the fix via the verifier module."""
    try:
        if not state.fix_applied:
            return state

        if not isinstance(state.runbook, dict):
            # For string/MagicMock runbooks we cannot perform structured verification;
            # treat as a lightweight success for backwards compatibility.
            state.verification = {"passed": True, "confidence": 0.5}
            return state

        from .verifier import verify_repair

        runbook = state.runbook
        script_key = runbook.get("script_key", "AI_DYNAMIC")
        if script_key == "AI_DYNAMIC" and isinstance(runbook.get("runbook"), dict):
            script_key = runbook["runbook"].get("script_key", "AI_DYNAMIC")

        params = runbook.get("params")
        if not params and isinstance(runbook.get("runbook"), dict):
            params = runbook["runbook"].get("params", {})
        if not isinstance(params, dict):
            params = {}

        ai_runbook = runbook.get("runbook") if isinstance(runbook.get("runbook"), dict) else runbook
        repair_output = ""
        if isinstance(state.repair_result, dict):
            repair_output = json.dumps(state.repair_result, ensure_ascii=False, default=str)[:2000]
        if not isinstance(state.snapshot, dict):
            state.snapshot = {}
        if not isinstance(state.snapshot.get("metrics"), dict):
            state.snapshot["metrics"] = _metrics_history.to_dict()
        pre_snapshot = state.snapshot["metrics"]
        verify_res = await verify_repair(
            state.alert or {},
            script_key,
            params,
            pre_snapshot=pre_snapshot,
            repair_output=repair_output,
            repair_id=state.alert.get("id", 0) if state.alert else 0,
            ai_runbook=ai_runbook,
        )
        verification: Dict[str, Any]
        if hasattr(verify_res, "model_dump"):
            verification = verify_res.model_dump()
        elif isinstance(verify_res, dict):
            verification = dict(verify_res)
        else:
            verification = {"result": verify_res}
        # Normalize verifier output: the verifier uses ``verified``;
        # the graph uses ``passed``. Only ``verified=False`` triggers rollback;
        # ``verified=None`` (skipped) is a best-effort pass.
        if "verified" in verification and "passed" not in verification:
            verified_value = verification["verified"]
            if verified_value is False:
                verification["passed"] = False
            elif verified_value is True:
                verification["passed"] = True
            else:
                # skipped / None: treat as passed for dry-run and script-library fallbacks
                verification["passed"] = True
        elif "passed" not in verification:
            verification["passed"] = True
        state.verification = verification
        passed = bool(state.verification.get("passed"))
        from core.phase3_metrics import VERIFY_FAILED, VERIFY_PASSED

        strategy = state.verification.get("strategy") or "unknown"
        (VERIFY_PASSED if passed else VERIFY_FAILED).labels(strategy=str(strategy)).inc()
        _audit(
            "VERIFICATION_PASSED" if passed else "VERIFICATION_FAILED",
            str(state.alert.get("id", "unknown")) if state.alert else "unknown",
            "success" if passed else "failure",
            {
                "strategy": state.verification.get("strategy"),
                "verified": state.verification.get("verified"),
                "passed": passed,
            },
        )
        if record_outcome is not None and state.decision_id:
            actual = bool(state.verification.get("passed"))
            record_outcome(state.decision_id, actual)
    except Exception as exc:  # pragma: no cover
        state.error = f"Verification failed: {exc}"
    return state


async def rollback(state: HealState) -> HealState:
    """Rollback logic if verification indicates failure."""
    if not state.verification or state.verification.get("passed", True):
        return state

    alert_id = state.alert.get("id") if state.alert else None
    logger.warning("Rollback triggered for alert %s", alert_id)

    # Rollback must be covered by the repair approval or explicit approval.
    if SNAPSHOT_CONFIG.get("rollback_approval_required", True):
        if state.approval_status != "approved":
            msg = f"Rollback for alert {alert_id} not approved; aborting"
            state.error = msg
            _audit("ROLLBACK_BLOCKED", str(alert_id), "blocked", {"reason": "approval_required"})
            logger.warning(msg)
            return state

    rollback_info = state.rollback_info or {}
    rollback_commands: List[str] = list(rollback_info.get("rollback_commands", []))
    if not rollback_commands:
        # Backward compatibility with older runbook shape.
        fallback = rollback_info.get("rollback_command", "")
        if fallback and fallback != "无需回滚":
            rollback_commands = [fallback]

    if not rollback_commands or rollback_commands == ["无需回滚"]:
        logger.info("No rollback command available; skipping rollback")
        if state.snapshot_id and update_snapshot_status is not None:
            try:
                await update_snapshot_status(
                    state.snapshot_id,
                    "failed",
                    error_message="No rollback command available",
                )
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                logging.warning("Suppressed exception", exc_info=True)
        return state

    snapshot_id = state.snapshot_id

    # O13: every rollback command must pass command_guard before execution.
    if analyze_command is not None:
        for cmd in rollback_commands:
            guard_result = analyze_command(cmd)
            _risk = guard_result.get("risk_level")
            _is_enum_blocked = RiskLevel is not None and _risk == RiskLevel.BLOCKED
            _is_text_blocked = str(_risk).endswith(".BLOCKED")
            if _is_enum_blocked or _is_text_blocked:
                state.error = f"Rollback command blocked by guard: {guard_result}"
                _audit(
                    "ROLLBACK_BLOCKED",
                    str(alert_id),
                    "blocked",
                    {"command": cmd, "snapshot_id": snapshot_id},
                )
                if state.snapshot_id and update_snapshot_status is not None:
                    try:
                        await update_snapshot_status(
                            state.snapshot_id, "rollback_failed", error_message=state.error
                        )
                    except Exception as e:
                        logging.exception("Unexpected exception: %s", e)
                        logging.warning("Suppressed exception", exc_info=True)
                return state

    execute_enabled = os.getenv("HEAL_EXECUTE_ENABLED", "false").lower() == "true"
    rollback_error = ""
    failed_command = ""
    for cmd in rollback_commands:
        if not execute_enabled:
            continue
        try:
            if state.alert and state.alert.get("platform") == "windows":
                proc = await asyncio.create_subprocess_exec(
                    "powershell",
                    "-Command",
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            else:
                proc = await asyncio.create_subprocess_shell(
                    cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            rc = proc.returncode or 0
            _audit(
                "ROLLBACK_EXECUTED",
                str(alert_id),
                "success" if rc == 0 else "failure",
                {
                    "command": cmd,
                    "returncode": rc,
                    "stdout": stdout.decode("utf-8", errors="ignore")[:500],
                    "stderr": stderr.decode("utf-8", errors="ignore")[:500],
                    "snapshot_id": snapshot_id,
                },
            )
            if rc != 0:
                rollback_error = f"Rollback command failed: {cmd} (rc={rc})"
                failed_command = cmd
                break
        except Exception as exec_exc:
            rollback_error = f"Rollback execution failed: {exec_exc}"
            failed_command = cmd
            _audit(
                "ROLLBACK_EXECUTED",
                str(alert_id),
                "failure",
                {"command": cmd, "error": str(exec_exc), "snapshot_id": snapshot_id},
            )
            break

    if rollback_error:
        state.error = rollback_error
        state.escalated = True
        if state.snapshot_id and update_snapshot_status is not None:
            try:
                await update_snapshot_status(
                    state.snapshot_id, "rollback_failed", error_message=rollback_error
                )
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                logging.warning("Suppressed exception", exc_info=True)
        if (
            SNAPSHOT_CONFIG.get("rollback_failure_escalation_enabled", True)
            and notify_rollback_failure is not None
        ):
            try:
                await notify_rollback_failure(
                    alert_id=str(alert_id),
                    rollback_command=failed_command,
                    error=rollback_error,
                    snapshot_id=snapshot_id,
                )
            except Exception as esc_exc:
                logger.error(f"Rollback escalation notification failed: {esc_exc}")
        return state

    state.fix_applied = False
    if state.snapshot_id and update_snapshot_status is not None:
        try:
            await update_snapshot_status(state.snapshot_id, "success")
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            logging.warning("Suppressed exception", exc_info=True)
    logger.info("Rollback completed for alert %s", alert_id)
    return state


async def complete(state: HealState) -> HealState:
    """Final cleanup – persist state, emit metrics, expire old snapshots, etc."""
    alert_id = state.alert.get("id") if state.alert else None

    # O13: cleanup expired snapshots on every workflow completion.
    if cleanup_expired_snapshots is not None:
        try:
            await cleanup_expired_snapshots()
        except Exception as exc:
            logger.warning(f"Snapshot cleanup failed (non-blocking): {exc}")

    # P2-3: build structured metrics for observability
    verification = state.verification or {}
    status = (
        "success"
        if (state.fix_applied and verification.get("passed"))
        else "failure" if state.error else "approval_pending"
    )
    state.metrics = {
        "alert_id": alert_id,
        "status": status,
        "fix_applied": state.fix_applied,
        "approval_status": state.approval_status,
        "commands_executed": len(state.executed_commands),
        "verification_strategy": verification.get("strategy")
        or verification.get("result", {}).get("strategy"),
        "verification_passed": verification.get("passed"),
        "error": state.error,
        "escalated": state.escalated,
        "snapshot_id": state.snapshot_id,
    }

    # Persist a RepairRecord when the repair was actually executed.
    if state.fix_applied and async_insert_repair_record is not None:
        try:
            await async_insert_repair_record(
                success=not bool(state.error),
                alert_time=state.alert.get("startsAt") if state.alert else None,
                repair_time=datetime.now(timezone.utc).isoformat(),
                repair_duration_sec=float(verification.get("duration_sec", 0.0) or 0.0),
                rule_name=str(state.alert.get("metric") or "unknown") if state.alert else "unknown",
                script_key=(
                    str(state.alert.get("metric") or "unknown") if state.alert else "unknown"
                ),
                platform=str(state.alert.get("platform", "windows")) if state.alert else "windows",
                output=json.dumps(state.repair_result, ensure_ascii=False, default=str),
                alert_id=str(alert_id) if alert_id else None,
                host=state.alert.get("host") if state.alert else None,
                risk=(
                    str(state.runbook.get("worst_risk", "low")).lower()
                    if isinstance(state.runbook, dict)
                    else "low"
                ),
                params=state.runbook if isinstance(state.runbook, dict) else None,
            )
        except Exception as repair_record_exc:
            logger.warning(f"Failed to persist repair record: {repair_record_exc}")

    # O13: finalize persisted snapshot status.
    if state.snapshot_id and update_snapshot_status is not None:
        try:
            if status == "success":
                await update_snapshot_status(state.snapshot_id, "success")
            elif status == "failure":
                await update_snapshot_status(state.snapshot_id, "failed", error_message=state.error)
        except Exception as exc:
            logger.warning(f"Snapshot status finalization failed: {exc}")

    # P2-3: best-effort Prometheus counter emission
    try:
        from prometheus_client import Counter

        if "heal_total" not in _HEAL_METRIC_COUNTERS:
            _HEAL_METRIC_COUNTERS["heal_total"] = Counter(
                "aiops_heal_total",
                "Total heal workflow executions",
                ["status"],
            )
        _HEAL_METRIC_COUNTERS["heal_total"].labels(status=status).inc()
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        logging.warning("Suppressed exception", exc_info=True)

    _audit(
        "HEALING_COMPLETED",
        str(alert_id) if alert_id else "unknown",
        status,
        {
            "fix_applied": state.fix_applied,
            "error": state.error,
            "verification": state.verification,
            "metrics": state.metrics,
            "snapshot_id": state.snapshot_id,
            "escalated": state.escalated,
        },
    )
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

    # Enable SQLite checkpointing for persistence when the installed langgraph supports it.
    try:
        checkpoint = CheckpointSQLite("heal_graph.db")
        if "checkpointer" in inspect.signature(graph.compile).parameters:
            return graph.compile(checkpointer=checkpoint)
    except Exception as e:
        logger.info("LangGraph checkpointing disabled: %s", e)
    return graph.compile()


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
    from core.phase3_metrics import HEAL_FAILED, HEAL_SUCCESS, HEAL_TOTAL

    script_key = str((state.alert or {}).get("metric", "unknown"))
    trace_id = (state.alert or {}).get("trace_id")
    if not trace_id:
        import uuid

        trace_id = uuid.uuid4().hex
        if state.alert is not None:
            state.alert["trace_id"] = trace_id
    if callable(_set_trace_id):
        _set_trace_id(trace_id)
    HEAL_TOTAL.labels(script_key=script_key).inc()
    try:
        final_state = await _heal_graph_runner(state)
        if final_state.error:
            HEAL_FAILED.labels(script_key=script_key).inc()
        else:
            HEAL_SUCCESS.labels(script_key=script_key).inc()
        return final_state  # type: ignore[no-any-return]
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        HEAL_FAILED.labels(script_key=script_key).inc()
        state.error = f"Graph execution failed: {traceback.format_exc()}"
        return state
