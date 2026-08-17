# -*- coding: utf-8 -*-
# Docker 相关 API 路由

"""Docker 相关 API 路由

提供容器指标采集以及容器修复两大功能：
- GET  /api/docker/metrics   → 采集所有配置的 Docker 主机容器指标
- POST /api/docker/repair   → 对单个 Docker 主机执行修复脚本（如重启容器）

所有业务层实现均在 core.docker_* 中，保持与 Linux/Windows 的接口统一。

SECURITY: 所有端点需要认证才能访问
🔧 重构:使用 api.schemas.repair 统一修复请求模型
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from api.schemas.repair import DockerRepairRequest
from core.config import DOCKER_HOSTS
from core.docker_collector import collect_docker
from core.docker_repair import execute_repair_sync

# 使用项目统一的 Loguru logger
_logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/platforms/docker",
    tags=["Docker"],
)


# ============================================================
# 🔧 重构:DockerRepairRequest 已移至 api.schemas.repair
# ============================================================


@router.get(
    "/metrics",
    response_model=List[Dict[str, Any]],
    summary="采集 Docker 容器指标",
    responses={
        200: {"description": "Docker容器指标列表"},
        400: {"description": "Docker主机列表未配置"},
        401: {"description": "未授权"},
    },
)
async def get_docker_metrics() -> List[Dict[str, Any]]:
    """采集所有配置的 Docker 主机的容器指标。

    Returns:
        List of snapshot dicts, each conforming to the structure defined
        in ``core.docker_collector.collect_docker``.
    """
    if not DOCKER_HOSTS:
        raise HTTPException(status_code=400, detail="Docker 主机列表未配置 (DOCKER_HOSTS)")
    results: List[Dict[str, Any]] = []
    for host_cfg in DOCKER_HOSTS:
        try:
            snapshot = collect_docker(host_cfg)
            if snapshot:
                results.append(snapshot)
        except Exception as exc:
            _logger.error(f"Docker 主机 {host_cfg.get('host')} 采集失败: {exc}")
            # 继续采集其他主机，不抛出导致整体失败
    return results


@router.post(
    "/repair",
    summary="执行 Docker 修复脚本",
    responses={
        200: {
            "description": "修复执行成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "output": "Container restarted successfully",
                        "exit_code": 0,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        404: {"description": "Docker主机未配置"},
        500: {"description": "执行异常"},
    },
)
async def post_docker_repair(payload: DockerRepairRequest) -> Dict[str, Any]:
    """对指定 Docker 主机执行修复脚本。

    Expected JSON payload:
        {
            "host": "10.0.0.5",
            "script_name": "restart_container",
            "args": {"container_id": "abc123def456"}
        }
    """
    # 在 DOCKER_HOSTS 中查找匹配的 host 配置
    host_cfg = next((h for h in DOCKER_HOSTS if h.get("host") == payload.host), None)
    if not host_cfg:
        raise HTTPException(
            status_code=404, detail=f"Docker 主机 {payload.host} 未在 DOCKER_HOSTS 中配置"
        )
    try:
        result = await execute_repair_sync(payload.host, payload.script_name, payload.args)
    except Exception as exc:
        _logger.error(f"Docker 修复执行异常: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))
    return result
