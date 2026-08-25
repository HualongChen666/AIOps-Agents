# -*- coding: utf-8 -*-
"""Caching strategy management for performance optimization.

This module provides multi-level caching configuration and management
including in-memory caching, distributed caching, and cache invalidation strategies.
"""

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, Optional

from loguru import logger

# Cache configuration
_cache_config: Dict[str, Any] = {
    "enabled": False,
    "default_ttl_seconds": 300,
    "max_size": 10000,
    "cache_backend": "memory",  # memory, redis, memcached
    "cache_key_prefix": "aiops",
    "compression_enabled": False,
    "serialization_format": "json",
}

# In-memory cache storage
_memory_cache: Dict[str, Dict[str, Any]] = {}
_cache_stats: Dict[str, Any] = {
    "hits": 0,
    "misses": 0,
    "evictions": 0,
    "size": 0,
}


def configure_caching_strategy(
    default_ttl_seconds: int = 300,
    max_size: int = 10000,
    cache_backend: str = "memory",
    cache_key_prefix: str = "aiops",
    compression_enabled: bool = False,
    serialization_format: str = "json",
) -> None:
    """Configure caching strategy settings.

    Args:
        default_ttl_seconds: Default time-to-live for cache entries
        max_size: Maximum number of cache entries
        cache_backend: Cache backend type (memory, redis, memcached)
        cache_key_prefix: Prefix for cache keys
        compression_enabled: Enable cache compression
        serialization_format: Serialization format for cached data
    """

    _cache_config["enabled"] = True
    _cache_config["default_ttl_seconds"] = default_ttl_seconds
    _cache_config["max_size"] = max_size
    _cache_config["cache_backend"] = cache_backend
    _cache_config["cache_key_prefix"] = cache_key_prefix
    _cache_config["compression_enabled"] = compression_enabled
    _cache_config["serialization_format"] = serialization_format

    logger.info(f"Configured caching strategy with {cache_backend} backend")


def get_cache_config() -> Dict[str, Any]:
    """Get cache configuration.

    Returns:
        Cache configuration dictionary
    """
    return _cache_config.copy()


def is_caching_enabled() -> bool:
    """Check if caching is enabled.

    Returns:
        True if caching is enabled
    """
    return bool(_cache_config["enabled"])


def generate_cache_key(key: str, prefix: Optional[str] = None) -> str:
    """Generate a cache key with prefix.

    Args:
        key: Base cache key
        prefix: Optional prefix override

    Returns:
        Full cache key with prefix
    """
    key_prefix = prefix or _cache_config["cache_key_prefix"]
    return f"{key_prefix}:{key}"


def set_cache(
    key: str,
    value: Any,
    ttl_seconds: Optional[int] = None,
) -> bool:
    """Set a value in cache.

    Args:
        key: Cache key
        value: Value to cache
        ttl_seconds: Time-to-live in seconds

    Returns:
        True if successful
    """
    if not _cache_config["enabled"]:
        return False

    try:
        ttl = ttl_seconds or _cache_config["default_ttl_seconds"]
        expiry_timestamp = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).timestamp()

        # Serialize value if needed
        if _cache_config["serialization_format"] == "json":
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
        else:
            serialized_value = str(value)

        cache_key = generate_cache_key(key)

        # Check cache size limit
        if len(_memory_cache) >= _cache_config["max_size"]:
            _evict_oldest_entry()

        _memory_cache[cache_key] = {
            "value": serialized_value,
            "expiry": expiry_timestamp,
            "created": datetime.now(timezone.utc).timestamp(),
        }

        _cache_stats["size"] = len(_memory_cache)
        return True

    except Exception as e:
        logger.error(f"Failed to set cache key {key}: {e}")
        return False


def get_cache(key: str) -> Optional[Any]:
    """Get a value from cache.

    Args:
        key: Cache key

    Returns:
        Cached value or None if not found/expired
    """
    if not _cache_config["enabled"]:
        return None

    try:
        cache_key = generate_cache_key(key)
        entry = _memory_cache.get(cache_key)

        if not entry:
            _cache_stats["misses"] += 1
            return None

        # Check expiry
        expiry_timestamp = entry["expiry"]
        current_timestamp = datetime.now(timezone.utc).timestamp()

        if current_timestamp > expiry_timestamp:
            del _memory_cache[cache_key]
            _cache_stats["misses"] += 1
            _cache_stats["size"] = len(_memory_cache)
            return None

        _cache_stats["hits"] += 1

        # Deserialize value if needed
        value = entry["value"]
        if _cache_config["serialization_format"] == "json":
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value

        return value

    except Exception as e:
        logger.error(f"Failed to get cache key {key}: {e}")
        _cache_stats["misses"] += 1
        return None


def delete_cache(key: str) -> bool:
    """Delete a value from cache.

    Args:
        key: Cache key

    Returns:
        True if successful
    """
    if not _cache_config["enabled"]:
        return False

    try:
        cache_key = generate_cache_key(key)
        if cache_key in _memory_cache:
            del _memory_cache[cache_key]
            _cache_stats["size"] = len(_memory_cache)
            return True
        return False

    except Exception as e:
        logger.error(f"Failed to delete cache key {key}: {e}")
        return False


def clear_cache() -> int:
    """Clear all cache entries.

    Returns:
        Number of entries cleared
    """

    count = len(_memory_cache)
    _memory_cache.clear()
    _cache_stats["size"] = 0

    logger.info(f"Cleared {count} cache entries")
    return count


def _evict_oldest_entry() -> None:
    """Evict the oldest cache entry."""
    if not _memory_cache:
        return

    # Find oldest entry
    oldest_key = None
    oldest_time = None

    for key, entry in _memory_cache.items():
        entry_time = entry.get("created", 0)
        if oldest_time is None or entry_time < oldest_time:
            oldest_time = entry_time
            oldest_key = key

    if oldest_key:
        del _memory_cache[oldest_key]
        _cache_stats["evictions"] += 1
        _cache_stats["size"] = len(_memory_cache)


def get_cache_statistics() -> Dict[str, Any]:
    """Get cache statistics.

    Returns:
        Cache statistics dictionary
    """
    total = _cache_stats["hits"] + _cache_stats["misses"]
    hit_rate = _cache_stats["hits"] / total if total > 0 else 0

    return {
        "enabled": _cache_config["enabled"],
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "evictions": _cache_stats["evictions"],
        "size": _cache_stats["size"],
        "max_size": _cache_config["max_size"],
        "hit_rate": hit_rate * 100,
        "backend": _cache_config["cache_backend"],
    }


def reset_cache_statistics() -> None:
    """Reset cache statistics."""
    global _cache_stats
    _cache_stats = {
        "hits": 0,
        "misses": 0,
        "evictions": 0,
        "size": len(_memory_cache),
    }
    logger.info("Reset cache statistics")


def cache_decorator(ttl_seconds: Optional[int] = None):
    """Decorator for caching function results.

    Args:
        ttl_seconds: Time-to-live for cached results

    Returns:
        Decorator function
    """

    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key from function name and arguments
            key_data = f"{func.__name__}_{str(args)}_{str(kwargs)}"
            cache_key = hashlib.sha256(key_data.encode()).hexdigest()

            # Try to get from cache
            cached_value = get_cache(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function and cache result
            result = func(*args, **kwargs)
            set_cache(cache_key, result, ttl_seconds)

            return result

        return wrapper

    return decorator


def invalidate_pattern(pattern: str) -> int:
    """Invalidate cache entries matching a pattern.

    Args:
        pattern: Pattern to match (simple substring match)

    Returns:
        Number of entries invalidated
    """
    if not _cache_config["enabled"]:
        return 0

    count = 0
    keys_to_delete = []

    for key in _memory_cache.keys():
        if pattern in key:
            keys_to_delete.append(key)

    for key in keys_to_delete:
        del _memory_cache[key]
        count += 1

    _cache_stats["size"] = len(_memory_cache)
    logger.info(f"Invalidated {count} cache entries matching pattern '{pattern}'")

    return count


def get_cache_info() -> Dict[str, Any]:
    """Get detailed cache information.

    Returns:
        Cache information dictionary
    """
    return {
        "configuration": get_cache_config(),
        "statistics": get_cache_statistics(),
        "keys": list(_memory_cache.keys()),
        "memory_usage_bytes": sum(len(str(v)) for v in _memory_cache.values()),
    }


__all__ = [
    "configure_caching_strategy",
    "get_cache_config",
    "is_caching_enabled",
    "generate_cache_key",
    "set_cache",
    "get_cache",
    "delete_cache",
    "clear_cache",
    "get_cache_statistics",
    "reset_cache_statistics",
    "cache_decorator",
    "invalidate_pattern",
    "get_cache_info",
]
