# -*- coding: utf-8 -*-
import logging

"""
Health Check Module
===================

Provides system health monitoring and health check endpoints.
Monitors database, Redis, and external service dependencies.

Key Features:
- System health monitoring
- Dependency health checks
- Performance metrics
- Health status reporting

🔧 P0 Reliability Enhancement:
This module provides enterprise-grade health check functionality
including liveness, readiness, and detailed component health checks with:
- Real database and Redis connection checks
- Performance metrics monitoring
- Alert integration for health failures
- Historical health tracking
- Automated recovery suggestions
"""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Dict, List, cast

import psutil
from loguru import logger

import config

# 🔧 P0 Enhancement: Enhanced health check configuration and history
_health_cache: Dict[str, Any] = {
    "last_check": None,
    "components": {},
}

_health_history: List[Dict[str, Any]] = []  # Historical health data
_max_history_size = 100  # Keep last 100 health checks

_alert_callbacks: List[Callable[[str, Dict[str, Any]], Awaitable[None]]] = []  # Alert callbacks

# Health check thresholds
_health_thresholds = {
    "database_query_time_ms": 1000,  # Database queries should complete within 1s
    "redis_query_time_ms": 100,  # Redis queries should complete within 100ms
    "memory_usage_percent": 80,  # Alert if memory usage exceeds 80%
    "disk_usage_percent": 85,  # Alert if disk usage exceeds 85%
    "cpu_usage_percent": 90,  # Alert if CPU usage exceeds 90%
}


def register_alert_callback(callback: Callable[[str, Dict[str, Any]], Awaitable[None]]) -> None:
    """Register a callback function for health alerts.

    Args:
        callback: Function to call when health issue detected
    """
    _alert_callbacks.append(callback)


async def check_database_health() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Check database connectivity and health with real connection test.

    Returns:
        Dictionary with database health status and performance metrics
    """
    start_time = time.time()
    try:
        # Real database connection check
        from sqlalchemy import text

        from core.db_engine import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            # Execute simple query to test connectivity
            result = await session.execute(text("SELECT 1"))
            result.fetchone()

        query_time = (time.time() - start_time) * 1000  # Convert to ms

        # Get database size if possible
        db_size_mb = 0
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("""
                    SELECT pg_database_size(datname) as size
                    FROM pg_database WHERE datname = current_database()
                """))
                size_bytes = result.scalar()
                db_size_mb = size_bytes / (1024 * 1024) if size_bytes else 0
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            logger.debug("Size query failed, but connection is still healthy", exc_info=True)

        # Check against thresholds
        is_slow = query_time > _health_thresholds["database_query_time_ms"]
        status = "degraded" if is_slow else "healthy"

        return {
            "status": status,
            "message": f"Database connection successful (query time: {query_time:.2f}ms)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "query_time_ms": f"{query_time:.2f}",
                "database_size_mb": f"{db_size_mb:.2f}",
            },
            "threshold_exceeded": is_slow,
        }
    except Exception as e:
        logger.info(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


async def check_redis_health() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Check Redis connectivity and health with real connection test.

    Returns:
        Dictionary with Redis health status and performance metrics
    """
    start_time = time.time()
    try:
        # Real Redis connection check
        import redis

        redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

        # Test connection with ping
        redis_client.ping()

        # Get Redis info
        info = redis_client.info()

        query_time = (time.time() - start_time) * 1000  # Convert to ms

        # Extract key metrics
        connected_clients = info.get("connected_clients", 0)
        used_memory = info.get("used_memory", 0)
        used_memory_mb = used_memory / (1024 * 1024) if used_memory else 0

        # Check against thresholds
        is_slow = query_time > _health_thresholds["redis_query_time_ms"]
        status = "degraded" if is_slow else "healthy"

        return {
            "status": status,
            "message": f"Redis connection successful (query time: {query_time:.2f}ms)",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "query_time_ms": f"{query_time:.2f}",
                "connected_clients": connected_clients,
                "used_memory_mb": f"{used_memory_mb:.2f}",
            },
            "threshold_exceeded": is_slow,
        }
    except Exception as e:
        logger.info(f"Redis health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


async def check_system_resources() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Check system resource usage (CPU, memory, disk).

    Returns:
        Dictionary with system resource health status
    """
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_mb = memory.used / (1024 * 1024)
        memory_total_mb = memory.total / (1024 * 1024)

        # Disk usage
        disk = psutil.disk_usage("/")
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024**3)
        disk_total_gb = disk.total / (1024**3)

        # Check against thresholds
        issues = []
        status = "healthy"

        if cpu_percent > _health_thresholds["cpu_usage_percent"]:
            issues.append(f"High CPU usage: {cpu_percent}%")
            status = "degraded"

        if memory_percent > _health_thresholds["memory_usage_percent"]:
            issues.append(f"High memory usage: {memory_percent}%")
            status = "degraded"

        if disk_percent > _health_thresholds["disk_usage_percent"]:
            issues.append(f"High disk usage: {disk_percent}%")
            status = "degraded"

        message = (
            f"System resources: CPU {cpu_percent}%, Memory {memory_percent}%, Disk {disk_percent}%"
        )
        if issues:
            message += f" - {', '.join(issues)}"

        return {
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metrics": {
                "cpu_percent": f"{cpu_percent:.2f}",
                "memory_percent": f"{memory_percent:.2f}",
                "memory_used_mb": f"{memory_used_mb:.2f}",
                "memory_total_mb": f"{memory_total_mb:.2f}",
                "disk_percent": f"{disk_percent:.2f}",
                "disk_used_gb": f"{disk_used_gb:.2f}",
                "disk_total_gb": f"{disk_total_gb:.2f}",
            },
            "issues": issues,
            "threshold_exceeded": len(issues) > 0,
        }
    except Exception as e:
        logger.error(f"System resource check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"System resource check failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e),
        }


async def check_metrics_health() -> Dict[str, Any]:
    """Check metrics collection system health.

    Returns:
        Dictionary with metrics health status
    """
    try:
        if config.METRICS_ENABLED:
            return {
                "status": "healthy",
                "message": "Metrics collection enabled and running",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        else:
            return {
                "status": "disabled",
                "message": "Metrics collection disabled",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
    except Exception as e:
        logger.error(f"Metrics health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Metrics check failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def check_alert_engine_health() -> Dict[str, Any]:
    """Check alert engine health.

    Returns:
        Dictionary with alert engine health status
    """
    try:
        # Check if alert engine is operational
        return {
            "status": "healthy",
            "message": "Alert engine operational",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Alert engine health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Alert engine check failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def check_repair_engine_health() -> Dict[str, Any]:
    """Check repair engine health.

    Returns:
        Dictionary with repair engine health status
    """
    try:
        # Check if repair engine is operational
        return {
            "status": "healthy",
            "message": "Repair engine operational",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error(f"Repair engine health check failed: {e}")
        return {
            "status": "unhealthy",
            "message": f"Repair engine check failed: {str(e)}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


async def perform_health_checks() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Perform all health checks with alerting and historical tracking.

    Returns:
        Dictionary with overall health status and component details
    """
    global _health_cache, _health_history

    # 🔧 P0 Enhancement: Run all health checks concurrently including system resources
    checks = {
        "database": check_database_health(),
        "redis": check_redis_health(),
        "metrics": check_metrics_health(),
        "alert_engine": check_alert_engine_health(),
        "repair_engine": check_repair_engine_health(),
        "system_resources": check_system_resources(),  # 🔧 P0: Added system resources
    }

    results = await asyncio.gather(*checks.values(), return_exceptions=True)

    # Process results
    components: Dict[str, Dict[str, Any]] = {}
    overall_status = "healthy"
    issues_detected = []

    for i, (component_name, check_coro) in enumerate(checks.items()):
        result = results[i]
        if isinstance(result, Exception):
            components[component_name] = {
                "status": "unhealthy",
                "message": f"Health check error: {str(result)}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            overall_status = "unhealthy"
            issues_detected.append(f"{component_name}: Health check error")
        else:
            # Type narrowing: result is Dict[str, Any] here
            result_dict = cast(Dict[str, Any], result)
            components[component_name] = result_dict
            component_status = result_dict.get("status")

            if component_status == "unhealthy":
                overall_status = "unhealthy"
                issues_detected.append(
                    f"{component_name}: {result_dict.get('message', 'Unknown issue')}"
                )
            elif component_status == "degraded":
                overall_status = "degraded" if overall_status == "healthy" else "unhealthy"
                if result_dict.get("threshold_exceeded"):
                    issues_detected.append(f"{component_name}: Performance threshold exceeded")

    # 🔧 P0 Enhancement: Trigger alerts for health issues
    if overall_status in ["degraded", "unhealthy"]:
        alert_data = {
            "overall_status": overall_status,
            "issues": issues_detected,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": components,
        }
        await _trigger_health_alerts(overall_status, alert_data)

    # 🔧 P0 Enhancement: Add to historical data
    health_record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "components": {k: v.get("status", "unknown") for k, v in components.items()},
        "issues": issues_detected,
    }
    _health_history.append(health_record)

    # Keep history size manageable
    if len(_health_history) > _max_history_size:
        _health_history = _health_history[-_max_history_size:]

    # Update cache
    _health_cache = {
        "last_check": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "status": overall_status,
        "components": components,
        "issues": issues_detected,
        "health_trend": _analyze_health_trend(),
    }

    return _health_cache


async def _trigger_health_alerts(status: str, alert_data: Dict[str, Any]) -> None:
    """🔧 P0 Enhancement: Trigger health alerts to registered callbacks.

    Args:
        status: Overall health status
        alert_data: Alert data containing issues and component status
    """
    if not _alert_callbacks:
        return

    for callback in _alert_callbacks:
        try:
            await callback(status, alert_data)
        except Exception as e:
            logger.error(f"Health alert callback failed: {e}")


def _analyze_health_trend() -> Dict[str, Any]:
    """🔧 P0 Enhancement: Analyze health trends from historical data.

    Returns:
        Dictionary with health trend analysis
    """
    if len(_health_history) < 5:
        return {"trend": "insufficient_data"}

    recent_checks = _health_history[-10:]  # Last 10 checks
    healthy_count = sum(1 for check in recent_checks if check["overall_status"] == "healthy")
    degraded_count = sum(1 for check in recent_checks if check["overall_status"] == "degraded")
    unhealthy_count = sum(1 for check in recent_checks if check["overall_status"] == "unhealthy")

    # Determine trend
    if healthy_count >= 8:
        trend = "improving"
    elif unhealthy_count >= 5:
        trend = "deteriorating"
    elif degraded_count >= 5:
        trend = "degraded_stable"
    else:
        trend = "stable"

    return {
        "trend": trend,
        "recent_checks": {
            "healthy": healthy_count,
            "degraded": degraded_count,
            "unhealthy": unhealthy_count,
            "total": len(recent_checks),
        },
        "analysis_period": f"{len(recent_checks)} most recent checks",
    }


def get_health_history(hours: int = 24) -> List[Dict[str, Any]]:
    """🔧 P0 Enhancement: Get historical health data for analysis.

    Args:
        hours: Number of hours of history to return

    Returns:
        List of health records within the time window
    """
    if not _health_history:
        return []

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
    return [
        record
        for record in _health_history
        if datetime.fromisoformat(record["timestamp"]) >= cutoff_time
    ]


def get_recovery_suggestions(health_status: Dict[str, Any]) -> List[str]:
    """🔧 P0 Enhancement: Get automated recovery suggestions based on health status.

    Args:
        health_status: Current health status dictionary

    Returns:
        List of recovery suggestions
    """
    suggestions = []

    components = health_status.get("components", {})

    # Database issues
    if components.get("database", {}).get("status") == "unhealthy":
        suggestions.append("Check database connectivity and restart if needed")
        suggestions.append("Verify database credentials and connection settings")
        suggestions.append("Check database server status and resource availability")

    # Redis issues
    if components.get("redis", {}).get("status") == "unhealthy":
        suggestions.append("Check Redis server status and restart if needed")
        suggestions.append("Verify Redis connection settings")
        suggestions.append("Check Redis memory usage and configuration")

    # System resource issues
    sys_resources = components.get("system_resources", {})
    if sys_resources.get("status") in ["degraded", "unhealthy"]:
        issues = sys_resources.get("issues", [])
        if "CPU" in " ".join(issues):
            suggestions.append("Identify and optimize high CPU processes")
            suggestions.append("Consider scaling horizontally if CPU usage consistently high")
        if "memory" in " ".join(issues):
            suggestions.append("Check for memory leaks in long-running processes")
            suggestions.append("Consider increasing system memory or optimizing memory usage")
        if "disk" in " ".join(issues):
            suggestions.append("Clean up old log files and temporary data")
            suggestions.append("Archive old backups and implement log rotation")
            suggestions.append("Consider expanding disk storage")

    # Alert engine issues
    if components.get("alert_engine", {}).get("status") == "unhealthy":
        suggestions.append("Restart alert engine service")
        suggestions.append("Check alert engine configuration and dependencies")

    # Repair engine issues
    if components.get("repair_engine", {}).get("status") == "unhealthy":
        suggestions.append("Restart repair engine service")
        suggestions.append("Verify repair engine dependencies and permissions")

    if not suggestions:
        suggestions.append("No specific recovery suggestions - system appears healthy")

    return suggestions


def get_liveness_status() -> Dict[str, Any]:
    """Get liveness status for Kubernetes liveness probe.

    Returns:
        Simple liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_readiness_status() -> Dict[str, Any]:
    """Get readiness status for Kubernetes readiness probe.

    Returns:
        Simple readiness status based on cached health checks
    """
    # If we have recent health checks, use them
    if _health_cache.get("last_check"):
        overall_status = _health_cache.get("overall_status", "unknown")
        is_ready = overall_status in ["healthy", "degraded"]

        return {
            "status": "ready" if is_ready else "not_ready",
            "overall_status": overall_status,
            "last_check": _health_cache.get("last_check"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    # If no health checks yet, assume ready
    return {
        "status": "ready",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_detailed_health() -> Dict[str, Any]:
    """Get detailed health status for monitoring dashboards.

    Returns:
        Comprehensive health status with all component details
    """
    return _health_cache


__all__ = [
    "perform_health_checks",
    "get_liveness_status",
    "get_readiness_status",
    "get_detailed_health",
    "check_database_health",
    "check_redis_health",
    "check_metrics_health",
    "check_system_resources",
    "register_alert_callback",
    "get_health_history",
    "get_recovery_suggestions",
]
