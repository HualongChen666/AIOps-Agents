# -*- coding: utf-8 -*-
"""
System Resource Optimization Router
Provides API endpoints for system resource monitoring and optimization
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from core.authentication import get_current_active_user

router = APIRouter(prefix="/api/resources", tags=["System Resources"])


@router.get(
    "/status",
    summary="获取系统资源优化状态",
    responses={
        200: {"description": "优化状态"},
        500: {"description": "获取失败"},
    },
)
async def get_optimization_status(user=Depends(get_current_active_user)):
    """
    Get current system resource optimization status

    Returns:
        Current optimization status
    """
    try:
        from core.system_resource_optimizer import get_system_resource_optimizer

        optimizer = get_system_resource_optimizer()
        status = optimizer.get_optimization_status()
        return {"status": "success", "data": status, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting optimization status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/summary",
    summary="获取资源摘要",
    responses={
        200: {"description": "资源摘要"},
        500: {"description": "获取失败"},
    },
)
async def get_resource_summary(user=Depends(get_current_active_user)):
    """
    Get comprehensive resource summary

    Returns:
        Resource summary
    """
    try:
        from core.system_resource_optimizer import get_system_resource_optimizer

        optimizer = get_system_resource_optimizer()
        summary = optimizer.get_resource_summary()
        return {"status": "success", "data": summary, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error getting resource summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/memory",
    summary="分析内存使用",
    responses={
        200: {"description": "内存分析结果"},
        500: {"description": "分析失败"},
    },
)
async def analyze_memory_usage(user=Depends(get_current_active_user)):
    """
    Analyze memory usage

    Returns:
        Memory usage analysis
    """
    try:
        from core.system_resource_optimizer import get_system_resource_optimizer

        optimizer = get_system_resource_optimizer()
        analysis = optimizer.analyze_memory_usage()
        return {"status": "success", "data": analysis, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error analyzing memory usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/memory/optimize",
    summary="优化内存使用",
    responses={
        200: {"description": "优化结果"},
        500: {"description": "优化失败"},
    },
)
async def optimize_memory(user=Depends(get_current_active_user)):
    """
    Optimize memory usage

    Returns:
        Memory optimization results
    """
    try:
        from core.system_resource_optimizer import get_system_resource_optimizer

        optimizer = get_system_resource_optimizer()
        results = optimizer.optimize_memory()
        return {"status": "success", "data": results, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error optimizing memory: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/cpu",
    summary="分析CPU使用",
    responses={
        200: {"description": "CPU分析结果"},
        500: {"description": "分析失败"},
    },
)
async def analyze_cpu_usage(user=Depends(get_current_active_user)):
    """
    Analyze CPU usage

    Returns:
        CPU usage analysis
    """
    try:
        from core.system_resource_optimizer import get_system_resource_optimizer

        optimizer = get_system_resource_optimizer()
        analysis = optimizer.analyze_cpu_usage()
        return {"status": "success", "data": analysis, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error analyzing CPU usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/cpu/optimize",
    summary="优化CPU使用",
    responses={
        200: {"description": "优化结果"},
        500: {"description": "优化失败"},
    },
)
async def optimize_cpu(user=Depends(get_current_active_user)):
    """
    Optimize CPU usage

    Returns:
        CPU optimization results
    """
    try:
        from core.system_resource_optimizer import get_system_resource_optimizer

        optimizer = get_system_resource_optimizer()
        results = optimizer.optimize_cpu()
        return {"status": "success", "data": results, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error optimizing CPU: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/network",
    summary="分析网络使用",
    responses={
        200: {"description": "网络分析结果"},
        500: {"description": "分析失败"},
    },
)
async def analyze_network_usage(user=Depends(get_current_active_user)):
    """
    Analyze network usage

    Returns:
        Network usage analysis
    """
    try:
        from core.system_resource_optimizer import get_system_resource_optimizer

        optimizer = get_system_resource_optimizer()
        analysis = optimizer.optimize_network()
        return {"status": "success", "data": analysis, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error analyzing network usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/network/optimize",
    summary="优化网络使用",
    responses={
        200: {"description": "优化结果"},
        500: {"description": "优化失败"},
    },
)
async def optimize_network(user=Depends(get_current_active_user)):
    """
    Optimize network usage

    Returns:
        Network optimization results
    """
    try:
        from core.system_resource_optimizer import get_system_resource_optimizer

        optimizer = get_system_resource_optimizer()
        results = optimizer.optimize_network()
        return {"status": "success", "data": results, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error optimizing network: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/optimize",
    summary="运行综合优化",
    responses={
        200: {"description": "优化结果"},
        500: {"description": "优化失败"},
    },
)
async def run_comprehensive_optimization(
    memory_optimization: bool = Query(True, description="Enable memory optimization"),
    cpu_optimization: bool = Query(True, description="Enable CPU optimization"),
    network_optimization: bool = Query(True, description="Enable network optimization"),
    user=Depends(get_current_active_user),
):
    """
    Run comprehensive system resource optimization

    Args:
        memory_optimization: Enable memory optimization
        cpu_optimization: Enable CPU optimization
        network_optimization: Enable network optimization

    Returns:
        Comprehensive optimization results
    """
    try:
        from core.system_resource_optimizer import get_system_resource_optimizer

        optimizer = get_system_resource_optimizer()

        # Run comprehensive optimization
        results = optimizer.run_comprehensive_optimization()

        return {"status": "success", "data": results, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error running comprehensive optimization: {e}")
        raise HTTPException(status_code=500, detail=str(e))
