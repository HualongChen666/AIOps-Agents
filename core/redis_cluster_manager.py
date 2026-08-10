# -*- coding: utf-8 -*-
"""Redis-compatible key/value, lock and cluster manager.

First attempts to use a real Redis server via ``REDIS_URL`` (or ``redis``
package). Falls back to an in-memory data store for local development/tests.
"""

import logging
import os
import socket
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _create_redis_client() -> Optional[Any]:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None
    try:
        import redis

        return redis.from_url(redis_url, decode_responses=True)
    except Exception as exc:
        logger.warning(f"Redis not reachable at {redis_url}: {exc}")
        return None


class RedisClusterManager:
    """Redis-compatible cluster manager with a real-Redis-first, in-memory fallback."""

    def __init__(self, connection_string: Optional[str] = None):
        self._data_store: Dict[str, Any] = {}
        self._lock_store: Dict[str, bool] = {}
        self._client: Optional[Any] = None
        self._connection_string = connection_string or os.getenv("REDIS_URL")
        if self._connection_string:
            self._client = _create_redis_client()

    # ------------------------------------------------------------------
    # Connection helpers
    # ------------------------------------------------------------------
    def connect(self, host: str = "localhost", port: int = 6379) -> Dict[str, Any]:
        """Try to connect to a real Redis endpoint."""
        if self._client:
            return {"status": "connected", "mode": "redis"}
        try:
            with socket.create_connection((host, port), timeout=2):
                self._connection_string = f"redis://{host}:{port}/0"
                self._client = _create_redis_client()
                return {
                    "status": "connected" if self._client else "socket_only",
                    "host": host,
                    "port": port,
                    "mode": "redis" if self._client else "memory",
                }
        except Exception as exc:
            return {"status": "memory_fallback", "error": str(exc)}

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    def ping(self) -> Dict[str, Any]:
        """Ping the backend and report latency."""
        start = time.time()
        if self._client:
            try:
                pong = self._client.ping()
                return {"ok": pong, "latency_ms": round(
                    (time.time() - start) * 1000, 2), "mode": "redis"}
            except Exception as exc:
                return {"ok": False, "error": str(exc), "mode": "redis"}
        return {"ok": True, "latency_ms": 0, "mode": "memory"}

    def info(self) -> Dict[str, Any]:
        if self._client:
            try:
                return {"mode": "redis", "info": dict(self._client.info())}
            except Exception as exc:
                return {"mode": "redis", "error": str(exc)}
        return {"mode": "memory", "keys": len(self._data_store), "locks": len(self._lock_store)}

    # ------------------------------------------------------------------
    # Key/value operations
    # ------------------------------------------------------------------
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        if self._client:
            try:
                self._client.set(key, value, ex=ttl)
                return True
            except Exception as exc:
                logger.warning(f"Redis set failed: {exc}; falling back to memory")
        self._data_store[key] = {"value": value, "expires_at": time.time() + ttl if ttl else None}
        return True

    def get(self, key: str) -> Optional[Any]:
        if self._client:
            try:
                value = self._client.get(key)
                return value
            except Exception as exc:
                logger.warning(f"Redis get failed: {exc}; falling back to memory")
        if key in self._data_store:
            data = self._data_store[key]
            if data["expires_at"] is None or time.time() < data["expires_at"]:
                return data["value"]
            del self._data_store[key]
        return None

    def delete(self, key: str) -> bool:
        if self._client:
            try:
                return bool(self._client.delete(key))
            except Exception as exc:
                logger.warning(f"Redis delete failed: {exc}; falling back to memory")
        if key in self._data_store:
            del self._data_store[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        return self.get(key) is not None

    def mset(self, mapping: Dict[str, Any]) -> bool:
        for k, v in mapping.items():
            self.set(k, v)
        return True

    def mget(self, keys: List[str]) -> List[Optional[Any]]:
        return [self.get(k) for k in keys]

    def expire(self, key: str, ttl: int) -> bool:
        if self._client:
            try:
                return bool(self._client.expire(key, ttl))
            except Exception:
                pass
        if key in self._data_store:
            self._data_store[key]["expires_at"] = time.time() + ttl
            return True
        return False

    # ------------------------------------------------------------------
    # Distributed locks
    # ------------------------------------------------------------------
    def distributed_lock(self, lock_key: str, ttl: int = 10) -> bool:
        if self._client:
            try:
                return bool(self._client.set(lock_key, "1", nx=True, ex=ttl))
            except Exception as exc:
                logger.warning(f"Redis lock failed: {exc}; falling back to memory")
        if lock_key not in self._lock_store:
            self._lock_store[lock_key] = True
            return True
        return False

    def release_lock(self, lock_key: str) -> bool:
        if self._client:
            try:
                return bool(self._client.delete(lock_key))
            except Exception as exc:
                logger.warning(f"Redis unlock failed: {exc}; falling back to memory")
        if lock_key in self._lock_store:
            del self._lock_store[lock_key]
            return True
        return False
