# -*- coding: utf-8 -*-
"""Unified Cloud Platform API Router

提供对 AWS CloudWatch、Azure Monitor、阿里云 CloudMonitor 三大公有云的统一 REST 接口。

已实现的基础接口（在之前的实现中已经存在）:
- ``GET /api/cloud/metrics``          → 批量采集所有已配置的云平台指标。
- ``POST /api/cloud/collect``         → 手动触发单个云平台的采集（请求体为 ``CLOUD_PROVIDERS`` 中的单条配置）。
- ``GET /api/cloud/history``          → 查询最近的采集历史（默认 20 条）。

新增的统一化入口:
- ``GET /api/cloud/{provider}/metrics``   → 只采集指定 ``provider``（aws、azure、alibaba） 的指标。
- ``POST /api/cloud/{provider}/collect``  → 根据 ``provider`` 从配置中自动找到对应配置并采集，返回统一结构。
- ``GET /api/cloud/{provider}/history``   → 查询指定提供商的采集历史（默认 20 条），仅返回该 provider 的记录。

所有接口统一返回 ``List[Dict[str, Any]]``（集合）或 ``Dict[str, Any]``（单条），并在异常时抛出 ``HTTPException``，
错误信息统一为 ``str(e)``，便于前端统一处理。

SECURITY: 所有端点需要认证才能访问
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, Body, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field


from core.cloud_collector import (
    CLOUD_PROVIDERS,
    collect_all_cloud,
    collect_cloud,
    get_cloud_collect_history,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/platforms/cloud",
    tags=["Cloud"],
)


class CloudRepairRequest(BaseModel):
    """云平台修复请求模型"""

    action: str = Field(
        ..., min_length=1, max_length=64, description="修复操作名称，如 restart_instance"
    )
    params: Dict[str, Any] = Field(default_factory=dict, description="修复操作参数")

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"action": "example", "params": {}}},
    }


@router.get(
    "/metrics",
    response_model=List[Dict[str, Any]],
    summary="批量采集所有云平台指标",
    responses={
        (200): {"description": "云平台指标列表"},
        (401): {"description": "未授权"},
        (500): {"description": "采集失败"},
    },
)
async def get_cloud_metrics():
    """批量采集所有云平台指标（向后兼容）"""
    try:
        return collect_all_cloud()
    except Exception as e:
        logger.error(f"Cloud collection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Cloud collection failed")


@router.post(
    "/collect",
    response_model=Dict[str, Any],
    summary="手动触发单个云平台采集",
    responses={
        (200): {"description": "采集结果"},
        (401): {"description": "未授权"},
        (500): {"description": "采集失败"},
    },
)
async def collect_one(provider_cfg: Dict[str, Any]):
    """手动触发单个云平台的采集，payload 与 config.CLOUD_PROVIDERS 条目结构相同"""
    try:
        return collect_cloud(provider_cfg)
    except Exception as e:
        logger.error(f"Cloud provider collection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Cloud provider collection failed")


@router.get(
    "/history",
    response_model=List[Dict[str, Any]],
    summary="获取云平台采集历史",
    responses={
        (200): {"description": "采集历史列表"},
        (401): {"description": "未授权"},
        (500): {"description": "获取历史失败"},
    },
)
async def cloud_history(limit: int = Query(20, ge=1, le=100)):
    """返回最近的云平台采集历史（全平台）"""
    try:
        return get_cloud_collect_history(limit)
    except Exception as e:
        logger.error(f"Failed to get cloud history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve cloud history")


@router.get(
    "/{provider}/metrics",
    response_model=List[Dict[str, Any]],
    summary="采集指定云平台指标",
    responses={
        (200): {"description": "云平台指标列表"},
        (401): {"description": "未授权"},
        (404): {"description": "云平台未配置"},
        (500): {"description": "采集失败"},
    },
)
async def get_provider_metrics(
    provider: str = Path(..., description="cloud provider name: aws / azure / alibaba")
):
    """采集指定云平台的指标并返回列表（单条列表）"""
    provider = provider.lower()
    matched_cfg = [cfg for cfg in CLOUD_PROVIDERS if cfg.get("provider", "").lower() == provider]
    if not matched_cfg:
        raise HTTPException(status_code=404, detail=f"Cloud provider '{provider}' not configured")
    try:
        result = collect_cloud(matched_cfg[0])
        return [result] if result else []
    except Exception as e:
        logger.error(f"Provider metrics collection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Provider metrics collection failed")


@router.post(
    "/{provider}/collect",
    response_model=Dict[str, Any],
    summary="采集指定云平台数据",
    responses={
        (200): {"description": "采集结果"},
        (401): {"description": "未授权"},
        (404): {"description": "云平台未配置"},
        (500): {"description": "采集失败"},
    },
)
async def collect_provider(
    provider: str = Path(..., description="cloud provider name: aws / azure / alibaba")
):
    """根据 provider 名称自动从配置中找到对应条目并执行采集"""
    provider = provider.lower()
    matched_cfg = [cfg for cfg in CLOUD_PROVIDERS if cfg.get("provider", "").lower() == provider]
    if not matched_cfg:
        raise HTTPException(status_code=404, detail=f"Cloud provider '{provider}' not configured")
    try:
        return collect_cloud(matched_cfg[0])
    except Exception as e:
        logger.error(f"Provider collection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Provider collection failed")


@router.get(
    "/{provider}/history",
    response_model=List[Dict[str, Any]],
    summary="获取指定云平台采集历史",
    responses={
        (200): {"description": "采集历史列表"},
        (401): {"description": "未授权"},
        (500): {"description": "获取历史失败"},
    },
)
async def provider_history(
    provider: str = Path(..., description="cloud provider name: aws / azure / alibaba"),
    limit: int = Query(20, ge=1, le=100),
):
    """查询指定 provider 的采集历史（过滤后返回，按照 limit 截取）"""
    provider = provider.lower()
    try:
        full_history = get_cloud_collect_history(1000)
        filtered = [h for h in full_history if h.get("provider", "").lower() == provider]
        return filtered[:limit]
    except Exception as e:
        logger.error(f"Provider history retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to retrieve provider history")


@router.post(
    "/{provider}/repair",
    response_model=Dict[str, Any],
    summary="执行云平台修复操作",
    responses={
        (200): {"description": "修复执行结果"},
        (401): {"description": "未授权"},
        (404): {"description": "云平台未配置"},
        (500): {"description": "修复执行失败"},
    },
)
async def repair_provider(
    provider: str = Path(..., description="cloud provider name: aws / azure / alibaba"),
    payload: CloudRepairRequest = Body(...),
):
    """执行指定云平台的修复操作。
    请求体示例：
    {
        "action": "restart_instance",
        "params": {"instance_id": "i-12345678"}
    }
    """
    provider = provider.lower()
    matched_cfg = [cfg for cfg in CLOUD_PROVIDERS if cfg.get("provider", "").lower() == provider]
    if not matched_cfg:
        raise HTTPException(status_code=404, detail=f"Cloud provider '{provider}' not configured")
    try:
        from core.cloud_repair import execute_cloud_repair

        result = await execute_cloud_repair(matched_cfg[0], payload.action, **payload.params)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/{provider}/repair/history",
    response_model=List[Dict[str, Any]],
    summary="获取云平台修复历史",
    responses={
        (200): {"description": "修复历史列表"},
        (401): {"description": "未授权"},
        (500): {"description": "获取历史失败"},
    },
)
async def provider_repair_history(
    provider: str = Path(..., description="cloud provider name: aws / azure / alibaba"),
    limit: int = Query(20, ge=1, le=100),
):
    """查询指定 provider 的修复历史（倒序）"""
    provider = provider.lower()
    try:
        from core.cloud_repair import get_cloud_repair_history

        full_history = get_cloud_repair_history(1000)
        filtered = [h for h in full_history if h.get("provider", "").lower() == provider]
        return filtered[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
