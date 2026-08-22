# -*- coding: utf-8 -*-
"""Unit tests for cache.py - Cache manager with optional Redis backend."""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from extensions.addons.ai_plus.llm_router_service.cache import CacheManager


class TestCacheManager:
    """Test CacheManager class."""

    @pytest.mark.asyncio
    async def test_cache_manager_without_redis(self):
        """Test cache manager initialization without Redis."""
        cache = CacheManager(redis_url=None)
        assert cache._redis is None
        assert cache._memory == {}

    @pytest.mark.asyncio
    async def test_cache_manager_with_invalid_redis_url(self):
        """Test cache manager with invalid Redis URL."""
        cache = CacheManager(redis_url="invalid://url")
        # Should fall back to memory cache
        assert cache._redis is None
        assert isinstance(cache._memory, dict)

    @pytest.mark.asyncio
    async def test_cache_manager_with_valid_redis_url(self):
        """Test cache manager with valid Redis URL (mocked)."""
        with patch("extensions.addons.ai_plus.llm_router_service.cache.aioredis") as mock_aioredis:
            mock_redis = AsyncMock()
            mock_aioredis.from_url.return_value = mock_redis

            cache = CacheManager(redis_url="redis://localhost:6379")
            assert cache._redis == mock_redis
            mock_aioredis.from_url.assert_called_once_with("redis://localhost:6379", decode_responses=True)

    @pytest.mark.asyncio
    async def test_key_generation(self):
        """Test _key method for generating cache keys."""
        cache = CacheManager()
        key1 = cache._key("route", "prompt1", "general")
        key2 = cache._key("route", "prompt2", "code")
        key3 = cache._key("route", "prompt1", "general")

        assert key1 == "route:prompt1:general"
        assert key2 == "route:prompt2:code"
        assert key1 == key3  # Same inputs produce same key

    @pytest.mark.asyncio
    async def test_key_generation_with_numbers(self):
        """Test _key method with numeric inputs."""
        cache = CacheManager()
        key = cache._key("route", 123, 456.789)
        assert key == "route:123:456.789"

    @pytest.mark.asyncio
    async def test_get_from_memory_cache_hit(self):
        """Test getting value from memory cache (hit)."""
        cache = CacheManager()
        cache._memory["test_key"] = {"data": "test_value"}

        result = await cache.get("test_key")
        assert result == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_get_from_memory_cache_miss(self):
        """Test getting value from memory cache (miss)."""
        cache = CacheManager()
        result = await cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_from_redis_cache_hit(self):
        """Test getting value from Redis cache (hit)."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({"data": "test_value"})

        cache = CacheManager()
        cache._redis = mock_redis

        result = await cache.get("test_key")
        assert result == {"data": "test_value"}
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_from_redis_cache_miss(self):
        """Test getting value from Redis cache (miss)."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        cache = CacheManager()
        cache._redis = mock_redis
        cache._memory = {}

        result = await cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_redis_error_fallback_to_memory(self):
        """Test Redis error falls back to memory cache."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")

        cache = CacheManager()
        cache._redis = mock_redis
        cache._memory["test_key"] = {"data": "memory_value"}

        result = await cache.get("test_key")
        assert result == {"data": "memory_value"}

    @pytest.mark.asyncio
    async def test_get_redis_error_no_memory_fallback(self):
        """Test Redis error with no memory fallback."""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")

        cache = CacheManager()
        cache._redis = mock_redis
        cache._memory = {}

        result = await cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_to_memory_cache(self):
        """Test setting value to memory cache."""
        cache = CacheManager()
        await cache.set("test_key", {"data": "test_value"})

        assert cache._memory["test_key"] == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_set_to_redis_cache(self):
        """Test setting value to Redis cache."""
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        cache = CacheManager()
        cache._redis = mock_redis

        await cache.set("test_key", {"data": "test_value"}, ttl=300)

        mock_redis.setex.assert_called_once_with(
            "test_key", 300, json.dumps({"data": "test_value"})
        )

    @pytest.mark.asyncio
    async def test_set_with_default_ttl(self):
        """Test setting value with default TTL."""
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        cache = CacheManager()
        cache._redis = mock_redis

        await cache.set("test_key", {"data": "test_value"})

        mock_redis.setex.assert_called_once_with(
            "test_key", 300, json.dumps({"data": "test_value"})
        )

    @pytest.mark.asyncio
    async def test_set_with_custom_ttl(self):
        """Test setting value with custom TTL."""
        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        cache = CacheManager()
        cache._redis = mock_redis

        await cache.set("test_key", {"data": "test_value"}, ttl=600)

        mock_redis.setex.assert_called_once_with(
            "test_key", 600, json.dumps({"data": "test_value"})
        )

    @pytest.mark.asyncio
    async def test_set_redis_error_fallback_to_memory(self):
        """Test Redis error falls back to memory cache on set."""
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Redis error")

        cache = CacheManager()
        cache._redis = mock_redis

        await cache.set("test_key", {"data": "test_value"})

        assert cache._memory["test_key"] == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_set_complex_data_structure(self):
        """Test setting complex data structure."""
        cache = CacheManager()
        complex_data = {
            "nested": {
                "list": [1, 2, 3],
                "dict": {"key": "value"},
            },
            "string": "test",
            "number": 123,
            "boolean": True,
            "null": None,
        }

        await cache.set("complex_key", complex_data)
        result = await cache.get("complex_key")

        assert result == complex_data

    @pytest.mark.asyncio
    async def test_get_set_roundtrip(self):
        """Test roundtrip of set and get operations."""
        cache = CacheManager()
        original_data = {"prompt": "test", "model": "gpt-4", "cost": 0.01}

        await cache.set("roundtrip_key", original_data)
        retrieved_data = await cache.get("roundtrip_key")

        assert retrieved_data == original_data

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self):
        """Test overwriting an existing cache key."""
        cache = CacheManager()
        await cache.set("overwrite_key", {"version": 1})
        await cache.set("overwrite_key", {"version": 2})

        result = await cache.get("overwrite_key")
        assert result == {"version": 2}

    @pytest.mark.asyncio
    async def test_set_none_value(self):
        """Test setting None value."""
        cache = CacheManager()
        await cache.set("none_key", None)

        result = await cache.get("none_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_empty_string(self):
        """Test setting empty string."""
        cache = CacheManager()
        await cache.set("empty_key", "")

        result = await cache.get("empty_key")
        assert result == ""

    @pytest.mark.asyncio
    async def test_set_zero_value(self):
        """Test setting zero value."""
        cache = CacheManager()
        await cache.set("zero_key", 0)

        result = await cache.get("zero_key")
        assert result == 0

    @pytest.mark.asyncio
    async def test_set_false_value(self):
        """Test setting False value."""
        cache = CacheManager()
        await cache.set("false_key", False)

        result = await cache.get("false_key")
        assert result is False

    @pytest.mark.asyncio
    async def test_set_empty_list(self):
        """Test setting empty list."""
        cache = CacheManager()
        await cache.set("empty_list_key", [])

        result = await cache.get("empty_list_key")
        assert result == []

    @pytest.mark.asyncio
    async def test_set_empty_dict(self):
        """Test setting empty dict."""
        cache = CacheManager()
        await cache.set("empty_dict_key", {})

        result = await cache.get("empty_dict_key")
        assert result == {}

    @pytest.mark.asyncio
    async def test_multiple_keys(self):
        """Test managing multiple cache keys."""
        cache = CacheManager()
        keys_values = {
            "key1": {"data": "value1"},
            "key2": {"data": "value2"},
            "key3": {"data": "value3"},
        }

        for key, value in keys_values.items():
            await cache.set(key, value)

        for key, expected_value in keys_values.items():
            result = await cache.get(key)
            assert result == expected_value

    @pytest.mark.asyncio
    async def test_key_with_special_characters(self):
        """Test cache key with special characters."""
        cache = CacheManager()
        special_key = cache._key("route", "test:prompt", "special::key")

        await cache.set(special_key, {"data": "test"})
        result = await cache.get(special_key)

        assert result == {"data": "test"}

    @pytest.mark.asyncio
    async def test_key_with_unicode(self):
        """Test cache key with unicode characters."""
        cache = CacheManager()
        unicode_key = cache._key("route", "测试", "中文")

        await cache.set(unicode_key, {"data": "unicode"})
        result = await cache.get(unicode_key)

        assert result == {"data": "unicode"}

    @pytest.mark.asyncio
    async def test_large_value(self):
        """Test caching large value."""
        cache = CacheManager()
        large_value = {"data": "x" * 10000}

        await cache.set("large_key", large_value)
        result = await cache.get("large_key")

        assert result == large_value

    @pytest.mark.asyncio
    async def test_json_serialization_error(self):
        """Test handling of JSON serialization errors."""
        cache = CacheManager()
        # Object that can't be JSON serialized
        non_serializable = lambda: None

        # This should raise an error or handle gracefully
        with pytest.raises(Exception):
            await cache.set("bad_key", non_serializable)

    @pytest.mark.asyncio
    async def test_redis_json_decode_error(self):
        """Test handling of JSON decode errors from Redis."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "invalid json"

        cache = CacheManager()
        cache._redis = mock_redis
        cache._memory = {}

        result = await cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_memory_cache_isolation(self):
        """Test that memory cache is isolated between instances."""
        cache1 = CacheManager()
        cache2 = CacheManager()

        await cache1.set("key1", {"instance": 1})
        await cache2.set("key2", {"instance": 2})

        assert await cache1.get("key1") == {"instance": 1}
        assert await cache1.get("key2") is None
        assert await cache2.get("key2") == {"instance": 2}
        assert await cache2.get("key1") is None

    @pytest.mark.asyncio
    async def test_ttl_parameter_variations(self):
        """Test different TTL values."""
        cache = CacheManager()
        ttl_values = [0, 1, 60, 300, 3600, 86400]

        for ttl in ttl_values:
            await cache.set(f"ttl_key_{ttl}", {"ttl": ttl}, ttl=ttl)
            result = await cache.get(f"ttl_key_{ttl}")
            assert result == {"ttl": ttl}

    @pytest.mark.asyncio
    async def test_concurrent_operations(self):
        """Test concurrent cache operations."""
        import asyncio

        cache = CacheManager()
        tasks = []

        for i in range(10):
            tasks.append(cache.set(f"concurrent_key_{i}", {"value": i}))
            tasks.append(cache.get(f"concurrent_key_{i}"))

        await asyncio.gather(*tasks)

        for i in range(10):
            result = await cache.get(f"concurrent_key_{i}")
            assert result == {"value": i}
