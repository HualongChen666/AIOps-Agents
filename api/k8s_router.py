# -*- coding: utf-8 -*-
"""Kubernetes 采集 & 修复 API 路由

SECURITY: 所有端点需要认证才能访问
🔧 重构:使用 api.schemas.repair 统一修复请求模型
"""

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.authentication import get_current_active_user
from core.k8s_collector import collect_all_k8s, get_k8s_collect_history
from core.k8s_repair import execute_repair_sync, get_k8s_repair_history, repair_all_k8s


class K8sRepairRequest(BaseModel):
    host: str
    script_name: str
    args: dict = {}

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"host": "example", "script_name": "example", "args": {}}},
    }


router = APIRouter(
    prefix="/api/v1/platforms/kubernetes",
    tags=["Kubernetes"],
    dependencies=[Depends(get_current_active_user)],
)


@router.get(
    "/metrics",
    response_model=List[Dict[str, Any]],
    summary="采集 Kubernetes 集群指标",
    responses={
        (200): {"description": "K8s集群指标列表"},
        (401): {"description": "未授权"},
        (500): {"description": "采集失败"},
    },
)
async def get_k8s_metrics() -> List[Dict[str, Any]]:
    try:
        return collect_all_k8s()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/history",
    response_model=List[Dict[str, Any]],
    summary="获取 Kubernetes 采集历史",
    responses={(200): {"description": "采集历史记录"}, (401): {"description": "未授权"}},
)
async def get_k8s_history(limit: int = 20) -> List[Dict[str, Any]]:
    return get_k8s_collect_history(limit)


@router.post(
    "/repair",
    response_model=Dict[str, Any],
    summary="执行 Kubernetes 修复脚本",
    responses={
        (200): {
            "description": "修复执行成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "output": "Pod restarted successfully",
                        "exit_code": 0,
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "执行异常"},
    },
)
async def post_k8s_repair(payload: K8sRepairRequest) -> Dict[str, Any]:
    host_cfg = {"host": payload.host}
    try:
        result = execute_repair_sync(host_cfg, payload.script_name, payload.args)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/repair/all",
    response_model=List[Dict[str, Any]],
    summary="对所有 Kubernetes 集群执行修复脚本",
    responses={
        (200): {"description": "所有集群修复结果"},
        (401): {"description": "未授权"},
        (500): {"description": "执行异常"},
    },
)
async def post_k8s_repair_all(payload: K8sRepairRequest) -> List[Dict[str, Any]]:
    try:
        return await repair_all_k8s(payload.script_name, payload.args)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/repair/history",
    response_model=List[Dict[str, Any]],
    summary="获取 Kubernetes 修复历史",
    responses={(200): {"description": "修复历史记录"}, (401): {"description": "未授权"}},
)
async def get_k8s_repair_history_endpoint(limit: int = 20) -> List[Dict[str, Any]]:
    return get_k8s_repair_history(limit)
