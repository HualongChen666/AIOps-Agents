# -*- coding: utf-8 -*-
import asyncio
import copy
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from config import LINUX_HOSTS, LINUX_SSH_TIMEOUT
from core.api_helpers import find_host_config, get_operator_ip, hostname_field_validator
from core.authentication import get_current_active_user
from core.linux_collector import (
    collect_all_linux,
    collect_linux_host,
    get_available_metrics,
    get_configured_hosts,
)
from core.linux_repair import execute_linux_repair, get_linux_repair_scripts

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/platforms/linux",
    tags=["Linux 监控"],
    dependencies=[Depends(get_current_active_user)],
)
_METRICS_LIST_MAX = 50


def find_linux_host_config(host_name: str) -> Optional[dict]:
    """
    根据主机名或 IP 查找配置

    🔧 LR2:跨模块复用接口,日志/拓扑等模块均通过本函数查找
    🔧 LR6:返回类型从 dict|None 改为 Optional[dict],类型更清晰
    🔧 重构:内部调用 core.api_helpers.find_host_config

    Args:
        host_name: 主机名或 IP
    Returns:
        匹配的配置字典 / None(找不到)
    """
    hosts_list = list(LINUX_HOSTS.values()) if isinstance(LINUX_HOSTS, dict) else LINUX_HOSTS
    return find_host_config(host_name, hosts_list, "name", "host")


class LinuxRepairRequest(BaseModel):
    host_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="目标主机名称或 IP",
        examples=["linux-server-01"],
    )
    script_key: str = Field(
        ..., min_length=1, max_length=64, description="修复脚本键名", examples=["clear_tmp"]
    )
    params: dict[str, str] = Field(default_factory=dict, description="脚本参数")

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


class LinuxCollectRequest(BaseModel):
    host_name: str = Field(..., min_length=1, max_length=128, description="目标主机名称或 IP")
    metrics: Optional[list[str]] = Field(default=None, description="要采集的指标列表,None=全量")

    @field_validator("host_name")
    @classmethod
    def _validate_host_name(cls, v: str) -> str:
        return hostname_field_validator(v)

    @field_validator("metrics")
    @classmethod
    def _validate_metrics(cls, v: Optional[list[str]]) -> Optional[list[str]]:
        if v is None:
            return None
        if not isinstance(v, list):
            raise ValueError("metrics 必须是字符串列表")
        if len(v) > _METRICS_LIST_MAX:
            raise ValueError(f"metrics 列表长度超出 {_METRICS_LIST_MAX}: {len(v)}")
        cleaned = []
        for item in v:
            if not isinstance(item, str):
                continue
            stripped = item.strip()[:64]
            if stripped:
                cleaned.append(stripped)
        return cleaned

    model_config = {
        "extra": "ignore",
        "json_schema_extra": {"example": {"host_name": "example", "metrics": "example"}},
    }


@router.get(
    "/hosts",
    summary="获取已配置的 Linux 主机列表",
    responses={
        (200): {
            "description": "Linux主机列表",
            "content": {
                "application/json": {
                    "example": {
                        "total": 3,
                        "hosts": [
                            {
                                "name": "linux-server-01",
                                "host": "192.168.1.10",
                                "role": "app",
                                "layer": "backend",
                            }
                        ],
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "获取失败"},
    },
)
async def list_hosts() -> dict[str, Any]:
    """
    返回所有已配置的 Linux 主机(不含敏感信息)

    🔧 LR7 [P2]:返回字段含 role/layer/downstream(供前端拓扑可视化)
        - 此修复依赖 linux_collector 修订版的 get_configured_hosts
        - 旧版 get_configured_hosts 不返回这些字段,前端会显示空值
    """
    logger.info("请求 Linux 主机列表")
    try:
        hosts = get_configured_hosts()
        return {"total": len(hosts), "hosts": hosts}
    except Exception as e:
        logger.error(f"获取主机列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取主机列表失败,请查看服务日志")


@router.get(
    "/metrics/available",
    summary="获取可采集的指标维度列表",
    responses={
        (200): {
            "description": "可采集指标列表",
            "content": {
                "application/json": {
                    "example": {
                        "total": 20,
                        "metrics": [
                            {"key": "cpu", "name": "CPU使用率", "unit": "%"},
                            {"key": "memory", "name": "内存使用率", "unit": "%"},
                        ],
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "获取失败"},
    },
)
async def list_available_metrics() -> dict[str, Any]:
    """返回所有可采集的 Linux 指标维度和描述"""
    logger.info("请求可用指标列表")
    try:
        metrics = get_available_metrics()
        return {"total": len(metrics), "metrics": metrics}
    except Exception as e:
        logger.error(f"获取指标列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取指标列表失败")


@router.get(
    "/collect/all",
    summary="采集所有 Linux 主机指标",
    responses={
        (200): {
            "description": "所有主机指标采集结果",
            "content": {
                "application/json": {
                    "example": {
                        "total": 3,
                        "hosts": [
                            {
                                "host": "linux-server-01",
                                "cpu": {"usage_percent": 45.2},
                                "memory": {"usage_percent": 68.3},
                            }
                        ],
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (504): {"description": "采集超时"},
        (500): {"description": "采集失败"},
    },
)
async def collect_all_hosts_endpoint() -> dict[str, Any]:
    """
    并行采集所有已配置 Linux 主机的全量指标

    ✅ 修复1:增加整体超时保护,防止长时间阻塞
    🔧 LR1 [P1]:函数从 collect_all 改名,避免与 [6] collector.collect_all 混淆
                  函数名仅影响内部,URL 路径不变(保持向后兼容)
    """
    logger.info("请求采集全部 Linux 主机")
    if not LINUX_HOSTS:
        return {"total": 0, "hosts": [], "message": "未配置任何 Linux 主机"}
    total_timeout = LINUX_SSH_TIMEOUT * 2 + len(LINUX_HOSTS) * 5
    try:
        results = await asyncio.wait_for(collect_all_linux(), timeout=total_timeout)
        return {"total": len(results), "hosts": results}
    except asyncio.TimeoutError:
        logger.error(f"全量采集整体超时(>{total_timeout}s),可能网络不可达或主机过多")
        raise HTTPException(status_code=504, detail=f"采集超时(>{total_timeout}s),请检查网络连通性")
    except asyncio.CancelledError:
        logger.info("全量采集被取消")
        raise
    except Exception as e:
        logger.error(f"全量采集失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="全量采集失败,请查看服务日志")


@router.post(
    "/collect/host",
    summary="采集指定 Linux 主机指标",
    responses={
        (200): {
            "description": "主机指标采集结果",
            "content": {
                "application/json": {
                    "example": {
                        "host": "linux-server-01",
                        "cpu": {"usage_percent": 45.2},
                        "memory": {"usage_percent": 68.3},
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (404): {"description": "主机不存在"},
        (504): {"description": "采集超时"},
        (500): {"description": "采集失败"},
    },
)
async def collect_single_host(req: LinuxCollectRequest) -> dict[str, Any]:
    """
    对指定 Linux 主机执行全量或指定维度的指标采集
    ✅ 修复3:增加单主机超时保护
    🔧 LR5 [P1]:metrics 列表已在 Pydantic 层校验
    """
    logger.info(f"请求采集主机: {req.host_name}")
    host_config = find_linux_host_config(req.host_name)
    if not host_config:
        raise HTTPException(status_code=404, detail=f"未找到主机: {req.host_name}")
    host_timeout = LINUX_SSH_TIMEOUT * 3
    try:
        result = await asyncio.wait_for(
            collect_linux_host(host_config, req.metrics), timeout=host_timeout
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"主机采集超时: {req.host_name}")
        raise HTTPException(
            status_code=504, detail=f"主机 {req.host_name} 采集超时,请检查 SSH 连通性"
        )
    except asyncio.CancelledError:
        logger.info(f"主机采集被取消: {req.host_name}")
        raise
    except Exception as e:
        logger.error(f"主机采集失败: {req.host_name} | {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"主机 {req.host_name} 采集失败")


@router.get(
    "/repair/scripts",
    summary="获取 Linux 修复脚本列表",
    responses={
        (200): {
            "description": "修复脚本列表",
            "content": {
                "application/json": {
                    "example": {
                        "scripts": [
                            {"key": "clear_tmp", "name": "清理临时文件", "params": {}},
                            {
                                "key": "restart_service",
                                "name": "重启服务",
                                "params": {"service_name": "nginx"},
                            },
                        ]
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (500): {"description": "获取失败"},
    },
)
async def list_repair_scripts() -> dict[str, Any]:
    """
    返回所有可用的 Linux 修复脚本

    🔧 LR4 [P1]:返回深拷贝,防止前端修改 params 字段污染原数据
        - 此修复依赖 linux_repair 修订版的 get_linux_repair_scripts(已含深拷贝)
        - 旧版直接返回引用,此处再加一层 copy.deepcopy 双重保险
    """
    logger.info("请求 Linux 修复脚本列表")
    try:
        scripts = get_linux_repair_scripts()
        scripts_safe = copy.deepcopy(scripts)
        return {"scripts": scripts_safe}
    except Exception as e:
        logger.error(f"获取修复脚本列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取脚本列表失败")


@router.post(
    "/repair/execute",
    summary="执行 Linux 修复脚本",
    responses={
        (200): {
            "description": "修复执行成功",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "output": "Command executed successfully",
                        "exit_code": 0,
                    }
                }
            },
        },
        (202): {
            "description": "已转入审批队列",
            "content": {
                "application/json": {
                    "example": {
                        "status": "pending_approval",
                        "alert_id": "alert_123",
                        "reason": "High risk operation",
                    }
                }
            },
        },
        (401): {"description": "未授权"},
        (403): {"description": "指令被护栏拦截"},
        (404): {"description": "主机或脚本不存在"},
        (422): {"description": "参数校验失败"},
        (500): {"description": "执行异常"},
    },
)
async def run_repair(req: LinuxRepairRequest, request: Request) -> dict[str, Any]:
    """
    在指定 Linux 主机上执行修复脚本
    含高危指令护栏检查

    HTTP 状态码说明:
    - 200: 执行成功
    - 202: 已转入审批队列
    - 403: 指令被拦截
    - 404: 主机/脚本未找到
    - 422: 参数校验失败(pid 非数字、PID 受保护等)
    - 500: 执行异常

    🔧 LR3 [P1]:错误码细分(422 / 403 / 404 / 500)
    🔧 LR8 [P2]:记录操作人 IP
    🔧 重构:使用 core.api_helpers.get_operator_ip
    """
    operator_ip = get_operator_ip(request)
    logger.warning(
        f"Linux 修复请求 | operator={operator_ip} | host={req.host_name} | script={req.script_key}"
        f" | params={req.params}"
    )
    try:
        result = await execute_linux_repair(req.host_name, req.script_key, req.params)
    except asyncio.CancelledError:
        logger.info(f"Linux 修复执行被取消 | host={req.host_name}")
        raise
    except Exception as e:
        logger.error(f"Linux 修复执行异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="修复执行内部错误,请查看服务日志")
    if result is None:
        raise HTTPException(status_code=500, detail="修复引擎未返回结果")
    if not isinstance(result, dict):
        raise HTTPException(status_code=500, detail="修复引擎返回类型异常")
    if result.get("blocked"):
        reason = result.get("reason", "指令被拦截")
        alt = result.get("safe_alternative", "")
        detail_msg = f"指令被拦截: {reason}"
        if alt:
            detail_msg += f"\n安全替代方案: {alt}"
        logger.warning(f"Linux 修复被护栏拦截 | operator={operator_ip} | host={req.host_name}")
        raise HTTPException(status_code=403, detail=detail_msg)
    if result.get("pending_approval"):
        logger.info(
            f"Linux 修复已转入审批 | operator={operator_ip} | alert_id={result.get('alert_id')}"
        )
        return {
            "status": "pending_approval",
            "alert_id": result.get("alert_id"),
            "reason": result.get("reason"),
            "proposal": result.get("proposal", ""),
            "rule": result.get("rule", ""),
            "approve_url": result.get("approve_url", ""),
            "message": "高风险操作已转入审批队列",
        }
    if not result.get("success") and "error" in result:
        error_msg = str(result["error"])
        if "未知修复脚本" in error_msg or "未找到主机" in error_msg:
            logger.warning(f"Linux 修复 404 | host={req.host_name} | {error_msg}")
            raise HTTPException(status_code=404, detail=error_msg)
        param_error_keywords = ("pid", "service_name", "缺少参数", "必须为", "禁止操作", "不允许")
        if any(kw in error_msg for kw in param_error_keywords):
            logger.warning(f"Linux 修复参数错误 | host={req.host_name} | {error_msg}")
            raise HTTPException(status_code=422, detail=error_msg)
        logger.warning(
            f"Linux 修复失败 | operator={operator_ip} | host={req.host_name} | {error_msg}"
        )
        raise HTTPException(status_code=500, detail=error_msg)
    logger.info(
        f"Linux 修复成功 | operator={operator_ip} | host={req.host_name} | script={req.script_key}"
    )
    return result
