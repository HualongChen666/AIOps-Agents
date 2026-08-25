# -*- coding: utf-8 -*-
"""
Chaos Engineering Router
混沌工程路由

提供混沌工程实验的控制API端点。
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter

from core.api_response_standard import create_error_response, create_success_response
from core.chaos_engineering import ChaosExperiment, chaos_engine

router = APIRouter(prefix="/api/v1/chaos", tags=["混沌工程"])


@router.get(
    "/status",
    summary="获取混沌工程状态",
    responses={
        200: {
            "description": "混沌工程状态",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "enabled": True,
                            "stats": {"total_experiments": 10, "success_rate": 0.9},
                        },
                    }
                }
            },
        },
        500: {
            "description": "获取状态失败",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Failed to retrieve chaos engineering status",
                        "error_code": "CHAOS_STATUS_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_chaos_status() -> Dict[str, Any]:
    """
    获取混沌工程引擎状态

    Returns:
        混沌工程状态信息
    """
    try:
        stats = chaos_engine.get_experiment_stats()
        return create_success_response({"enabled": chaos_engine.is_enabled(), "stats": stats})
    except Exception as e:
        return create_error_response(error=str(e), error_code="CHAOS_STATUS_ERROR")


@router.post(
    "/enable",
    summary="启用混沌工程",
    responses={
        200: {
            "description": "启用成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {"message": "Chaos engineering enabled", "enabled": True},
                    }
                }
            },
        },
        500: {
            "description": "启用失败",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Failed to enable chaos engineering",
                        "error_code": "CHAOS_ENABLE_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def enable_chaos() -> Dict[str, Any]:
    """
    启用混沌工程

    注意: 仅在测试/开发环境使用，生产环境默认禁用

    Returns:
        操作结果
    """
    try:
        chaos_engine.enable()
        return create_success_response({"message": "Chaos engineering enabled", "enabled": True})
    except Exception as e:
        return create_error_response(error=str(e), error_code="CHAOS_ENABLE_ERROR")


@router.post(
    "/disable",
    summary="禁用混沌工程",
    responses={
        200: {
            "description": "禁用成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {"message": "Chaos engineering disabled", "enabled": False},
                    }
                }
            },
        },
        500: {
            "description": "禁用失败",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Failed to disable chaos engineering",
                        "error_code": "CHAOS_DISABLE_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def disable_chaos() -> Dict[str, Any]:
    """
    禁用混沌工程

    Returns:
        操作结果
    """
    try:
        chaos_engine.disable()
        return create_success_response({"message": "Chaos engineering disabled", "enabled": False})
    except Exception as e:
        return create_error_response(error=str(e), error_code="CHAOS_DISABLE_ERROR")


@router.post(
    "/experiment/{experiment_type}",
    summary="执行混沌实验",
    responses={
        200: {
            "description": "实验执行成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "experiment": "latency_injection",
                            "status": "completed",
                            "success": True,
                            "duration_seconds": 5.2,
                            "metrics": {"affected_services": 3},
                        },
                    }
                }
            },
        },
        400: {
            "description": "无效的实验类型",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Invalid experiment type: unknown_type",
                        "error_code": "INVALID_EXPERIMENT",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
        500: {
            "description": "实验执行失败",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Failed to execute chaos experiment",
                        "error_code": "EXPERIMENT_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def run_experiment(
    experiment_type: str, parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    执行混沌实验

    Args:
        experiment_type: 实验类型 (latency_injection, fault_injection,
            resource_limitation, network_partition, service_failure)
        parameters: 实验参数

    Returns:
        实验结果
    """
    try:
        # 验证实验类型
        try:
            experiment = ChaosExperiment(experiment_type)
        except ValueError:
            return create_error_response(
                error=f"Invalid experiment type: {experiment_type}",
                error_code="INVALID_EXPERIMENT",
            )

        # 执行实验
        result = await chaos_engine.run_experiment(experiment, parameters or {})

        return create_success_response(
            {
                "experiment": experiment_type,
                "status": result.status.value,
                "success": result.success,
                "duration_seconds": result.duration_seconds,
                "metrics": result.metrics,
            }
        )
    except Exception as e:
        return create_error_response(error=str(e), error_code="EXPERIMENT_ERROR")


@router.get(
    "/experiments",
    summary="获取实验历史",
    responses={
        200: {
            "description": "实验历史",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "total": 2,
                            "experiments": [
                                {
                                    "experiment": "latency_injection",
                                    "status": "completed",
                                    "success": True,
                                    "duration_seconds": 5.2,
                                    "start_time": "2026-07-03T09:00:00Z",
                                    "end_time": "2026-07-03T09:00:05Z",
                                }
                            ],
                        },
                    }
                }
            },
        },
        500: {
            "description": "获取失败",
            "content": {
                "application/json": {
                    "example": {
                        "success": False,
                        "error": "Failed to retrieve experiment history",
                        "error_code": "EXPERIMENT_HISTORY_ERROR",
                        "timestamp": "2026-07-04T00:00:00Z",
                        "request_id": "uuid",
                    }
                }
            },
        },
    },
)
async def get_experiments(limit: int = 10) -> Dict[str, Any]:
    """
    获取混沌实验历史

    Args:
        limit: 返回数量限制

    Returns:
        实验历史
    """
    try:
        history = chaos_engine.get_experiment_history(limit)

        formatted_history = [
            {
                "experiment": exp.experiment.value,
                "status": exp.status.value,
                "success": exp.success,
                "duration_seconds": exp.duration_seconds,
                "start_time": exp.start_time.isoformat(),
                "end_time": exp.end_time.isoformat() if exp.end_time else None,
            }
            for exp in history
        ]

        return create_success_response(
            {"total": len(formatted_history), "experiments": formatted_history}
        )
    except Exception as e:
        return create_error_response(error=str(e), error_code="EXPERIMENT_HISTORY_ERROR")


@router.get(
    "/templates",
    summary="获取故障实验模板",
    responses={
        200: {
            "description": "故障实验模板列表",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "templates": [
                                {
                                    "id": "latency_injection",
                                    "name": "网络延迟注入",
                                    "type": "network",
                                    "description": "向目标注入指定毫秒数的网络延迟",
                                    "severity": "medium",
                                    "parameters": ["target", "duration", "delay_ms"],
                                }
                            ]
                        },
                    }
                }
            },
        },
    },
)
async def get_chaos_templates() -> Dict[str, Any]:
    """
    返回支持的混沌实验模板列表
    """
    try:
        templates = [
            {
                "id": "latency_injection",
                "name": "网络延迟注入",
                "type": "network",
                "description": "向目标注入指定毫秒数的网络延迟，验证链路超时与降级能力",
                "severity": "medium",
                "parameters": ["target", "duration", "delay_ms"],
            },
            {
                "id": "fault_injection",
                "name": "磁盘故障注入",
                "type": "disk",
                "description": "注入磁盘 I/O、数据库或缓存等故障，验证系统容错能力",
                "severity": "high",
                "parameters": ["target", "duration", "fault_type"],
            },
            {
                "id": "resource_limitation",
                "name": "资源限制",
                "type": "cpu",
                "description": "限制 CPU 或内存资源使用，验证资源瓶颈下的服务表现",
                "severity": "medium",
                "parameters": ["target", "duration", "resource_type", "limit"],
            },
            {
                "id": "network_partition",
                "name": "网络分区",
                "type": "network",
                "description": "创建网络分区，验证服务在分区场景下的降级与恢复能力",
                "severity": "high",
                "parameters": ["target", "duration", "partition_type"],
            },
            {
                "id": "service_failure",
                "name": "服务故障",
                "type": "service",
                "description": "触发指定服务故障并验证其恢复能力",
                "severity": "medium",
                "parameters": ["target", "duration", "service_name"],
            },
        ]
        return create_success_response({"templates": templates})
    except Exception as e:
        return create_error_response(error=str(e), error_code="TEMPLATES_ERROR")
