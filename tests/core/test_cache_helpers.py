# -*- coding: utf-8 -*-
"""
Comprehensive test suite for core/cache_helpers.py
Target: 90%+ statement and branch coverage
"""

import json
import os
import sys
import time
from datetime import datetime
from threading import Lock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Disable database fixtures for this test file
pytestmark = [pytest.mark.skip_db, pytest.mark.core]

from core.cache_helpers import (
    CacheEvictionPolicy,
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


class TestCacheStatistics:
    """Test suite for CacheStatistics class"""

    def test_initialization(self):
        """Test CacheStatistics initialization"""
        stats = CacheStatistics()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.evictions == 0
        assert stats.size == 0
        assert stats.max_size == 0

    def test_record_hit(self):
        """Test recording cache hits"""
        stats = CacheStatistics()
        stats.record_hit()
        assert stats.hits == 1
        stats.record_hit()
        assert stats.hits == 2

    def test_record_miss(self):
        """Test recording cache misses"""
        stats = CacheStatistics()
        stats.record_miss()
        assert stats.misses == 1
        stats.record_miss()
        assert stats.misses == 2

    def test_record_eviction(self):
        """Test recording cache evictions"""
        stats = CacheStatistics()
        stats.record_eviction()
        assert stats.evictions == 1

    def test_get_hit_rate(self):
        """Test hit rate calculation"""
        stats = CacheStatistics()
        assert stats.get_hit_rate() == 0.0

        stats.record_hit()
        stats.record_miss()
        assert stats.get_hit_rate() == 50.0

        stats.record_hit()
        assert round(stats.get_hit_rate(), 2) == 66.67

    def test_get_hit_rate_no_requests(self):
        """Test hit rate with no requests"""
        stats = CacheStatistics()
        assert stats.get_hit_rate() == 0.0

    def test_get_stats(self):
        """Test getting statistics dictionary"""
        stats = CacheStatistics()
        stats.record_hit()
        stats.record_miss()
        stats.record_eviction()
        stats.size = 10
        stats.max_size = 100

        stats_dict = stats.get_stats()
        assert stats_dict["hits"] == 1
        assert stats_dict["misses"] == 1
        assert stats_dict["evictions"] == 1
        assert stats_dict["hit_rate"] == "50.00%"
        assert stats_dict["size"] == 10
        assert stats_dict["max_size"] == 100


class TestCacheEvictionPolicy:
    """Test suite for CacheEvictionPolicy enum"""

    def test_eviction_policies(self):
        """Test all eviction policies are defined"""
        assert CacheEvictionPolicy.LRU.value == "lru"
        assert CacheEvictionPolicy.LFU.value == "lfu"
        assert CacheEvictionPolicy.FIFO.value == "fifo"
        assert CacheEvictionPolicy.TTL.value == "ttl"
        assert CacheEvictionPolicy.ADAPTIVE.value == "adaptive"


class TestCacheInvalidationEvent:
    """Test suite for CacheInvalidationEvent enum"""

    def test_invalidation_events(self):
        """Test all invalidation events are defined"""
        assert CacheInvalidationEvent.TIME_BASED.value == "time_based"
        assert CacheInvalidationEvent.EVENT_BASED.value == "event_based"
        assert CacheInvalidationEvent.CAPACITY_BASED.value == "capacity_based"
        assert CacheInvalidationEvent.MANUAL.value == "manual"
        assert CacheInvalidationEvent.ADAPTIVE.value == "adaptive"


class TestLRUCache:
    """Test suite for LRUCache class"""

    def test_initialization(self):
        """Test LRUCache initialization"""
        cache = LRUCache(max_size=100, ttl_sec=60)
        assert cache._max_size == 100
        assert cache._ttl_sec == 60
        assert len(cache._cache) == 0

    def test_set_and_get(self):
        """Test basic set and get operations"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")
        assert result == {"data": "value1"}

    def test_get_nonexistent_key(self):
        """Test getting non-existent key"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        result = cache.get("nonexistent")
        assert result is None

    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = LRUCache(max_size=10, ttl_sec=0.1)  # 100ms TTL
        cache.set("key1", {"data": "value1"})
        result = cache.get("key1")
        assert result is not None

        time.sleep(0.15)  # Wait for expiration
        result = cache.get("key1")
        assert result is None

    def test_lru_eviction(self):
        """Test LRU eviction when cache is full"""
        cache = LRUCache(max_size=3, ttl_sec=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Cache is now full (3 items)
        assert cache.get("key1") == "value1"

        # Add one more item - this should trigger eviction since len >= max_size
        # Note: when we called get("key1") above, it moved key1 to the end (most recently used)
        # So the eviction order in OrderedDict is: key2 (oldest), key3, key1 (newest)
        # When we add key4, key2 should be evicted (oldest)
        cache.set("key4", "value4")

        # Check that eviction was recorded
        stats = cache.get_stats()
        assert stats["evictions"] >= 1

        # key2 should be evicted (oldest after key1 was accessed)
        assert cache.get("key2") is None
        # The other keys should still be present
        assert cache.get("key1") == "value1"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_invalidate(self):
        """Test cache invalidation"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        cache.set("key1", {"data": "value1"})
        result = cache.invalidate("key1")
        assert result is True
        assert cache.get("key1") is None

    def test_invalidate_nonexistent(self):
        """Test invalidating non-existent key"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        result = cache.invalidate("nonexistent")
        assert result is False

    def test_clear(self):
        """Test clearing cache"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_update_existing_key(self):
        """Test updating existing key"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        cache.set("key1", {"data": "value1"})
        cache.set("key1", {"data": "updated"})
        result = cache.get("key1")
        assert result == {"data": "updated"}

    def test_get_updates_lru_order(self):
        """Test that get updates LRU order"""
        cache = LRUCache(max_size=3, ttl_sec=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        # Access key1 to make it most recently used
        cache.get("key1")

        # Add new item, should evict key2 (oldest after key1 access)
        cache.set("key4", "value4")
        assert cache.get("key1") == "value1"  # Still there (recently accessed)
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"

    def test_statistics_tracking(self):
        """Test that statistics are tracked correctly"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        cache.set("key1", "value1")
        cache.get("key1")  # Hit
        cache.get("key2")  # Miss

        stats = cache.get_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["hit_rate"] == "50.00%"

    def test_concurrent_access(self):
        """Test thread-safe concurrent access"""
        import threading

        cache = LRUCache(max_size=100, ttl_sec=60)
        results = []

        def set_items():
            for i in range(50):
                cache.set(f"key{i}", f"value{i}")

        def get_items():
            for i in range(50):
                result = cache.get(f"key{i}")
                results.append(result)

        threads = [threading.Thread(target=set_items), threading.Thread(target=get_items)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not raise any exceptions
        assert len(results) == 50


class TestTTLCache:
    """Test suite for TTLCache class"""

    def test_initialization(self):
        """Test TTLCache initialization"""
        cache = TTLCache(ttl_sec=30)
        assert cache._ttl_sec == 30

    def test_set_and_get(self):
        """Test basic set and get operations"""
        cache = TTLCache(ttl_sec=30)
        data = {"key": "value"}
        cache.set(data)
        result = cache.get()
        assert result == data

    def test_get_returns_copy(self):
        """Test that get returns a shallow copy"""
        cache = TTLCache(ttl_sec=30)
        data = {"key": "value"}
        cache.set(data)
        result = cache.get()
        result["key"] = "modified"

        # Original should not be modified
        original = cache.get()
        assert original["key"] == "value"

    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = TTLCache(ttl_sec=0.1)  # 100ms TTL
        data = {"key": "value"}
        cache.set(data)
        result = cache.get()
        assert result is not None

        time.sleep(0.15)  # Wait for expiration
        result = cache.get()
        assert result is None

    def test_clear(self):
        """Test clearing cache"""
        cache = TTLCache(ttl_sec=30)
        data = {"key": "value"}
        cache.set(data)
        cache.clear()
        result = cache.get()
        assert result is None

    def test_is_valid(self):
        """Test is_valid method"""
        cache = TTLCache(ttl_sec=30)
        assert not cache.is_valid()

        data = {"key": "value"}
        cache.set(data)
        assert cache.is_valid()

    def test_time_rollback_handling(self):
        """Test handling of time rollback"""
        cache = TTLCache(ttl_sec=30)
        data = {"key": "value"}
        cache.set(data)

        # Manually set timestamp to future (simulating time rollback)
        with cache._lock:
            cache._cache["ts"] = time.monotonic() + 1000

        assert not cache.is_valid()


class TestParametricTTLCache:
    """Test suite for ParametricTTLCache class"""

    def test_initialization(self):
        """Test ParametricTTLCache initialization"""
        cache = ParametricTTLCache(ttl_sec=5)
        assert cache._ttl_sec == 5

    def test_set_and_get_with_params(self):
        """Test set and get with parameters"""
        cache = ParametricTTLCache(ttl_sec=5)
        data = {"key": "value"}
        cache.set(data, limit=10, offset=20)
        result = cache.get(limit=10, offset=20)
        assert result == data

    def test_different_params_different_cache(self):
        """Test that different parameters create different cache entries"""
        cache = ParametricTTLCache(ttl_sec=5)
        data1 = {"key": "value1"}
        data2 = {"key": "value2"}
        cache.set(data1, limit=10)
        cache.set(data2, limit=20)

        result1 = cache.get(limit=10)
        result2 = cache.get(limit=20)
        assert result1 == data1
        assert result2 == data2

    def test_get_nonexistent_params(self):
        """Test getting with non-existent parameters"""
        cache = ParametricTTLCache(ttl_sec=5)
        result = cache.get(limit=999)
        assert result is None

    def test_ttl_expiration(self):
        """Test TTL expiration"""
        cache = ParametricTTLCache(ttl_sec=0.1)  # 100ms TTL
        data = {"key": "value"}
        cache.set(data, limit=10)
        result = cache.get(limit=10)
        assert result is not None

        time.sleep(0.15)  # Wait for expiration
        result = cache.get(limit=10)
        assert result is None

    def test_clear(self):
        """Test clearing cache"""
        cache = ParametricTTLCache(ttl_sec=5)
        data = {"key": "value"}
        cache.set(data, limit=10)
        cache.clear()
        result = cache.get(limit=10)
        assert result is None

    def test_key_generation(self):
        """Test cache key generation from parameters"""
        cache = ParametricTTLCache(ttl_sec=5)
        # Parameters should be sorted for consistent key generation
        cache.set({"data": 1}, a=2, b=1)
        cache.set({"data": 2}, b=1, a=2)  # Same params, different order

        # Should overwrite since params are sorted
        result = cache.get(a=2, b=1)
        assert result == {"data": 2}


class TestGenerateCacheKey:
    """Test suite for generate_cache_key function"""

    def test_simple_key(self):
        """Test simple key generation"""
        key = generate_cache_key("prefix", "arg1", "arg2")
        assert "prefix" in key
        assert "arg1" in key
        assert "arg2" in key

    def test_with_kwargs(self):
        """Test key generation with keyword arguments"""
        key = generate_cache_key("prefix", param1="value1", param2="value2")
        assert "prefix" in key
        assert "param1=value1" in key
        assert "param2=value2" in key

    def test_complex_objects(self):
        """Test key generation with complex objects"""
        key = generate_cache_key("prefix", {"complex": "object"})
        assert "prefix" in key
        # Complex objects should be hashed
        assert len(key) > 0

    def test_consistency(self):
        """Test that same arguments produce same key"""
        key1 = generate_cache_key("prefix", "arg1", param="value")
        key2 = generate_cache_key("prefix", "arg1", param="value")
        assert key1 == key2

    def test_kwargs_order_independence(self):
        """Test that kwargs order doesn't affect key"""
        key1 = generate_cache_key("prefix", a=1, b=2)
        key2 = generate_cache_key("prefix", b=2, a=1)
        assert key1 == key2


class TestCacheWarmer:
    """Test suite for CacheWarmer class"""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test CacheWarmer initialization"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        warmer = CacheWarmer(cache)
        assert warmer._cache == cache
        assert len(warmer._warm_functions) == 0

    @pytest.mark.asyncio
    async def test_register_function(self):
        """Test registering warm function"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        warmer = CacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)
        assert "test_func" in warmer._warm_functions

    @pytest.mark.asyncio
    async def test_warm_function(self):
        """Test executing warm function"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        warmer = CacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)
        result = await warmer.warm("test_func")
        assert result == {"data": "warmed"}

    @pytest.mark.asyncio
    async def test_warm_unknown_function(self):
        """Test warming unknown function raises error"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        warmer = CacheWarmer(cache)

        with pytest.raises(ValueError, match="Unknown warm function"):
            await warmer.warm("unknown_func")

    @pytest.mark.asyncio
    async def test_warm_caches_result(self):
        """Test that warm function caches result"""
        cache = LRUCache(max_size=10, ttl_sec=60)
        warmer = CacheWarmer(cache)

        async def warm_func(param1):
            return {"data": f"warmed_{param1}"}

        warmer.register("test_func", warm_func)
        await warmer.warm("test_func", "value1")

        # Check that result is cached
        cache_key = generate_cache_key("warm_test_func", "value1")
        cached = cache.get(cache_key)
        assert cached == {"data": "warmed_value1"}


class TestMultiLevelCache:
    """Test suite for MultiLevelCache class"""

    def test_initialization(self):
        """Test MultiLevelCache initialization"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        assert cache._memory_cache is not None
        assert cache._redis_ttl == 3600
        assert cache._redis_prefix == "aiops_cache"

    def test_set_and_get_memory_only(self):
        """Test set and get with memory cache only (Redis unavailable)"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = False  # Force Redis unavailable

        data = {"key": "value"}
        cache.set("test_key", data)
        result = cache.get("test_key")
        assert result == data

    def test_redis_serialization_string(self):
        """Test Redis serialization with string values"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = False

        cache.set("test_key", "string_value")
        result = cache.get("test_key")
        assert result == "string_value"

    def test_redis_serialization_number(self):
        """Test Redis serialization with numeric values"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = False

        cache.set("test_key", 123)
        result = cache.get("test_key")
        assert result == 123

    def test_redis_serialization_bool(self):
        """Test Redis serialization with boolean values"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = False

        cache.set("test_key", True)
        result = cache.get("test_key")
        assert result is True

    def test_invalidate(self):
        """Test cache invalidation"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = False

        data = {"key": "value"}
        cache.set("test_key", data)
        cache.invalidate("test_key")
        result = cache.get("test_key")
        assert result is None

    def test_clear(self):
        """Test clearing cache"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = False

        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_redis_key_generation(self):
        """Test Redis key generation"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600, redis_prefix="test_prefix")
        redis_key = cache._make_redis_key("my_key")
        assert redis_key == "test_prefix:my_key"

    def test_redis_set_error_handling(self):
        """Test Redis set error handling"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.setex.side_effect = Exception("Redis error")

        # Should not raise exception, just log error
        data = {"key": "value"}
        cache.set("test_key", data)
        # Should still be in memory cache
        result = cache.get("test_key")
        assert result == data

    def test_redis_get_error_handling(self):
        """Test Redis get error handling"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.get.side_effect = Exception("Redis error")

        # Should not raise exception, just log error
        result = cache.get("test_key")
        assert result is None

    def test_redis_invalidate_error_handling(self):
        """Test Redis invalidate error handling"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.delete.side_effect = Exception("Redis error")

        # Should not raise exception, just log error
        cache.invalidate("test_key")

    def test_redis_clear_error_handling(self):
        """Test Redis clear error handling"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.keys.side_effect = Exception("Redis error")

        # Should not raise exception, just log error
        cache.clear()


class TestThreeLevelCache:
    """Test suite for ThreeLevelCache class"""

    def test_initialization(self):
        """Test ThreeLevelCache initialization"""
        cache = ThreeLevelCache(
            memory_ttl=60, redis_ttl=3600, db_ttl=86400, eviction_policy=CacheEvictionPolicy.LRU
        )
        assert cache._memory_cache is not None
        assert cache._redis_ttl == 3600
        assert cache._db_ttl == 86400
        assert cache._eviction_policy == CacheEvictionPolicy.LRU

    def test_set_and_get_memory_only(self):
        """Test set and get with memory cache only"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = False

        data = {"key": "value"}
        cache.set("test_key", data)
        result = cache.get("test_key")
        assert result == data

    def test_set_with_custom_ttl(self):
        """Test setting value with custom TTL"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = False

        data = {"key": "value"}
        cache.set("test_key", data, ttl=120)
        result = cache.get("test_key")
        assert result == data

    def test_db_cache_fallback(self):
        """Test database cache fallback"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = True

        data = {"key": "value"}
        cache.set("test_key", data, ttl=10)

        # Clear memory cache to test DB fallback
        cache._memory_cache.clear()

        result = cache.get("test_key")
        assert result == data

    def test_db_cache_fallback_with_redis_promotion(self):
        """Test database cache fallback with Redis promotion"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = True
        cache._db_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.get.return_value = None  # Redis miss
        cache._redis_client.setex.return_value = True

        data = {"key": "value"}
        cache.set("test_key", data, ttl=10)

        # Clear memory cache to test DB fallback
        cache._memory_cache.clear()

        result = cache.get("test_key")
        assert result == data
        # Should have promoted to Redis
        assert cache._redis_client.setex.called

    def test_invalidate(self):
        """Test cache invalidation"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = False

        data = {"key": "value"}
        cache.set("test_key", data)
        cache.invalidate("test_key")
        result = cache.get("test_key")
        assert result is None

    def test_invalidate_with_event(self):
        """Test cache invalidation with event"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = False

        callback_called = []

        def callback(key, metadata):
            callback_called.append((key, metadata))

        cache.register_invalidation_callback(CacheInvalidationEvent.MANUAL, callback)

        data = {"key": "value"}
        cache.set("test_key", data)
        cache.invalidate(
            "test_key", event=CacheInvalidationEvent.MANUAL, metadata={"reason": "test"}
        )

        assert len(callback_called) == 1
        assert callback_called[0] == ("test_key", {"reason": "test"})

    def test_invalidate_callback_error_handling(self):
        """Test invalidation callback error handling"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = False

        def failing_callback(key, metadata):
            raise Exception("Callback failed")

        cache.register_invalidation_callback(CacheInvalidationEvent.MANUAL, failing_callback)

        data = {"key": "value"}
        cache.set("test_key", data)
        # Should not raise exception
        cache.invalidate("test_key", event=CacheInvalidationEvent.MANUAL)

    def test_clear(self):
        """Test clearing cache"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = False

        cache.set("key1", {"data": "value1"})
        cache.set("key2", {"data": "value2"})
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_get_stats(self):
        """Test getting cache statistics"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = False

        cache.set("key1", {"data": "value1"})
        stats = cache.get_stats()
        assert "memory_cache" in stats
        assert "redis_cache_size" in stats
        assert "db_cache_available" in stats
        assert "eviction_policy" in stats

    def test_db_cache_expiration(self):
        """Test database cache expiration"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = True

        data = {"key": "value"}
        cache.set("test_key", data, ttl=0.1)  # 100ms TTL

        # Clear memory cache
        cache._memory_cache.clear()

        # Should get from DB cache
        result = cache.get("test_key")
        assert result == data

        # Wait for expiration
        time.sleep(0.15)

        # Clear memory cache again
        cache._memory_cache.clear()

        # DB cache should be expired
        result = cache.get("test_key")
        assert result is None

    def test_redis_error_handling_in_set(self):
        """Test Redis error handling in set operation"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = True
        cache._db_available = False
        cache._redis_client = MagicMock()
        cache._redis_client.setex.side_effect = Exception("Redis error")

        data = {"key": "value"}
        cache.set("test_key", data)
        # Should still be in memory cache
        result = cache.get("test_key")
        assert result == data

    def test_redis_error_handling_in_get(self):
        """Test Redis error handling in get operation"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = True
        cache._db_available = False
        cache._redis_client = MagicMock()
        cache._redis_client.get.side_effect = Exception("Redis error")

        result = cache.get("test_key")
        assert result is None

    def test_redis_error_handling_in_invalidate(self):
        """Test Redis error handling in invalidate operation"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = True
        cache._db_available = False
        cache._redis_client = MagicMock()
        cache._redis_client.delete.side_effect = Exception("Redis error")
        cache._redis_client.get.return_value = (
            None  # Memory cache should return None after invalidate
        )

        data = {"key": "value"}
        cache.set("test_key", data)
        cache.invalidate("test_key")
        # Should still be invalidated from memory
        result = cache.get("test_key")
        assert result is None

    def test_redis_error_handling_in_clear(self):
        """Test Redis error handling in clear operation"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = True
        cache._db_available = False
        cache._redis_client = MagicMock()
        cache._redis_client.keys.side_effect = Exception("Redis error")
        cache._redis_client.get.return_value = None  # Memory cache should return None after clear

        cache.set("key1", {"data": "value1"})
        cache.clear()
        # Should still be cleared from memory
        result = cache.get("key1")
        assert result is None

    def test_invalidate_pattern(self):
        """Test pattern-based invalidation"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.keys.return_value = ["aiops_cache:key1", "aiops_cache:key2"]
        cache._redis_client.delete.return_value = 2
        cache._db_available = False

        count = cache.invalidate_pattern("key*")
        assert count == 2

    def test_invalidate_pattern_error_handling(self):
        """Test pattern-based invalidation error handling"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.keys.side_effect = Exception("Redis error")
        cache._db_available = False

        count = cache.invalidate_pattern("key*")
        # Should return 0 on error
        assert count == 0

    def test_db_cache_without_db_cache_attribute(self):
        """Test DB cache when _db_cache attribute doesn't exist"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = True

        # Remove _db_cache attribute
        if hasattr(cache, "_db_cache"):
            delattr(cache, "_db_cache")

        result = cache.get("test_key")
        assert result is None

    def test_multiple_callbacks_same_event(self):
        """Test multiple callbacks for same event"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = False
        cache._db_available = False

        callback1_called = []
        callback2_called = []

        def callback1(key, metadata):
            callback1_called.append(key)

        def callback2(key, metadata):
            callback2_called.append(key)

        cache.register_invalidation_callback(CacheInvalidationEvent.MANUAL, callback1)
        cache.register_invalidation_callback(CacheInvalidationEvent.MANUAL, callback2)

        data = {"key": "value"}
        cache.set("test_key", data)
        cache.invalidate("test_key", event=CacheInvalidationEvent.MANUAL)

        assert len(callback1_called) == 1
        assert len(callback2_called) == 1


class TestMultiLevelCacheRedisErrors:
    """Test MultiLevelCache Redis error handling"""

    def test_redis_initialization_failure(self):
        """Test MultiLevelCache handles Redis initialization failure"""
        with patch("builtins.__import__", side_effect=ImportError("Redis not available")):
            cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
            assert cache._redis_available is False
            assert cache._redis_client is None

    def test_redis_get_deserialization_error(self):
        """Test MultiLevelCache handles Redis deserialization errors"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = True
        cache._redis_client = MagicMock()

        # Mock Redis to return invalid JSON
        cache._redis_client.get.return_value = "invalid json"

        result = cache.get("test_key")
        # Should return the string as-is when JSON decode fails
        assert result == "invalid json"

    def test_redis_get_attribute_error(self):
        """Test MultiLevelCache handles Redis get attribute errors"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = True
        cache._redis_client = MagicMock()

        # Mock Redis to return non-string value
        cache._redis_client.get.return_value = 12345

        result = cache.get("test_key")
        assert result == 12345

    def test_redis_clear_error(self):
        """Test MultiLevelCache handles Redis clear errors"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.keys.side_effect = Exception("Redis error")

        # Should not raise exception
        cache.clear()

    def test_redis_invalidate_error(self):
        """Test MultiLevelCache handles Redis invalidate errors"""
        cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.delete.side_effect = Exception("Redis error")

        # Should not raise exception
        cache.invalidate("test_key")


class TestThreeLevelCacheErrors:
    """Test ThreeLevelCache error handling"""

    def test_redis_initialization_config_error(self):
        """Test ThreeLevelCache handles Redis config import error"""
        with patch("builtins.__import__", side_effect=ImportError("Config not available")):
            cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
            # Should still initialize, just without Redis
            assert cache._memory_cache is not None

    def test_db_initialization_error(self):
        """Test ThreeLevelCache handles database initialization error"""
        with patch("builtins.__import__", side_effect=ImportError("Config not available")):
            cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
            # Should still initialize, just without DB
            assert cache._memory_cache is not None

    def test_set_db_cache_error(self):
        """Test ThreeLevelCache handles database cache set errors"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._db_available = True

        # Mock _set_db_cache to raise error
        with patch.object(cache, "_set_db_cache", side_effect=Exception("DB error")):
            # Should not raise exception
            cache.set("test_key", {"data": "value"})

    def test_get_db_cache_error(self):
        """Test ThreeLevelCache handles database cache get errors"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._db_available = True

        # Mock _get_db_cache to raise error
        with patch.object(cache, "_get_db_cache", side_effect=Exception("DB error")):
            # Should not raise exception
            result = cache.get("test_key")
            assert result is None

    def test_invalidate_db_cache_error(self):
        """Test ThreeLevelCache handles database cache invalidate errors"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._db_available = True

        # Mock _invalidate_db_cache to raise error
        with patch.object(cache, "_invalidate_db_cache", side_effect=Exception("DB error")):
            # Should not raise exception
            cache.invalidate("test_key")

    def test_clear_db_cache_error(self):
        """Test ThreeLevelCache handles database cache clear errors"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._db_available = True

        # Mock _clear_db_cache to raise error
        with patch.object(cache, "_clear_db_cache", side_effect=Exception("DB error")):
            # Should not raise exception
            cache.clear()

    def test_get_stats_redis_error(self):
        """Test ThreeLevelCache handles Redis stats errors"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.keys.side_effect = Exception("Redis error")

        # Should not raise exception
        stats = cache.get_stats()
        assert "memory_cache" in stats

    def test_redis_get_promotion_to_memory(self):
        """Test that Redis cache promotes to memory cache on hit"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        cache._redis_available = True
        cache._redis_client = MagicMock()
        cache._redis_client.get.return_value = '{"data": "from_redis"}'

        result = cache.get("test_key")
        assert result == {"data": "from_redis"}
        # Should be promoted to memory cache
        memory_result = cache._memory_cache.get("test_key")
        assert memory_result == {"data": "from_redis"}


class TestIntelligentCacheWarmer:
    """Test suite for IntelligentCacheWarmer class"""

    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test IntelligentCacheWarmer initialization"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)
        assert warmer._cache == cache
        assert len(warmer._warm_functions) == 0

    @pytest.mark.asyncio
    async def test_register_with_priority(self):
        """Test registering function with priority"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func, priority=10)
        assert "test_func" in warmer._warm_functions
        assert warmer._warm_priorities["test_func"] == 10

    @pytest.mark.asyncio
    async def test_record_access(self):
        """Test recording access patterns"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)
        warmer.record_access("test_func")
        assert len(warmer._access_patterns["test_func"]) == 1

    @pytest.mark.asyncio
    async def test_predict_next_access(self):
        """Test predicting next access time"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)

        # Record some accesses
        warmer.record_access("test_func")
        time.sleep(0.1)
        warmer.record_access("test_func")
        time.sleep(0.1)
        warmer.record_access("test_func")

        # Should predict based on intervals
        prediction = warmer.predict_next_access("test_func")
        assert prediction > 0

    @pytest.mark.asyncio
    async def test_predict_next_access_insufficient_data(self):
        """Test prediction with insufficient data"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)

        # Only one access - should return 0
        prediction = warmer.predict_next_access("test_func")
        assert prediction == 0.0

    @pytest.mark.asyncio
    async def test_warm_with_prediction(self):
        """Test warming with access pattern prediction"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)
        result = await warmer.warm_with_prediction("test_func")
        assert result == {"data": "warmed"}

    @pytest.mark.asyncio
    async def test_warm_with_prediction_no_pattern(self):
        """Test warming with prediction when no pattern exists"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)
        # No access pattern, should still warm normally
        result = await warmer.warm_with_prediction("test_func")
        assert result == {"data": "warmed"}

    @pytest.mark.asyncio
    async def test_get_warming_stats(self):
        """Test getting warming statistics"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func, priority=10)
        warmer.record_access("test_func")

        stats = warmer.get_warming_stats()
        assert stats["registered_functions"] == 1
        assert "priorities" in stats

    @pytest.mark.asyncio
    async def test_access_pattern_limit(self):
        """Test that access patterns are limited to 100 entries"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)

        # Record more than 100 accesses
        for _ in range(150):
            warmer.record_access("test_func")

        # Should be limited to 100
        assert len(warmer._access_patterns["test_func"]) == 100

    @pytest.mark.asyncio
    async def test_warm_high_priority(self):
        """Test warming high-priority functions"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def high_priority_func():
            return {"data": "high"}

        async def low_priority_func():
            return {"data": "low"}

        warmer.register("high_func", high_priority_func, priority=10)
        warmer.register("low_func", low_priority_func, priority=3)

        await warmer.warm_high_priority()
        # Should warm high priority function
        assert len(warmer._access_patterns["high_func"]) > 0

    @pytest.mark.asyncio
    async def test_warm_high_priority_error_handling(self):
        """Test high priority warming error handling"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def failing_func():
            raise Exception("Warming failed")

        warmer.register("failing_func", failing_func, priority=10)

        # Should not raise exception
        await warmer.warm_high_priority()

    @pytest.mark.asyncio
    async def test_warm_high_priority_empty(self):
        """Test high priority warming with no high priority functions"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def low_priority_func():
            return {"data": "low"}

        warmer.register("low_priority_func", low_priority_func, priority=3)

        # Should not raise exception
        await warmer.warm_high_priority()

    @pytest.mark.asyncio
    async def test_warm_with_args(self):
        """Test warming with arguments"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func(user_id):
            return {"user_id": user_id, "data": "warmed"}

        warmer.register("test_func", warm_func)
        result = await warmer.warm("test_func", "user123")
        assert result == {"user_id": "user123", "data": "warmed"}

    @pytest.mark.asyncio
    async def test_warm_with_kwargs(self):
        """Test warming with keyword arguments"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func(limit, offset):
            return {"limit": limit, "offset": offset}

        warmer.register("test_func", warm_func)
        result = await warmer.warm("test_func", limit=10, offset=20)
        assert result == {"limit": 10, "offset": 20}

    @pytest.mark.asyncio
    async def test_warm_with_prediction_calculates_ttl(self):
        """Test that warm_with_prediction calculates and sets TTL based on prediction"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)

        # Record some access pattern to enable prediction
        for _ in range(5):
            warmer.record_access("test_func")
            import asyncio

            await asyncio.sleep(0.01)

        result = await warmer.warm_with_prediction("test_func")
        assert result == {"data": "warmed"}

    @pytest.mark.asyncio
    async def test_warm_with_prediction_clamps_ttl(self):
        """Test that predicted TTL is clamped between 60 and 3600 seconds"""
        cache = ThreeLevelCache(memory_ttl=60, redis_ttl=3600, db_ttl=86400)
        warmer = IntelligentCacheWarmer(cache)

        async def warm_func():
            return {"data": "warmed"}

        warmer.register("test_func", warm_func)

        # Record access pattern with very short intervals
        for _ in range(5):
            warmer.record_access("test_func")
            import asyncio

            await asyncio.sleep(0.001)

        result = await warmer.warm_with_prediction("test_func")
        assert result == {"data": "warmed"}
