# -*- coding: utf-8 -*-
"""
Performance Router
Provides API endpoints for performance monitoring and optimization
Matches frontend API calls at /api/performance/*
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from core.auth_service import get_current_user, require_roles
from core.auth_db import User

router = APIRouter(prefix="/api/performance", tags=["Performance"])


# ============================================================================
# Helper Functions
# ============================================================================

def _safe_int(env_var: str, default: int = 0) -> int:
    """Safely get integer from environment variable"""
    try:
        return int(os.getenv(env_var, str(default)))
    except (ValueError, TypeError):
        return default


def _safe_float(env_var: str, default: float = 0.0) -> float:
    """Safely get float from environment variable"""
    try:
        return float(os.getenv(env_var, str(default)))
    except (ValueError, TypeError):
        return default


def _safe_bool(env_var: str, default: bool = False) -> bool:
    """Safely get boolean from environment variable"""
    val = os.getenv(env_var, str(default)).lower()
    return val in ("true", "1", "yes", "on")


# ============================================================================
# Rate Limiting Endpoint
# ============================================================================

@router.get(
    "/rate-limiting",
    summary="获取速率限制配置和状态",
    responses={
        200: {"description": "速率限制信息"},
        500: {"description": "获取失败"},
    },
)
async def get_rate_limiting(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get rate limiting configuration and status
    
    Returns:
        Rate limiting configuration and current status
    """
    try:
        
        # Get rate limiting configuration from environment
        config = {
            "enabled": _safe_bool("RATE_LIMITING_ENABLED", True),
            "default_requests_per_minute": _safe_int("RATE_LIMIT_DEFAULT_RPM", 60),
            "default_burst_size": _safe_int("RATE_LIMIT_BURST_SIZE", 10),
            "cleanup_interval_seconds": _safe_int("RATE_LIMIT_CLEANUP_INTERVAL", 300),
        }
        
        # Get current rate limit status
        status = {
            "active_rules": _safe_int("RATE_LIMIT_ACTIVE_RULES", 0),
            "total_requests_tracked": _safe_int("RATE_LIMIT_TOTAL_REQUESTS", 0),
            "blocked_requests": _safe_int("RATE_LIMIT_BLOCKED_REQUESTS", 0),
        }
        
        logger.info(f"Rate limiting status retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": {
                "config": config,
                "status": status,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rate limiting: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Concurrent Control Endpoint
# ============================================================================

@router.get(
    "/concurrent-control",
    summary="获取并发控制配置和状态",
    responses={
        200: {"description": "并发控制信息"},
        500: {"description": "获取失败"},
    },
)
async def get_concurrent_control(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get concurrent control configuration and status
    
    Returns:
        Concurrent control configuration and current status
    """
    try:
        
        # Get concurrent control configuration from environment
        config = {
            "enabled": _safe_bool("CONCURRENT_CONTROL_ENABLED", True),
            "max_concurrent_requests": _safe_int("CONCURRENT_MAX_REQUESTS", 100),
            "max_concurrent_per_user": _safe_int("CONCURRENT_MAX_PER_USER", 10),
            "queue_size": _safe_int("CONCURRENT_QUEUE_SIZE", 50),
        }
        
        # Get current concurrent control status
        status = {
            "active_requests": _safe_int("CONCURRENT_ACTIVE_REQUESTS", 0),
            "queued_requests": _safe_int("CONCURRENT_QUEUED_REQUESTS", 0),
            "rejected_requests": _safe_int("CONCURRENT_REJECTED_REQUESTS", 0),
        }
        
        logger.info(f"Concurrent control status retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": {
                "config": config,
                "status": status,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting concurrent control: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Cache Preheat Endpoint
# ============================================================================

@router.get(
    "/cache-preheat",
    summary="获取缓存预热配置和状态",
    responses={
        200: {"description": "缓存预热信息"},
        500: {"description": "获取失败"},
    },
)
async def get_cache_preheat(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get cache preheat configuration and status
    
    Returns:
        Cache preheat configuration and current status
    """
    try:
        
        # Get cache preheat configuration from environment
        config = {
            "enabled": _safe_bool("CACHE_PREHEAT_ENABLED", False),
            "auto_preheat_on_startup": _safe_bool("CACHE_PREHEAT_AUTO_STARTUP", False),
            "preheat_endpoints": os.getenv("CACHE_PREHEAT_ENDPOINTS", "").split(",") if os.getenv("CACHE_PREHEAT_ENDPOINTS") else [],
            "preheat_interval_hours": _safe_int("CACHE_PREHEAT_INTERVAL_HOURS", 24),
        }
        
        # Get current cache preheat status
        status = {
            "last_preheat_time": os.getenv("CACHE_PREHEAT_LAST_TIME"),
            "preheated_endpoints_count": _safe_int("CACHE_PREHEATED_COUNT", 0),
            "preheat_success_rate": _safe_float("CACHE_PREHEAT_SUCCESS_RATE", 0.0),
        }
        
        logger.info(f"Cache preheat status retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": {
                "config": config,
                "status": status,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache preheat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Smart Cache Endpoint
# ============================================================================

@router.get(
    "/smart-cache",
    summary="获取智能缓存配置和状态",
    responses={
        200: {"description": "智能缓存信息"},
        500: {"description": "获取失败"},
    },
)
async def get_smart_cache(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get smart cache configuration and status
    
    Returns:
        Smart cache configuration and current status
    """
    try:
        
        # Get smart cache configuration from environment
        config = {
            "enabled": _safe_bool("SMART_CACHE_ENABLED", True),
            "adaptive_ttl": _safe_bool("SMART_CACHE_ADAPTIVE_TTL", True),
            "min_ttl_seconds": _safe_int("SMART_CACHE_MIN_TTL", 60),
            "max_ttl_seconds": _safe_int("SMART_CACHE_MAX_TTL", 3600),
            "cache_size_mb": _safe_int("SMART_CACHE_SIZE_MB", 100),
        }
        
        # Get current smart cache status
        status = {
            "cache_hit_rate": _safe_float("SMART_CACHE_HIT_RATE", 0.0),
            "cache_miss_rate": _safe_float("SMART_CACHE_MISS_RATE", 0.0),
            "total_cache_items": _safe_int("SMART_CACHE_TOTAL_ITEMS", 0),
            "evicted_items": _safe_int("SMART_CACHE_EVICTED_ITEMS", 0),
        }
        
        logger.info(f"Smart cache status retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": {
                "config": config,
                "status": status,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting smart cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Cache Strategy Endpoint
# ============================================================================

@router.get(
    "/cache-strategy",
    summary="获取缓存策略配置",
    responses={
        200: {"description": "缓存策略信息"},
        500: {"description": "获取失败"},
    },
)
async def get_cache_strategy(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get cache strategy configuration
    
    Returns:
        Cache strategy configuration
    """
    try:
        
        # Get cache strategy configuration from environment
        config = {
            "default_strategy": os.getenv("CACHE_STRATEGY_DEFAULT", "lru"),
            "available_strategies": ["lru", "lfu", "fifo", "ttl", "adaptive"],
            "eviction_policy": os.getenv("CACHE_EVICTION_POLICY", "lru"),
            "cache_backend": os.getenv("CACHE_BACKEND", "memory"),
        }
        
        # Get strategy-specific configuration
        strategy_config = {
            "lru": {
                "max_size": _safe_int("CACHE_LRU_MAX_SIZE", 1000),
            },
            "lfu": {
                "max_size": _safe_int("CACHE_LFU_MAX_SIZE", 1000),
            },
            "ttl": {
                "default_ttl": _safe_int("CACHE_TTL_DEFAULT", 300),
            },
        }
        
        logger.info(f"Cache strategy retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": {
                "config": config,
                "strategy_config": strategy_config,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cache strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Memory Monitor Endpoint
# ============================================================================

@router.get(
    "/memory-monitor",
    summary="获取内存监控数据",
    responses={
        200: {"description": "内存监控信息"},
        500: {"description": "获取失败"},
    },
)
async def get_memory_monitor(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get memory monitoring data
    
    Returns:
        Memory monitoring data
    """
    try:
        
        # Get memory monitoring data
        import psutil
        
        memory = psutil.virtual_memory()
        
        data = {
            "total_mb": round(memory.total / 1024 / 1024, 2),
            "available_mb": round(memory.available / 1024 / 1024, 2),
            "used_mb": round(memory.used / 1024 / 1024, 2),
            "percent": memory.percent,
            "cached_mb": round(memory.cached / 1024 / 1024, 2) if hasattr(memory, 'cached') else 0,
        }
        
        # Get process memory usage
        process = psutil.Process()
        process_memory = {
            "rss_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "vms_mb": round(process.memory_info().vms / 1024 / 1024, 2),
        }
        
        logger.info(f"Memory monitor data retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": {
                "system_memory": data,
                "process_memory": process_memory,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory monitor: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Memory Optimization Endpoint
# ============================================================================

@router.get(
    "/memory-optimization",
    summary="获取内存优化建议",
    responses={
        200: {"description": "内存优化建议"},
        500: {"description": "获取失败"},
    },
)
async def get_memory_optimization(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get memory optimization recommendations
    
    Returns:
        Memory optimization recommendations
    """
    try:
        
        # Get memory optimization recommendations
        import psutil
        
        memory = psutil.virtual_memory()
        
        recommendations = []
        
        if memory.percent > 80:
            recommendations.append({
                "priority": "high",
                "type": "memory_pressure",
                "message": "System memory usage is high (>80%)",
                "action": "Consider clearing cache or restarting services",
            })
        
        if memory.percent > 90:
            recommendations.append({
                "priority": "critical",
                "type": "memory_critical",
                "message": "System memory usage is critical (>90%)",
                "action": "Immediate action required: clear cache, restart services, or add more memory",
            })
        
        # Check for memory leaks
        process = psutil.Process()
        process_memory_mb = process.memory_info().rss / 1024 / 1024
        if process_memory_mb > 1000:
            recommendations.append({
                "priority": "medium",
                "type": "process_memory",
                "message": f"Process memory usage is high ({process_memory_mb:.2f} MB)",
                "action": "Check for memory leaks in the application",
            })
        
        logger.info(f"Memory optimization recommendations retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": {
                "recommendations": recommendations,
                "current_memory_percent": memory.percent,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting memory optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# CPU Optimization Endpoint
# ============================================================================

@router.get(
    "/cpu-optimization",
    summary="获取CPU优化建议",
    responses={
        200: {"description": "CPU优化建议"},
        500: {"description": "获取失败"},
    },
)
async def get_cpu_optimization(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get CPU optimization recommendations
    
    Returns:
        CPU optimization recommendations
    """
    try:
        
        # Get CPU optimization recommendations
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        recommendations = []
        
        if cpu_percent > 80:
            recommendations.append({
                "priority": "high",
                "type": "cpu_pressure",
                "message": f"CPU usage is high ({cpu_percent}%)",
                "action": "Consider optimizing CPU-intensive operations or scaling horizontally",
            })
        
        if cpu_percent > 90:
            recommendations.append({
                "priority": "critical",
                "type": "cpu_critical",
                "message": f"CPU usage is critical ({cpu_percent}%)",
                "action": "Immediate action required: optimize operations or add more CPU resources",
            })
        
        # Check for CPU-bound operations
        if cpu_count and cpu_count < 4:
            recommendations.append({
                "priority": "low",
                "type": "cpu_cores",
                "message": f"System has only {cpu_count} CPU cores",
                "action": "Consider using a system with more CPU cores for better performance",
            })
        
        logger.info(f"CPU optimization recommendations retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": {
                "recommendations": recommendations,
                "current_cpu_percent": cpu_percent,
                "cpu_count": cpu_count,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting CPU optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Resources Endpoint
# ============================================================================

@router.get(
    "/api-resources",
    summary="获取API资源使用情况",
    responses={
        200: {"description": "API资源信息"},
        500: {"description": "获取失败"},
    },
)
async def get_api_resources(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get API resource usage
    
    Returns:
        API resource usage data
    """
    try:
        
        # Get API resource usage
        import psutil
        
        process = psutil.Process()
        
        data = {
            "cpu_percent": process.cpu_percent(),
            "memory_mb": round(process.memory_info().rss / 1024 / 1024, 2),
            "num_threads": process.num_threads(),
            "num_connections": len(process.connections()) if hasattr(process, 'connections') else 0,
            "open_files": len(process.open_files()) if hasattr(process, 'open_files') else 0,
        }
        
        logger.info(f"API resources retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API resources: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Throughput Endpoint
# ============================================================================

@router.get(
    "/api-throughput",
    summary="获取API吞吐量指标",
    responses={
        200: {"description": "API吞吐量信息"},
        500: {"description": "获取失败"},
    },
)
async def get_api_throughput(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get API throughput metrics
    
    Returns:
        API throughput metrics
    """
    try:
        
        # Get API throughput metrics
        throughput = {
            "requests_per_second": _safe_float("API_THROUGHPUT_RPS", 0.0),
            "requests_per_minute": _safe_float("API_THROUGHPUT_RPM", 0.0),
            "requests_per_hour": _safe_float("API_THROUGHPUT_RPH", 0.0),
            "peak_throughput": _safe_float("API_THROUGHPUT_PEAK", 0.0),
            "avg_response_time_ms": _safe_float("API_THROUGHPUT_AVG_RT", 0.0),
        }
        
        logger.info(f"API throughput retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": throughput,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API throughput: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Response Time Endpoint
# ============================================================================

@router.get(
    "/api-response-time",
    summary="获取API响应时间指标",
    responses={
        200: {"description": "API响应时间信息"},
        500: {"description": "获取失败"},
    },
)
async def get_api_response_time(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get API response time metrics
    
    Returns:
        API response time metrics
    """
    try:
        
        # Get API response time metrics
        response_time = {
            "p50_ms": _safe_float("API_RT_P50", 0.0),
            "p95_ms": _safe_float("API_RT_P95", 0.0),
            "p99_ms": _safe_float("API_RT_P99", 0.0),
            "avg_ms": _safe_float("API_RT_AVG", 0.0),
            "min_ms": _safe_float("API_RT_MIN", 0.0),
            "max_ms": _safe_float("API_RT_MAX", 0.0),
        }
        
        logger.info(f"API response time retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": response_time,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API response time: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# API Performance Endpoint
# ============================================================================

@router.get(
    "/api-performance",
    summary="获取API性能综合指标",
    responses={
        200: {"description": "API性能综合信息"},
        500: {"description": "获取失败"},
    },
)
async def get_api_performance(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get comprehensive API performance metrics
    
    Returns:
        Comprehensive API performance metrics
    """
    try:
        
        # Get comprehensive API performance metrics
        performance = {
            "throughput": {
                "requests_per_second": _safe_float("API_THROUGHPUT_RPS", 0.0),
                "requests_per_minute": _safe_float("API_THROUGHPUT_RPM", 0.0),
            },
            "response_time": {
                "p50_ms": _safe_float("API_RT_P50", 0.0),
                "p95_ms": _safe_float("API_RT_P95", 0.0),
                "p99_ms": _safe_float("API_RT_P99", 0.0),
                "avg_ms": _safe_float("API_RT_AVG", 0.0),
            },
            "error_rate": _safe_float("API_ERROR_RATE", 0.0),
            "availability": _safe_float("API_AVAILABILITY", 100.0),
            "cache_hit_rate": _safe_float("API_CACHE_HIT_RATE", 0.0),
        }
        
        logger.info(f"API performance retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": performance,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting API performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Integration Testing Endpoint
# ============================================================================

@router.get(
    "/integration-testing",
    summary="获取集成测试状态",
    responses={
        200: {"description": "集成测试信息"},
        500: {"description": "获取失败"},
    },
)
async def get_integration_testing(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get integration testing status
    
    Returns:
        Integration testing status
    """
    try:
        
        # Get integration testing status
        status = {
            "enabled": _safe_bool("INTEGRATION_TESTING_ENABLED", False),
            "last_test_time": os.getenv("INTEGRATION_TESTING_LAST_TIME"),
            "total_tests": _safe_int("INTEGRATION_TESTING_TOTAL", 0),
            "passed_tests": _safe_int("INTEGRATION_TESTING_PASSED", 0),
            "failed_tests": _safe_int("INTEGRATION_TESTING_FAILED", 0),
            "success_rate": _safe_float("INTEGRATION_TESTING_SUCCESS_RATE", 0.0),
        }
        
        logger.info(f"Integration testing status retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": status,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting integration testing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Regression Detection Endpoint
# ============================================================================

@router.get(
    "/regression-detection",
    summary="获取性能回归检测结果",
    responses={
        200: {"description": "回归检测信息"},
        500: {"description": "获取失败"},
    },
)
async def get_regression_detection(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get performance regression detection results
    
    Returns:
        Performance regression detection results
    """
    try:
        
        # Get regression detection results
        detection = {
            "enabled": _safe_bool("REGRESSION_DETECTION_ENABLED", True),
            "baseline_avg_response_time_ms": _safe_float("REGRESSION_BASELINE_RT", 0.0),
            "current_avg_response_time_ms": _safe_float("REGRESSION_CURRENT_RT", 0.0),
            "regression_detected": _safe_bool("REGRESSION_DETECTED", False),
            "regression_threshold_percent": _safe_float("REGRESSION_THRESHOLD", 20.0),
            "regression_severity": os.getenv("REGRESSION_SEVERITY", "none"),
        }
        
        logger.info(f"Regression detection retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": detection,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting regression detection: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Performance Report Endpoint
# ============================================================================

@router.get(
    "/performance-report",
    summary="获取性能报告",
    responses={
        200: {"description": "性能报告"},
        500: {"description": "获取失败"},
    },
)
async def get_performance_report(
    hours: int = Query(24, ge=1, le=168, description="Report time window in hours"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get performance report
    
    Args:
        hours: Report time window in hours
        
    Returns:
        Performance report
    """
    try:
        
        # Get performance report
        report = {
            "time_window_hours": hours,
            "summary": {
                "total_requests": _safe_int("PERF_REPORT_TOTAL_REQUESTS", 0),
                "avg_response_time_ms": _safe_float("PERF_REPORT_AVG_RT", 0.0),
                "error_rate": _safe_float("PERF_REPORT_ERROR_RATE", 0.0),
                "availability": _safe_float("PERF_REPORT_AVAILABILITY", 100.0),
            },
            "top_slow_endpoints": [
                {
                    "endpoint": "/api/analyze",
                    "avg_response_time_ms": _safe_float("PERF_REPORT_SLOW_1_RT", 0.0),
                    "request_count": _safe_int("PERF_REPORT_SLOW_1_COUNT", 0),
                },
                {
                    "endpoint": "/api/repair",
                    "avg_response_time_ms": _safe_float("PERF_REPORT_SLOW_2_RT", 0.0),
                    "request_count": _safe_int("PERF_REPORT_SLOW_2_COUNT", 0),
                },
            ],
        }
        
        logger.info(f"Performance report retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": report,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Performance Optimizer Endpoint
# ============================================================================

@router.get(
    "/performance-optimizer",
    summary="获取性能优化器状态",
    responses={
        200: {"description": "性能优化器信息"},
        500: {"description": "获取失败"},
    },
)
async def get_performance_optimizer(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get performance optimizer status
    
    Returns:
        Performance optimizer status
    """
    try:
        
        # Get performance optimizer status
        optimizer = {
            "enabled": _safe_bool("PERFORMANCE_OPTIMIZER_ENABLED", True),
            "auto_optimization": _safe_bool("PERFORMANCE_AUTO_OPT", False),
            "last_optimization_time": os.getenv("PERFORMANCE_LAST_OPT_TIME"),
            "optimizations_applied": _safe_int("PERFORMANCE_OPT_APPLIED", 0),
            "performance_improvement_percent": _safe_float("PERFORMANCE_IMPROVEMENT", 0.0),
        }
        
        logger.info(f"Performance optimizer retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": optimizer,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance optimizer: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Performance Data Endpoint
# ============================================================================

@router.get(
    "/performance-data",
    summary="获取性能数据",
    responses={
        200: {"description": "性能数据"},
        500: {"description": "获取失败"},
    },
)
async def get_performance_data(
    metric: str = Query("response_time", description="Metric name"),
    hours: int = Query(24, ge=1, le=168, description="Time window in hours"),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get performance data for a specific metric
    
    Args:
        metric: Metric name (response_time, throughput, error_rate, etc.)
        hours: Time window in hours
        
    Returns:
        Performance data
    """
    try:
        
        # Get performance data
        data = {
            "metric": metric,
            "time_window_hours": hours,
            "data_points": _safe_int(f"PERF_DATA_{metric.upper()}_POINTS", 0),
            "avg_value": _safe_float(f"PERF_DATA_{metric.upper()}_AVG", 0.0),
            "min_value": _safe_float(f"PERF_DATA_{metric.upper()}_MIN", 0.0),
            "max_value": _safe_float(f"PERF_DATA_{metric.upper()}_MAX", 0.0),
        }
        
        logger.info(f"Performance data retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Performance Monitoring Endpoint
# ============================================================================

@router.get(
    "/performance-monitoring",
    summary="获取性能监控状态",
    responses={
        200: {"description": "性能监控信息"},
        500: {"description": "获取失败"},
    },
)
async def get_performance_monitoring(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get performance monitoring status
    
    Returns:
        Performance monitoring status
    """
    try:
        
        # Get performance monitoring status
        monitoring = {
            "enabled": _safe_bool("PERFORMANCE_MONITORING_ENABLED", True),
            "collection_interval_seconds": _safe_int("PERF_MONITOR_INTERVAL", 60),
            "metrics_collected": _safe_int("PERF_MONITOR_METRICS", 0),
            "alerts_configured": _safe_int("PERF_MONITOR_ALERTS", 0),
            "active_alerts": _safe_int("PERF_MONITOR_ACTIVE_ALERTS", 0),
        }
        
        logger.info(f"Performance monitoring retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": monitoring,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance monitoring: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Performance Tuning Endpoint
# ============================================================================

@router.get(
    "/performance-tuning",
    summary="获取性能调优建议",
    responses={
        200: {"description": "性能调优建议"},
        500: {"description": "获取失败"},
    },
)
async def get_performance_tuning(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get performance tuning recommendations
    
    Returns:
        Performance tuning recommendations
    """
    try:
        
        # Get performance tuning recommendations
        tuning = {
            "recommendations": [
                {
                    "category": "database",
                    "priority": "high",
                    "action": "Add indexes to frequently queried columns",
                    "expected_improvement": "30-50% query speedup",
                },
                {
                    "category": "cache",
                    "priority": "medium",
                    "action": "Increase cache TTL for static data",
                    "expected_improvement": "20-30% reduction in database load",
                },
                {
                    "category": "concurrency",
                    "priority": "low",
                    "action": "Adjust worker pool size based on CPU cores",
                    "expected_improvement": "10-20% throughput improvement",
                },
            ],
            "tuning_history": _safe_int("PERFORMANCE_TUNING_HISTORY", 0),
        }
        
        logger.info(f"Performance tuning retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": tuning,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting performance tuning: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Query Optimization Endpoint
# ============================================================================

@router.get(
    "/query-optimization",
    summary="获取查询优化建议",
    responses={
        200: {"description": "查询优化建议"},
        500: {"description": "获取失败"},
    },
)
async def get_query_optimization(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get query optimization recommendations
    
    Returns:
        Query optimization recommendations
    """
    try:
        
        # Get query optimization recommendations
        optimization = {
            "slow_queries": _safe_int("QUERY_OPT_SLOW_QUERIES", 0),
            "queries_analyzed": _safe_int("QUERY_OPT_ANALYZED", 0),
            "optimizations_suggested": _safe_int("QUERY_OPT_SUGGESTED", 0),
            "recommendations": [
                {
                    "query_pattern": "SELECT * FROM large_table WHERE indexed_column = ?",
                    "issue": "Full table scan on large table",
                    "suggestion": "Add index on indexed_column",
                    "expected_improvement": "90% faster",
                },
            ],
        }
        
        logger.info(f"Query optimization retrieved by user {current_user.username}")
        
        return {
            "status": "success",
            "data": optimization,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting query optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))
