# -*- coding: utf-8 -*-
from typing import Dict, List

from fastapi import APIRouter, HTTPException

from api.common import handle_service_error
from core.macos_collector import collect_macos_metrics
from core.macos_repair import execute_macos_repair

router = APIRouter(prefix="/api/macos", tags=["macOS"])


@router.get(
    "/metrics",
    summary="获取 macOS 主机指标（批量）",
    responses={
        200: {
            "description": "macOS主机指标",
            "content": {
                "application/json": {
                    "example": {
                        "host1": {"cpu": 0.23, "mem": 0.56, "disk": 0.45},
                        "host2": {"cpu": 0.35, "mem": 0.68, "disk": 0.52},
                    }
                }
            },
        },
        500: {"description": "采集失败"},
    },
)
async def get_macos_metrics(hosts: List[str] = None):
    """
    如果未提供 hosts 参数，则返回所有已注册的 macOS 主机的最新快照。
    返回示例:
    {
        "host1": {"cpu": 0.23, "mem": 0.56, ...},
        "host2": {...}
    }
    """
    try:
        data = await collect_macos_metrics(hosts)
        return data
    except Exception as e:
        handle_service_error(e, "macOS 指标采集")


@router.post(
    "/repair",
    summary="在指定 macOS 主机上执行修复脚本",
    responses={
        200: {
            "description": "修复执行成功",
            "content": {
                "application/json": {
                    "example": {
                        "host": "macbook-pro-01",
                        "script": "clear_cache",
                        "result": {"success": True, "output": "Cache cleared"},
                    }
                }
            },
        },
        500: {"description": "执行失败"},
    },
)
async def post_macos_repair(host: str, script_name: str, args: Dict = None):
    """立即在目标 macOS 主机上运行指定脚本并返回执行结果"""
    try:
        result = await execute_macos_repair(host, script_name, args or {})
        return {"host": host, "script": script_name, "result": result}
    except Exception as e:
        handle_service_error(e, "macOS 修复执行")
