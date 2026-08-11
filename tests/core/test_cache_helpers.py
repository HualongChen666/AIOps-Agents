# -*- coding: utf-8 -*-
"""Unit tests for core/cache_helpers.py."""

import pytest

from core.cache_helpers import (
    CacheStatistics,
    CacheWarmer,
    LRUCache,
    ParametricTTLCache,
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
    result = await warmer.warm("double", 5)
    assert result == 10
