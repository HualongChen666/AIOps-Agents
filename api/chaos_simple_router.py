# -*- coding: utf-8 -*-
"""
Chaos Simple Router
混沌工程简单路由，用于 /api/chaos/* 路径
"""

from typing import Any, Dict

from fastapi import APIRouter, Depends

from core.authentication import get_current_active_user
from core.rbac import role_required
from core.chaos_engineering import chaos_engine

router = APIRouter(prefix="/api/chaos", tags=["混沌工程"])


@router.get("/chaos-configuration")
async def get_chaos_configuration(user=Depends(get_current_active_user)):
    """获取混沌配置"""
    return {
        "status": "success",
        "configuration": {
            "enabled": chaos_engine.is_enabled(),
            "safety_checks": True,
            "allowed_environments": ["development", "staging"]
        }
    }


@router.get("/chaos-reports")
async def get_chaos_reports(user=Depends(get_current_active_user)):
    """获取混沌报告"""
    history = chaos_engine.get_experiment_history(limit=10)
    return {
        "status": "success",
        "reports": [
            {
                "experiment": exp.experiment.value,
                "status": exp.status.value,
                "success": exp.success,
                "duration_seconds": exp.duration_seconds,
                "start_time": exp.start_time.isoformat()
            }
            for exp in history
        ]
    }


@router.get("/chaos-dashboard")
async def get_chaos_dashboard(user=Depends(get_current_active_user)):
    """获取混沌仪表板"""
    stats = chaos_engine.get_experiment_stats()
    return {
        "status": "success",
        "dashboard": {
            "active_experiments": chaos_engine.get_active_experiments(),
            "success_rate": stats.get("success_rate", 0.0),
            "total_experiments": stats.get("total_experiments", 0)
        }
    }


@router.get("/chaos-scenarios")
async def get_chaos_scenarios(user=Depends(get_current_active_user)):
    """获取混沌场景"""
    return {
        "status": "success",
        "scenarios": [
            {"id": "latency_injection", "name": "网络延迟注入", "severity": "medium"},
            {"id": "fault_injection", "name": "磁盘故障注入", "severity": "high"},
            {"id": "resource_limitation", "name": "资源限制", "severity": "medium"},
            {"id": "network_partition", "name": "网络分区", "severity": "high"},
            {"id": "service_failure", "name": "服务故障", "severity": "medium"}
        ]
    }


@router.get("/chaos-experiments")
async def get_chaos_experiments(user=Depends(get_current_active_user)):
    """获取混沌实验"""
    history = chaos_engine.get_experiment_history(limit=20)
    return {
        "status": "success",
        "experiments": [
            {
                "experiment": exp.experiment.value,
                "status": exp.status.value,
                "success": exp.success,
                "start_time": exp.start_time.isoformat(),
                "end_time": exp.end_time.isoformat() if exp.end_time else None
            }
            for exp in history
        ]
    }


@router.get("/chaos-mesh")
async def get_chaos_mesh(user=Depends(get_current_active_user)):
    """获取混沌网格（真实的注入后端能力，非硬编码）"""
    injector = chaos_engine.injector
    try:
        import kubernetes  # noqa: F401

        kubernetes_client_available = True
    except Exception:
        kubernetes_client_available = False

    return {
        "status": "success",
        "mesh": {
            "enabled": chaos_engine.is_enabled(),
            "injector": type(injector).__name__,
            "api_group": getattr(injector, "group", None),
            "chaos_mesh_version": getattr(injector, "version", None),
            "namespace": getattr(injector, "namespace", None),
            "kubernetes_client_available": kubernetes_client_available,
            "installed": kubernetes_client_available,
        },
    }


@router.get("/fault-injection")
async def get_fault_injection(user=Depends(get_current_active_user)):
    """获取故障注入"""
    return {
        "status": "success",
        "fault_injection": {
            "types": ["cpu", "memory", "network", "disk"],
            "enabled": chaos_engine.is_enabled()
        }
    }


@router.get("/chaos-engineering")
async def get_chaos_engineering(user=Depends(get_current_active_user)):
    """获取混沌工程"""
    return {
        "status": "success",
        "engineering": {
            "version": "1.0",
            "enabled": chaos_engine.is_enabled(),
            "features": ["latency_injection", "fault_injection", "resource_limitation"]
        }
    }
