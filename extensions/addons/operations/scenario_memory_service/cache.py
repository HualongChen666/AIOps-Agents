# -*- coding: utf-8 -*-
"""Cache manager for the Scenario Memory microservice."""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from loguru import logger


class CacheManager:
    """In-memory cache with optional Redis fallback."""

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._memory: Dict[str, Any] = {}
        self._redis_url = redis_url or ""
        self._redis: Any = None

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        if self._redis is not None:
            try:
                raw = await self._redis.get(key)
                if raw:
                    return json.loads(raw)
            except Exception as exc:
                logger.debug(f"Redis get failed: {exc}")
        return self._memory.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set a value in cache with optional TTL."""
        self._memory[key] = value
        if self._redis is not None:
            try:
                ttl = ttl or 300
                await self._redis.setex(key, ttl, json.dumps(value))
            except Exception as exc:
                logger.debug(f"Redis set failed: {exc}")

    async def delete(self, key: str) -> None:
        """Delete a value from cache."""
        self._memory.pop(key, None)
        if self._redis is not None:
            try:
                await self._redis.delete(key)
            except Exception as exc:
                logger.debug(f"Redis delete failed: {exc}")

    async def clear(self) -> None:
        """Clear the cache."""
        self._memory.clear()
        if self._redis is not None:
            try:
                await self._redis.flushdb()
            except Exception as exc:
                logger.debug(f"Redis clear failed: {exc}")

    async def connect(self) -> None:
        """Connect to Redis if a URL is configured."""
        if not self._redis_url or self._redis is not None:
            return
        try:
            import aioredis

            self._redis = await aioredis.from_url(self._redis_url)
            logger.info("Connected to Redis cache")
        except Exception as exc:
            logger.warning(f"Redis connection failed: {exc}; using in-memory cache")
            self._redis = None
