# -*- coding: utf-8 -*-
"""Distributed lock and idempotency helpers.

Provides a Redis-backed distributed lock with an in-process fallback,
and an idempotency manager backed by the service cache.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import time
import uuid
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

from loguru import logger

from .cache import CacheManager
from .config import settings

try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore[misc, assignment]


class LockManager:
    """Distributed lock with in-process asyncio.Lock fallback."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis_url = redis_url or settings.redis_url
        self._local_locks: Dict[str, asyncio.Lock] = {}
        self._redis: Any = None
        if settings.enable_distributed_lock and self._redis_url and aioredis is not None:
            try:
                self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
                logger.info("Connected to Redis for distributed locking")
            except Exception as exc:  # pragma: no cover
                logger.warning(f"Redis lock unavailable: {exc}")

    def _lock_name(self, resource: str, request_id: Optional[str] = None) -> str:
        return f"{resource}:{request_id}" if request_id else resource

    @asynccontextmanager
    async def acquire(self, resource: str, request_id: Optional[str] = None) -> Any:
        """Acquire a lock for *resource* and optional *request_id*."""
        name = self._lock_name(resource, request_id)
        if self._redis:
            token = f"{settings.service_name}:{uuid.uuid4().hex}"
            lock_key = f"{settings.service_name}:lock:{name}"
            acquired = False
            for _ in range(20):
                try:
                    ok = await self._redis.set(
                        lock_key,
                        token,
                        nx=True,
                        ex=settings.lock_ttl_seconds or 30,
                    )
                    if ok:
                        acquired = True
                        break
                except Exception as exc:  # pragma: no cover
                    logger.warning(f"Redis lock acquire failed: {exc}")
                await asyncio.sleep(0.05)
            if not acquired:
                raise RuntimeError(f"Could not acquire lock for {resource}")
            try:
                yield
            finally:
                try:
                    current = await self._redis.get(lock_key)
                    if current == token:
                        await self._redis.delete(lock_key)
                except Exception as exc:  # pragma: no cover
                    logger.warning(f"Redis lock release failed: {exc}")
        else:
            lock = self._local_locks.setdefault(name, asyncio.Lock())
            async with lock:
                yield


class IdempotencyManager:
    """Idempotency manager using the service cache with in-memory fallback."""

    def __init__(self, cache: Optional[CacheManager] = None) -> None:
        self.cache = cache or CacheManager(settings.redis_url)
        self._memory: Dict[str, Any] = {}

    @staticmethod
    def _serialize(value: Any) -> str:
        return json.dumps(value, sort_keys=True, default=str, separators=(",", ":"))

    def _key(self, request_id: str) -> str:
        return f"{settings.service_name}:idempotency:{request_id}"

    def get_key(self, request: Any, operation: str) -> str:
        """Build an idempotency key for *request* and *operation*."""
        data: Any = {}
        if request is None:
            data = {}
        elif hasattr(request, "model_dump"):
            data = request.model_dump()
        elif isinstance(request, dict):
            data = request
        else:
            data = {}
        if not isinstance(data, dict):
            data = {}
        explicit = data.get("idempotency_key")
        if not explicit and isinstance(data.get("config"), dict):
            explicit = data["config"].get("idempotency_key")
        if explicit:
            return f"{operation}:{explicit}"
        payload = {
            "op": operation,
            "config": data.get("config", data) if "config" in data else data,
        }
        digest = hashlib.sha256(self._serialize(payload).encode()).hexdigest()[:16]
        return f"{operation}:{digest}"

    async def is_processed(self, request_id: str) -> bool:
        cached = await self.cache.get(self._key(request_id))
        if cached is not None:
            return True
        return self._memory.get(request_id) is not None

    async def mark_processed(self, request_id: str, result: Any = None) -> None:
        record = {"processed": True, "timestamp": time.time(), "result": result}
        ttl = settings.idempotency_ttl_seconds or 3600
        await self.cache.set(self._key(request_id), record, ttl=ttl)
        self._memory[request_id] = record
