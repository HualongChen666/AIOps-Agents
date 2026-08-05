# -*- coding: utf-8 -*-
"""
core/slo_engine.py
==================

SLO/SLA evaluation engine. Stores SLO rules in memory and evaluates
service-level objectives against a numeric metric history.

Key concepts
------------
- ``SLORule`` captures the objective: service + metric + target (0-1)
  + time window (hours) + alert threshold (0-1).
- ``evaluate_slo`` computes the current SLI, remaining error budget,
  burn rate and alert/health status.
- ``create_slo`` / ``list_slos`` / ``get_slo`` / ``delete_slo``
  provide simple CRUD helpers over the in-memory store.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class SLORule:
    """Single SLO rule.

    Fields:
        id: Unique identifier.
        name: Human-readable name.
        service: Service/system this SLO belongs to.
        metric: Metric name used for the SLI (e.g. ``cpu``, ``availability``).
        target: Target value in the 0-1 scale.
        window: Evaluation time window in hours.
        alert_threshold: 0-1 threshold below which an alert is raised.
    """

    id: str
    name: str
    service: str
    metric: str
    target: float
    window: int
    alert_threshold: float


# In-memory storage for SLO rules.
_slo_store: dict[str, SLORule] = {}
_slo_counter = 0


# Metrics where a *lower* value is better (must stay below the target).
_LOWER_IS_BETTER = frozenset({"latency", "error_rate", "cpu", "memory"})


def _generate_id() -> str:
    """Generate a sequential SLO id, e.g. ``SLO-001``."""
    global _slo_counter
    _slo_counter += 1
    return f"SLO-{str(_slo_counter).zfill(3)}"


def _higher_is_better(metric: str) -> bool:
    """Return True if the metric is a higher-is-better SLI."""
    return metric not in _LOWER_IS_BETTER


def create_slo(
    name: str,
    service: str,
    metric: str,
    target: float,
    window: int,
    alert_threshold: Optional[float] = None,
    slo_id: Optional[str] = None,
) -> SLORule:
    """Create and persist a new SLO rule.

    Args:
        name: Human-readable SLO name.
        service: Service name.
        metric: Metric name.
        target: Target value in the 0-1 scale.
        window: Evaluation window in hours.
        alert_threshold: Optional alert threshold in 0-1. Defaults to
            ``max(0, 2*target - 1)`` when omitted.
        slo_id: Optional explicit id; generated if not provided.

    Returns:
        The created ``SLORule`` instance.
    """
    safe_target = max(0.0, min(1.0, float(target)))
    safe_alert = (
        max(0.0, min(1.0, float(alert_threshold)))
        if alert_threshold is not None
        else max(0.0, 2.0 * safe_target - 1.0)
    )
    rule = SLORule(
        id=slo_id or _generate_id(),
        name=name,
        service=service,
        metric=metric,
        target=safe_target,
        window=max(1, int(window)),
        alert_threshold=safe_alert,
    )
    _slo_store[rule.id] = rule
    logger.info(f"Created SLO {rule.id}: {rule}")
    return rule


def list_slos() -> list[SLORule]:
    """Return all stored SLO rules."""
    return list(_slo_store.values())


def get_slo(slo_id: str) -> Optional[SLORule]:
    """Fetch a single SLO rule by id."""
    return _slo_store.get(slo_id)


def delete_slo(slo_id: str) -> bool:
    """Delete an SLO rule. Returns True if it existed."""
    if slo_id in _slo_store:
        del _slo_store[slo_id]
        logger.info(f"Deleted SLO {slo_id}")
        return True
    return False


def evaluate_slo(rule: SLORule, history: list[float]) -> dict[str, Any]:
    """Evaluate an SLO rule against a numeric history.

    ``history`` values are expected to be in the same 0-1 scale as
    ``rule.target``.

    Args:
        rule: The ``SLORule`` to evaluate.
        history: List of numeric metric samples.

    Returns:
        dict with keys:
            ``current`` (0-1 SLI),
            ``error_budget_remaining_percent`` (0-100),
            ``burn_rate`` (dimensionless),
            ``status`` (``healthy`` | ``warning`` | ``critical``),
            ``alert`` (bool).
    """
    if not history:
        return {
            "current": 1.0,
            "error_budget_remaining_percent": 100.0,
            "burn_rate": 0.0,
            "status": "healthy",
            "alert": False,
        }

    total = len(history)
    high = _higher_is_better(rule.metric)
    good_count = sum(
        1
        for value in history
        if (value >= rule.target if high else value <= rule.target)
    )
    current = good_count / total

    if rule.target >= 1.0 - 1e-9:
        error_budget_remaining_percent = 100.0 if current >= 1.0 else 0.0
        burn_rate = 0.0 if current >= 1.0 else 100.0
    else:
        bad_ratio = 1.0 - current
        allowed_bad = 1.0 - rule.target
        consumed_percent = (bad_ratio / allowed_bad) * 100.0
        error_budget_remaining_percent = max(0.0, 100.0 - consumed_percent)
        burn_rate = bad_ratio / allowed_bad

    if current >= rule.target:
        status = "healthy"
    elif current >= rule.alert_threshold:
        status = "warning"
    else:
        status = "critical"

    return {
        "current": current,
        "error_budget_remaining_percent": error_budget_remaining_percent,
        "burn_rate": burn_rate,
        "status": status,
        "alert": status == "critical",
    }
