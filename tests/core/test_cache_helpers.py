# -*- coding: utf-8 -*-
"""Unit tests for core/cache_helpers.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.cache_helpers import (
    CacheInvalidationEvent,
    CacheStatistics,
    CacheWarmer,
    IntelligentCacheWarmer,
    LRUCache,
    MultiLevelCache,
    ParametricTTLCache,
    ThreeLevelCache,
    TTLCache,
    generate_cache_key,
)


def test_generate_cache_key():
    key1 = generate_cache_key("test", 1, 2, a=3)
    key2 = generate_cache_key("test", 1, 2, a=3)
    assert key1 == key2
    assert isinstance(key1, str)


def test_cache_statistics():
    stats = CacheStatistics()
    stats.record_hit()
    stats.record_miss()
    stats.record_eviction()
    rate = stats.get_hit_rate()
    assert 0.0 <= rate <= 100.0
    assert isinstance(stats.get_stats(), dict)


def test_lru_cache():
    cache = LRUCache(max_size=2, ttl_sec=1.0)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.invalidate("a") is True
    cache.clear()
    assert isinstance(cache.get_stats(), dict)


def test_ttl_cache():
    cache = TTLCache(ttl_sec=0.5)
    cache.set({"key": "value"})
    assert cache.get()["key"] == "value"
    assert cache.is_valid() is True
    cache.clear()
    assert cache.get() is None


def test_parametric_ttl_cache():
    cache = ParametricTTLCache(ttl_sec=0.5)
    cache.set({"key": "value"}, param="x")
    assert cache.get(param="x")["key"] == "value"
    assert cache.get(param="y") is None
    cache.clear()


@pytest.mark.asyncio
async def test_cache_warmer():
    cache = LRUCache()
    warmer = CacheWarmer(cache)

    async def double(x):
        return x * 2

    warmer.register("double", double)
    result = await warmer.warm("double", 5)  # noqa: F841  # Variable for test verification
    assert result == 10  # noqa: F841  # Variable for test verification


class _FakeRedis:
    def __init__(self, *args, **kwargs):
        raise ConnectionError("redis disabled")


def _patch_redis(monkeypatch):
    try:
        import redis

        monkeypatch.setattr(redis, "Redis", _FakeRedis)
    except ImportError:
        pass


def test_multi_level_cache(monkeypatch):
    _patch_redis(monkeypatch)
    cache = MultiLevelCache()
    cache.set("k", "v")
    assert cache.get("k") == "v"
    cache.invalidate("k")
    assert cache.get("k") is None
    cache.clear()


def test_three_level_cache(monkeypatch):
    _patch_redis(monkeypatch)
    cache = ThreeLevelCache()
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}
    cache.invalidate("k")
    assert cache.get("k") is None
    cache.register_invalidation_callback(
        CacheInvalidationEvent.MANUAL,
        lambda key, meta: None,
    )
    cache._trigger_invalidation_event(CacheInvalidationEvent.MANUAL, "k")
    stats = cache.get_stats()
    assert isinstance(stats, dict)
    cache.clear()


@pytest.mark.asyncio
async def test_intelligent_cache_warmer(monkeypatch):
    _patch_redis(monkeypatch)
    cache = ThreeLevelCache()
    warmer = IntelligentCacheWarmer(cache)

    async def double(x):
        return x * 2

    warmer.register("double", double)
    assert await warmer.warm("double", 5) == 10
    assert isinstance(warmer.predict_next_access("double"), float)
    assert await warmer.warm_with_prediction("double", 5) == 10
    await warmer.warm_high_priority()
    stats = warmer.get_warming_stats()
    assert isinstance(stats, dict)
    assert "registered_functions" in stats
