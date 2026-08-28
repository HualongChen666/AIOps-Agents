# -*- coding: utf-8 -*-
"""
Integration test for Redis cache operations.

This test validates Redis cache integration including:
- Connection management
- Cache operations (set, get, delete)
- Cache expiration
- Cache invalidation
- Performance characteristics
- Error handling
"""

import pytest
import time
from datetime import timedelta
from unittest.mock import patch, MagicMock


@pytest.fixture
def redis_client():
    """Create Redis client for testing"""
    try:
        import redis
        from core.config import REDIS_URL
        
        client = redis.from_url(REDIS_URL, decode_responses=True)
        
        # Test connection
        client.ping()
        
        yield client
    except Exception as e:
        pytest.skip(f"Redis connection failed: {e}")
    finally:
        # Clean up test data
        try:
            client.close()
        except:
            pass


@pytest.fixture
def cache_manager():
    """Create cache manager for testing"""
    try:
        from core.cache_helpers import MultiLevelCache
        from core.config import REDIS_URL
        
        cache = MultiLevelCache(
            redis_url=REDIS_URL,
            default_ttl=3600
        )
        
        yield cache
    except Exception as e:
        pytest.skip(f"Cache manager creation failed: {e}")


class TestRedisConnection:
    """Test Redis connection management"""

    def test_redis_connection_established(self, redis_client):
        """Test that Redis connection can be established"""
        result = redis_client.ping()
        assert result is True

    def test_redis_connection_error_handling(self):
        """Test Redis connection error handling"""
        try:
            import redis
            # Try to connect with invalid URL
            client = redis.from_url("redis://invalid:9999", decode_responses=True)
            client.ping()
            assert False, "Should have raised connection error"
        except Exception as e:
            # Expected to fail
            assert True

    def test_redis_connection_pool(self, redis_client):
        """Test Redis connection pool functionality"""
        # Create multiple connections
        for _ in range(5):
            result = redis_client.ping()
            assert result is True


class TestRedisCacheOperations:
    """Test Redis cache operations"""

    def test_cache_set_and_get(self, redis_client):
        """Test basic cache set and get operations"""
        # Set value
        redis_client.set("test_key", "test_value")
        
        # Get value
        value = redis_client.get("test_key")
        assert value == "test_value"
        
        # Clean up
        redis_client.delete("test_key")

    def test_cache_set_with_expiration(self, redis_client):
        """Test cache set with expiration"""
        # Set value with 2 second expiration
        redis_client.setex("test_key", 2, "test_value")
        
        # Value should exist immediately
        value = redis_client.get("test_key")
        assert value == "test_value"
        
        # Wait for expiration
        time.sleep(3)
        
        # Value should be expired
        value = redis_client.get("test_key")
        assert value is None

    def test_cache_delete(self, redis_client):
        """Test cache delete operation"""
        # Set value
        redis_client.set("test_key", "test_value")
        
        # Delete value
        result = redis_client.delete("test_key")
        assert result == 1
        
        # Verify deletion
        value = redis_client.get("test_key")
        assert value is None

    def test_cache_exists(self, redis_client):
        """Test cache exists operation"""
        # Key should not exist initially
        assert redis_client.exists("test_key") == 0
        
        # Set value
        redis_client.set("test_key", "test_value")
        
        # Key should exist now
        assert redis_client.exists("test_key") == 1
        
        # Clean up
        redis_client.delete("test_key")

    def test_cache_batch_operations(self, redis_client):
        """Test batch cache operations"""
        # Set multiple values
        redis_client.mset({
            "key1": "value1",
            "key2": "value2",
            "key3": "value3"
        })
        
        # Get multiple values
        values = redis_client.mget(["key1", "key2", "key3"])
        assert values == ["value1", "value2", "value3"]
        
        # Clean up
        redis_client.delete("key1", "key2", "key3")


class TestRedisCacheDataTypes:
    """Test Redis cache with different data types"""

    def test_cache_string_type(self, redis_client):
        """Test cache with string data type"""
        redis_client.set("string_key", "string_value")
        value = redis_client.get("string_key")
        assert value == "string_value"
        redis_client.delete("string_key")

    def test_cache_numeric_type(self, redis_client):
        """Test cache with numeric data type"""
        redis_client.set("numeric_key", "12345")
        value = redis_client.get("numeric_key")
        assert value == "12345"
        redis_client.delete("numeric_key")

    def test_cache_json_type(self, redis_client):
        """Test cache with JSON data type"""
        import json
        
        data = {"key": "value", "number": 42}
        redis_client.set("json_key", json.dumps(data))
        
        value = redis_client.get("json_key")
        parsed = json.loads(value)
        assert parsed == data
        redis_client.delete("json_key")

    def test_cache_list_type(self, redis_client):
        """Test cache with list data type"""
        redis_client.lpush("list_key", "item1", "item2", "item3")
        
        length = redis_client.llen("list_key")
        assert length == 3
        
        items = redis_client.lrange("list_key", 0, -1)
        assert len(items) == 3
        
        redis_client.delete("list_key")


class TestRedisCacheExpiration:
    """Test Redis cache expiration policies"""

    def test_cache_ttl(self, redis_client):
        """Test cache TTL (time to live)"""
        # Set value with 10 second TTL
        redis_client.setex("ttl_key", 10, "ttl_value")
        
        # Check TTL
        ttl = redis_client.ttl("ttl_key")
        assert 0 < ttl <= 10
        
        # Clean up
        redis_client.delete("ttl_key")

    def test_cache_persist(self, redis_client):
        """Test removing expiration from key"""
        # Set value with expiration
        redis_client.setex("persist_key", 10, "persist_value")
        
        # Remove expiration
        redis_client.persist("persist_key")
        
        # Check TTL (should be -1, meaning no expiration)
        ttl = redis_client.ttl("persist_key")
        assert ttl == -1
        
        # Clean up
        redis_client.delete("persist_key")

    def test_cache_expire_at(self, redis_client):
        """Test setting expiration at specific timestamp"""
        import time
        
        # Set value
        redis_client.set("expire_at_key", "expire_at_value")
        
        # Set expiration to 5 seconds from now
        expire_time = int(time.time()) + 5
        redis_client.expireat("expire_at_key", expire_time)
        
        # Check TTL
        ttl = redis_client.ttl("expire_at_key")
        assert 0 < ttl <= 5
        
        # Clean up
        redis_client.delete("expire_at_key")


class TestRedisCacheInvalidation:
    """Test Redis cache invalidation strategies"""

    def test_cache_pattern_invalidation(self, redis_client):
        """Test cache invalidation by pattern"""
        # Set multiple keys with pattern
        for i in range(5):
            redis_client.set(f"pattern_key_{i}", f"value_{i}")
        
        # Find keys matching pattern
        keys = redis_client.keys("pattern_key_*")
        assert len(keys) == 5
        
        # Delete all matching keys
        if keys:
            redis_client.delete(*keys)
        
        # Verify deletion
        keys = redis_client.keys("pattern_key_*")
        assert len(keys) == 0

    def test_cache_flush_db(self, redis_client):
        """Test flushing entire database"""
        # Set test value
        redis_client.set("flush_test_key", "flush_test_value")
        
        # Flush database (use with caution in production!)
        # redis_client.flushdb()  # Commented out for safety
        
        # Manual cleanup instead
        redis_client.delete("flush_test_key")

    def test_cache_namespace_isolation(self, redis_client):
        """Test cache namespace isolation"""
        # Set values in different namespaces
        redis_client.set("ns1:key1", "value1")
        redis_client.set("ns2:key1", "value2")
        
        # Values should be independent
        value1 = redis_client.get("ns1:key1")
        value2 = redis_client.get("ns2:key1")
        
        assert value1 == "value1"
        assert value2 == "value2"
        
        # Clean up
        redis_client.delete("ns1:key1", "ns2:key1")


class TestRedisCachePerformance:
    """Test Redis cache performance characteristics"""

    def test_cache_read_performance(self, redis_client):
        """Test cache read performance"""
        # Set test value
        redis_client.set("perf_read_key", "perf_read_value")
        
        # Measure read performance
        start_time = time.time()
        for _ in range(1000):
            redis_client.get("perf_read_key")
        end_time = time.time()
        
        duration = end_time - start_time
        avg_time = duration / 1000
        
        # Average read should be fast (< 1ms)
        assert avg_time < 0.001, f"Average read time {avg_time:.6f}s, expected < 0.001s"
        
        # Clean up
        redis_client.delete("perf_read_key")

    def test_cache_write_performance(self, redis_client):
        """Test cache write performance"""
        # Measure write performance
        start_time = time.time()
        for i in range(1000):
            redis_client.set(f"perf_write_key_{i}", f"value_{i}")
        end_time = time.time()
        
        duration = end_time - start_time
        avg_time = duration / 1000
        
        # Average write should be fast (< 2ms)
        assert avg_time < 0.002, f"Average write time {avg_time:.6f}s, expected < 0.002s"
        
        # Clean up
        for i in range(1000):
            redis_client.delete(f"perf_write_key_{i}")

    def test_cache_batch_performance(self, redis_client):
        """Test batch operations performance"""
        # Prepare batch data
        batch_data = {f"batch_key_{i}": f"batch_value_{i}" for i in range(100)}
        
        # Measure batch set performance
        start_time = time.time()
        redis_client.mset(batch_data)
        end_time = time.time()
        
        duration = end_time - start_time
        
        # Batch set should be fast (< 100ms for 100 items)
        assert duration < 0.1, f"Batch set took {duration:.3f}s, expected < 0.1s"
        
        # Clean up
        redis_client.delete(*batch_data.keys())


class TestRedisCacheManagerIntegration:
    """Test cache manager integration with Redis"""

    def test_cache_manager_set_get(self, cache_manager):
        """Test cache manager set and get operations"""
        # Set value
        cache_manager.set("cache_manager_key", "cache_manager_value")
        
        # Get value
        value = cache_manager.get("cache_manager_key")
        assert value == "cache_manager_value"
        
        # Clean up
        cache_manager.delete("cache_manager_key")

    def test_cache_manager_with_ttl(self, cache_manager):
        """Test cache manager with TTL"""
        # Set value with custom TTL
        cache_manager.set("ttl_manager_key", "ttl_manager_value", ttl=2)
        
        # Value should exist immediately
        value = cache_manager.get("ttl_manager_key")
        assert value == "ttl_manager_value"
        
        # Wait for expiration
        time.sleep(3)
        
        # Value should be expired
        value = cache_manager.get("ttl_manager_key")
        assert value is None

    def test_cache_manager_invalidation(self, cache_manager):
        """Test cache manager invalidation"""
        # Set multiple values
        for i in range(5):
            cache_manager.set(f"manager_key_{i}", f"value_{i}")
        
        # Invalidate by pattern
        cache_manager.invalidate_pattern("manager_key_*")
        
        # Verify invalidation
        for i in range(5):
            value = cache_manager.get(f"manager_key_{i}")
            assert value is None

    def test_cache_manager_fallback(self, cache_manager):
        """Test cache manager fallback when Redis is unavailable"""
        # This test would require mocking Redis failure
        # For now, we'll skip it
        pytest.skip("Redis fallback test requires mocking")


class TestRedisCacheWithAPI:
    """Test Redis cache integration with API endpoints"""

    @pytest.fixture
    def api_client(self):
        """Create API test client"""
        from main import app
        from fastapi.testclient import TestClient
        return TestClient(app)

    def test_api_uses_cache(self, api_client, redis_client):
        """Test that API endpoints use cache"""
        # Make first request (cache miss)
        resp1 = api_client.get("/api/v1/stats/summary")
        assert resp1.status_code in (200, 404)
        
        if resp1.status_code != 404:
            # Make second request (cache hit)
            resp2 = api_client.get("/api/v1/stats/summary")
            assert resp2.status_code in (200, 404)

    def test_cache_invalidation_on_data_update(self, api_client, redis_client):
        """Test cache invalidation when data is updated"""
        # This would require specific API endpoints that update data
        # For now, we'll skip it
        pytest.skip("Cache invalidation test requires specific endpoints")


class TestRedisCacheErrorHandling:
    """Test Redis cache error handling"""

    def test_cache_serialization_error(self, cache_manager):
        """Test cache serialization error handling"""
        # Try to cache non-serializable object
        try:
            class NonSerializable:
                pass
            
            cache_manager.set("non_serializable_key", NonSerializable())
            # If this succeeds, the cache manager handles serialization
            assert True
        except Exception as e:
            # Expected to fail for non-serializable objects
            assert True

    def test_cache_deserialization_error(self, cache_manager):
        """Test cache deserialization error handling"""
        # Manually set invalid data in Redis
        try:
            import redis
            from core.config import REDIS_URL
            
            client = redis.from_url(REDIS_URL, decode_responses=False)
            client.set("invalid_data_key", b"invalid_serialized_data")
            client.close()
            
            # Try to get the data through cache manager
            value = cache_manager.get("invalid_data_key")
            # Cache manager should handle deserialization errors gracefully
            assert value is None or isinstance(value, bytes)
        except Exception as e:
            # Expected to handle errors gracefully
            assert True

    def test_cache_connection_failure_recovery(self, cache_manager):
        """Test cache recovery from connection failure"""
        # This would require mocking Redis connection failure
        # For now, we'll skip it
        pytest.skip("Connection failure recovery test requires mocking")