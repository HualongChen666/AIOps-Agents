# -*- coding: utf-8 -*-
"""Unit tests for the cache helpers and cache manager."""

import time

from core.cache_helpers import CacheStatistics, LRUCache
from core.cache_manager import MemoryCacheBackend


def test_lru_cache_basic():
    cache = LRUCache(max_size=2, ttl_sec=60.0)
    cache.set("a", 1)
    assert cache.get("a") == 1


def test_lru_cache_eviction():
    cache = LRUCache(max_size=2, ttl_sec=60.0)
    cache.set("a", 1)
    cache.set("b", 2)
    cache.set("c", 3)
    assert cache.get("a") is None


def test_lru_cache_ttl_expiration():
    cache = LRUCache(max_size=10, ttl_sec=0.1)
    cache.set("a", 1)
    time.sleep(0.15)
    assert cache.get("a") is None


def test_cache_statistics():
    stats = CacheStatistics()
    stats.record_hit()
    stats.record_miss()
    stats.record_eviction()
    result = stats.get_stats()
    assert result["hits"] == 1
    assert result["misses"] == 1
    assert result["evictions"] == 1
    assert "%" in result["hit_rate"]


def test_memory_cache_backend():
    backend = MemoryCacheBackend()
    backend.set("key", "value", ttl=60)
    assert backend.get("key") == "value"
    assert backend.delete("key") is True
    assert backend.get("key") is None
    backend.set("x", 1, ttl=60)
    backend.clear()
    assert backend.get("x") is None
    stats = backend.stats()
    assert "cache_size" in stats
