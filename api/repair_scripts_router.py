# -*- coding: utf-8 -*-
"""
修复脚本资源路由

修复脚本是独立资源，不应嵌套在 repairs 下。
提供修复脚本的查询和管理功能。
🔧 重构:使用策略模式替代 if/elif 链
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Path

# 🔧 重构:使用策略模式
from core.platform_strategies import get_all_platform_strategies, get_platform_strategy

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/repair-scripts",
    tags=["修复脚本"],
)


# ============================================================
# 接口1:获取所有修复脚本
# ============================================================
@router.get(
    "/",
    summary="获取所有修复脚本",
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
        401: {"description": "未授权"},
        500: {"description": "服务器内部错误"},
    },
)
async def list_all_scripts() -> dict[str, Any]:
    """
    返回所有平台的修复脚本列表
    🔧 重构:使用策略模式
    """
    logger.info("请求所有修复脚本列表")
    try:
        strategies = get_all_platform_strategies()
        scripts = {plat: strat.get_scripts() for plat, strat in strategies.items()}
        logger.debug(f"返回 {len(scripts)} 个平台的修复脚本")
        return {"scripts": scripts}
    except Exception as e:
        logger.error(f"获取修复脚本列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取修复脚本列表失败: {str(e)[:200]}")


# ============================================================
# 接口2:按平台获取修复脚本
# ============================================================
@router.get(
    "/{platform}",
    summary="按平台获取修复脚本",
    responses={
        200: {
            "description": "指定平台的修复脚本列表",
            "content": {
                "application/json": {
                    "example": {
                        "platform": "windows",
                        "scripts": [{"key": "kill_process", "name": "终止进程"}],
                    }
                }
            },
        },
        400: {"description": "不支持的平台"},
        401: {"description": "未授权"},
        500: {"description": "服务器内部错误"},
    },
)
async def list_platform_scripts(
    platform: str = Path(..., description="平台类型: windows, linux, docker, kubernetes")
) -> dict[str, Any]:
    """
    返回指定平台的修复脚本列表
    🔧 重构:使用策略模式
    """
    logger.info(f"请求 {platform} 平台修复脚本列表")
    try:
        strategy = get_platform_strategy(platform)
        scripts = strategy.get_scripts()

        logger.debug(f"返回 {len(scripts)} 个 {platform} 修复脚本")
        return {"platform": platform, "scripts": scripts}
    except ValueError as e:
        logger.error(f"不支持的平台: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取 {platform} 修复脚本列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取修复脚本列表失败: {str(e)[:200]}")
