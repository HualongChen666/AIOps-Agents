# -*- coding: utf-8 -*-
"""
Anomaly Detection Engine
========================
Lightweight Z-score based anomaly detection over metrics history.
"""

import datetime
import logging
import statistics
import uuid
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LATEST_N = 30
METRIC_LABELS = {
    "cpu": "CPU使用率",
    "memory": "内存使用率",
    "net_in": "网络入流量",
}


def _make_timestamp(raw_ts: Any) -> str:
    """Convert a raw history timestamp to an ISO8601 string."""
    if isinstance(raw_ts, datetime.datetime):
        return raw_ts.isoformat()
    if isinstance(raw_ts, str) and raw_ts:
        # MetricsHistory stores "%H:%M:%S"; prepend today's date if needed.
        if raw_ts.count(":") >= 1 and "-" not in raw_ts and "T" not in raw_ts:
            return f"{datetime.date.today().isoformat()}T{raw_ts.strip()}"
        return raw_ts
    return datetime.datetime.now().isoformat()


def detect_anomalies(
    metric_history: dict,
    metric_name: str,
    threshold_z: float = 3.0,
) -> list[dict[str, Any]]:
    """
    Detect anomalies for the latest data point of a single metric using Z-score.

    Args:
        metric_history: dict with metric name keys (e.g. cpu, memory, net_in)
                        and an optional "timestamps" list.
        metric_name:    metric key to analyse.
        threshold_z:    Z-score magnitude above which the point is an anomaly.

    Returns:
        List of AnomalyRecord-like dicts for anomalous points.
    """
    values = metric_history.get(metric_name)
    if not isinstance(values, list) or len(values) < 3:
        return []

    n = DEFAULT_LATEST_N
    window = values[-n:] if len(values) > n else values
    current = values[-1]

    mean = statistics.mean(window)
    try:
        stdev = statistics.stdev(window)
    except statistics.StatisticsError:
        stdev = 0.0

    if stdev < 1e-9:
        return []

    z_score = (current - mean) / stdev
    if abs(z_score) <= threshold_z:
        return []

    timestamps = metric_history.get("timestamps", [])
    if isinstance(timestamps, list) and timestamps:
        raw_ts = timestamps[-1]
    else:
        raw_ts = None

    actual = round(float(current), 2)
    predicted = round(float(mean), 2)
    deviation = round(((actual - predicted) / predicted) * 100, 1) if predicted else 0.0
    confidence = min(100, int(abs(z_score) * 25))

    return [
        {
            "id": f"AN-{metric_name}-{uuid.uuid4().hex[:8]}",
            "timestamp": _make_timestamp(raw_ts),
            "metric": METRIC_LABELS.get(metric_name, metric_name),
            "actualValue": actual,
            "predictedValue": predicted,
            "deviation": deviation,
            "confidence": confidence,
        }
    ]


def detect_all_anomalies(history: dict) -> list[dict[str, Any]]:
    """
    Run anomaly detection for cpu, memory and net_in.

    Returns:
        Flat list of AnomalyRecord-like dicts, sorted by timestamp desc.
    """
    results: list[dict[str, Any]] = []
    for metric in ("cpu", "memory", "net_in"):
        results.extend(detect_anomalies(history, metric))
    results.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return results
