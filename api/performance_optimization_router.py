# -*- coding: utf-8 -*-
"""
Performance Optimization Router Module
====================================

Provides API endpoints for performance optimization configuration.
Supports caching, connection pooling, query optimization, and resource management.

Endpoints:
- GET /api/v1/performance/config - Get performance configuration
- PUT /api/v1/performance/config - Update performance configuration
- GET /api/v1/performance/cache-config - Get cache configuration
- PUT /api/v1/performance/cache-config - Update cache configuration
- GET /api/v1/performance/database-config - Get database configuration
- PUT /api/v1/performance/database-config - Update database configuration
- GET /api/v1/performance/resource-limits - Get resource limits
- PUT /api/v1/performance/resource-limits - Update resource limits
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.backend_requirements import requires_backend

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/performance", tags=["性能优化"])


# ============================================================================
# Pydantic Models
# ============================================================================


class PerformanceConfig(BaseModel):
    """性能配置模型"""

    enable_caching: bool = Field(True, description="是否启用缓存")
    enable_query_optimization: bool = Field(True, description="是否启用查询优化")
    enable_connection_pooling: bool = Field(True, description="是否启用连接池")
    enable_async_operations: bool = Field(True, description="是否启用异步操作")
    max_concurrent_requests: int = Field(100, description="最大并发请求数")
    request_timeout: int = Field(30, description="请求超时时间（秒）")


class CacheConfig(BaseModel):
    """缓存配置模型"""

    enabled: bool = Field(True, description="是否启用缓存")
    backend: str = Field("redis", description="缓存后端")
    ttl_seconds: int = Field(3600, description="缓存过期时间（秒）")
    max_memory_mb: int = Field(1024, description="最大内存使用（MB）")
    eviction_policy: str = Field("lru", description="淘汰策略")
    enable_compression: bool = Field(True, description="是否启用压缩")


class DatabaseConfig(BaseModel):
    """数据库配置模型"""

    pool_size: int = Field(10, description="连接池大小")
    max_overflow: int = Field(20, description="最大溢出连接数")
    pool_timeout: int = Field(30, description="连接池超时（秒）")
    pool_recycle: int = Field(3600, description="连接回收时间（秒）")
    enable_query_cache: bool = Field(True, description="是否启用查询缓存")
    enable_statement_cache: bool = Field(True, description="是否启用语句缓存")
    max_query_cache_size: int = Field(1000, description="最大查询缓存大小")


class ResourceLimits(BaseModel):
    """资源限制配置模型"""

    max_memory_mb: int = Field(4096, description="最大内存使用（MB）")
    max_cpu_percent: int = Field(80, description="最大CPU使用率")
    max_disk_usage_percent: int = Field(90, description="最大磁盘使用率")
    max_open_files: int = Field(10000, description="最大打开文件数")
    max_threads: int = Field(100, description="最大线程数")
    enable_auto_scaling: bool = Field(False, description="是否启用自动扩缩容")


# ============================================================================
# In-Memory Configuration Storage
# ============================================================================

_performance_config = {
    "enable_caching": True,
    "enable_query_optimization": True,
    "enable_connection_pooling": True,
    "enable_async_operations": True,
    "max_concurrent_requests": 100,
    "request_timeout": 30,
}

_cache_config = {
    "enabled": True,
    "backend": "redis",
    "ttl_seconds": 3600,
    "max_memory_mb": 1024,
    "eviction_policy": "lru",
    "enable_compression": True,
}

_database_config = {
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "enable_query_cache": True,
    "enable_statement_cache": True,
    "max_query_cache_size": 1000,
}

_resource_limits = {
    "max_memory_mb": 4096,
    "max_cpu_percent": 80,
    "max_disk_usage_percent": 90,
    "max_open_files": 10000,
    "max_threads": 100,
    "enable_auto_scaling": False,
}


# ============================================================================
# Real metric collection
# ============================================================================


def _collect_status() -> Dict[str, Any]:
    """Collect real runtime performance status (psutil + pool + exporters)."""
    import psutil

    vm = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    process = psutil.Process()

    pool_size = active_connections = max_overflow = None
    try:
        from core.database import engine

        pool = engine.pool
        pool_size = pool.size() if hasattr(pool, "size") else None
        active_connections = pool.checkedout() if hasattr(pool, "checkedout") else None
        max_overflow = _database_config.get("max_overflow")
    except Exception as exc:  # noqa: BLE001 - pool introspection is best-effort
        logger.warning(f"Failed to read DB pool stats: {exc}")

    avg_ms = None
    error_rate = 0.0
    try:
        from api.monitoring_advanced_router import _collect_api_telemetry

        _, total_requests, total_errors, avg_ms = _collect_api_telemetry(None)
        error_rate = round(total_errors / total_requests, 4) if total_requests else 0.0
    except Exception as exc:  # noqa: BLE001 - telemetry is best-effort
        logger.warning(f"Failed to read API telemetry: {exc}")

    return {
        "caching": {
            "enabled": _cache_config.get("enabled", False),
            "backend": _cache_config.get("backend", "unknown"),
            "max_memory_mb": _cache_config.get("max_memory_mb", 1024),
        },
        "database": {
            "pool_size": pool_size,
            "active_connections": active_connections,
            "max_overflow": max_overflow,
        },
        "resources": {
            "memory_usage_mb": round(vm.used / (1024 ** 2), 2),
            "max_memory_mb": round(vm.total / (1024 ** 2), 2),
            "cpu_usage_percent": psutil.cpu_percent(interval=None),
            "disk_usage_percent": disk.percent,
            "max_disk_usage_percent": _resource_limits.get("max_disk_usage_percent", 90),
            "open_files": len(process.open_files()),
            "active_threads": process.num_threads(),
            "max_threads": _resource_limits.get("max_threads", 100),
        },
        "performance_metrics": {
            "avg_response_time_ms": avg_ms,
            "error_rate": error_rate,
        },
    }


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/config", summary="获取性能配置")
async def get_performance_config() -> Dict[str, Any]:
    """获取性能配置"""
    return _performance_config.copy()


@router.put("/config", summary="更新性能配置")
async def update_performance_config(config: PerformanceConfig) -> Dict[str, Any]:
    """更新性能配置"""
    global _performance_config
    _performance_config = config.dict()
    return {"status": "success", "config": _performance_config}


@router.get("/cache-config", summary="获取缓存配置")
async def get_cache_config() -> Dict[str, Any]:
    """获取缓存配置"""
    return _cache_config.copy()


@router.put("/cache-config", summary="更新缓存配置")
async def update_cache_config(config: CacheConfig) -> Dict[str, Any]:
    """更新缓存配置"""
    global _cache_config
    _cache_config = config.dict()
    return {"status": "success", "config": _cache_config}


@router.get("/database-config", summary="获取数据库配置")
async def get_database_config() -> Dict[str, Any]:
    """获取数据库配置"""
    return _database_config.copy()


@router.put("/database-config", summary="更新数据库配置")
async def update_database_config(config: DatabaseConfig) -> Dict[str, Any]:
    """更新数据库配置"""
    global _database_config
    _database_config = config.dict()
    return {"status": "success", "config": _database_config}


@router.get("/resource-limits", summary="获取资源限制")
async def get_resource_limits() -> Dict[str, Any]:
    """获取资源限制"""
    return _resource_limits.copy()


@router.put("/resource-limits", summary="更新资源限制")
async def update_resource_limits(config: ResourceLimits) -> Dict[str, Any]:
    """更新资源限制"""
    global _resource_limits
    _resource_limits = config.dict()
    return {"status": "success", "config": _resource_limits}


@router.get("/status", summary="获取性能状态")
async def get_performance_status() -> Dict[str, Any]:
    """获取性能状态"""
    try:
        status = _collect_status()
        status["overall_status"] = "healthy"
        return status
    except Exception as e:
        logger.error(f"获取性能状态失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取性能状态失败: {str(e)[:200]}")


@router.post("/optimize", summary="执行性能优化")
async def optimize_performance() -> Dict[str, Any]:
    """执行性能优化"""
    try:
        # No performance-optimizer backend is wired here; refuse to fabricate
        # the list of applied optimisations.
        requires_backend(
            "performance-optimizer",
            capability="apply performance optimization",
            reason="No performance-optimizer backend is configured in this deployment",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行性能优化失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"执行性能优化失败: {str(e)[:200]}")


@router.get("/recommendations", summary="获取性能优化建议")
async def get_performance_recommendations() -> Dict[str, Any]:
    """获取性能优化建议"""
    try:
        status = _collect_status()
        resources = status["resources"]
        recommendations = []

        mem_pct = (
            resources["memory_usage_mb"] / resources["max_memory_mb"] * 100
            if resources["max_memory_mb"]
            else 0.0
        )
        if mem_pct >= 80:
            recommendations.append(
                {
                    "category": "resource",
                    "priority": "high",
                    "title": "内存使用率偏高",
                    "description": f"内存使用率 {mem_pct:.1f}%，建议扩容或排查内存泄漏",
                }
            )
        if resources["disk_usage_percent"] >= 85:
            recommendations.append(
                {
                    "category": "resource",
                    "priority": "high",
                    "title": "磁盘使用率偏高",
                    "description": f"磁盘使用率 {resources['disk_usage_percent']:.1f}%，建议清理",
                }
            )
        if status["database"]["active_connections"] is not None and status["database"]["pool_size"]:
            ratio = status["database"]["active_connections"] / status["database"]["pool_size"]
            if ratio >= 0.8:
                recommendations.append(
                    {
                        "category": "database",
                        "priority": "medium",
                        "title": "连接池接近饱和",
                        "description": (
                            f"活跃连接 {status['database']['active_connections']}/"
                            f"{status['database']['pool_size']}，建议扩大连接池"
                        ),
                    }
                )
        if status["performance_metrics"]["error_rate"] and status["performance_metrics"]["error_rate"] > 0.01:
            recommendations.append(
                {
                    "category": "api",
                    "priority": "high",
                    "title": "API 错误率偏高",
                    "description": f"错误率 {status['performance_metrics']['error_rate']:.2%}，建议排查",
                }
            )

        return {"recommendations": recommendations}
    except Exception as e:
        logger.error(f"获取性能优化建议失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取性能优化建议失败: {str(e)[:200]}")
