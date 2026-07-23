# -*- coding: utf-8 -*-
import copy
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from loguru import logger as _logger
from pydantic import BaseModel, Field, field_validator

from config import WIN_HOSTS
from core.api_helpers import find_host_config, get_operator_ip, hostname_field_validator
from core.windows_repair import (
    WINDOWS_REPAIR_SCRIPTS,
    execute_windows_repair,
    get_windows_repair_history,
)

router = APIRouter(prefix="/api/v1/platforms/windows", tags=["Windows 修复"])


def find_windows_host_config(host_name: str) -> Optional[dict]:
    """根据主机名或 IP 在 WIN_HOSTS 中查找对应的配置字典。

    返回值若为 ``None`` 表示未匹配到主机，调用方应返回 404 错误。
    🔧 重构:内部调用 core.api_helpers.find_host_config
    """
    return find_host_config(host_name, WIN_HOSTS, "name", "ip")


class WindowsRepairRequest(BaseModel):
    host_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="目标 Windows 主机名称或 IP",
        examples=["win-server-01"],
    )
    script_key: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="修复脚本键名，对应 WINDOWS_REPAIR_SCRIPTS",
        examples=["restart_service"],
    )
    params: dict[str, str] = Field(
        default_factory=dict, description="脚本所需的占位参数，如 {'service_name': 'Spooler'}"
    )

    @field_validator("host_name")
    @classmethod
    def _validate_host_name(cls, v: str) -> str:
        return hostname_field_validator(v)

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {
            "example": {"host_name": "example", "script_key": "example", "params": {}}
        },
    }


@router.get(
    "/repair/scripts",
    summary="获取 Windows 修复脚本列表",
    responses={
        (200): {
            "description": "修复脚本列表",
            "content": {
                "application/json": {
                    "example": {
                        "scripts": {
                            "kill_process": {"name": "终止进程", "description": "终止指定进程"},
                            "restart_service": {"name": "重启服务", "description": "重启指定服务"},
                        }
                    }
                }
            },
        },
        (500): {"description": "获取失败"},
    },
)
async def list_repair_scripts() -> dict[str, Any]:
    """返回所有预置的 Windows 修复脚本（深拷贝，防止外部修改）。"""
    _logger.info("请求 Windows 修复脚本列表")
    try:
        scripts = copy.deepcopy(dict(WINDOWS_REPAIR_SCRIPTS))
        return {"scripts": scripts}
    except Exception as e:
        _logger.error(f"获取 Windows 修复脚本失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取脚本列表失败")


@router.post(
    "/repair/execute",
    summary="在指定 Windows 主机上执行修复脚本",
    responses={
        (200): {
            "description": "执行结果",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "output": "Process killed successfully",
                        "exit_code": 0,
                        "duration_sec": 1.5,
                    }
                }
            },
        },
        (403): {"description": "指令被护栏拦截"},
        (404): {"description": "主机或脚本不存在"},
        (422): {"description": "参数校验失败"},
        (500): {"description": "执行失败"},
    },
)
async def run_repair(req: WindowsRepairRequest, request: Request) -> dict[str, Any]:
    """执行单台 Windows 主机的修复脚本。

    返回示例结构与 Linux 修复保持一致，错误码细分如下：
    - 404: 主机或脚本不存在
    - 403: 脚本被护栏拦截
    - 422: 参数校验错误（如 PID 非数字、受保护等）
    - 500: 其他内部错误
    🔧 重构:使用 core.api_helpers.get_operator_ip
    """
    operator_ip = get_operator_ip(request)
    _logger.warning(
        f"Windows 修复请求 | operator={operator_ip} | host={req.host_name} |"
        f" script={req.script_key} | params={req.params}"
    )
    host_cfg = find_windows_host_config(req.host_name)
    if not host_cfg:
        raise HTTPException(status_code=404, detail=f"未找到 Windows 主机: {req.host_name}")
    try:
        result = await execute_windows_repair(req.script_key, req.params or {})
    except Exception as e:
        _logger.error(f"执行 Windows 修复异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Windows repair execution failed")
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="修复引擎返回非 dict 类型")
    if result.get("error"):
        err_msg = str(result["error"]).lower()
        if "未知的 windows 修复脚本" in err_msg:
            raise HTTPException(status_code=404, detail=result["error"])
        if any(keyword in err_msg for keyword in ["pid", "service_name", "必须为", "禁止操作"]):
            raise HTTPException(status_code=422, detail=result["error"])
        raise HTTPException(status_code=500, detail=result["error"])
    _logger.info(
        f"Windows 修复成功 | operator={operator_ip} | host={req.host_name} |"
        f" script={req.script_key}"
    )
    return result


@router.get(
    "/repair/history",
    summary="获取 Windows 修复历史记录",
    responses={
        (200): {
            "description": "修复历史记录",
            "content": {
                "application/json": {
                    "example": {
                        "total": 5,
                        "records": [
                            {
                                "host": "win-server-01",
                                "script": "kill_process",
                                "success": True,
                                "timestamp": "2026-07-03T09:00:00Z",
                            }
                        ],
                        "filter": {"host_name": "win-server-01"},
                    }
                }
            },
        },
        (500): {"description": "获取失败"},
    },
)
async def get_history(
    limit: int = Query(default=20, ge=1, le=200),
    host_name: Optional[str] = Query(
        default=None, max_length=128, description="按主机名过滤（留空返回全部）"
    ),
) -> dict[str, Any]:
    """返回 Windows 修复执行历史。

    - ``limit`` 控制返回条数，上限 200 防止单次返回过多。
    - ``host_name`` 可选，用于过滤特定主机的历史记录。
    """
    _logger.info(f"请求 Windows 修复历史 | limit={limit} | host_filter={host_name or '全部'}")
    try:
        query_limit = min(limit * 3, 600)
        history = get_windows_repair_history(query_limit)
        if host_name:
            host_name_clean = host_name.strip()
            history = [h for h in history if h.get("host") == host_name_clean]
        history = history[:limit]
        return {"total": len(history), "records": history, "filter": {"host_name": host_name}}
    except Exception as e:
        _logger.error(f"获取 Windows 修复历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取修复历史失败")
