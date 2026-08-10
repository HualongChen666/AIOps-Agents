# -*- coding: utf-8 -*-
"""Cache helpers with pluggable backends: memory, disk or redis.

The default is a thread-safe in-memory store. Set ``CACHE_BACKEND=redis`` and
``REDIS_URL`` (or ``CACHE_BACKEND=disk``) to use a real cache implementation.
"""

import hashlib
import json
import logging
import os
import threading
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)

_BACKENDS: Dict[str, Any] = {}
_DEFAULT_BACKEND = "memory"
_BACKEND = os.getenv("CACHE_BACKEND", _DEFAULT_BACKEND).lower()

_LOCK = threading.RLock()


def _get_backend() -> "CacheBackend":
    if _BACKEND not in _BACKENDS:
        _BACKENDS[_BACKEND] = _create_backend(_BACKEND)
    return _BACKENDS[_BACKEND]


def _create_backend(name: str) -> "CacheBackend":
    if name == "redis":
        try:
            import redis

            client = redis.from_url(os.environ["REDIS_URL"], decode_responses=True)
            return RedisCacheBackend(client)
        except Exception as exc:
            logger.warning(f"Redis cache init failed: {exc}; falling back to memory")
    if name == "disk":
        try:
            import diskcache

            return DiskCacheBackend(diskcache.Cache(os.getenv("DISK_CACHE_DIR", "data/cache")))
        except Exception as exc:
            logger.warning(f"Disk cache init failed: {exc}; falling back to memory")
    return MemoryCacheBackend()


class CacheBackend:
    def get(self, key: str) -> Optional[Any]:  # pragma: no cover
        raise NotImplementedError

    def set(self, key: str, value: Any, ttl: int) -> None:  # pragma: no cover
        raise NotImplementedError

    def delete(self, key: str) -> bool:  # pragma: no cover
        raise NotImplementedError

    def clear(self) -> bool:  # pragma: no cover
        raise NotImplementedError

    def stats(self) -> Dict[str, int]:  # pragma: no cover
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """Thread-safe in-memory cache."""

    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        with _LOCK:
            if key in self._store:
                meta = self._metadata[key]
                if time.time() - meta["timestamp"] < meta["ttl"]:
                    self._hits += 1
                    meta["hits"] = meta.get("hits", 0) + 1
                    return self._store[key]
                del self._store[key]
                del self._metadata[key]
            self._misses += 1
            return None

    def set(self, key: str, value: Any, ttl: int) -> None:
        with _LOCK:
            self._store[key] = value
            # key format: func:<func_name>:<md5>
            func_name = ""
            if key.startswith("func:"):
                parts = key.split(":", 2)
                func_name = parts[1] if len(parts) >= 2 else ""
            self._metadata[key] = {
                "timestamp": time.time(),
                "ttl": ttl,
                "hits": 1,
                "func_name": func_name,
            }

    def delete(self, key: str) -> bool:
        with _LOCK:
            if key in self._store:
                del self._store[key]
                del self._metadata[key]
                return True
            return False

    def clear(self) -> bool:
        with _LOCK:
            self._store.clear()
            self._metadata.clear()
            self._hits = self._misses = 0
            return True

    def stats(self) -> Dict[str, int]:
        with _LOCK:
            return {
                "total_hits": self._hits,
                "total_misses": self._misses,
                "cache_size": len(self._store),
            }


class RedisCacheBackend(CacheBackend):
    def __init__(self, client: Any):
        self._client = client

    def get(self, key: str) -> Optional[Any]:
        raw = self._client.get(key)
        return json.loads(raw) if raw is not None else None

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._client.setex(key, ttl, json.dumps(value, default=str))

    def delete(self, key: str) -> bool:
        return bool(self._client.delete(key))

    def clear(self) -> bool:
        self._client.flushdb()
        return True

    def stats(self) -> Dict[str, int]:
        info = self._client.info()
        return {
            "total_hits": info.get("keyspace_hits", 0),
            "total_misses": info.get("keyspace_misses", 0),
            "cache_size": self._client.dbsize(),
        }


class DiskCacheBackend(CacheBackend):
    def __init__(self, cache: Any):
        self._cache = cache

    def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)

    def set(self, key: str, value: Any, ttl: int) -> None:
        self._cache.set(key, value, expire=ttl)

    def delete(self, key: str) -> bool:
        return self._cache.delete(key)

    def clear(self) -> bool:
        self._cache.clear()
        return True

    def stats(self) -> Dict[str, int]:
        return {"total_hits": 0, "total_misses": 0, "cache_size": len(self._cache)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def _generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    key_str = f"{func_name}_{str(args)}_{str(sorted(kwargs.items()))}"
    return hashlib.md5(key_str.encode(), usedforsecurity=False).hexdigest()


def cache_result(
    ttl: int = 300,
    cache_level: str = "memory",
    max_size: int = 100,
    track_stats: bool = False,
    enable_monitoring: bool = False,
):
    """Cache the result of a function."""

    def decorator(func: Callable) -> Callable:
        func_name = func.__name__

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            backend = _get_backend()
            cache_key = f"func:{func_name}:{_generate_cache_key(func_name, args, kwargs)}"
            value = backend.get(cache_key)
            if value is not None:
                if enable_monitoring:
                    logger.debug(f"Cache hit for {func_name}")
                return value

            result = func(*args, **kwargs)
            backend.set(cache_key, result, ttl)
            if enable_monitoring:
                logger.debug(f"Cache set for {func_name}")
            return result

        return wrapper

    return decorator


def invalidate_cache(func_name: str, args: tuple = ()) -> int:
    """Invalidate cached entries for a function name."""
    backend = _get_backend()
    keys_to_remove = []
    if isinstance(backend, MemoryCacheBackend):
        with _LOCK:
            for key, meta in backend._metadata.items():
                if meta.get("func_name") == func_name:
                    keys_to_remove.append(key)
            for key in keys_to_remove:
                backend.delete(key)
    return len(keys_to_remove)


def get_cache_stats(func_name: str) -> Dict[str, Any]:
    """Get cache statistics."""
    backend = _get_backend()
    stats = backend.stats()
    if isinstance(backend, MemoryCacheBackend):
        with _LOCK:
            func_hits = 0
            func_size = 0
            for meta in backend._metadata.values():
                if meta.get("func_name") == func_name:
                    func_hits += meta.get("hits", 0) or 0
                    func_size += 1
            stats.update({"function_hits": func_hits, "function_size": func_size})
    return stats


def get_cache_metrics(func_name: str) -> Dict[str, Any]:
    """Get cache monitoring metrics."""
    return get_cache_stats(func_name)


def backup_cache(func_name: str) -> Dict[str, Any]:
    """Backup cache entries for a function."""
    backend = _get_backend()
    backup_data = {}
    if isinstance(backend, MemoryCacheBackend):
        with _LOCK:
            for key, meta in backend._metadata.items():
                if meta.get("func_name") == func_name:
                    backup_data[key] = {"value": backend._store[key], "metadata": meta}
    return backup_data


def restore_cache(backup_data: Dict[str, Any]) -> int:
    """Restore cache entries from a backup dictionary."""
    backend = _get_backend()
    if isinstance(backend, MemoryCacheBackend):
        with _LOCK:
            for key, data in backup_data.items():
                backend._store[key] = data["value"]
                backend._metadata[key] = data["metadata"]
    return len(backup_data)


def flush_all() -> bool:
    """Clear all cached data."""
    return _get_backend().clear()


def configure_backend(name: str, **options: Any) -> bool:
    """Switch the active cache backend at runtime."""
    global _BACKEND
    _BACKEND = name
    _BACKENDS[name] = _create_backend(name)
    logger.info(f"Cache backend switched to {name} with options {options}")
    return True
