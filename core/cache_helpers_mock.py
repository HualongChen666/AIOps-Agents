# -*- coding: utf-8 -*-
# core/cache_helpers_mock.py
# 缓存辅助模块的Mock实现
# 用于测试目的，提供基本的缓存功能

import hashlib
import time
from functools import wraps
from typing import Any, Callable, Dict

# 简单的内存缓存实现
_cache_store: Dict[str, Any] = {}
_cache_metadata: Dict[str, Dict[str, Any]] = {}


def cache_result(
    ttl: int = 300,
    cache_level: str = "memory",
    max_size: int = 100,
    track_stats: bool = False,
    enable_monitoring: bool = False,
):
    """
    缓存结果装饰器

    Args:
        ttl: 缓存过期时间（秒）
        cache_level: 缓存级别
        max_size: 最大缓存大小
        track_stats: 是否跟踪统计信息
        enable_monitoring: 是否启用监控
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # 生成缓存键
            cache_key = _generate_cache_key(func.__name__, args, kwargs)

            # 检查缓存
            if cache_key in _cache_store:
                cache_data = _cache_metadata[cache_key]
                if time.time() - cache_data["timestamp"] < ttl:
                    if track_stats:
                        cache_data["hits"] = cache_data.get("hits", 0) + 1
                    return _cache_store[cache_key]

            # 执行函数并缓存结果
            result = func(*args, **kwargs)

            # 检查缓存大小限制
            if len(_cache_store) >= max_size:
                _remove_oldest_cache()

            # 存入缓存
            _cache_store[cache_key] = result
            _cache_metadata[cache_key] = {
                "timestamp": time.time(),
                "hits": 0 if track_stats else None,
                "func_name": func.__name__,
            }

            return result

        return wrapper

    return decorator


def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """生成缓存键"""
    key_str = f"{func_name}_{str(args)}_{str(sorted(kwargs.items()))}"
    return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()


def _remove_oldest_cache():
    """移除最旧的缓存条目"""
    if _cache_metadata:
        oldest_key = min(_cache_metadata.keys(), key=lambda k: _cache_metadata[k]["timestamp"])
        del _cache_store[oldest_key]
        del _cache_metadata[oldest_key]


def invalidate_cache(func_name: str, args: tuple = ()):
    """使缓存失效"""
    keys_to_remove = []
    for key, metadata in _cache_metadata.items():
        if metadata["func_name"] == func_name:
            keys_to_remove.append(key)

    for key in keys_to_remove:
        del _cache_store[key]
        del _cache_metadata[key]


def get_cache_stats(func_name: str) -> Dict[str, Any]:
    """获取缓存统计信息"""
    stats = {"total_hits": 0, "total_misses": 0, "cache_size": 0}

    for metadata in _cache_metadata.values():
        if metadata["func_name"] == func_name:
            hits = metadata.get("hits", 0) or 0  # 确保不是None
            stats["total_hits"] += hits
            stats["cache_size"] += 1

    return stats


def get_cache_metrics(func_name: str) -> Dict[str, Any]:
    """获取缓存监控指标"""
    return get_cache_stats(func_name)


def backup_cache(func_name: str):
    """备份缓存"""
    backup_data = {}
    for key, metadata in _cache_metadata.items():
        if metadata["func_name"] == func_name:
            backup_data[key] = {"value": _cache_store[key], "metadata": metadata}
    return backup_data
