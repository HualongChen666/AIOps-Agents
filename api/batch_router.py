# -*- coding: utf-8 -*-
import logging
"""
Batch API Router
批量API路由
"""

from typing import List

from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/batch", tags=["Batch"])


@router.post(
    "/alerts",
    summary="批量获取告警",
    responses={
        200: {
            "description": "批量告警结果",
            "content": {
                "application/json": {
                    "example": {
                        "results": [
                            {"id": "alert-1", "title": "CPU告警", "level": "critical"},
                            {"id": "alert-2", "title": "内存告警", "level": "warning"},
                        ]
                    }
                }
            },
        },
        500: {"description": "批量获取失败"},
    },
)
async def batch_get_alerts(alert_ids: List[str]):
    """批量获取告警"""
    from core.alert_engine import alert_history

    results = []
    for alert_id in alert_ids:
        try:
            # Search in alert_history
            alert = None
            for alert_data in alert_history:
                if alert_data.get("id") == alert_id:
                    alert = alert_data
                    break
            results.append(alert)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            results.append(None)
    return {"results": results}


@router.post(
    "/metrics",
    summary="批量获取指标",
    responses={
        200: {
            "description": "批量指标结果",
            "content": {
                "application/json": {
                    "example": {
                        "results": {
                            "cpu_usage": {"value": 45.2, "unit": "%"},
                            "memory_usage": {"value": 68.3, "unit": "%"},
                        }
                    }
                }
            },
        },
        500: {"description": "批量获取失败"},
    },
)
async def batch_get_metrics(metric_ids: List[str]):
    """批量获取指标"""
    from core.collector import collect_all

    all_metrics = collect_all()
    results = {k: v for k, v in all_metrics.items() if k in metric_ids}
    return {"results": results}