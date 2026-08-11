# -*- coding: utf-8 -*-
"""Tests for cache helpers, manager and strategy."""

import time

import core.cache_helpers
import core.cache_manager
import core.smart_cache_strategy


def test_cache_statistics():
    stats = core.cache_helpers.CacheStatistics()
    stats.record_hit()
    stats.record_miss()
    stats.record_eviction()
    stats.size = 5
    stats.max_size = 10
    result = stats.get_stats()
    assert result["hits"] == 1
    assert result["misses"] == 1
    assert result["evictions"] == 1
    assert "hit_rate" in result


def test_lru_cache_basic():
    cache = core.cache_helpers.LRUCache(max_size=2, ttl_sec=10.0)
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    cache.set("c", 3)
    assert cache.get("b") is None
    assert cache.get("c") == 3
    assert cache.invalidate("a") is True
    assert cache.invalidate("missing") is False
    cache.clear()
    assert cache.get("a") is None


def test_lru_cache_ttl():
    cache = core.cache_helpers.LRUCache(max_size=10, ttl_sec=0.05)
    cache.set("x", 42)
    assert cache.get("x") == 42
    time.sleep(0.1)
    assert cache.get("x") is None


def test_generate_cache_key():
    key = core.cache_helpers.generate_cache_key("pref", 1, 2, x=3)
    assert isinstance(key, str)
    assert "pref" in key


def test_memory_cache_backend():
    backend = core.cache_manager.MemoryCacheBackend()
    backend.set("k", {"v": 1}, ttl=1)
    assert backend.get("k") == {"v": 1}
    assert backend.stats()["cache_size"] == 1
    assert backend.delete("k") is True
    assert backend.delete("k") is False
    backend.set("k2", 2, ttl=1)
    assert backend.clear() is True
    assert backend.get("k2") is None


def test_cache_result_decorator():
    core.cache_manager.flush_all()

    @core.cache_manager.cache_result(ttl=60)
    def add(a, b):
        calls.append((a, b))
        return a + b

    calls = []
    assert add(1, 2) == 3
    assert add(1, 2) == 3
    assert len(calls) == 1
    stats = core.cache_manager.get_cache_stats("add")
    assert stats["function_size"] >= 1


def test_invalidate_backup_restore():
    core.cache_manager.flush_all()

    @core.cache_manager.cache_result(ttl=60)
    def double(x):
        return x * 2

    double(5)
    backup = core.cache_manager.backup_cache("double")
    assert len(backup) == 1
    core.cache_manager.flush_all()
    assert core.cache_manager.restore_cache(backup) == 1
    assert core.cache_manager.invalidate_cache("double") == 1


def test_smart_cache_strategy():
    assert core.smart_cache_strategy.SmartCacheStrategy.get_ttl("k", 200, 100) == 60
    assert core.smart_cache_strategy.SmartCacheStrategy.get_ttl("k", 50, 100) == 300
    assert core.smart_cache_strategy.SmartCacheStrategy.get_ttl("k", 1, 100) == 3600
    assert core.smart_cache_strategy.SmartCacheStrategy.get_cache_tier("k") == "cold"
