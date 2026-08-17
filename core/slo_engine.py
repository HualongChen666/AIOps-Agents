# -*- coding: utf-8 -*-
"""
core/slo_engine.py
==================

SLO/SLA evaluation engine. Stores SLO rules in memory and evaluates
service-level objectives against a numeric metric history.

Key concepts
------------
- ``SLORule`` captures the objective: service + metric + target (0-1)
  + time window (hours) + alert threshold (0-1) + aggregation.
- ``evaluate_slo`` computes the current SLI, remaining error budget,
  burn rate and alert/health status.
- ``create_slo`` / ``list_slos`` / ``get_slo`` / ``delete_slo``
  provide simple CRUD helpers over the in-memory store.
"""

from __future__ import annotations

import datetime
import logging
import math
import statistics
from dataclasses import dataclass
from typing import Any, Optional

from core.slo_storage import load_slos  # type: ignore

logger = logging.getLogger(__name__)


# Window string <-> hours conversions.
_WINDOW_TO_HOURS = {
    "1h": 1,
    "24h": 24,
    "7d": 168,
    "30d": 720,
    "90d": 2160,
}
_HOURS_TO_WINDOW = {v: k for k, v in _WINDOW_TO_HOURS.items()}

ALLOWED_AGGREGATIONS = {"good_ratio", "uptime", "p99_lt", "mean_lt"}
DEFAULT_AGGREGATION = "good_ratio"


def parse_window(window: str) -> int:
    """Parse a window string like 1h / 7d / 30d into hours."""
    if window in _WINDOW_TO_HOURS:
        return _WINDOW_TO_HOURS[window]
    if window.endswith("h"):
        return int(window[:-1])
    if window.endswith("d"):
        return int(window[:-1]) * 24
    try:
        return int(window)
    except ValueError as exc:
        raise ValueError(f"Invalid window format: {window}") from exc


def format_window(hours: int) -> str:
    """Format an hour count back to a UI-friendly window string."""
    return _HOURS_TO_WINDOW.get(hours, f"{hours}h")


@dataclass
class SLORule:
    """Single SLO rule.

    Fields:
        id: Unique identifier.
        name: Human-readable name.
        service: Service/system this SLO belongs to.
        metric: Metric name used for the SLI (e.g. ``cpu``, ``availability``).
        target: Target value in the 0-1 scale (or a latency threshold
            for ``p99_lt`` / ``mean_lt``).
        window: Evaluation time window in hours.
        alert_threshold: 0-1 threshold below which an alert is raised.
        aggregation: How to aggregate the metric history. One of
            ``good_ratio``, ``uptime``, ``p99_lt``, ``mean_lt``.
    """

    id: str
    name: str
    service: str
    metric: str
    target: float
    window: int
    alert_threshold: float
    aggregation: str = DEFAULT_AGGREGATION


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


def _validate_aggregation(aggregation: Optional[str]) -> str:
    """Return a normalized aggregation value or raise ValueError."""
    value = aggregation if aggregation is not None else DEFAULT_AGGREGATION
    value = value.strip().lower()
    if value not in ALLOWED_AGGREGATIONS:
        raise ValueError(
            f"Invalid aggregation '{aggregation}'; allowed: {sorted(ALLOWED_AGGREGATIONS)}"
        )
    return value


def _metric_point_value(point: Any, metric: str) -> float:
    """Extract a value and normalize known percent metrics."""
    value = float(point.value)
    if metric in {"cpu", "memory"}:
        return value / 100.0
    return value


def _point_is_good(point: Any, rule: SLORule) -> bool:
    """Return True if a metric point satisfies the SLO target."""
    value = _metric_point_value(point, rule.metric)
    high = _higher_is_better(rule.metric)
    return value >= rule.target if high else value <= rule.target


def _to_epoch(ts: Any) -> float:
    """Convert a metric point timestamp to seconds since epoch."""
    if isinstance(ts, (int, float)):
        return float(ts)
    if isinstance(ts, datetime.datetime):
        return ts.timestamp()
    try:
        return float(ts)
    except (TypeError, ValueError):
        try:
            parsed = datetime.datetime.strptime(str(ts).strip(), "%H:%M:%S")
            now = datetime.datetime.now()
            parsed = parsed.replace(year=now.year, month=now.month, day=now.day)
            return parsed.timestamp()
        except ValueError:
            return 0.0


def _percentile(values: list[float], q: float) -> float:
    """Return the q-th percentile of a non-empty list of floats."""
    n = len(values)
    if n == 0:
        return 0.0
    sorted_vals = sorted(values)
    idx = max(0, min(n - 1, math.ceil((n - 1) * q)))
    return sorted_vals[idx]


def _uptime_ratio(points: list[Any], rule: SLORule) -> float:
    """Good duration / total duration using point timestamps."""
    if not points:
        return 1.0
    if len(points) == 1:
        return 1.0 if _point_is_good(points[0], rule) else 0.0

    epochs = [_to_epoch(p.timestamp) for p in points]
    total = max(0.0, epochs[-1] - epochs[0])
    if total <= 0.0:
        return 1.0

    good = 0.0
    for i in range(len(points) - 1):
        duration = max(0.0, epochs[i + 1] - epochs[i])
        if _point_is_good(points[i], rule):
            good += duration
    return good / total


def create_slo(
    name: str,
    service: str,
    metric: str,
    target: float,
    window: int,
    alert_threshold: Optional[float] = None,
    slo_id: Optional[str] = None,
    aggregation: Optional[str] = None,
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
        aggregation: Optional aggregation strategy. Defaults to ``good_ratio``.

    Returns:
        The created ``SLORule`` instance.
    """
    safe_target = max(0.0, min(1.0, float(target)))
    safe_alert = (
        max(0.0, min(1.0, float(alert_threshold)))
        if alert_threshold is not None
        else max(0.0, 2.0 * safe_target - 1.0)
    )
    safe_aggregation = _validate_aggregation(aggregation)

    rule = SLORule(
        id=slo_id or _generate_id(),
        name=name,
        service=service,
        metric=metric,
        target=safe_target,
        window=max(1, int(window)),
        alert_threshold=safe_alert,
        aggregation=safe_aggregation,
    )
    _slo_store[rule.id] = rule
    from core.slo_storage import save_slos

    save_slos()
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
        from core.slo_storage import save_slos

        save_slos()
        logger.info(f"Deleted SLO {slo_id}")
        return True
    return False


def evaluate_slo(rule: SLORule, points: list[Any]) -> dict[str, Any]:
    """Evaluate an SLO rule against metric history points.

    ``points`` are duck-typed objects with ``timestamp`` and ``value``
    attributes (e.g. ``MetricPoint``).

    Args:
        rule: The ``SLORule`` to evaluate.
        points: List of metric samples.

    Returns:
        dict with keys:
            ``current`` (0-1 SLI),
            ``error_budget_remaining_percent`` (0-100),
            ``burn_rate`` (dimensionless),
            ``status`` (``healthy`` | ``warning`` | ``critical``),
            ``alert`` (bool).
    """
    if not points:
        return {
            "current": 1.0,
            "error_budget_remaining_percent": 100.0,
            "burn_rate": 0.0,
            "status": "healthy",
            "alert": False,
        }

    aggregation = rule.aggregation

    if aggregation == "good_ratio":
        total = len(points)
        good_count = sum(1 for p in points if _point_is_good(p, rule))
        current = good_count / total
    elif aggregation == "uptime":
        current = _uptime_ratio(points, rule)
    elif aggregation == "p99_lt":
        values = [_metric_point_value(p, rule.metric) for p in points]
        p99 = _percentile(values, 0.99)
        current = 1.0 if p99 <= rule.target else 0.0
    elif aggregation == "mean_lt":
        values = [_metric_point_value(p, rule.metric) for p in points]
        mean = statistics.mean(values)
        current = 1.0 if mean <= rule.target else 0.0
    else:
        # Defensive fallback: treat everything as good.
        current = 1.0

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


def update_slo(
    slo_id: str,
    name: Optional[str] = None,
    service: Optional[str] = None,
    metric: Optional[str] = None,
    target: Optional[float] = None,
    window: Optional[int] = None,
    alert_threshold: Optional[float] = None,
    aggregation: Optional[str] = None,
) -> Optional[SLORule]:
    """Update an existing SLO rule. Only provided fields are changed."""
    rule = _slo_store.get(slo_id)
    if not rule:
        return None

    if name is not None:
        rule.name = name
    if service is not None:
        rule.service = service
    if metric is not None:
        rule.metric = metric
    if target is not None:
        rule.target = max(0.0, min(1.0, float(target)))
    if window is not None:
        rule.window = max(1, int(window))
    if alert_threshold is not None:
        rule.alert_threshold = max(0.0, min(1.0, float(alert_threshold)))
    if aggregation is not None:
        rule.aggregation = _validate_aggregation(aggregation)

    from core.slo_storage import save_slos

    save_slos()
    logger.info(f"Updated SLO {slo_id}: {rule}")
    return rule


def generate_sla_report(period: str = "30d") -> list[dict[str, Any]]:
    """Generate an SLA compliance report for all SLO rules over a period.

    The report queries metric history for each SLO's service and metric in
    the requested time window, evaluates the SLO, and produces availability,
    target, compliance and incident counts.
    """
    from core.metrics_history import metrics_history

    hours = parse_window(period)
    end_dt = datetime.datetime.utcnow()
    start_dt = end_dt - datetime.timedelta(hours=hours)
    reports: list[dict[str, Any]] = []

    for rule in list_slos():
        points = metrics_history.query(rule.metric, rule.service, start_dt, end_dt)
        result = evaluate_slo(rule, points)

        availability = round(result["current"] * 100.0, 2)
        target_percent = round(rule.target * 100.0, 2)
        compliance = "compliant" if availability >= target_percent else "non-compliant"

        if rule.aggregation == "uptime" and len(points) >= 2:
            total_seconds = _to_epoch(points[-1].timestamp) - _to_epoch(points[0].timestamp)
            bad_seconds = max(0.0, total_seconds * (1.0 - result["current"]))
            incidents = int(bad_seconds / 60.0)
        else:
            incidents = sum(1 for p in points if not _point_is_good(p, rule))

        reports.append(
            {
                "id": f"SLA-{rule.id}-{period}",
                "slo_id": rule.id,
                "slo_name": rule.name,
                "service": rule.service,
                "metric": rule.metric,
                "period": period,
                "availability": availability,
                "slaTarget": target_percent,
                "compliance": compliance,
                "incidents": incidents,
                "aggregation": rule.aggregation,
            }
        )

    return reports


# Load persisted SLOs at module import time.

load_slos()
