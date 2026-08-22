# -*- coding: utf-8 -*-
"""Cache manager with optional Redis backend for the RAG service."""

from __future__ import annotations

import json
from typing import Any, Optional

from loguru import logger

from . import metrics

try:
    import redis.asyncio as aioredis
except ImportError:  # pragma: no cover
    aioredis = None  # type: ignore[misc, assignment]


class CacheManager:
    """In-memory cache with optional Redis backend."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis: Any = None
        self._memory: dict[str, Any] = {}
        if redis_url and aioredis is not None:
            try:
                self._redis = aioredis.from_url(redis_url, decode_responses=True)
                logger.info("Connected to Redis cache")
            except Exception as exc:
                logger.warning(f"Redis cache unavailable: {exc}")

    def _key(self, *parts: Any) -> str:
        return ":".join(str(p) for p in parts)

    async def get(self, key: str) -> Optional[Any]:
        value: Optional[Any] = None
        if self._redis:
            try:
                raw = await self._redis.get(key)
                if raw is not None:
                    value = json.loads(raw)
            except Exception as exc:
                logger.debug(f"Redis cache operation failed: {exc}")
        if value is None:
            value = self._memory.get(key)
        if value is not None:
            metrics.RAG_CACHE_HITS.inc()
            return value
        metrics.RAG_CACHE_MISSES.inc()
        return None

    async def set(self, key: str, value: Any, ttl: int = 300) -> None:
        if self._redis:
            try:
                await self._redis.setex(key, ttl, json.dumps(value))
                return
            except Exception as exc:
                logger.debug(f"Redis cache operation failed: {exc}")
        self._memory[key] = value

    async def clear(self) -> None:
        self._memory.clear()
        if self._redis:
            try:
                await self._redis.flushdb()
            except Exception as exc:
                logger.debug(f"Redis cache operation failed: {exc}")
