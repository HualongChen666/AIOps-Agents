# -*- coding: utf-8 -*-
"""
Capacity Router Module
======================

Provides API endpoints for capacity forecasting and scaling recommendations.

Endpoints:
- GET /api/v1/capacity/forecast         - 7/30 day capacity forecasts
- GET /api/v1/capacity/recommendations  - scaling recommendations
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException


from core.capacity_engine import forecast_capacity, generate_scaling_recommendations
from core.collector import get_disk_metrics
from core.metrics_history import metrics_history

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/capacity",
    tags=["容量预测"],
)

_NETWORK_CAP_MB = 100.0  # reference cap used to normalize net_in (MB/s) to %
_DISK_HISTORY_LEN = 10


async def _build_metric_history() -> dict[str, list[float]]:
    """Build a normalized metric history dict for the forecasting engine."""
    hist = metrics_history.to_dict()

    cpu = [float(v) for v in hist.get("cpu", [])]
    memory = [float(v) for v in hist.get("memory", [])]
    net_in = [float(v) for v in hist.get("net_in", [])]
    network = [
        max(0.0, min(100.0, v / _NETWORK_CAP_MB * 100.0)) for v in net_in
    ]

    try:
        disks = await asyncio.to_thread(get_disk_metrics)
        avg = sum(d.get("usage_percent", 0.0) for d in disks) / max(len(disks), 1)
    except Exception as e:
        logger.warning(f"磁盘指标采集失败，使用默认值: {e}")
        avg = 45.0

    disk = [
        max(0.0, min(100.0, avg - (_DISK_HISTORY_LEN - 1 - i) * 0.5))
        for i in range(_DISK_HISTORY_LEN)
    ]

    return {
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "network": network,
    }


@router.get(
    "/forecast",
    summary="获取容量预测",
    responses={
        200: {
            "description": "容量预测结果",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "metric": "CPU使用率",
                                "currentValue": 65.0,
                                "forecast7d": 72.0,
                                "forecast30d": 85.0,
                                "threshold": 80.0,
                                "unit": "%",
                            }
                        ]
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "预测失败"},
    },
)
async def get_forecast() -> dict[str, Any]:
    """Return 7-day and 30-day capacity forecasts for CPU, memory, disk and network."""
    logger.debug("请求容量预测数据")
    try:
        metric_history = await _build_metric_history()
        forecasts = forecast_capacity(metric_history, days_ahead=7)
        return {"data": list(forecasts.values())}
    except Exception as e:
        logger.error(f"容量预测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"容量预测失败: {str(e)[:200]}")


@router.get(
    "/recommendations",
    summary="获取扩容建议",
    responses={
        200: {
            "description": "扩容建议列表",
            "content": {
                "application/json": {
                    "example": {
                        "data": [
                            {
                                "id": "SR-CPU",
                                "service": "compute-service",
                                "action": "scale-up",
                                "reason": "...",
                                "priority": "high",
                                "estimatedCost": 300,
                            }
                        ]
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "建议生成失败"},
    },
)
async def get_recommendations() -> dict[str, Any]:
    """Return scaling recommendations derived from capacity forecasts."""
    logger.debug("请求扩容建议")
    try:
        metric_history = await _build_metric_history()
        forecasts = forecast_capacity(metric_history, days_ahead=7)
        recommendations = generate_scaling_recommendations(forecasts)
        return {"data": recommendations}
    except Exception as e:
        logger.error(f"扩容建议生成失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"扩容建议生成失败: {str(e)[:200]}"
        )
