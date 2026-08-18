# -*- coding: utf-8 -*-
"""Tests for cache.py - Cache manager with optional Redis backend."""

import asyncio
import json
import pytest

from extensions.addons.documentation.sphinx_documentation_service.cache import CacheManager
from extensions.addons.documentation.sphinx_documentation_service.metrics import MetricsCollector


class TestCacheManager:
    """Test suite for CacheManager."""

    @pytest.fixture
    def metrics(self):
        """Fixture for MetricsCollector."""
        return MetricsCollector("cache_test")

    @pytest.fixture
    def cache_manager(self, metrics):
        """Fixture for CacheManager without Redis."""
        return CacheManager(redis_url=None, metrics=metrics)

    @pytest.fixture
    def cache_manager_with_redis(self, metrics):
        """Fixture for CacheManager with Redis URL (may not connect)."""
        return CacheManager(redis_url="redis://localhost:6379/0", metrics=metrics)

    def test_init_without_redis(self, metrics):
        """Test initialization without Redis."""
        cache = CacheManager(redis_url=None, metrics=metrics)
        assert cache._redis is None
        assert isinstance(cache._memory, dict)
        assert cache.metrics is metrics

    def test_init_with_redis_url(self, metrics):
        """Test initialization with Redis URL."""
        cache = CacheManager(redis_url="redis://localhost:6379/0", metrics=metrics)
        # Redis connection may fail in test environment, but should not raise
        assert cache.metrics is metrics

    def test_init_without_metrics(self):
        """Test initialization without metrics (creates default)."""
        cache = CacheManager(redis_url=None, metrics=None)
        assert cache.metrics is not None
        assert isinstance(cache.metrics, MetricsCollector)

    def test_key_method(self, cache_manager):
        """Test _key method generates correct keys."""
        key = cache_manager._key("prefix", "middle", "suffix")
        assert key == "prefix:middle:suffix"

    def test_key_method_single_part(self, cache_manager):
        """Test _key method with single part."""
        key = cache_manager._key("single")
        assert key == "single"

    def test_key_method_with_numbers(self, cache_manager):
        """Test _key method with numeric parts."""
        key = cache_manager._key("test", 123, 456.7)
        assert key == "test:123:456.7"

    @pytest.mark.asyncio
    async def test_get_miss(self, cache_manager):
        """Test get with non-existent key returns None."""
        result = await cache_manager.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_and_get(self, cache_manager):
        """Test set and get operations."""
        await cache_manager.set("test_key", {"data": "value"})
        result = await cache_manager.get("test_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_set_overwrite(self, cache_manager):
        """Test that set overwrites existing value."""
        await cache_manager.set("test_key", {"data": "old"})
        await cache_manager.set("test_key", {"data": "new"})
        result = await cache_manager.get("test_key")
        assert result == {"data": "new"}

    @pytest.mark.asyncio
    async def test_delete_existing(self, cache_manager):
        """Test delete existing key."""
        await cache_manager.set("test_key", {"data": "value"})
        await cache_manager.delete("test_key")
        result = await cache_manager.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, cache_manager):
        """Test delete non-existent key does not raise."""
        await cache_manager.delete("nonexistent_key")
        # Should not raise any exception

    @pytest.mark.asyncio
    async def test_clear(self, cache_manager):
        """Test clear operation."""
        await cache_manager.set("key1", {"data": "value1"})
        await cache_manager.set("key2", {"data": "value2"})
        await cache_manager.clear()
        assert await cache_manager.get("key1") is None
        assert await cache_manager.get("key2") is None

    @pytest.mark.asyncio
    async def test_clear_empty_cache(self, cache_manager):
        """Test clear on empty cache."""
        await cache_manager.clear()
        # Should not raise any exception

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache_manager):
        """Test set with TTL parameter."""
        await cache_manager.set("test_key", {"data": "value"}, ttl=100)
        result = await cache_manager.get("test_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_set_default_ttl(self, cache_manager):
        """Test set with default TTL."""
        await cache_manager.set("test_key", {"data": "value"})
        result = await cache_manager.get("test_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_cache_hit_metrics(self, cache_manager, metrics):
        """Test that cache hit increments metrics."""
        await cache_manager.set("test_key", {"data": "value"})
        initial_hits = metrics.cache_hits_count
        await cache_manager.get("test_key")
        assert metrics.cache_hits_count == initial_hits + 1

    @pytest.mark.asyncio
    async def test_cache_miss_metrics(self, cache_manager, metrics):
        """Test that cache miss increments metrics."""
        initial_misses = metrics.cache_misses_count
        await cache_manager.get("nonexistent_key")
        assert metrics.cache_misses_count == initial_misses + 1

    @pytest.mark.asyncio
    async def test_complex_data_types(self, cache_manager):
        """Test storing complex data types."""
        complex_data = {
            "string": "value",
            "number": 123,
            "float": 45.67,
            "bool": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
        }
        await cache_manager.set("complex_key", complex_data)
        result = await cache_manager.get("complex_key")
        assert result == complex_data

    @pytest.mark.asyncio
    async def test_none_value(self, cache_manager):
        """Test storing None value."""
        await cache_manager.set("none_key", None)
        result = await cache_manager.get("none_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_string(self, cache_manager):
        """Test storing empty string."""
        await cache_manager.set("empty_key", "")
        result = await cache_manager.get("empty_key")
        assert result == ""

    @pytest.mark.asyncio
    async def test_empty_list(self, cache_manager):
        """Test storing empty list."""
        await cache_manager.set("empty_list", [])
        result = await cache_manager.get("empty_list")
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_dict(self, cache_manager):
        """Test storing empty dict."""
        await cache_manager.set("empty_dict", {})
        result = await cache_manager.get("empty_dict")
        assert result == {}

    @pytest.mark.asyncio
    async def test_unicode_characters(self, cache_manager):
        """Test storing unicode characters."""
        unicode_data = {"text": "Hello 世界 🌍"}
        await cache_manager.set("unicode_key", unicode_data)
        result = await cache_manager.get("unicode_key")
        assert result == unicode_data

    @pytest.mark.asyncio
    async def test_large_data(self, cache_manager):
        """Test storing large data."""
        large_data = {"items": list(range(1000))}
        await cache_manager.set("large_key", large_data)
        result = await cache_manager.get("large_key")
        assert result == large_data

    @pytest.mark.asyncio
    async def test_concurrent_access(self, cache_manager):
        """Test concurrent access to cache."""
        async def set_get(key, value):
            await cache_manager.set(key, value)
            return await cache_manager.get(key)

        tasks = [set_get(f"key_{i}", f"value_{i}") for i in range(10)]
        results = await asyncio.gather(*tasks)
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result == f"value_{i}"

    @pytest.mark.asyncio
    async def test_redis_connection_failure_handling(self, metrics):
        """Test that Redis connection failure falls back to memory cache."""
        # Use invalid Redis URL to force connection failure
        cache = CacheManager(redis_url="redis://invalid:9999/0", metrics=metrics)
        await cache.set("test_key", {"data": "value"})
        result = await cache.get("test_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_memory_cache_isolation(self, metrics):
        """Test that different cache instances have isolated memory caches."""
        cache1 = CacheManager(redis_url=None, metrics=metrics)
        cache2 = CacheManager(redis_url=None, metrics=metrics)

        await cache1.set("key1", {"data": "value1"})
        await cache2.set("key1", {"data": "value2"})

        result1 = await cache1.get("key1")
        result2 = await cache2.get("key1")

        assert result1 == {"data": "value1"}
        assert result2 == {"data": "value2"}

    @pytest.mark.asyncio
    async def test_delete_from_memory_only(self, cache_manager):
        """Test delete removes from memory cache."""
        await cache_manager.set("test_key", {"data": "value"})
        await cache_manager.delete("test_key")
        assert "test_key" not in cache_manager._memory

    @pytest.mark.asyncio
    async def test_clear_memory_only(self, cache_manager):
        """Test clear empties memory cache."""
        await cache_manager.set("key1", {"data": "value1"})
        await cache_manager.set("key2", {"data": "value2"})
        await cache_manager.clear()
        assert len(cache_manager._memory) == 0

    @pytest.mark.asyncio
    async def test_set_with_zero_ttl(self, cache_manager):
        """Test set with TTL=0."""
        await cache_manager.set("test_key", {"data": "value"}, ttl=0)
        result = await cache_manager.get("test_key")
        assert result == {"data": "value"}

    @pytest.mark.asyncio
    async def test_special_characters_in_key(self, cache_manager):
        """Test keys with special characters."""
        special_keys = ["key:with:colons", "key-with-dashes", "key_with_underscores"]
        for key in special_keys:
            await cache_manager.set(key, {"data": key})
            result = await cache_manager.get(key)
            assert result == {"data": key}

    @pytest.mark.asyncio
    async def test_get_after_delete_returns_none(self, cache_manager):
        """Test that get after delete returns None."""
        await cache_manager.set("test_key", {"data": "value"})
        await cache_manager.delete("test_key")
        result = await cache_manager.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_overwrite_increments_metrics(self, cache_manager, metrics):
        """Test that overwriting a key affects metrics correctly."""
        await cache_manager.set("test_key", {"data": "old"})
        await cache_manager.set("test_key", {"data": "new"})
        # First get should be a hit
        await cache_manager.get("test_key")
        assert metrics.cache_hits_count > 0
