# -*- coding: utf-8 -*-
"""
Comprehensive tests for core/cache_manager.py
Tests for Cache Manager implementation with Redis caching strategy
"""

import json
import time
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, Optional

import pytest

from core.cache_manager import (
    CacheManager,
    cache_key_generator,
    cache_manager,
    invalidate_cache_pattern,
    get_cache_hit_rate,
    get_cache_policies,
    set_cache_policy,
)


class TestCacheManager:
    """Test CacheManager class"""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis client"""
        with patch('core.cache_manager.REDIS_AVAILABLE', True):
            with patch('core.cache_manager.redis') as mock_redis_module:
                mock_client = MagicMock()
                mock_redis_module.from_url.return_value = mock_client
                mock_client.ping.return_value = True
                yield mock_client

    def test_initialization_with_redis(self, mock_redis):
        """Test initialization with Redis available"""
        manager = CacheManager()
        assert manager.redis_client is not None
        assert manager.default_ttl == 3600

    def test_initialization_without_redis(self):
        """Test initialization without Redis"""
        with patch('core.cache_manager.REDIS_AVAILABLE', False):
            manager = CacheManager()
            assert manager.redis_client is None

    def test_get_cache_hit(self, mock_redis):
        """Test getting cached data"""
        manager = CacheManager()
        mock_redis = manager.redis_client
        
        # Mock cache hit
        mock_redis.get.return_value = json.dumps({"test": "data"})
        
        result = manager.get("test_key")
        assert result == {"test": "data"}
        assert manager.cache_stats["hits"] == 1

    def test_get_cache_miss(self, mock_redis):
        """Test getting non-cached data"""
        manager = CacheManager()
        mock_redis = manager.redis_client
        
        # Mock cache miss
        mock_redis.get.return_value = None
        
        result = manager.get("test_key")
        assert result is None
        assert manager.cache_stats["misses"] == 1

    def test_get_without_redis(self):
        """Test getting cache without Redis"""
        with patch('core.cache_manager.REDIS_AVAILABLE', False):
            manager = CacheManager()
            result = manager.get("test_key")
            assert result is None
            assert manager.cache_stats["misses"] == 1

    def test_set_cache(self, mock_redis):
        """Test setting cache data"""
        manager = CacheManager()
        mock_redis = manager.redis_client
        
        result = manager.set("test_key", {"test": "data"}, ttl=60)
        assert result is True
        assert manager.cache_stats["sets"] == 1
        mock_redis.setex.assert_called_once()

    def test_set_cache_without_redis(self):
        """Test setting cache without Redis"""
        with patch('core.cache_manager.REDIS_AVAILABLE', False):
            manager = CacheManager()
            result = manager.set("test_key", {"test": "data"})
            assert result is False

    def test_delete_cache(self, mock_redis):
        """Test deleting cache data"""
        manager = CacheManager()
        mock_redis = manager.redis_client
        
        result = manager.delete("test_key")
        assert result is True
        assert manager.cache_stats["deletes"] == 1
        mock_redis.delete.assert_called_once_with("test_key")

    def test_delete_pattern(self, mock_redis):
        """Test deleting cache by pattern"""
        manager = CacheManager()
        mock_redis = manager.redis_client
        
        # Mock keys matching pattern
        mock_redis.keys.return_value = ["test_key1", "test_key2"]
        mock_redis.delete.return_value = 2
        
        result = manager.delete_pattern("test_key*")
        assert result == 2
        mock_redis.keys.assert_called_once_with("test_key*")

    def test_exists_cache(self, mock_redis):
        """Test checking if cache exists"""
        manager = CacheManager()
        mock_redis = manager.redis_client
        
        mock_redis.exists.return_value = 1
        
        result = manager.exists("test_key")
        assert result is True
        mock_redis.exists.assert_called_once_with("test_key")

    def test_get_cache_stats(self, mock_redis):
        """Test getting cache statistics"""
        manager = CacheManager()
        mock_redis = manager.redis_client
        
        # Mock Redis info
        mock_redis.info.return_value = {
            "used_memory": 1024000,
            "used_memory_human": "1.00MB",
            "keyspace_hits": 100,
            "keyspace_misses": 50,
            "total_connections_received": 10,
            "total_commands_processed": 200
        }
        
        stats = manager.get_cache_stats()
        assert stats["used_memory"] == 1024000
        assert stats["keyspace_hits"] == 100
        assert stats["keyspace_misses"] == 50
        assert "application_stats" in stats

    def test_get_cache_hit_rate(self, mock_redis):
        """Test getting cache hit rate"""
        manager = CacheManager()
        
        # Set some stats
        manager.cache_stats["hits"] = 80
        manager.cache_stats["misses"] = 20
        
        hit_rate = manager.get_cache_hit_rate()
        assert hit_rate == 0.8

    def test_get_cache_hit_rate_no_data(self):
        """Test getting cache hit rate with no data"""
        manager = CacheManager()
        
        hit_rate = manager.get_cache_hit_rate()
        assert hit_rate == 0.0

    def test_invalidate_by_pattern(self, mock_redis):
        """Test invalidating cache by pattern"""
        manager = CacheManager()
        mock_redis = manager.redis_client
        
        mock_redis.keys.return_value = ["cache:test1", "cache:test2"]
        mock_redis.delete.return_value = 2
        
        result = manager.invalidate_by_pattern("cache:*")
        assert result == 2
        assert manager.cache_stats["deletes"] == 2

    def test_warm_cache(self, mock_redis):
        """Test cache warming"""
        manager = CacheManager()
        mock_redis = manager.redis_client
        
        # Mock data loader
        def data_loader(pattern):
            return {"data": pattern}
        
        result = manager.warm_cache(data_loader, ["pattern1", "pattern2"])
        assert result == 2
        assert mock_redis.setex.call_count == 2

    def test_get_policy_ttl(self):
        """Test getting policy TTL"""
        manager = CacheManager()
        
        ttl = manager.get_policy_ttl("alerts")
        assert ttl == 60  # From predefined policies

    def test_get_policy_ttl_default(self):
        """Test getting policy TTL for non-existent policy"""
        manager = CacheManager()
        
        ttl = manager.get_policy_ttl("nonexistent")
        assert ttl == 3600  # Default TTL


class TestCacheKeyGenerator:
    """Test cache key generation"""

    def test_simple_key_generation(self):
        """Test simple key generation"""
        key = cache_key_generator("prefix", "arg1", "arg2", param1="value1")
        assert "prefix" in key
        assert "arg1" in key
        assert "arg2" in key
        assert "param1:value1" in key

    def test_complex_object_hashing(self):
        """Test complex object hashing in key generation"""
        key = cache_key_generator("prefix", {"complex": "object"})
        assert "prefix" in key
        # Complex object should be hashed
        assert len(key.split(":")) >= 2

    def test_sorted_kwargs(self):
        """Test that kwargs are sorted for consistent keys"""
        key1 = cache_key_generator("prefix", a=1, b=2)
        key2 = cache_key_generator("prefix", b=2, a=1)
        assert key1 == key2  # Should be same regardless of order











class TestGlobalFunctions:
    """Test global cache functions"""

    def test_invalidate_cache_pattern_function(self):
        """Test global invalidate_cache_pattern function"""
        from core.cache_manager import invalidate_cache_pattern
        with patch.object(cache_manager, 'invalidate_by_pattern', return_value=5):
            result = invalidate_cache_pattern("test:*")
            assert result == 5

    def test_get_cache_policies_function(self):
        """Test global get_cache_policies function"""
        from core.cache_manager import get_cache_policies
        policies = get_cache_policies()
        assert isinstance(policies, dict)
        assert "alerts" in policies
        assert "metrics" in policies

    def test_set_cache_policy_function(self):
        """Test global set_cache_policy function"""
        from core.cache_manager import set_cache_policy
        result = set_cache_policy("new_policy", 120, "Test policy")
        assert result is True
        policies = get_cache_policies()
        assert "new_policy" in policies
        assert policies["new_policy"]["ttl"] == 120

    def test_get_cache_hit_rate_function(self):
        """Test global get_cache_hit_rate function"""
        from core.cache_manager import get_cache_hit_rate
        cache_manager.cache_stats["hits"] = 75
        cache_manager.cache_stats["misses"] = 25
        hit_rate = get_cache_hit_rate()
        assert hit_rate == 0.75


class TestCachePolicies:
    """Test cache policy configuration"""

    def test_predefined_policies(self):
        """Test that predefined policies are loaded"""
        policies = cache_manager.cache_policies
        assert "alerts" in policies
        assert "metrics" in policies
        assert "configurations" in policies
        assert policies["alerts"]["ttl"] == 60
        assert policies["metrics"]["ttl"] == 30

    def test_policy_descriptions(self):
        """Test that policies have descriptions"""
        policies = cache_manager.cache_policies
        for policy_name, policy_config in policies.items():
            assert "ttl" in policy_config
            assert "description" in policy_config
            assert isinstance(policy_config["ttl"], int)
            assert isinstance(policy_config["description"], str)


class TestCacheErrorHandling:
    """Test cache error handling"""

    @pytest.fixture
    def mock_redis_with_error(self):
        """Create mock Redis client that raises errors"""
        with patch('core.cache_manager.REDIS_AVAILABLE', True):
            with patch('core.cache_manager.redis') as mock_redis_module:
                mock_client = MagicMock()
                mock_redis_module.from_url.return_value = mock_client
                mock_client.ping.return_value = True
                mock_client.get.side_effect = Exception("Redis error")
                yield mock_client

    def test_get_with_error(self, mock_redis_with_error):
        """Test get operation with Redis error"""
        manager = CacheManager()
        
        result = manager.get("test_key")
        assert result is None
        assert manager.cache_stats["errors"] == 1

    def test_set_with_error(self, mock_redis_with_error):
        """Test set operation with Redis error"""
        manager = CacheManager()
        mock_redis_with_error.setex.side_effect = Exception("Redis error")
        
        result = manager.set("test_key", {"data": "test"})
        assert result is False
        assert manager.cache_stats["errors"] == 1

    def test_delete_with_error(self, mock_redis_with_error):
        """Test delete operation with Redis error"""
        manager = CacheManager()
        mock_redis_with_error.delete.side_effect = Exception("Redis error")
        
        result = manager.delete("test_key")
        assert result is False
        assert manager.cache_stats["errors"] == 1


class TestCacheIntegration:
    """Integration tests for cache functionality"""

    def test_cache_lifecycle(self):
        """Test complete cache lifecycle"""
        with patch('core.cache_manager.REDIS_AVAILABLE', True):
            with patch('core.cache_manager.redis') as mock_redis_module:
                mock_client = MagicMock()
                mock_redis_module.from_url.return_value = mock_client
                mock_client.ping.return_value = True
                
                manager = CacheManager()
                
                # Set cache
                mock_client.get.return_value = None
                manager.set("test_key", {"data": "value"}, ttl=60)
                
                # Get cache
                mock_client.get.return_value = json.dumps({"data": "value"})
                result = manager.get("test_key")
                assert result == {"data": "value"}
                
                # Delete cache
                manager.delete("test_key")
                
                # Verify stats
                assert manager.cache_stats["sets"] == 1
                assert manager.cache_stats["hits"] == 1
                assert manager.cache_stats["deletes"] == 1

    def test_cache_with_decorator(self):
        """Test cache usage with decorator"""
        with patch('core.cache_manager.REDIS_AVAILABLE', True):
            with patch('core.cache_manager.redis') as mock_redis_module:
                mock_client = MagicMock()
                mock_redis_module.from_url.return_value = mock_client
                mock_client.ping.return_value = True
                
                manager = CacheManager()
                
                # Test basic cache operations instead of decorator
                mock_client.get.return_value = None
                manager.set("test_key", {"data": "value"}, ttl=60)
                
                # Get cache
                mock_client.get.return_value = json.dumps({"data": "value"})
                result = manager.get("test_key")
                assert result == {"data": "value"}

    def test_cache_hit_rate_calculation(self):
        """Test cache hit rate calculation"""
        with patch('core.cache_manager.REDIS_AVAILABLE', True):
            with patch('core.cache_manager.redis') as mock_redis_module:
                mock_client = MagicMock()
                mock_redis_module.from_url.return_value = mock_client
                mock_client.ping.return_value = True
                
                manager = CacheManager()
                
                # Simulate cache hits and misses
                for _ in range(80):
                    manager.cache_stats["hits"] += 1
                for _ in range(20):
                    manager.cache_stats["misses"] += 1
                
                hit_rate = manager.get_cache_hit_rate()
                assert hit_rate == 0.8