# -*- coding: utf-8 -*-
"""
Database Optimization API Router
Provides API endpoints for database optimization management
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

router = APIRouter(prefix="/api/database-optimization", tags=["Database Optimization"])


@router.get(
    "/status",
    summary="获取数据库优化状态",
    responses={
        200: {
            "description": "优化状态",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "optimization_enabled": True,
                            "last_optimization": "2026-07-03T09:00:00Z",
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "获取状态失败"},
    },
)
async def get_optimization_status():
    """
    Get current database optimization status

    Returns:
        Current optimization status
    """
    try:
        from core.database_optimization_manager import get_database_optimization_manager

        manager = get_database_optimization_manager()
        status = manager.get_optimization_status()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting optimization status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/optimize",
    summary="运行数据库优化",
    responses={
        200: {
            "description": "优化结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {"optimized_queries": 10, "improved_connections": 5},
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "优化失败"},
    },
)
async def run_optimization(
    query_optimization: bool = Query(True, description="Enable query optimization"),
    connection_optimization: bool = Query(True, description="Enable connection optimization"),
    cache_optimization: bool = Query(True, description="Enable cache optimization"),
):
    """
    Run database optimization

    Args:
        query_optimization: Enable query optimization
        connection_optimization: Enable connection optimization
        cache_optimization: Enable cache optimization

    Returns:
        Optimization results
    """
    try:
        from core.database_optimization_manager import get_database_optimization_manager

        manager = get_database_optimization_manager()

        # Run comprehensive optimization
        results = manager.run_comprehensive_optimization()

        return {"status": "success", "data": results, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error running optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/slow-queries",
    summary="分析慢查询",
    responses={
        200: {
            "description": "慢查询分析结果",
            "content": {
                "application/json": {
                    "example": {
                        "status": "success",
                        "data": {
                            "total_slow_queries": 5,
                            "queries": [{"query": "SELECT * FROM users", "duration": 2.5}],
                        },
                        "timestamp": "2026-07-03T09:00:00Z",
                    }
                }
            },
        },
        500: {"description": "分析失败"},
    },
)
async def analyze_slow_queries(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of queries to return")
):
    """
    Analyze slow queries

    Args:
        limit: Maximum number of queries to return

    Returns:
        Slow query analysis results
    """
    try:
        from core.database_optimization_manager import get_database_optimization_manager

        manager = get_database_optimization_manager()
        analysis = manager.analyze_slow_queries()

        return {"status": "success", "data": analysis, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error analyzing slow queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/connection-pool/optimize",
    summary="优化连接池",
    responses={
        200: {"description": "连接池优化结果"},
        500: {"description": "优化失败"},
    },
)
async def optimize_connection_pool():
    """
    Optimize database connection pool

    Returns:
        Connection pool optimization results
    """
    try:
        from core.database_optimization_manager import get_database_optimization_manager

        manager = get_database_optimization_manager()
        results = manager.optimize_connection_pool()

        return {"status": "success", "data": results, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error optimizing connection pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cache/setup",
    summary="设置查询缓存",
    responses={
        200: {"description": "缓存设置结果"},
        500: {"description": "设置失败"},
    },
)
async def setup_query_cache(
    ttl_seconds: int = Query(300, ge=60, le=3600, description="Cache TTL in seconds")
):
    """
    Setup query result caching

    Args:
        ttl_seconds: Cache time-to-live in seconds

    Returns:
        Cache setup results
    """
    try:
        from core.database_optimization_manager import get_database_optimization_manager

        manager = get_database_optimization_manager()
        results = manager.setup_query_cache(cache_ttl_seconds=ttl_seconds)

        return {"status": "success", "data": results, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error setting up query cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/query/record",
    summary="记录查询执行",
    responses={
        200: {"description": "记录成功"},
        500: {"description": "记录失败"},
    },
)
async def record_query_execution(
    query_text: str, duration_ms: float, database: str = "default", table_name: str = "unknown"
):
    """
    Record query execution for analysis

    Args:
        query_text: SQL query text
        duration_ms: Execution duration in milliseconds
        database: Database name
        table_name: Table name

    Returns:
        Recording result
    """
    try:
        from core.database_optimization_manager import get_database_optimization_manager

        manager = get_database_optimization_manager()
        manager.record_query_execution(
            query_text=query_text,
            duration_ms=duration_ms,
            database=database,
            table_name=table_name,
        )

        return {
            "status": "success",
            "message": "Query execution recorded",
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Error recording query execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/metrics",
    summary="获取数据库性能指标",
    responses={
        200: {"description": "数据库性能指标"},
        500: {"description": "获取失败"},
    },
)
async def get_database_metrics():
    """
    Get database performance metrics

    Returns:
        Database performance metrics
    """
    try:
        from core.database_optimization_manager import get_database_optimization_manager

        manager = get_database_optimization_manager()

        # Get comprehensive metrics
        metrics = {
            "optimization_status": manager.get_optimization_status(),
            "query_analysis": manager.analyze_slow_queries(),
            "connection_pool": manager.optimize_connection_pool(),
        }

        return {"status": "success", "data": metrics, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting database metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))
