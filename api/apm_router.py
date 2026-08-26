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

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
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


@router.get(
    "/traces",
    summary="获取性能追踪数据",
    responses={
        200: {
            "description": "性能追踪数据",
            "content": {
                "application/json": {
                    "example": {
                        "traces": [
                            {
                                "trace_id": "trace-123",
                                "span_id": "span-456",
                                "parent_span_id": "span-789",
                                "operation_name": "GET /api/v1/alerts",
                                "service_name": "aiops-agent",
                                "start_time": "2026-06-12T00:00:00Z",
                                "duration_ms": 150,
                                "status": "success",
                                "tags": {"http.method": "GET", "http.status_code": "200"},
                                "logs": [],
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "page_size": 20,
                    }
                }
            },
        },
        500: {"description": "获取性能追踪数据失败"},
    },
)
async def get_traces(
    service_name: Optional[str] = Query(None, description="服务名称过滤"),
    operation_name: Optional[str] = Query(None, description="操作名称过滤"),
    min_duration: Optional[int] = Query(None, description="最小持续时间（毫秒）"),
    max_duration: Optional[int] = Query(None, description="最大持续时间（毫秒）"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
) -> Dict[str, Any]:
    """
    🔧 P1 Enhancement: 获取性能追踪数据

    提供应用性能追踪数据，包括：
    - 追踪ID
    - 跨度ID
    - 操作名称
    - 服务名称
    - 持续时间
    - 状态
    - 标签
    - 日志

    Args:
        service_name: 服务名称过滤
        operation_name: 操作名称过滤
        min_duration: 最小持续时间（毫秒）
        max_duration: 最大持续时间（毫秒）
        page: 页码
        page_size: 每页数量

    Returns:
        追踪数据字典
    """
    try:
        # 获取追踪数据
        traces_data = telemetry.get_traces(
            service_name=service_name,
            operation_name=operation_name,
            min_duration=min_duration,
            max_duration=max_duration,
            page=page,
            page_size=page_size,
        )

        return {
            "traces": traces_data.get("traces", []),
            "total": traces_data.get("total", 0),
            "page": page,
            "page_size": page_size,
        }
    except Exception as e:
        logger.error(f"获取性能追踪数据失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取性能追踪数据失败: {str(e)[:200]}")
