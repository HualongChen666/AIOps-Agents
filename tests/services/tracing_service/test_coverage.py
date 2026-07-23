# -*- coding: utf-8 -*-
"""Coverage tests for the Tracing microservice."""

from __future__ import annotations

import uuid
from unittest import mock

import pytest

import services.tracing_service.cache as cache_module
import services.tracing_service.retry as retry_module
from services.tracing_service.metrics import MetricsCollector
from services.tracing_service.service import Service


class _FakeRedis:
    """Fake Redis client for cache coverage tests."""

    def __init__(self, fail: bool = False) -> None:
        self._data: dict[str, str] = {}
        self._fail = fail

    async def get(self, key: str) -> str | None:
        if self._fail:
            raise ConnectionError("redis down")
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self._data[key] = value

    async def delete(self, key: str) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self._data.pop(key, None)

    async def flushdb(self) -> None:
        if self._fail:
            raise ConnectionError("redis down")
        self._data.clear()


class _FakeAioredis:
    """Fake aioredis factory."""

    @staticmethod
    def from_url(url: str, *, decode_responses: bool = True) -> _FakeRedis:
        return _FakeRedis()


@pytest.mark.asyncio
async def test_cache_manager_redis_paths() -> None:
    """Test cache manager with Redis backend."""
    metrics = MetricsCollector(f"tracing-redis-{uuid.uuid4().hex[:6]}")
    with mock.patch.object(cache_module, "aioredis", _FakeAioredis()):
        cache = cache_module.CacheManager(redis_url="redis://fake", metrics=metrics)
        assert cache._redis is not None
        assert cache._key("a", 1) == "a:1"
        await cache.set("k", {"x": 1})
        assert await cache.get("k") == {"x": 1}
        await cache.delete("k")
        assert await cache.get("k") is None
        await cache.set("k2", {"y": 2})
        await cache.clear()
        assert await cache.get("k2") is None
        cache._memory["k3"] = {"z": 3}
        assert await cache.get("k3") == {"z": 3}


@pytest.mark.asyncio
async def test_cache_manager_redis_failures() -> None:
    """Test cache manager fallback on Redis failure."""
    metrics = MetricsCollector(f"tracing-fail-{uuid.uuid4().hex[:6]}")
    with mock.patch.object(cache_module, "aioredis", _FakeAioredis()):
        cache = cache_module.CacheManager(redis_url="redis://fake", metrics=metrics)
        cache._redis._fail = True
        await cache.set("k", {"x": 1})
        assert await cache.get("k") == {"x": 1}
        await cache.delete("k")
        assert await cache.get("k") is None
        await cache.set("k2", {"y": 2})
        await cache.clear()
        assert await cache.get("k2") is None


@pytest.mark.asyncio
async def test_retry_engine_coverage() -> None:
    """Test retry engine policies and failure handling."""
    metrics = MetricsCollector(f"tracing-retry-{uuid.uuid4().hex[:6]}")
    engine = retry_module.RetryEngine("exponential_fast", metrics=metrics)
    custom = retry_module.RetryPolicy(name="custom", max_retries=1)
    engine.add_policy(custom)
    assert "custom" in engine.list_policies()

    fn = mock.AsyncMock(side_effect=Exception("retryable error"))
    with pytest.raises(Exception):
        await engine.execute(fn, operation="op")
    assert fn.call_count == engine.default_policy.max_retries + 1


@pytest.mark.asyncio
async def test_service_edge_cases() -> None:
    """Test service edge cases."""
    metrics = MetricsCollector(f"tracing-edge-{uuid.uuid4().hex[:6]}")
    service = Service(redis_url="", metrics=metrics)
    missing = await service.get_state({"config": {"feature": "missing"}})
    assert missing["success"] is False
    restore = await service.restore_state({"config": {"name": "missing"}})
    assert restore["success"] is False
    stats = await service.get_stats()
    assert "total_requests" in stats["result"]
    with pytest.raises(ValueError):
        await service.call("unknown_method", request={})
