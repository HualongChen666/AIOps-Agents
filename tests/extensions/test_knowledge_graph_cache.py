# -*- coding: utf-8 -*-
"""Comprehensive tests for knowledge graph cache manager."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from extensions.addons.ai_plus.knowledge_graph_service.cache import CacheManager


class TestCacheManager:
    """Test suite for CacheManager class."""

    def test_initialization_default(self):
        """Test cache manager initialization with default parameters."""
        cache = CacheManager()
        assert cache._memory == {}
        assert cache._redis_url == ""
        assert cache._redis is None

    def test_initialization_with_redis_url(self):
        """Test cache manager initialization with Redis URL."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        assert cache._redis_url == "redis://localhost:6379"
        assert cache._redis is None

    @pytest.mark.asyncio
    async def test_get_from_memory(self):
        """Test getting value from in-memory cache."""
        cache = CacheManager()
        cache._memory["test_key"] = {"data": "test_value"}
        
        result = await cache.get("test_key")
        assert result == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_get_from_memory_nonexistent(self):
        """Test getting nonexistent key from in-memory cache."""
        cache = CacheManager()
        result = await cache.get("nonexistent_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_from_redis_success(self):
        """Test getting value from Redis cache successfully."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        mock_redis.get.return_value = b'{"data": "test_value"}'
        cache._redis = mock_redis
        
        result = await cache.get("test_key")
        assert result == {"data": "test_value"}
        mock_redis.get.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_get_from_redis_failure_fallback_to_memory(self):
        """Test Redis get failure falls back to memory cache."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis error")
        cache._redis = mock_redis
        cache._memory["test_key"] = {"data": "memory_value"}
        
        result = await cache.get("test_key")
        assert result == {"data": "memory_value"}

    @pytest.mark.asyncio
    async def test_get_from_redis_none_value(self):
        """Test getting None value from Redis falls back to memory."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        cache._redis = mock_redis
        cache._memory["test_key"] = {"data": "memory_value"}
        
        result = await cache.get("test_key")
        assert result == {"data": "memory_value"}

    @pytest.mark.asyncio
    async def test_set_to_memory(self):
        """Test setting value to in-memory cache."""
        cache = CacheManager()
        await cache.set("test_key", {"data": "test_value"})
        
        assert cache._memory["test_key"] == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_set_to_memory_with_ttl(self):
        """Test setting value to in-memory cache with TTL (TTL ignored for memory)."""
        cache = CacheManager()
        await cache.set("test_key", {"data": "test_value"}, ttl=300)
        
        assert cache._memory["test_key"] == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_set_to_redis_success(self):
        """Test setting value to Redis cache successfully."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._redis = mock_redis
        
        await cache.set("test_key", {"data": "test_value"}, ttl=600)
        
        assert cache._memory["test_key"] == {"data": "test_value"}
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_to_redis_default_ttl(self):
        """Test setting value to Redis with default TTL."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._redis = mock_redis
        
        await cache.set("test_key", {"data": "test_value"})
        
        assert cache._memory["test_key"] == {"data": "test_value"}
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_to_redis_failure(self):
        """Test Redis set failure still updates memory cache."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        mock_redis.setex.side_effect = Exception("Redis error")
        cache._redis = mock_redis
        
        await cache.set("test_key", {"data": "test_value"}, ttl=600)
        
        assert cache._memory["test_key"] == {"data": "test_value"}

    @pytest.mark.asyncio
    async def test_delete_from_memory(self):
        """Test deleting value from in-memory cache."""
        cache = CacheManager()
        cache._memory["test_key"] = {"data": "test_value"}
        
        await cache.delete("test_key")
        
        assert "test_key" not in cache._memory

    @pytest.mark.asyncio
    async def test_delete_nonexistent_from_memory(self):
        """Test deleting nonexistent key from memory cache."""
        cache = CacheManager()
        
        await cache.delete("nonexistent_key")
        
        # Should not raise an error
        assert "nonexistent_key" not in cache._memory

    @pytest.mark.asyncio
    async def test_delete_from_redis_success(self):
        """Test deleting value from Redis cache successfully."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._redis = mock_redis
        cache._memory["test_key"] = {"data": "test_value"}
        
        await cache.delete("test_key")
        
        assert "test_key" not in cache._memory
        mock_redis.delete.assert_called_once_with("test_key")

    @pytest.mark.asyncio
    async def test_delete_from_redis_failure(self):
        """Test Redis delete failure still updates memory cache."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = Exception("Redis error")
        cache._redis = mock_redis
        cache._memory["test_key"] = {"data": "test_value"}
        
        await cache.delete("test_key")
        
        assert "test_key" not in cache._memory

    @pytest.mark.asyncio
    async def test_clear_memory(self):
        """Test clearing in-memory cache."""
        cache = CacheManager()
        cache._memory["key1"] = {"data": "value1"}
        cache._memory["key2"] = {"data": "value2"}
        
        await cache.clear()
        
        assert cache._memory == {}

    @pytest.mark.asyncio
    async def test_clear_redis_success(self):
        """Test clearing Redis cache successfully."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._redis = mock_redis
        cache._memory["key1"] = {"data": "value1"}
        
        await cache.clear()
        
        assert cache._memory == {}
        mock_redis.flushdb.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_redis_failure(self):
        """Test Redis clear failure still clears memory cache."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        mock_redis.flushdb.side_effect = Exception("Redis error")
        cache._redis = mock_redis
        cache._memory["key1"] = {"data": "value1"}
        
        await cache.clear()
        
        assert cache._memory == {}

    @pytest.mark.asyncio
    async def test_connect_no_redis_url(self):
        """Test connect with no Redis URL configured."""
        cache = CacheManager()
        
        await cache.connect()
        
        assert cache._redis is None

    @pytest.mark.asyncio
    async def test_connect_already_connected(self):
        """Test connect when already connected to Redis."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._redis = mock_redis
        
        await cache.connect()
        
        # Should not try to connect again
        assert cache._redis is mock_redis

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful Redis connection."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        
        try:
            with patch('extensions.addons.ai_plus.knowledge_graph_service.cache.aioredis') as mock_aioredis:
                mock_redis = AsyncMock()
                mock_aioredis.from_url.return_value = mock_redis
                
                await cache.connect()
                
                mock_aioredis.from_url.assert_called_once_with("redis://localhost:6379")
                assert cache._redis is mock_redis
        except (ImportError, AttributeError):
            # Skip if aioredis is not available
            pytest.skip("aioredis not available")

    @pytest.mark.asyncio
    async def test_connect_import_failure(self):
        """Test Redis connection failure due to import error."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        
        try:
            with patch('extensions.addons.ai_plus.knowledge_graph_service.cache.aioredis', side_effect=ImportError("No module named 'aioredis'")):
                await cache.connect()
                
                assert cache._redis is None
        except (ImportError, AttributeError):
            # Skip if aioredis is not available
            pytest.skip("aioredis not available")

    @pytest.mark.asyncio
    async def test_connect_connection_failure(self):
        """Test Redis connection failure due to connection error."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        
        try:
            with patch('extensions.addons.ai_plus.knowledge_graph_service.cache.aioredis') as mock_aioredis:
                mock_aioredis.from_url.side_effect = Exception("Connection refused")
                
                await cache.connect()
                
                assert cache._redis is None
        except (ImportError, AttributeError):
            # Skip if aioredis is not available
            pytest.skip("aioredis not available")

    @pytest.mark.asyncio
    async def test_set_complex_data_structure(self):
        """Test setting complex nested data structures."""
        cache = CacheManager()
        complex_data = {
            "nested": {
                "array": [1, 2, 3],
                "object": {"key": "value"}
            },
            "simple": "string"
        }
        
        await cache.set("complex_key", complex_data)
        
        assert cache._memory["complex_key"] == complex_data

    @pytest.mark.asyncio
    async def test_get_set_roundtrip(self):
        """Test roundtrip of set and get operations."""
        cache = CacheManager()
        original_data = {"test": "data", "number": 42}
        
        await cache.set("roundtrip_key", original_data)
        retrieved_data = await cache.get("roundtrip_key")
        
        assert retrieved_data == original_data

    @pytest.mark.asyncio
    async def test_overwrite_existing_key(self):
        """Test overwriting an existing key."""
        cache = CacheManager()
        cache._memory["test_key"] = {"old": "data"}
        
        await cache.set("test_key", {"new": "data"})
        
        assert cache._memory["test_key"] == {"new": "data"}

    @pytest.mark.asyncio
    async def test_multiple_keys_operations(self):
        """Test operations with multiple keys."""
        cache = CacheManager()
        
        # Set multiple keys
        await cache.set("key1", "value1")
        await cache.set("key2", "value2")
        await cache.set("key3", "value3")
        
        # Verify all keys exist
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") == "value2"
        assert await cache.get("key3") == "value3"
        
        # Delete one key
        await cache.delete("key2")
        
        # Verify deletion
        assert await cache.get("key1") == "value1"
        assert await cache.get("key2") is None
        assert await cache.get("key3") == "value3"

    @pytest.mark.asyncio
    async def test_empty_string_key(self):
        """Test operations with empty string as key."""
        cache = CacheManager()
        
        await cache.set("", "empty_key_value")
        assert await cache.get("") == "empty_key_value"
        
        await cache.delete("")
        assert await cache.get("") is None

    @pytest.mark.asyncio
    async def test_none_value(self):
        """Test storing None as a value."""
        cache = CacheManager()
        
        await cache.set("none_key", None)
        result = await cache.get("none_key")
        
        assert result is None

    @pytest.mark.asyncio
    async def test_zero_ttl(self):
        """Test setting value with zero TTL."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._redis = mock_redis
        
        await cache.set("test_key", {"data": "value"}, ttl=0)
        
        assert cache._memory["test_key"] == {"data": "value"}
        # Redis should be called with ttl=0
        mock_redis.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_large_ttl(self):
        """Test setting value with very large TTL."""
        cache = CacheManager(redis_url="redis://localhost:6379")
        mock_redis = AsyncMock()
        cache._redis = mock_redis
        
        await cache.set("test_key", {"data": "value"}, ttl=86400)  # 24 hours
        
        assert cache._memory["test_key"] == {"data": "value"}
        mock_redis.setex.assert_called_once()
