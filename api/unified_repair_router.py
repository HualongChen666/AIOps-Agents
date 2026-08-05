# -*- coding: utf-8 -*-
"""
统一修复路由 - 合并所有平台的修复接口

提供对 Windows、Linux、Docker、K8s 等平台的统一修复接口。
通过 platform 参数区分不同平台。
🔧 重构:使用策略模式替代 if/elif 链
"""

import logging
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from api.schemas import UnifiedRepairRequest


# 🔧 重构:使用策略模式
from core.platform_strategies import get_platform_strategy

# Define PlatformType
PlatformType = Literal["windows", "linux", "docker", "k8s"]

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/repairs", tags=["统一修复"]
)


# ============================================================
# 接口1:获取所有可用修复脚本列表
# ============================================================
@router.get(
    "/scripts",
    summary="获取所有可用修复脚本",
    responses={
        200: {
            "description": "修复脚本列表",
            "content": {
                "application/json": {
                    "example": {
                        "scripts": {
                            "windows": [{"key": "kill_process", "name": "终止进程"}],
                            "linux": [{"key": "restart_service", "name": "重启服务"}],
                        }
                    }
                }
            },
        },
        400: {"description": "不支持的平台"},
        401: {"description": "未授权"},
        500: {"description": "服务器内部错误"},
    },
)
async def list_scripts(
    platform: Optional[PlatformType] = Query(None, description="按平台过滤脚本")
) -> dict[str, Any]:
    """
    返回预置修复脚本列表
    支持按平台过滤
    🔧 重构:使用策略模式
    """
    logger.info(f"请求修复脚本列表, platform={platform}")
    try:
        if platform is None:
            # 返回所有平台的脚本
            from core.platform_strategies import get_all_platform_strategies

            strategies = get_all_platform_strategies()
            scripts = {plat: strat.get_scripts() for plat, strat in strategies.items()}
        else:
            strategy = get_platform_strategy(platform)
            scripts = strategy.get_scripts()

        logger.debug(
            f"返回 {len(scripts) if isinstance(scripts, dict) else len(scripts)} 个可用修复脚本"
        )
        return {"scripts": scripts}
    except ValueError as e:
        logger.error(f"不支持的平台: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取修复脚本列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取修复脚本列表失败: {str(e)[:200]}")


# ============================================================
# 🔧 重构：run_repair 辅助函数（降低复杂度）
# ============================================================


def _validate_host_name_requirement(platform: str, host_name: Optional[str]) -> None:
    """验证平台是否需要 host_name 参数
    🔧 重构:使用策略模式
    """
    strategy = get_platform_strategy(platform)
    if strategy.requires_host_name() and not host_name:
        raise HTTPException(
            status_code=422, detail=f"{platform.capitalize()} 平台需要提供 host_name 参数"
        )


async def _execute_platform_repair(
    platform: str,
    script_key: str,
    host_name: Optional[str],
    params: dict[str, str],
) -> dict[str, Any]:
    """执行特定平台的修复
    🔧 重构:使用策略模式
    """
    strategy = get_platform_strategy(platform)
    # Ensure host_name is not None when passed to execute_repair
    host_name_str = host_name if host_name is not None else ""
    return await strategy.execute_repair(script_key, host_name_str, params)


def _validate_repair_result(result: Any) -> dict[str, Any]:
    """验证修复结果类型"""
    if result is None:
        logger.error("execute_repair 返回 None,修复引擎异常")
        raise HTTPException(status_code=500, detail="修复引擎未返回结果,请检查服务日志")

    if not isinstance(result, dict):
        logger.error(f"execute_repair 返回非 dict 类型: {type(result).__name__}")
        raise HTTPException(status_code=500, detail="修复引擎返回类型异常")

    return result


def _map_error_to_http_status(
    result: dict[str, Any],
    platform: str,
    script_key: str,
    operator_ip: str,
) -> None:
    """根据错误类型映射到 HTTP 状态码"""
    if result.get("success"):
        return

    if "error" not in result:
        return

    error_msg = str(result["error"])

    # 命令被护栏拦截 → 403
    if result.get("blocked"):
        safe_alt = result.get("safe_alternative", "")
        detail = f"指令被护栏拦截: {error_msg}"
        if safe_alt:
            detail += f"\n安全替代方案: {safe_alt}"
        logger.warning(
            f"修复被护栏拦截 | operator={operator_ip} | "
            f"platform={platform} | script_key='{script_key}'"
        )
        raise HTTPException(status_code=403, detail=detail)

    # 脚本不存在 → 404
    if "未知修复脚本" in error_msg or "not found" in error_msg.lower():
        logger.warning(f"修复脚本不存在 | platform={platform} | script_key='{script_key}'")
        raise HTTPException(status_code=404, detail=error_msg)

    # 参数校验错误 → 422
    param_error_keywords = ("pid", "service_name", "缺少必要参数", "必须为", "禁止操作", "不允许")
    if any(kw in error_msg for kw in param_error_keywords):
        logger.warning(
            f"修复参数校验失败 | platform={platform} | script_key='{script_key}' | {error_msg}"
        )
        raise HTTPException(status_code=422, detail=error_msg)

    # 其他执行失败 → 500
    logger.warning(
        f"修复脚本执行失败 | operator={operator_ip} | "
        f"platform={platform} | script_key='{script_key}' | error={error_msg}"
    )
    raise HTTPException(status_code=500, detail=error_msg)


# ============================================================
# 接口2:执行修复脚本
# ============================================================
@router.post(
    "/execute",
    summary="执行修复脚本",
    responses={
        200: {
            "description": "修复执行结果",
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
        400: {"description": "参数错误"},
        401: {"description": "未授权"},
        403: {"description": "指令被护栏拦截"},
        404: {"description": "修复脚本不存在"},
        422: {"description": "参数校验失败"},
        500: {"description": "修复引擎内部错误"},
    },
)
async def run_repair(
    req: UnifiedRepairRequest,
    request: Request,
) -> dict[str, Any]:
    """
    统一执行修复脚本
    根据 platform 参数路由到对应的修复引擎
    """
    operator_ip = request.client.host if request.client else "unknown"

    logger.warning(
        f"收到修复请求 | operator={operator_ip} | "
        f"platform={req.platform} | script_key='{req.script_key}'"
    )

    try:
        # 验证 host_name 要求
        _validate_host_name_requirement(req.platform, req.host_name)

        # 执行平台修复
        result = await _execute_platform_repair(
            req.platform, req.script_key, req.host_name, req.params
        )
    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"不支持的平台: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(
            f"执行修复脚本时发生未预期异常: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"修复引擎内部错误: {str(e)[:200]}")

    # 验证结果类型
    result = _validate_repair_result(result)

    # 错误码细分
    _map_error_to_http_status(result, req.platform, req.script_key, operator_ip)

    logger.info(
        f"修复脚本执行成功 | operator={operator_ip} | "
        f"platform={req.platform} | script_key='{req.script_key}' | "
        f"output_length={len(str(result.get('output', '')))}"
    )
    return result


# ============================================================
# 接口3:获取修复历史记录
# ============================================================
@router.get(
    "/history",
    summary="获取修复历史记录",
    responses={
        200: {"description": "修复历史记录"},
        401: {"description": "未授权"},
        500: {"description": "获取失败"},
    },
)
async def get_history(
    platform: Optional[PlatformType] = Query(None, description="按平台过滤历史记录"),
    limit: int = Query(
        default=20,
        ge=1,
        le=500,
        description="返回记录数量上限,范围 1-500",
    ),
) -> dict[str, Any]:
    """
    返回最近的修复执行历史记录(时间倒序)
    支持按平台过滤
    🔧 重构:使用策略模式
    """
    safe_limit = max(1, min(500, int(limit) if limit else 20))

    logger.info(f"请求修复历史记录, platform={platform}, limit={safe_limit}")

    try:
        if platform is None:
            # 返回 Windows 修复历史（默认，保持向后兼容）
            from core.repair_engine import get_repair_history

            records = get_repair_history(safe_limit)
        else:
            strategy = get_platform_strategy(platform)
            records = strategy.get_history(safe_limit)

        total = len(records)

        logger.debug(f"修复历史查询成功 | platform={platform} | 返回={total}条")

        return {
            "total": total,
            "records": records,
        }
    except ValueError as e:
        logger.error(f"不支持的平台: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"获取修复历史记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取修复历史失败: {str(e)[:200]}")
