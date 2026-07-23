# -*- coding: utf-8 -*-
"""
API Performance Optimization Router
Provides API endpoints for API performance monitoring and optimization
"""

from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

router = APIRouter(prefix="/api/api-performance", tags=["API Performance"])


@router.get(
    "/status",
    summary="获取API性能状态",
    responses={
        200: {
            "description": "性能状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "avg_response_time": 150,
                            "total_requests": 10000,
                            "error_rate": 0.01,
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取性能状态失败"},
    },
)
async def get_performance_status() -> dict[str, Any]:
    """
    Get current API performance status

    Returns:
        Current performance status
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        status = optimizer.get_performance_summary()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting performance status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/response-times",
    summary="分析API响应时间分布",
    responses={
        200: {
            "description": "响应时间分析",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"p50": 120, "p95": 250, "p99": 500, "avg": 150},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "分析失败"},
    },
)
async def analyze_response_times() -> dict[str, Any]:
    """
    Analyze API response time distribution

    Returns:
        Response time analysis
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        analysis = optimizer.analyze_response_times()
        return {"status": "success", "data": analysis, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error analyzing response times: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/slow-apis",
    summary="识别慢API",
    responses={
        200: {
            "description": "慢API列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": [
                            {
                                "endpoint": "/api/analyze",
                                "avg_response_time": 500,
                                "call_count": 100,
                            }
                        ],
                        "total_slow_apis": 5,
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "识别失败"},
    },
)
async def identify_slow_apis(
    limit: int = Query(10, ge=1, le=50, description="Maximum number of APIs to return")
) -> dict[str, Any]:
    """
    Identify slow APIs

    Args:
        limit: Maximum number of APIs to return

    Returns:
        List of slow APIs
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        slow_apis = optimizer.identify_slow_apis()
        return {
            "status": "success",
            "data": slow_apis[:limit],
            "total_slow_apis": len(slow_apis),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error identifying slow APIs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/optimize",
    summary="生成API优化建议",
    responses={
        200: {
            "description": "优化建议列表",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": [
                            {
                                "optimization_id": "opt-1",
                                "endpoint": "/api/analyze",
                                "strategy": "cache",
                                "priority": "high",
                                "expected_improvement": 0.3,
                            }
                        ],
                        "total_optimizations": 5,
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "生成失败"},
    },
)
async def generate_optimizations() -> dict[str, Any]:
    """
    Generate API optimization recommendations

    Returns:
        Optimization recommendations
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        optimizations = optimizer.generate_optimizations()

        optimization_list = [
            {
                "optimization_id": opt.optimization_id,
                "endpoint": opt.endpoint,
                "strategy": opt.strategy.value,
                "priority": opt.priority.value,
                "expected_improvement": opt.expected_improvement,
                "description": opt.description,
            }
            for opt in optimizations
        ]

        return {
            "status": "success",
            "data": optimization_list,
            "total_optimizations": len(optimization_list),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error generating optimizations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cache/setup",
    summary="设置端点缓存",
    responses={
        200: {
            "description": "缓存设置成功",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "message": "Cache setup for endpoint: /api/analyze",
                        "ttl_seconds": 300,
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "设置失败"},
    },
)
async def setup_endpoint_cache(
    endpoint: str, ttl_seconds: int = Query(300, ge=60, le=3600, description="Cache TTL in seconds")
) -> dict[str, Any]:
    """
    Setup response cache for an endpoint

    Args:
        endpoint: API endpoint
        ttl_seconds: Cache TTL in seconds

    Returns:
        Cache setup result
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        optimizer.setup_response_cache(endpoint, ttl_seconds)

        return {
            "status": "success",
            "message": f"Cache setup for endpoint: {endpoint}",
            "ttl_seconds": ttl_seconds,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error setting up cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete(
    "/cache",
    summary="失效缓存",
    responses={
        200: {"description": "缓存失效成功"},
        500: {"description": "失效失败"},
    },
)
async def invalidate_cache(
    endpoint: Optional[str] = Query(None, description="Specific endpoint to invalidate")
) -> dict[str, Any]:
    """
    Invalidate cache

    Args:
        endpoint: Specific endpoint to invalidate, or None for all

    Returns:
        Cache invalidation result
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        optimizer.invalidate_cache(endpoint)

        return {
            "status": "success",
            "message": f"Cache invalidated for: {endpoint or 'all endpoints'}",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/record",
    summary="记录API调用性能指标",
    responses={
        200: {"description": "记录成功"},
        500: {"description": "记录失败"},
    },
)
async def record_api_call(
    endpoint: str, method: str, response_time_ms: float, status_code: int, cache_hit: bool = False
) -> dict[str, Any]:
    """
    Record API call performance metric

    Args:
        endpoint: API endpoint
        method: HTTP method
        response_time_ms: Response time in milliseconds
        status_code: HTTP status code
        cache_hit: Whether response was served from cache

    Returns:
        Recording result
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        optimizer.record_api_call(
            endpoint=endpoint,
            method=method,
            response_time_ms=response_time_ms,
            status_code=status_code,
            cache_hit=cache_hit,
        )

        return {
            "status": "success",
            "message": "API call recorded",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error recording API call: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/rate-limit/setup",
    summary="设置速率限制",
    responses={
        200: {"description": "速率限制设置成功"},
        500: {"description": "设置失败"},
    },
)
async def setup_rate_limit(
    endpoint: str, requests_per_minute: int, burst_size: Optional[int] = None
) -> dict[str, Any]:
    """
    Setup rate limit for an endpoint

    Args:
        endpoint: API endpoint
        requests_per_minute: Maximum requests per minute
        burst_size: Burst size (optional)

    Returns:
        Rate limit setup result
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        optimizer.setup_rate_limit(endpoint, requests_per_minute, burst_size)

        return {
            "status": "success",
            "message": f"Rate limit setup for {endpoint}: {requests_per_minute} req/min",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error setting up rate limit: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/throughput",
    summary="获取吞吐量指标",
    responses={
        200: {"description": "吞吐量指标"},
        500: {"description": "获取失败"},
    },
)
async def get_throughput_metrics() -> dict[str, Any]:
    """
    Get throughput metrics

    Returns:
        Throughput metrics
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        metrics = optimizer.get_throughput_metrics()

        return {"status": "success", "data": metrics, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting throughput metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/resources",
    summary="获取资源使用情况",
    responses={
        200: {"description": "资源使用指标"},
        500: {"description": "获取失败"},
    },
)
async def get_resource_usage() -> dict[str, Any]:
    """
    Get current resource usage

    Returns:
        Resource usage metrics
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        resource_usage = optimizer.monitor_resource_usage()

        return {
            "status": "success",
            "data": resource_usage,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error getting resource usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/resource-limits/setup",
    summary="设置资源限制",
    responses={
        200: {"description": "资源限制设置成功"},
        500: {"description": "设置失败"},
    },
)
async def setup_resource_limits(
    max_memory_mb: float, max_cpu_percent: float, max_connections: int
) -> dict[str, Any]:
    """
    Setup resource limits

    Args:
        max_memory_mb: Maximum memory usage in MB
        max_cpu_percent: Maximum CPU usage percentage
        max_connections: Maximum active connections

    Returns:
        Resource limits setup result
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        optimizer.setup_resource_limits(max_memory_mb, max_cpu_percent, max_connections)

        return {
            "status": "success",
            "message": (
                f"Resource limits setup: memory={max_memory_mb}MB, "
                f"cpu={max_cpu_percent}%, connections={max_connections}"
            ),
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error setting up resource limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/resource-limits/check",
    summary="检查资源限制",
    responses={
        200: {"description": "资源限制检查结果"},
        500: {"description": "检查失败"},
    },
)
async def check_resource_limits() -> dict[str, Any]:
    """
    Check if current resource usage is within limits

    Returns:
        Resource limit check results
    """
    try:
        from core.api_performance_optimizer import get_api_performance_optimizer

        optimizer = get_api_performance_optimizer()
        limit_checks = optimizer.check_resource_limits()

        return {
            "status": "success",
            "data": limit_checks,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error checking resource limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))
