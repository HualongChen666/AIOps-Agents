# -*- coding: utf-8 -*-
"""补充 Redis shard cluster 核心分支覆盖率测试。"""

from __future__ import annotations

import uuid
from unittest import mock

import pytest

import services.redis_shard_service.cache as cache_module
import services.redis_shard_service.retry as retry_module
from services.redis_shard_service.metrics import MetricsCollector
from services.redis_shard_service.service import ShardClusterService


class _FakeRedis:
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
    @staticmethod
    def from_url(url: str, *, decode_responses: bool = True) -> _FakeRedis:
        return _FakeRedis()


@pytest.mark.asyncio
async def test_cache_manager_redis_paths() -> None:
    metrics = MetricsCollector(f"redis_shard-redis-{uuid.uuid4().hex[:6]}")
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
    metrics = MetricsCollector(f"redis_shard-fail-{uuid.uuid4().hex[:6]}")
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
    metrics = MetricsCollector(f"redis_shard-retry-{uuid.uuid4().hex[:6]}")
    engine = retry_module.RetryEngine("exponential_fast", metrics=metrics)

    custom = retry_module.RetryPolicy(name="custom", max_retries=1)
    engine.add_policy(custom)
    assert "custom" in engine.list_policies()

    fn = mock.AsyncMock(side_effect=Exception("fatal error"))
    with pytest.raises(Exception, match="fatal error"):
        await engine.execute(fn, operation="op")
    assert fn.await_count == 1

    fn = mock.AsyncMock(side_effect=[Exception("retryable"), "ok"])
    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        result = await engine.execute(fn, policy_name="exponential_fast", operation="op")
    assert result == "ok"
    assert fn.await_count == 2


@pytest.mark.asyncio
async def test_service_edge_cases() -> None:
    metrics = MetricsCollector(f"redis_shard-edge-{uuid.uuid4().hex[:6]}")
    service = ShardClusterService(backend="redis", redis_url="", metrics=metrics)
    restore = await service.restore({"name": "missing"})
    assert restore["restored"] is False
    stats = service.get_stats()
    assert stats["shards"] >= 10
