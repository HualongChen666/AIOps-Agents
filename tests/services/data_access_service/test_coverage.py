# -*- coding: utf-8 -*-
"""补充 data_access_service 核心分支覆盖率测试。"""

from __future__ import annotations

import uuid
from unittest import mock

import pytest

import services.data_access_service.cache as cache_module
import services.data_access_service.retry as retry_module
from services.data_access_service.metrics import MetricsCollector


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
    metrics = MetricsCollector(f"da-redis-{uuid.uuid4().hex[:6]}")
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
    metrics = MetricsCollector(f"da-fail-{uuid.uuid4().hex[:6]}")
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
    metrics = MetricsCollector(f"da-retry-{uuid.uuid4().hex[:6]}")
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

    fn = mock.AsyncMock(side_effect=Exception("retryable"))
    with pytest.raises(Exception, match="retryable"):
        await engine.execute(fn, policy_name="no_retry")
    assert fn.await_count == 1

    engine.add_policy(
        retry_module.RetryPolicy(
            name="all", max_retries=1, base_delay_seconds=0, retryable_errors=[]
        )
    )
    fn = mock.AsyncMock(side_effect=[Exception("fatal"), "ok"])
    with mock.patch("asyncio.sleep", new_callable=mock.AsyncMock):
        result = await engine.execute(fn, policy_name="all", operation="op")
    assert result == "ok"
    assert fn.await_count == 2

    engine.add_policy(
        retry_module.RetryPolicy(
            name="jitter",
            max_retries=1,
            base_delay_seconds=1,
            max_delay_seconds=60,
            exponential_base=2.0,
        )
    )
    fn = mock.AsyncMock(side_effect=[Exception("retryable"), "ok"])
    sleep_mock = mock.AsyncMock()
    with mock.patch("asyncio.sleep", new=sleep_mock):
        with mock.patch.object(retry_module, "secrets") as mock_secrets:
            mock_secrets.SystemRandom.return_value.random.return_value = 0.5
            result = await engine.execute(fn, policy_name="jitter", operation="op")
    assert result == "ok"
    assert fn.await_count == 2
    sleep_mock.assert_awaited_once()
    args = sleep_mock.call_args[0]
    assert 0.5 <= args[0] <= 60.0
