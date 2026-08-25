# -*- coding: utf-8 -*-
"""
Anomaly Router Module
=====================
REST endpoints for Z-score based anomaly detection.

Endpoints:
- GET  /api/v1/anomaly/records      - List detected anomaly records
- GET  /api/v1/anomaly/statistics   - Anomaly counts by metric
- POST /api/v1/anomaly/detect       - Run detection on payload or metrics history
"""

import datetime
import logging
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException

from api.common import handle_service_error, validate_list_length
from core.anomaly_engine import detect_all_anomalies, detect_anomalies
from core.metrics_history import METRICS_HISTORY as metrics_history

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/anomaly",
    tags=["异常检测"],
)


@router.get("/records", summary="获取异常记录列表")
async def get_records() -> list[dict[str, Any]]:
    """返回基于当前指标历史检测出的异常记录。"""
    history = metrics_history.to_dict()
    return detect_all_anomalies(history)


@router.get("/statistics", summary="获取异常统计")
async def get_statistics() -> dict[str, Any]:
    """返回 cpu / memory / net_in 三个指标的异常数量。"""
    history = metrics_history.to_dict()
    counts = {}
    for metric in ("cpu", "memory", "net_in"):
        counts[metric] = len(detect_anomalies(history, metric))
    counts["total"] = sum(counts.values())
    return counts


@router.post("/detect", summary="执行异常检测")
async def detect_endpoint(payload: Optional[dict[str, Any]] = Body(default=None)) -> dict[str, Any]:
    """
    对请求体中的 { metric, values[, timestamps] } 进行异常检测；
    若请求体为空，则使用当前系统指标历史。
    """
    payload = payload or {}
    metric = payload.get("metric")
    values = payload.get("values")

    if metric and values is not None:
        # 🔧 重构:使用公共 validate_list_length 函数
        validated_values = validate_list_length(values, "values")
        timestamps = payload.get("timestamps") or [
            datetime.datetime.now().isoformat() for _ in validated_values
        ]
        history = {metric: validated_values, "timestamps": timestamps}
        anomalies = detect_anomalies(history, metric)
    else:
        history = metrics_history.to_dict()
        anomalies = detect_all_anomalies(history)

    return {"anomalies": anomalies, "count": len(anomalies)}
