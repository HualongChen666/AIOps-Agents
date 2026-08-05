# -*- coding: utf-8 -*-
"""
Capacity Forecasting Engine
===========================

Simple linear regression over historical metric series to produce
7-day and 30-day capacity forecasts for CPU, memory, disk and network.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

_METRIC_META = {
    "cpu": {"name": "CPU使用率", "threshold": 80.0, "unit": "%"},
    "memory": {"name": "内存使用率", "threshold": 85.0, "unit": "%"},
    "disk": {"name": "磁盘使用率", "threshold": 80.0, "unit": "%"},
    "network": {"name": "网络带宽", "threshold": 70.0, "unit": "%"},
}

_SERVICE_NAMES = {
    "cpu": "compute-service",
    "memory": "cache-service",
    "disk": "database",
    "network": "api-gateway",
}

_DEFAULT_SERIES = {
    "cpu": [45.0, 46.5, 48.0, 49.2, 50.1],
    "memory": [55.0, 57.0, 59.0, 60.5, 62.0],
    "disk": [40.0, 42.0, 44.0, 46.0, 48.0],
    "network": [30.0, 32.0, 34.0, 36.0, 38.0],
}


def _to_floats(values: Any) -> list[float]:
    """Convert a sequence to a list of floats, skipping invalid items."""
    result: list[float] = []
    if not isinstance(values, (list, tuple)):
        return result
    for v in values:
        try:
            result.append(float(v))
        except (TypeError, ValueError):
            logger.debug(f"跳过非数值历史数据: {v!r}")
            continue
    return result


def _linear_forecast(values: list[float], horizon: int) -> float:
    """Return the linear regression forecast `horizon` steps after the last value."""
    n = len(values)
    if n == 0:
        return 0.0
    if n == 1:
        return values[0]

    x = list(range(n))
    sx = sum(x)
    sy = sum(values)
    sxx = sum(i * i for i in x)
    sxy = sum(x[i] * values[i] for i in range(n))

    denom = n * sxx - sx * sx
    if denom == 0:
        return values[-1]

    slope = (n * sxy - sx * sy) / denom
    intercept = (sy - slope * sx) / n
    return intercept + slope * (n - 1 + horizon)


def forecast_capacity(metric_history: dict, days_ahead: int) -> dict:
    """
    Forecast capacity for the four target metrics.

    Args:
        metric_history: mapping of metric keys to numeric lists.
        days_ahead: accepted for interface compatibility; forecasts are always
            produced for 7 and 30 days ahead.

    Returns:
        dict mapping metric key -> {
            metric, currentValue, forecast7d, forecast30d, threshold, unit
        }
    """
    _ = days_ahead  # kept for API compatibility
    result: dict[str, dict[str, Any]] = {}

    for key, meta in _METRIC_META.items():
        raw = metric_history.get(key) if isinstance(metric_history, dict) else None
        values = _to_floats(raw)
        if len(values) < 2:
            values = _to_floats(_DEFAULT_SERIES.get(key, [0.0]))

        current = values[-1]
        forecast_7 = _linear_forecast(values, 7)
        forecast_30 = _linear_forecast(values, 30)

        # Clamp to realistic percentage range; network should be normalized
        # to a 0-100 % scale by the caller if it is sourced from MB/s.
        forecast_7 = max(0.0, min(100.0, forecast_7))
        forecast_30 = max(0.0, min(100.0, forecast_30))

        result[key] = {
            "metric": meta["name"],
            "currentValue": round(current, 2),
            "forecast7d": round(forecast_7, 2),
            "forecast30d": round(forecast_30, 2),
            "threshold": meta["threshold"],
            "unit": meta["unit"],
        }

    return result


def generate_scaling_recommendations(forecasts: dict) -> list:
    """
    Generate scale-up / scale-down / no-action recommendations from forecasts.

    Returns:
        list of recommendation dicts with id/service/action/reason/priority/estimatedCost.
    """
    recommendations: list[dict[str, Any]] = []

    for key, f in forecasts.items():
        meta = _METRIC_META.get(key, _METRIC_META["cpu"])
        metric_name = f.get("metric", meta["name"])
        threshold = f.get("threshold", meta["threshold"])
        forecast_7 = f.get("forecast7d", 0.0)
        forecast_30 = f.get("forecast30d", 0.0)
        current = f.get("currentValue", 0.0)

        if forecast_7 > threshold:
            action = "scale-up"
            priority = "high"
            reason = (
                f"预测7天内{metric_name}将达到{forecast_7}{f.get('unit', '')}，"
                f"超过阈值{threshold}{f.get('unit', '')}"
            )
            cost = 300
        elif forecast_30 > threshold:
            action = "scale-up"
            priority = "medium"
            reason = (
                f"预测30天内{metric_name}将达到{forecast_30}{f.get('unit', '')}，"
                f"超过阈值{threshold}{f.get('unit', '')}"
            )
            cost = 150
        elif forecast_30 < threshold * 0.5 and current < threshold * 0.5:
            action = "scale-down"
            priority = "low"
            reason = f"未来30天{metric_name}维持低位，可考虑缩容"
            cost = 0
        else:
            action = "no-action"
            priority = "low"
            reason = f"{metric_name}使用趋势平稳，无需调整"
            cost = 0

        recommendations.append(
            {
                "id": f"SR-{key.upper()}",
                "service": _SERVICE_NAMES.get(key, key),
                "action": action,
                "reason": reason,
                "priority": priority,
                "estimatedCost": cost,
            }
        )

    return recommendations
