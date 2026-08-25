# -*- coding: utf-8 -*-
"""
Common Cache Helpers
====================

Provides reusable caching patterns and utilities to reduce
code duplication across API routers.

This module addresses the following code duplication issues:
- Repeated TTL cache implementation patterns
- Repeated cache key generation logic
- Repeated cache hit/miss logging
- Repeated cache invalidation patterns
"""

import logging
import time
from threading import Lock
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SimpleTTLCache:
    """
    A simple thread-safe TTL cache implementation.

    This class reduces duplication of cache implementation patterns
    across different routers.

    Attributes:
        ttl_sec: Time-to-live in seconds
        _cache: Internal cache storage
        _timestamps: Timestamp tracking for TTL
        _lock: Thread lock for thread safety
    """

    def __init__(self, ttl_sec: int = 30):
        """
        Initialize the TTL cache.

        Args:
            ttl_sec: Time-to-live in seconds
        """
        self.ttl_sec = ttl_sec
        self._cache: dict[str, Any] = {}
        self._timestamps: dict[str, float] = {}
        self._lock = Lock()

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                return None

            # Check if expired
            if time.monotonic() - self._timestamps[key] > self.ttl_sec:
                del self._cache[key]
                del self._timestamps[key]
                return None

            # Return a shallow copy to prevent external modification
            value = self._cache[key]
            if isinstance(value, (list, dict)):
                return value.copy() if isinstance(value, list) else dict(value)
            return value

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache with current timestamp.

        Args:
            key: Cache key
            value: Value to cache
        """
        with self._lock:
            # Store a shallow copy to prevent external modification
            if isinstance(value, (list, dict)):
                value = value.copy() if isinstance(value, list) else dict(value)
            self._cache[key] = value
            self._timestamps[key] = time.monotonic()

    def clear(self) -> None:
        """Clear all cached values."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()

    def is_valid(self, key: str) -> bool:
        """
        Check if a cached value is still valid (not expired).

        Args:
            key: Cache key

        Returns:
            True if value exists and is not expired
        """
        with self._lock:
            if key not in self._cache:
                return False
            return time.monotonic() - self._timestamps[key] <= self.ttl_sec


def get_cached_or_execute(
    cache: SimpleTTLCache,
    cache_key: str,
    execute_func: Callable[[], T],
    cache_hit_log_msg: Optional[str] = None,
    cache_miss_log_msg: Optional[str] = None,
) -> T:
    """
    Get value from cache or execute function and cache result.

    This function reduces duplication of cache-or-execute patterns.

    Args:
        cache: Cache instance to use
        cache_key: Key for caching
        execute_func: Function to execute if cache miss
        cache_hit_log_msg: Optional log message on cache hit
        cache_miss_log_msg: Optional log message on cache miss

    Returns:
        Cached or freshly computed value

    Example:
        result = get_cached_or_execute(
            cache=_my_cache,
            cache_key="my_key",
            execute_func=lambda: expensive_operation(),
            cache_hit_log_msg="Cache hit for my_key",
            cache_miss_log_msg="Cache miss for my_key, executing"
        )
    """
    cached = cache.get(cache_key)
    if cached is not None:
        if cache_hit_log_msg:
            logger.debug(cache_hit_log_msg)
        return cached

    if cache_miss_log_msg:
        logger.debug(cache_miss_log_msg)

    result = execute_func()
    cache.set(cache_key, result)
    return result


def generate_cache_key(*parts: Any, separator: str = "_") -> str:
    """
    Generate a cache key from multiple parts.

    This function reduces duplication of cache key generation logic.

    Args:
        *parts: Parts to combine into cache key
        separator: Separator between parts

    Returns:
        Generated cache key string

    Example:
        key = generate_cache_key("system", "errors", newest=10)
        # Returns: "system_errors_10"
    """
    str_parts = [str(part) for part in parts]
    return separator.join(str_parts)


def with_cache_response(data: Any, cached: bool, **extra_fields) -> dict[str, Any]:
    """
    Wrap response data with cache status indicator.

    This function reduces duplication of cache response formatting.

    Args:
        data: The main data to include
        cached: Whether the data was from cache
        **extra_fields: Additional fields to include

    Returns:
        Response dictionary with cache status

    Example:
        return with_cache_response(
            data=log_records,
            cached=True,
            total=len(log_records)
        )
    """
    response: dict[str, Any] = {"cached": cached}
    if isinstance(data, (list, dict)):
        response.update(data if isinstance(data, dict) else {"data": data})
    else:
        response["data"] = data
    response.update(extra_fields)
    return response


class CacheStats:
    """
    Simple cache statistics tracker.

    This class helps monitor cache performance across routers.
    """

    def __init__(self):
        """Initialize cache statistics."""
        self.hits = 0
        self.misses = 0
        self._lock = Lock()

    def record_hit(self) -> None:
        """Record a cache hit."""
        with self._lock:
            self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss."""
        with self._lock:
            self.misses += 1

    def get_stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with hit/miss counts and hit rate
        """
        with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0.0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "total_requests": total,
                "hit_rate_percent": round(hit_rate, 2),
            }

    def reset(self) -> None:
        """Reset cache statistics."""
        with self._lock:
            self.hits = 0
            self.misses = 0
