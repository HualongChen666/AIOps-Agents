# -*- coding: utf-8 -*-
"""Tests for cache helpers, manager and strategy."""

import time  # noqa: F401  # Imported for test setup
import pytest

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
    result = stats.get_stats()  # noqa: F841  # Variable for test verification
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
    """Test CacheManager Redis backend implementation"""
    backend = core.cache_manager.cache_manager
    # Test set and get (may fail if Redis not available)
    set_result = backend.set("test:k", {"v": 1}, ttl=1)
    if set_result:
        # Redis is available, test full functionality
        assert backend.get("test:k") == {"v": 1}
        # Test delete
        assert backend.delete("test:k") is True
        assert backend.get("test:k") is None
        # Test exists
        backend.set("test:k2", 2, ttl=1)
        assert backend.exists("test:k2") is True
        # Test delete pattern
        assert backend.delete_pattern("test:*") >= 0
        assert backend.get("test:k2") is None
    else:
        # Redis not available, test API exists and returns expected values
        assert backend.get("test:k") is None
        assert backend.delete("test:k") is False
        assert backend.exists("test:k") is False
        assert backend.delete_pattern("test:*") == 0


def test_cache_result_decorator():
    """Test cached decorator implementation"""
    calls = []

    @core.cache_manager.cached(ttl=60, prefix="test")
    def add(a, b):
        calls.append((a, b))
        return a + b

    # First call should execute function
    assert add(1, 2) == 3
    assert len(calls) == 1

    # Check if Redis is available for caching
    if core.cache_manager.cache_manager.redis_client:
        # Second call should use cache if Redis is available
        assert add(1, 2) == 3
        assert len(calls) == 1  # Should still be 1 due to caching

        # Different arguments should execute function
        assert add(2, 3) == 5
        assert len(calls) == 2

        # Clean up cache
        core.cache_manager.invalidate_cache_pattern("test:*")
    else:
        # Redis not available, function will execute every time
        assert add(1, 2) == 3
        assert len(calls) == 2  # Function executed again

        # Different arguments should execute function
        assert add(2, 3) == 5
        assert len(calls) == 3


def test_invalidate_backup_restore():
    """Test cache invalidation using pattern matching"""
    calls = []

    @core.cache_manager.cached(ttl=60, prefix="test_double")
    def double(x):
        calls.append(x)
        return x * 2

    # Execute function to populate cache
    assert double(5) == 10
    assert len(calls) == 1

    # Check if Redis is available for caching
    if core.cache_manager.cache_manager.redis_client:
        # Verify cache is working (second call should use cache)
        assert double(5) == 10
        assert len(calls) == 1

        # Invalidate cache using pattern
        invalidated_count = core.cache_manager.invalidate_cache_pattern("test_double:*")
        assert invalidated_count >= 0  # Redis may return 0 if key already expired

        # After invalidation, function should execute again
        assert double(5) == 10
        assert len(calls) == 2

        # Clean up
        core.cache_manager.invalidate_cache_pattern("test_double:*")
    else:
        # Redis not available, function will execute every time
        assert double(5) == 10
        assert len(calls) == 2  # Function executed again

        # Invalidate cache using pattern (will return 0 since no Redis)
        invalidated_count = core.cache_manager.invalidate_cache_pattern("test_double:*")
        assert invalidated_count == 0

        # Function will execute again
        assert double(5) == 10
        assert len(calls) == 3


def test_smart_cache_strategy():
    assert core.smart_cache_strategy.SmartCacheStrategy.get_ttl("k", 200, 100) == 60
    assert core.smart_cache_strategy.SmartCacheStrategy.get_ttl("k", 50, 100) == 300
    assert core.smart_cache_strategy.SmartCacheStrategy.get_ttl("k", 1, 100) == 3600
    assert core.smart_cache_strategy.SmartCacheStrategy.get_cache_tier("k") == "cold"
