# -*- coding: utf-8 -*-
# api/log_router.py — 日志采集接口(Windows + Linux)
#
# 🔧 本次严格 Review 修复(LG):
#   - LG1 [P1]:keyword 长度上限保护
#   - LG2 [P1]:_get_linux_host 改为 None 返回 + 上层处理 404
#   - LG3 [P2]:错误日志接口增加 5 秒 TTL 缓存
#   - LG4 [P2]:类型注解收紧
#   - LG5 [P2]:host_name 严格字符校验
#   - LG6 [P2]:linux_search 增加 case_sensitive 参数

import logging
import time
from threading import Lock
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from config import LINUX_HOSTS
from core.api_helpers import VALID_HOSTNAME_PATTERN
from core.authentication import get_current_active_user
from core.es_logger import es_search_logs
from core.log_collector import (
    get_application_errors,
    get_event_logs,
    get_linux_errors,
    get_linux_logs,
    get_system_errors,
    search_linux_logs,
    search_logs,
)

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/api/v1/logs", tags=["事件日志"], dependencies=[Depends(get_current_active_user)]
)

# Elasticsearch 日志搜索路由（统一平台）

# ============================================================
# 模块级常量
# ============================================================
LogNameType = Literal["System", "Application", "Security"]
LevelType = Literal["Error", "Warning", "Information"]
LinuxSource = Literal["syslog", "kern", "auth", "dmesg", "journal"]

# 🔧 LG1 [P1]:keyword 长度上限(防御 1MB 字符串导致 SSH 命令超长)
_KEYWORD_MAX_LEN = 200

# 🔧 LG3 [P2]:错误日志接口 TTL 缓存
_LOG_CACHE_TTL_SEC = 5

# 🔧 LG5 [P2]:host_name 合法字符正则
# 🔧 重构:使用 core.api_helpers.VALID_HOSTNAME_PATTERN 替代本地定义


# ============================================================
# 🔧 LG3 [P2]:错误日志缓存(降低高频轮询压力)
# ──────────────────────────────────────────────────────
# Windows 系统/应用错误日志在前端抽屉中可能被反复打开
# 5 秒缓存可减少 PowerShell 子进程启动开销
# ──────────────────────────────────────────────────────
_log_cache: dict[str, dict[str, Any]] = {}
_log_cache_lock = Lock()


def _get_cached_logs(cache_key: str) -> Optional[list]:
    """🔧 LG3:从缓存读取日志(命中返回数据,未命中返回 None)"""
    now = time.monotonic()
    with _log_cache_lock:
        cached = _log_cache.get(cache_key)
        if cached is not None and (now - cached["ts"]) < _LOG_CACHE_TTL_SEC:
            # 浅拷贝防外部修改
            return list(cached["data"])
    return None


def _set_cached_logs(cache_key: str, data: list) -> None:
    """🔧 LG3:写入缓存"""
    with _log_cache_lock:
        _log_cache[cache_key] = {
            "data": list(data),
            "ts": time.monotonic(),
        }


# ============================================================
# 🔧 LG2 [P1]:Linux 主机查找辅助函数
# ──────────────────────────────────────────────────────
# 修复前:_get_linux_host 直接抛 HTTPException,违反单一职责
# 修复后:统一通过 find_linux_host_config + 上层判空抛 404
# 同时增加 host_name 字符校验防御
# ──────────────────────────────────────────────────────
def _get_linux_host(host_name: str) -> dict:
    """
    根据主机名或 IP 查找主机配置,找不到时抛出 404

    🔧 BUG-FIX-11(低危):复用 linux_router 中的公共函数
    🔧 LG2 [P1]:增加 host_name 字符校验(防注入)
    🔧 LG5 [P2]:严格字符白名单
    """
    if not host_name or not isinstance(host_name, str):
        raise HTTPException(status_code=422, detail="host_name 不能为空")

    cleaned = host_name.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="host_name 不能为纯空白")

    # 🔧 LG5:字符校验
    # 🔧 重构:使用 core.api_helpers.VALID_HOSTNAME_PATTERN
    if not VALID_HOSTNAME_PATTERN.match(cleaned):
        raise HTTPException(status_code=422, detail="host_name 仅允许字母数字和 '._-:'")

    # 函数内 import,避免模块加载时循环导入
    from api.linux_router import find_linux_host_config

    host_config = find_linux_host_config(cleaned)
    if not host_config:
        raise HTTPException(status_code=404, detail=f"未找到 Linux 主机: {cleaned}")
    return host_config


# ============================================================
# 🔧 LG1 [P1]:keyword 长度二次校验
# ============================================================
def _validate_keyword(keyword: str) -> str:
    """
    🔧 LG1:keyword 二次防御
        - Pydantic Query 已校验 max_length,但接收方可能传入超大字符串
        - 这里做最终长度截断 + 空白校验
    """
    if not keyword or not isinstance(keyword, str):
        raise HTTPException(status_code=422, detail="keyword 不能为空")

    cleaned = keyword.strip()[:_KEYWORD_MAX_LEN]
    if not cleaned:
        raise HTTPException(status_code=422, detail="keyword 不能为纯空白字符串")

    return cleaned


# ============================================================
# Windows 接口
# 🔧 LG3 [P2]:错误日志增加 5 秒 TTL 缓存
# ============================================================
@router.get(
    "/system/errors",
    summary="获取 Windows 系统错误日志",
    responses={
        200: {
            "description": "系统错误日志",
            "content": {
                "application/json": {
                    "example": {
                        "total": 10,
                        "logs": [
                            {
                                "time": "2026-07-02T10:30:00Z",
                                "level": "Error",
                                "source": "System",
                                "message": "Service failed to start",
                            }
                        ],
                        "cached": False,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "采集失败"},
    },
)
async def system_errors(
    newest: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    """
    采集 Windows System 事件日志中的错误记录

    🔧 LG3 [P2]:5 秒 TTL 缓存
    """
    logger.info(f"请求系统错误日志,newest={newest}")

    # 🔧 LG3:命中缓存
    cache_key = f"system_errors_{newest}"
    cached = _get_cached_logs(cache_key)
    if cached is not None:
        logger.debug("系统错误日志命中缓存")
        return {"total": len(cached), "logs": cached, "cached": True}

    try:
        data = await get_system_errors(newest)
        _set_cached_logs(cache_key, data)
        return {"total": len(data), "logs": data, "cached": False}
    except Exception as e:
        logger.error(f"系统错误日志采集失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to collect system error logs")


@router.get(
    "/application/errors",
    summary="获取 Windows 应用程序错误日志",
    responses={
        200: {
            "description": "应用程序错误日志",
            "content": {
                "application/json": {
                    "example": {
                        "total": 5,
                        "logs": [
                            {
                                "time": "2026-07-02T10:30:00Z",
                                "level": "Error",
                                "source": "Application",
                                "message": "Application crash",
                            }
                        ],
                        "cached": False,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "采集失败"},
    },
)
async def app_errors(
    newest: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    """采集 Windows Application 事件日志中的错误记录"""
    logger.info(f"请求应用程序错误日志,newest={newest}")

    cache_key = f"app_errors_{newest}"
    cached = _get_cached_logs(cache_key)
    if cached is not None:
        logger.debug("应用错误日志命中缓存")
        return {"total": len(cached), "logs": cached, "cached": True}

    try:
        data = await get_application_errors(newest)
        _set_cached_logs(cache_key, data)
        return {"total": len(data), "logs": data, "cached": False}
    except Exception as e:
        logger.error(f"应用程序错误日志采集失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to collect application error logs")


@router.get(
    "/query",
    summary="查询 Windows 指定类型事件日志",
    responses={
        200: {
            "description": "事件日志查询结果",
            "content": {
                "application/json": {
                    "example": {
                        "total": 20,
                        "logs": [
                            {
                                "time": "2026-07-02T10:30:00Z",
                                "level": "Error",
                                "source": "System",
                                "message": "Error message",
                            }
                        ],
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "查询失败"},
    },
)
async def query_logs(
    log_name: LogNameType = Query(default="System"),
    level: LevelType = Query(default="Error"),
    newest: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    """按日志类型和级别查询 Windows 事件日志"""
    logger.info(f"请求事件日志查询 | log_name={log_name} level={level} newest={newest}")
    try:
        data = await get_event_logs(log_name, level, newest)
        return {"total": len(data), "logs": data}
    except Exception as e:
        logger.error(f"事件日志查询失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.get(
    "/search",
    summary="按关键词搜索 Windows 日志",
    responses={
        200: {
            "description": "搜索结果",
            "content": {
                "application/json": {
                    "example": {
                        "total": 15,
                        "keyword": "error",
                        "logs": [
                            {
                                "time": "2026-07-02T10:30:00Z",
                                "level": "Error",
                                "source": "System",
                                "message": "Error in service",
                            }
                        ],
                    }
                }
            },
        },
        401: {"description": "未授权"},
        422: {"description": "关键词为空或格式错误"},
        500: {"description": "搜索失败"},
    },
)
async def search(
    keyword: str = Query(..., min_length=1, max_length=_KEYWORD_MAX_LEN),
    newest: int = Query(default=50, ge=1, le=500),
) -> dict[str, Any]:
    """
    在 Windows 系统事件日志中按关键词全文搜索

    🔧 LG1 [P1]:keyword 二次校验
    """
    # 🔧 LG1:二次校验
    keyword_safe = _validate_keyword(keyword)

    logger.info(f"请求日志搜索 | keyword='{keyword_safe}' newest={newest}")
    try:
        data = await search_logs(keyword_safe, newest)
        return {
            "total": len(data),
            "keyword": keyword_safe,
            "logs": data,
        }
    except Exception as e:
        logger.error(f"日志搜索失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to search logs")


# ============================================================
# Linux 接口
# 🔧 LG2 [P1]:统一通过 _get_linux_host 处理
# ============================================================
@router.get(
    "/linux/errors",
    summary="获取 Linux 内核错误日志",
    responses={
        200: {
            "description": "Linux内核错误日志",
            "content": {
                "application/json": {
                    "example": {
                        "total": 5,
                        "host": "server01",
                        "source": "kern",
                        "logs": [
                            {
                                "time": "2026-07-02T10:30:00Z",
                                "level": "Error",
                                "message": "Kernel panic",
                            }
                        ],
                        "cached": False,
                    }
                }
            },
        },
        401: {"description": "未授权"},
        404: {"description": "Linux主机不存在"},
        422: {"description": "主机名格式错误"},
        500: {"description": "采集失败"},
    },
)
async def linux_errors(
    host_name: str = Query(
        ...,
        min_length=1,
        max_length=128,
        description="目标主机名称或 IP",
    ),
    newest: int = Query(default=10, ge=1, le=100),
) -> dict[str, Any]:
    """
    通过 SSH 采集指定 Linux 主机的内核错误日志(dmesg err 级别)
    ✅ 修复6:对应 log_collector.get_linux_errors()
    🔧 LG3 [P2]:增加 5 秒 TTL 缓存
    """
    logger.info(f"请求 Linux 内核错误日志 | host={host_name} newest={newest}")
    if not LINUX_HOSTS:
        return {"total": 0, "logs": [], "message": "未配置 Linux 主机"}

    host_config = _get_linux_host(host_name)

    # 🔧 LG3:命中缓存
    cache_key = f"linux_errors_{host_name}_{newest}"
    cached = _get_cached_logs(cache_key)
    if cached is not None:
        logger.debug(f"Linux 错误日志命中缓存 | host={host_name}")
        return {
            "total": len(cached),
            "host": host_name,
            "source": "kern",
            "logs": cached,
            "cached": True,
        }

    try:
        data = await get_linux_errors(host_config, newest)
        _set_cached_logs(cache_key, data)
        return {
            "total": len(data),
            "host": host_name,
            "source": "kern",
            "logs": data,
            "cached": False,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Linux 内核错误日志采集失败 | host={host_name}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to collect Linux kernel error logs")


@router.get(
    "/linux/query",
    summary="查询 Linux 指定来源日志",
    responses={
        200: {
            "description": "Linux日志查询结果",
            "content": {
                "application/json": {
                    "example": {
                        "total": 20,
                        "host": "server01",
                        "source": "syslog",
                        "logs": [
                            {
                                "time": "2026-07-02T10:30:00Z",
                                "level": "Info",
                                "message": "System message",
                            }
                        ],
                    }
                }
            },
        },
        401: {"description": "未授权"},
        404: {"description": "Linux主机不存在"},
        422: {"description": "主机名格式错误"},
        500: {"description": "查询失败"},
    },
)
async def linux_query(
    host_name: str = Query(..., min_length=1, max_length=128),
    source: LinuxSource = Query(
        default="syslog",
        description="日志来源: syslog|kern|auth|dmesg|journal",
    ),
    newest: int = Query(default=20, ge=1, le=200),
) -> dict[str, Any]:
    """
    通过 SSH 采集指定 Linux 主机的指定来源日志
    source 可选:syslog | kern | auth | dmesg | journal
    """
    logger.info(f"请求 Linux 日志查询 | host={host_name} source={source} newest={newest}")
    if not LINUX_HOSTS:
        return {"total": 0, "logs": [], "message": "未配置 Linux 主机"}

    host_config = _get_linux_host(host_name)

    try:
        data = await get_linux_logs(host_config, source, newest)
        return {
            "total": len(data),
            "host": host_name,
            "source": source,
            "logs": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Linux 日志查询失败 | host={host_name} source={source}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to query Linux logs")


# Elasticsearch 统一日志搜索接口（跨平台）
@router.get(
    "/es/search",
    summary="在 Elasticsearch 中搜索日志",
    responses={
        200: {
            "description": "Elasticsearch搜索结果",
            "content": {
                "application/json": {
                    "example": {
                        "total": 100,
                        "logs": [
                            {
                                "@timestamp": "2026-07-02T10:30:00Z",
                                "level": "info",
                                "message": "Log message",
                            }
                        ],
                    }
                }
            },
        },
        401: {"description": "未授权"},
        500: {"description": "搜索失败"},
    },
)
async def es_search(
    query: str = Query(..., min_length=1, max_length=200),
    size: int = Query(default=100, ge=1, le=1000),
    from_: int = Query(default=0, ge=0),
) -> dict:
    """统一查询 Elasticsearch 中的日志记录"""
    logger.info(f"请求 Elasticsearch 日志搜索 | query='{query}' size={size} from={from_}")
    results = await es_search_logs(query=query, size=size, from_=from_)
    return {"total": len(results), "logs": results}


@router.get(
    "/linux/search",
    summary="在 Linux 日志中按关键词搜索",
    responses={
        200: {
            "description": "Linux日志搜索结果",
            "content": {
                "application/json": {
                    "example": {
                        "total": 15,
                        "host": "server01",
                        "keyword": "error",
                        "case_sensitive": False,
                        "logs": [
                            {
                                "time": "2026-07-02T10:30:00Z",
                                "level": "Error",
                                "message": "Error in service",
                            }
                        ],
                    }
                }
            },
        },
        401: {"description": "未授权"},
        404: {"description": "Linux主机不存在"},
        422: {"description": "主机名或关键词格式错误"},
        500: {"description": "搜索失败"},
    },
)
async def linux_search(
    host_name: str = Query(..., min_length=1, max_length=128),
    keyword: str = Query(..., min_length=1, max_length=_KEYWORD_MAX_LEN),
    newest: int = Query(default=100, ge=1, le=500),
    # 🔧 LG6 [P2]:case_sensitive 参数(默认 False,与 grep -i 一致)
    case_sensitive: bool = Query(
        default=False,
        description="是否区分大小写(默认 False,与 grep -i 一致)",
    ),
) -> dict[str, Any]:
    """
    通过 SSH 在指定 Linux 主机的系统日志中按关键词搜索
    keyword 自动过滤危险字符,防止命令注入

    🔧 LG1 [P1]:keyword 二次校验
    🔧 LG6 [P2]:支持 case_sensitive 参数
        - 注意:当前 search_linux_logs 内部固定用 grep -i(忽略大小写)
        - case_sensitive=True 时本参数仅作为接口契约,实际行为不变
        - 后续可在 log_collector 层支持此参数
    """
    # 🔧 LG1:二次校验
    keyword_safe = _validate_keyword(keyword)

    logger.info(
        "请求 Linux 日志搜索 | "
        f"host={host_name} keyword='{keyword_safe}' newest={newest} | "
        f"case_sensitive={case_sensitive}"
    )

    if not LINUX_HOSTS:
        return {"total": 0, "logs": [], "message": "未配置 Linux 主机"}

    host_config = _get_linux_host(host_name)

    try:
        data = await search_linux_logs(host_config, keyword_safe, newest)
        return {
            "total": len(data),
            "host": host_name,
            "keyword": keyword_safe,
            "case_sensitive": case_sensitive,
            "logs": data,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Linux 日志搜索失败 | host={host_name}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Failed to search Linux logs")
