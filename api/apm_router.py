# -*- coding: utf-8 -*-
"""
APM Router Module
=================

Provides API endpoints for Application Performance Monitoring.
Supports real-time performance metrics and APM data retrieval.

Endpoints:
- GET /api/v1/apm/metrics - Get APM metrics
- GET /api/v1/apm/health - Get APM health status
- GET /api/v1/apm/traces - Get performance traces

🔧 P1 Enhancement: APM and observability enhancements
Provides APM metrics and performance monitoring endpoints
"""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from loguru import logger

from core import telemetry_core as telemetry

router = APIRouter(prefix="/api/v1/apm", tags=["APM监控"])


@router.get(
    "/metrics",
    summary="APM性能指标",
    responses={
        200: {
            "description": "APM性能指标",
            "content": {
                "application/json": {
                    "example": {
                        "apm_metrics": {
                            "request_count": 1000,
                            "error_rate": 0.01,
                            "slow_request_rate": 0.05,
                        },
                        "system_resources": {"cpu": 45.2, "memory": 68.3},
                        "overall_status": "healthy",
                        "timestamp": "2026-06-12T00:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取APM指标失败"},
    },
)
async def get_apm_metrics() -> Dict[str, Any]:
    """
    🔧 P1 Enhancement: 获取APM性能指标

    提供应用性能监控指标，包括：
    - 请求计数
    - 错误率
    - 慢请求率
    - 系统资源使用情况

    Returns:
        APM指标字典
    """
    try:
        from core.health_check import check_system_resources

        # 获取APM指标
        apm_metrics = telemetry.get_apm_metrics()

        # 获取系统资源指标
        system_resources = await check_system_resources()

        return {
            "apm_metrics": apm_metrics,
            "system_resources": system_resources.get("metrics", {}),
            "overall_status": (
                "healthy" if system_resources.get("status") == "healthy" else "degraded"
            ),
            "timestamp": "2026-06-12T00:00:00Z",
        }
    except Exception as e:
        logger.error(f"获取APM指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取APM指标失败: {str(e)[:200]}")


@router.get(
    "/health",
    summary="应用健康状态",
    responses={
        200: {
            "description": "应用健康状态",
            "content": {
                "application/json": {
                    "example": {
                        "application": "aiops-agent",
                        "version": "1.0.0",
                        "health_status": {"status": "healthy", "checks": {}},
                        "timestamp": "2026-06-12T00:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取应用健康状态失败"},
    },
)
async def get_application_health() -> Dict[str, Any]:
    """
    🔧 P1 Enhancement: 获取应用整体健康状态

    Returns:
        应用健康状态字典
    """
    try:
        from core.health_check import perform_health_checks

        health_status = await perform_health_checks()

        return {
            "application": "aiops-agent",
            "version": "1.0.0",
            "health_status": health_status,
            "timestamp": "2026-06-12T00:00:00Z",
        }
    except Exception as e:
        logger.error(f"获取应用健康状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取应用健康状态失败: {str(e)[:200]}")


@router.post(
    "/metrics/reset",
    summary="重置APM指标",
    responses={
        200: {
            "description": "重置成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "APM指标已重置",
                        "timestamp": "2026-06-12T00:00:00Z",
                    }
                }
            },
        },
        500: {"description": "重置APM指标失败"},
    },
)
async def reset_apm_metrics() -> Dict[str, Any]:
    """
    🔧 P1 Enhancement: 重置APM指标计数器

    Returns:
        重置结果
    """
    try:
        telemetry.reset_apm_metrics()

        return {
            "status": "success",
            "message": "APM指标已重置",
            "timestamp": "2026-06-12T00:00:00Z",
        }
    except Exception as e:
        logger.error(f"重置APM指标失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"重置APM指标失败: {str(e)[:200]}")
