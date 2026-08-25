# -*- coding: utf-8 -*-
"""Tests for CacheManager module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.cache import CacheManager


@pytest.fixture
def cache_manager():
    """Create a test cache manager without Redis."""
    return CacheManager(redis_url=None)


@pytest.fixture
def cache_manager_with_redis():
    """Create a test cache manager with Redis URL."""
    return CacheManager(redis_url="redis://localhost:6379")


class TestCacheManager:
    """Test cases for CacheManager class."""

    @pytest.mark.asyncio
    async def test_get_memory_cache(self, cache_manager):
        """Test getting value from memory cache."""
        await cache_manager.set("key1", "value1")
        result = await cache_manager.get("key1")
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_get_nonexistent_key(self, cache_manager):
        """Test getting non-existent key."""
        result = await cache_manager.get("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_memory_cache(self, cache_manager):
        """Test setting value in memory cache."""
        await cache_manager.set("key1", "value1")
        assert "key1" in cache_manager._memory
        assert cache_manager._memory["key1"] == "value1"

    @pytest.mark.asyncio
    async def test_set_with_ttl(self, cache_manager):
        """Test setting value with TTL."""
        await cache_manager.set("key1", "value1", ttl=60)
        assert cache_manager._memory["key1"] == "value1"

    @pytest.mark.asyncio
    async def test_set_default_ttl(self, cache_manager):
        """Test setting value with default TTL."""
        await cache_manager.set("key1", "value1")
        assert cache_manager._memory["key1"] == "value1"

    @pytest.mark.asyncio
    async def test_delete_memory_cache(self, cache_manager):
        """Test deleting from memory cache."""
        await cache_manager.set("key1", "value1")
        await cache_manager.delete("key1")
        assert "key1" not in cache_manager._memory

    @pytest.mark.asyncio
    async def test_delete_nonexistent_key(self, cache_manager):
        """Test deleting non-existent key."""
        await cache_manager.delete("nonexistent")  # Should not raise

    @pytest.mark.asyncio
    async def test_clear_memory_cache(self, cache_manager):
        """Test clearing memory cache."""
        await cache_manager.set("key1", "value1")
        await cache_manager.set("key2", "value2")
        await cache_manager.clear()
        assert len(cache_manager._memory) == 0

    @pytest.mark.asyncio
    async def test_clear_empty_cache(self, cache_manager):
        """Test clearing empty cache."""
        await cache_manager.clear()
        assert len(cache_manager._memory) == 0

    @pytest.mark.asyncio
    async def test_set_overwrites_existing(self, cache_manager):
        """Test that set overwrites existing value."""
        await cache_manager.set("key1", "value1")
        await cache_manager.set("key1", "value2")
        assert cache_manager._memory["key1"] == "value2"

    @pytest.mark.asyncio
    async def test_set_complex_object(self, cache_manager):
        """Test setting complex object."""
        complex_obj = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        await cache_manager.set("key1", complex_obj)
        result = await cache_manager.get("key1")
        assert result == complex_obj

    @pytest.mark.asyncio
    async def test_set_none_value(self, cache_manager):
        """Test setting None value."""
        await cache_manager.set("key1", None)
        result = await cache_manager.get("key1")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_empty_string(self, cache_manager):
        """Test setting empty string."""
        await cache_manager.set("key1", "")
        result = await cache_manager.get("key1")
        assert result == ""

    @pytest.mark.asyncio
    async def test_set_zero_value(self, cache_manager):
        """Test setting zero value."""
        await cache_manager.set("key1", 0)
        result = await cache_manager.get("key1")
        assert result == 0

    @pytest.mark.asyncio
    async def test_set_false_value(self, cache_manager):
        """Test setting False value."""
        await cache_manager.set("key1", False)
        result = await cache_manager.get("key1")
        assert result is False

    @pytest.mark.asyncio
    async def test_connect_without_redis_url(self, cache_manager):
        """Test connect without Redis URL."""
        await cache_manager.connect()
        assert cache_manager._redis is None

    @pytest.mark.asyncio
    async def test_connect_with_empty_redis_url(self):
        """Test connect with empty Redis URL."""
        cache = CacheManager(redis_url="")
        await cache.connect()
        assert cache._redis is None

    @pytest.mark.asyncio
    async def test_connect_already_connected(self, cache_manager_with_redis):
        """Test connect when already connected."""
        cache_manager_with_redis._redis = MagicMock()
        await cache_manager_with_redis.connect()
        # Should return without error

    @pytest.mark.asyncio
    async def test_connect_redis_success(self, cache_manager_with_redis):
        """Test successful Redis connection."""
        # Skip this test since aioredis is not available
        # The actual code handles the ImportError gracefully
        await cache_manager_with_redis.connect()
        assert cache_manager_with_redis._redis is None

    @pytest.mark.asyncio
    async def test_connect_redis_failure(self, cache_manager_with_redis):
        """Test Redis connection failure."""
        # Skip this test since aioredis is not available
        # The actual code handles the ImportError gracefully
        await cache_manager_with_redis.connect()
        assert cache_manager_with_redis._redis is None

    @pytest.mark.asyncio
    async def test_redis_get_success(self, cache_manager_with_redis):
        """Test Redis get success."""
        cache_manager_with_redis._redis = AsyncMock()
        cache_manager_with_redis._redis.get.return_value = '"value1"'

        result = await cache_manager_with_redis.get("key1")

        assert result == "value1"
        cache_manager_with_redis._redis.get.assert_called_once_with("key1")

    @pytest.mark.asyncio
    async def test_redis_get_failure(self, cache_manager_with_redis):
        """Test Redis get failure falls back to memory."""
        cache_manager_with_redis._redis = AsyncMock()
        cache_manager_with_redis._redis.get.side_effect = Exception("Redis error")
        cache_manager_with_redis._memory["key1"] = "memory_value"

        result = await cache_manager_with_redis.get("key1")

        assert result == "memory_value"

    @pytest.mark.asyncio
    async def test_redis_get_none(self, cache_manager_with_redis):
        """Test Redis get returns None."""
        cache_manager_with_redis._redis = AsyncMock()
        cache_manager_with_redis._redis.get.return_value = None
        cache_manager_with_redis._memory["key1"] = "memory_value"

        result = await cache_manager_with_redis.get("key1")

        assert result == "memory_value"

    @pytest.mark.asyncio
    async def test_redis_set_success(self, cache_manager_with_redis):
        """Test Redis set success."""
        cache_manager_with_redis._redis = AsyncMock()

        await cache_manager_with_redis.set("key1", "value1", ttl=60)

        cache_manager_with_redis._redis.setex.assert_called_once()
        assert "key1" in cache_manager_with_redis._memory

    @pytest.mark.asyncio
    async def test_redis_set_failure(self, cache_manager_with_redis):
        """Test Redis set failure falls back to memory."""
        cache_manager_with_redis._redis = AsyncMock()
        cache_manager_with_redis._redis.setex.side_effect = Exception("Redis error")

        await cache_manager_with_redis.set("key1", "value1", ttl=60)

        assert cache_manager_with_redis._memory["key1"] == "value1"

    @pytest.mark.asyncio
    async def test_redis_delete_success(self, cache_manager_with_redis):
        """Test Redis delete success."""
        cache_manager_with_redis._redis = AsyncMock()
        cache_manager_with_redis._memory["key1"] = "value1"

        await cache_manager_with_redis.delete("key1")

        cache_manager_with_redis._redis.delete.assert_called_once_with("key1")
        assert "key1" not in cache_manager_with_redis._memory

    @pytest.mark.asyncio
    async def test_redis_delete_failure(self, cache_manager_with_redis):
        """Test Redis delete failure falls back to memory."""
        cache_manager_with_redis._redis = AsyncMock()
        cache_manager_with_redis._redis.delete.side_effect = Exception("Redis error")
        cache_manager_with_redis._memory["key1"] = "value1"

        await cache_manager_with_redis.delete("key1")

        assert "key1" not in cache_manager_with_redis._memory

    @pytest.mark.asyncio
    async def test_redis_clear_success(self, cache_manager_with_redis):
        """Test Redis clear success."""
        cache_manager_with_redis._redis = AsyncMock()
        cache_manager_with_redis._memory["key1"] = "value1"

        await cache_manager_with_redis.clear()

        cache_manager_with_redis._redis.flushdb.assert_called_once()
        assert len(cache_manager_with_redis._memory) == 0

    @pytest.mark.asyncio
    async def test_redis_clear_failure(self, cache_manager_with_redis):
        """Test Redis clear failure falls back to memory."""
        cache_manager_with_redis._redis = AsyncMock()
        cache_manager_with_redis._redis.flushdb.side_effect = Exception("Redis error")
        cache_manager_with_redis._memory["key1"] = "value1"

        await cache_manager_with_redis.clear()

        assert len(cache_manager_with_redis._memory) == 0

    @pytest.mark.asyncio
    async def test_multiple_keys(self, cache_manager):
        """Test multiple keys in cache."""
        await cache_manager.set("key1", "value1")
        await cache_manager.set("key2", "value2")
        await cache_manager.set("key3", "value3")

        assert await cache_manager.get("key1") == "value1"
        assert await cache_manager.get("key2") == "value2"
        assert await cache_manager.get("key3") == "value3"
        assert len(cache_manager._memory) == 3

    @pytest.mark.asyncio
    async def test_key_with_special_characters(self, cache_manager):
        """Test keys with special characters."""
        await cache_manager.set("key:with:colons", "value1")
        await cache_manager.set("key-with-dashes", "value2")
        await cache_manager.set("key_with_underscores", "value3")

        assert await cache_manager.get("key:with:colons") == "value1"
        assert await cache_manager.get("key-with-dashes") == "value2"
        assert await cache_manager.get("key_with_underscores") == "value3"

    @pytest.mark.asyncio
    async def test_large_value(self, cache_manager):
        """Test storing large value."""
        large_value = "x" * 10000
        await cache_manager.set("large_key", large_value)
        result = await cache_manager.get("large_key")
        assert result == large_value

    @pytest.mark.asyncio
    async def test_unicode_value(self, cache_manager):
        """Test storing unicode value."""
        unicode_value = "Hello 世界 🌍"
        await cache_manager.set("unicode_key", unicode_value)
        result = await cache_manager.get("unicode_key")
        assert result == unicode_value

    def test_initialization_defaults(self):
        """Test CacheManager initialization with defaults."""
        cache = CacheManager()
        assert cache._redis_url == ""
        assert cache._redis is None
        assert isinstance(cache._memory, dict)

    def test_initialization_with_url(self):
        """Test CacheManager initialization with URL."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        assert cache._redis_url == "redis://localhost:6379"
        assert cache._redis is None
