# -*- coding: utf-8 -*-
"""
behavior_monitor.py
-------------------
Agent behavior anomaly detection (O21).

Tracks per-agent execution metrics such as iteration count, tool call
frequency, repeated tool usage and error rate. When thresholds are
exceeded an anomaly alert is emitted so the orchestrator can take
action (e.g. terminate the agent or raise a HITL approval).
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class _AgentMetrics:
    agent_id: str
    iterations: int = 0
    tool_calls: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    actions: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    errors: int = 0
    start_time: float = field(default_factory=time.time)
    alerts: List[Dict[str, Any]] = field(default_factory=list)


class BehaviorMonitor:
    """Lightweight in-memory behavior monitor for autonomous agents."""

    # Thresholds
    MAX_ITERATIONS = 50
    MAX_TOTAL_TOOL_CALLS = 100
    MAX_TOOL_REPETITIONS = 10
    MAX_ERRORS = 10
    MAX_EXECUTION_TIME_SECONDS = 300

    def __init__(self):
        self._metrics: Dict[str, _AgentMetrics] = {}
        self._thresholds = {
            "max_iterations": self.MAX_ITERATIONS,
            "max_total_tool_calls": self.MAX_TOTAL_TOOL_CALLS,
            "max_tool_repetitions": self.MAX_TOOL_REPETITIONS,
            "max_errors": self.MAX_ERRORS,
            "max_execution_time_seconds": self.MAX_EXECUTION_TIME_SECONDS,
        }

    def _get_or_create(self, agent_id: str) -> _AgentMetrics:
        if agent_id not in self._metrics:
            self._metrics[agent_id] = _AgentMetrics(agent_id=agent_id)
        return self._metrics[agent_id]

    def set_thresholds(self, **kwargs) -> None:
        """Override default thresholds (e.g. for testing)."""
        self._thresholds.update(kwargs)

    def record_iteration(self, agent_id: str) -> None:
        """Record one execution iteration."""
        metrics = self._get_or_create(agent_id)
        metrics.iterations += 1

    def record_tool_call(self, agent_id: str, tool_name: str) -> None:
        """Record a tool invocation."""
        metrics = self._get_or_create(agent_id)
        metrics.tool_calls[tool_name] += 1

    def record_action(self, agent_id: str, action_key: str) -> None:
        """Record a concrete action signature (goal + tool + normalized params)."""
        metrics = self._get_or_create(agent_id)
        metrics.actions[action_key] += 1

    def record_error(self, agent_id: str) -> None:
        """Record an execution error."""
        metrics = self._get_or_create(agent_id)
        metrics.errors += 1

    def check_anomaly(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Check whether the agent has exceeded any behavior threshold."""
        metrics = self._get_or_create(agent_id)
        alerts: List[str] = []

        if metrics.iterations > self._thresholds["max_iterations"]:
            alerts.append(
                f"iteration limit exceeded ({metrics.iterations}/"
                f"{self._thresholds['max_iterations']})"
            )

        total_tool_calls = sum(metrics.tool_calls.values())
        if total_tool_calls > self._thresholds["max_total_tool_calls"]:
            alerts.append(
                f"total tool call limit exceeded ({total_tool_calls}/"
                f"{self._thresholds['max_total_tool_calls']})"
            )

        for tool_name, count in metrics.tool_calls.items():
            if count > self._thresholds["max_tool_repetitions"]:
                alerts.append(
                    f"repeated tool '{tool_name}' usage ({count}/"
                    f"{self._thresholds['max_tool_repetitions']})"
                )

        # Parameter-level loop detection: same goal + tool + normalized params
        for action_key, count in metrics.actions.items():
            if count > self._thresholds["max_tool_repetitions"]:
                alerts.append(
                    f"repeated action signature ({count}/"
                    f"{self._thresholds['max_tool_repetitions']})"
                )

        if metrics.errors > self._thresholds["max_errors"]:
            alerts.append(
                f"error limit exceeded ({metrics.errors}/" f"{self._thresholds['max_errors']})"
            )

        elapsed = time.time() - metrics.start_time
        if elapsed > self._thresholds["max_execution_time_seconds"]:
            alerts.append(
                f"execution time exceeded ({elapsed:.1f}s/"
                f"{self._thresholds['max_execution_time_seconds']}s)"
            )

        if alerts:
            anomaly = {
                "agent_id": agent_id,
                "level": "warning",
                "messages": alerts,
                "metrics": {
                    "iterations": metrics.iterations,
                    "tool_calls": dict(metrics.tool_calls),
                    "total_tool_calls": total_tool_calls,
                    "errors": metrics.errors,
                    "elapsed_seconds": elapsed,
                },
                "timestamp": time.time(),
            }
            metrics.alerts.append(anomaly)
            logger.warning(f"Agent behavior anomaly detected: {anomaly}")
            return anomaly

        return None

    def get_summary(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Return current behavior metrics, optionally filtered by agent."""
        if agent_id:
            metrics = self._metrics.get(agent_id)
            if not metrics:
                return {"agent_id": agent_id, "found": False}
            return {
                "agent_id": agent_id,
                "found": True,
                "iterations": metrics.iterations,
                "tool_calls": dict(metrics.tool_calls),
                "errors": metrics.errors,
                "alerts": metrics.alerts,
                "elapsed_seconds": time.time() - metrics.start_time,
            }

        return {
            agent_id: {
                "iterations": m.iterations,
                "tool_calls": dict(m.tool_calls),
                "errors": m.errors,
                "alerts": m.alerts,
                "elapsed_seconds": time.time() - m.start_time,
            }
            for agent_id, m in self._metrics.items()
        }

    def reset(self, agent_id: Optional[str] = None) -> None:
        """Reset metrics for one or all agents."""
        if agent_id:
            self._metrics.pop(agent_id, None)
        else:
            self._metrics.clear()


# Global monitor instance
_global_behavior_monitor = BehaviorMonitor()


def get_behavior_monitor() -> BehaviorMonitor:
    """Get the global behavior monitor instance."""
    return _global_behavior_monitor
