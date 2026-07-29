# -*- coding: utf-8 -*-
"""Core service logic for the cache microservice."""

from __future__ import annotations

import asyncio
import secrets
from typing import Any, Dict, List, Optional

from .cache import CacheManager
from .metrics import MetricsCollector
from .retry import RetryEngine
from .schemas import (
    AvalancheProtectRequest,
    AvalancheProtectResponse,
    BreakdownProtectRequest,
    BreakdownProtectResponse,
    CacheGetRequest,
    CacheGetResponse,
    CachePreheatRequest,
    CachePreheatResponse,
    CacheSetRequest,
    CacheStatsResponse,
    CacheStrategy,
    CacheStrategyRequest,
    CacheStrategyResponse,
)


class CacheService:
    """Cache microservice implementing distributed caching strategies and protections."""

    def __init__(
        self,
        redis_url: str = "",
        metrics: Optional[MetricsCollector] = None,
        retry_engine: Optional[RetryEngine] = None,
        cache: Optional[CacheManager] = None,
    ) -> None:
        self.metrics = metrics or MetricsCollector("cache")
        self.retry_engine = retry_engine or RetryEngine("exponential_fast", self.metrics)
        self.cache = cache or CacheManager(redis_url, self.metrics)
        self._locks: Dict[str, asyncio.Lock] = {}
        self._backend: Dict[str, Any] = {}
        self._tasks: set = set()

    async def initialize(self) -> None:
        """Optional initialization hook."""
        await self.cache.clear()

    async def reset(self) -> None:
        """Clear all caches and backend state for tests."""
        await self.cache.clear()
        self._backend.clear()
        for task in list(self._tasks):
            if not task.done():
                task.cancel()
        self._tasks.clear()

    async def get(self, request: CacheGetRequest) -> CacheGetResponse:
        self.metrics.inc_request("get")
        value = await self.cache.get(request.key)
        return CacheGetResponse(key=request.key, value=value, hit=value is not None)

    async def set(self, request: CacheSetRequest) -> Dict[str, Any]:
        self.metrics.inc_request("set")
        await self.cache.set(request.key, request.value, request.ttl)
        return {"key": request.key, "stored": True}

    async def delete(self, request: CacheGetRequest) -> Dict[str, bool]:
        self.metrics.inc_request("delete")
        await self.cache.delete(request.key)
        return {"deleted": True}

    async def clear(self) -> Dict[str, bool]:
        self.metrics.inc_request("clear")
        await self.cache.clear()
        return {"cleared": True}

    async def preheat(self, request: CachePreheatRequest) -> CachePreheatResponse:
        """Preload cache with key-value pairs to avoid cold-start misses."""
        self.metrics.inc_request("preheat")
        loaded = 0
        for key, value in request.data.items():
            await self.cache.set(key, value, request.ttl)
            loaded += 1
        self.metrics.observe_batch_size("preheat", loaded)
        self.metrics.inc_operation("preheat")
        return CachePreheatResponse(keys_loaded=loaded)

    async def protect_breakdown(self, request: BreakdownProtectRequest) -> BreakdownProtectResponse:
        """Use a per-key lock to protect against cache breakdown."""
        self.metrics.inc_request("protect_breakdown")
        lock = self._get_lock(request.key)
        async with lock:
            cached = await self.cache.get(request.key)
            if cached is not None:
                return BreakdownProtectResponse(key=request.key, locked=True, value=cached)
            value = request.value if request.value is not None else f"computed-{request.key}"
            await self.cache.set(request.key, value, request.ttl)
        self.metrics.inc_operation("breakdown_protect")
        return BreakdownProtectResponse(key=request.key, locked=True, value=value)

    async def protect_avalanche(self, request: AvalancheProtectRequest) -> AvalancheProtectResponse:
        """Add random jitter to TTL to prevent cache avalanche."""
        self.metrics.inc_request("protect_avalanche")
        jitter = secrets.randbelow(max(0, request.jitter_seconds) + 1)
        ttl = request.base_ttl + jitter
        await self.cache.set(request.key, request.value, ttl)
        self.metrics.inc_operation("avalanche_protect")
        return AvalancheProtectResponse(key=request.key, ttl=ttl, value=request.value)

    async def execute_strategy(self, request: CacheStrategyRequest) -> CacheStrategyResponse:
        """Execute one of the supported caching strategies."""
        self.metrics.inc_request("execute_strategy")
        strategy = request.strategy
        backend_written = False

        if strategy == CacheStrategy.CACHE_ASIDE:
            cached = await self.cache.get(request.key)
            if cached is None:
                value = request.value
                await self.cache.set(request.key, value, request.ttl)
            else:
                value = cached

        elif strategy == CacheStrategy.WRITE_THROUGH:
            await self.cache.set(request.key, request.value, request.ttl)
            self._backend[request.key] = request.value
            backend_written = True
            value = request.value

        elif strategy == CacheStrategy.WRITE_BEHIND:
            await self.cache.set(request.key, request.value, request.ttl)
            task = asyncio.create_task(self._write_behind(request.key, request.value))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            value = request.value

        elif strategy == CacheStrategy.REFRESH_AHEAD:
            await self.cache.set(request.key, request.value, request.ttl)
            task = asyncio.create_task(self._refresh_ahead(request.key, request.value, request.ttl))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
            value = request.value

        else:
            value = request.value

        self.metrics.inc_operation(f"strategy_{strategy.value}")
        return CacheStrategyResponse(
            strategy=strategy.value,
            key=request.key,
            value=value,
            status="ok",
            backend_written=backend_written,
        )

    async def _write_behind(self, key: str, value: Any) -> None:
        """Asynchronous write to backend."""
        await asyncio.sleep(0.01)
        self._backend[key] = value

    async def _refresh_ahead(self, key: str, value: Any, ttl: int) -> None:
        """Asynchronous refresh of cache value."""
        await asyncio.sleep(0.01)
        await self.cache.set(key, value, ttl)

    def _get_lock(self, key: str) -> asyncio.Lock:
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]

    def get_backend(self, key: str) -> Any:
        """Return value written to backend, useful for write-behind tests."""
        return self._backend.get(key)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_requests": self.metrics.request_count,
            "cache_hits": self.metrics.cache_hits_count,
            "cache_misses": self.metrics.cache_misses_count,
            "operations": {},
            "index_size": len(self._backend),
        }

    def get_cache_stats(self) -> CacheStatsResponse:
        return CacheStatsResponse(
            hits=self.metrics.cache_hits_count,
            misses=self.metrics.cache_misses_count,
            size=len(self.cache._memory),
            total_requests=self.metrics.request_count,
        )

    def list_methods(self) -> List[str]:
        return [
            "get",
            "set",
            "delete",
            "clear",
            "preheat",
            "protect_breakdown",
            "protect_avalanche",
            "execute_strategy",
            "get_stats",
            "get_cache_stats",
        ]

    async def call(self, method: str, **kwargs: Any) -> Any:
        fn = getattr(self, method, None)
        if not fn:
            raise ValueError(f"Unknown method: {method}")
        if asyncio.iscoroutinefunction(fn):
            return await fn(**kwargs)
        return fn(**kwargs)
