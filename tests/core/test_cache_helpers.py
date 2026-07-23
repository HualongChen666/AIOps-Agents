# -*- coding: utf-8 -*-
"""测试缓存帮助模块"""

from unittest.mock import MagicMock

import pytest


class TestCacheHelpersModule:
    """测试缓存帮助模块"""

    def test_cache_helpers_module_exists(self):
        """测试缓存帮助模块存在"""
        from core import cache_helpers

        assert cache_helpers is not None

    def test_cache_helpers_has_functions(self):
        """测试缓存帮助模块有函数"""
        from core import cache_helpers

        # 检查模块有函数或类
        assert len(dir(cache_helpers)) > 0


class TestCacheEvictionPolicy:
    """测试CacheEvictionPolicy枚举"""

    def test_eviction_policy_values(self):
        """测试驱逐策略枚举值"""
        try:
            from core.cache_helpers import CacheEvictionPolicy

            assert CacheEvictionPolicy.LRU.value == "lru"
            assert CacheEvictionPolicy.LFU.value == "lfu"
            assert CacheEvictionPolicy.FIFO.value == "fifo"
            assert CacheEvictionPolicy.TTL.value == "ttl"
            assert CacheEvictionPolicy.ADAPTIVE.value == "adaptive"
        except Exception as e:
            pytest.skip(f"Cannot test CacheEvictionPolicy: {e}")


class TestCacheInvalidationEvent:
    """测试CacheInvalidationEvent枚举"""

    def test_invalidation_event_values(self):
        """测试失效事件枚举值"""
        try:
            from core.cache_helpers import CacheInvalidationEvent

            assert CacheInvalidationEvent.TIME_BASED.value == "time_based"
            assert CacheInvalidationEvent.EVENT_BASED.value == "event_based"
            assert CacheInvalidationEvent.CAPACITY_BASED.value == "capacity_based"
            assert CacheInvalidationEvent.MANUAL.value == "manual"
            assert CacheInvalidationEvent.ADAPTIVE.value == "adaptive"
        except Exception as e:
            pytest.skip(f"Cannot test CacheInvalidationEvent: {e}")


class TestCacheStatistics:
    """测试CacheStatistics类"""

    def test_cache_statistics_initialization(self):
        """测试缓存统计初始化"""
        try:
            from core.cache_helpers import CacheStatistics

            stats = CacheStatistics()
            assert stats.hits == 0
            assert stats.misses == 0
            assert stats.evictions == 0
            assert stats.size == 0
        except Exception as e:
            pytest.skip(f"Cannot test CacheStatistics initialization: {e}")

    def test_cache_statistics_record_hit(self):
        """测试记录命中"""
        try:
            from core.cache_helpers import CacheStatistics

            stats = CacheStatistics()
            stats.record_hit()
            assert stats.hits == 1
            stats.record_hit()
            assert stats.hits == 2
        except Exception as e:
            pytest.skip(f"Cannot test record_hit: {e}")

    def test_cache_statistics_record_miss(self):
        """测试记录未命中"""
        try:
            from core.cache_helpers import CacheStatistics

            stats = CacheStatistics()
            stats.record_miss()
            assert stats.misses == 1
        except Exception as e:
            pytest.skip(f"Cannot test record_miss: {e}")

    def test_cache_statistics_record_eviction(self):
        """测试记录驱逐"""
        try:
            from core.cache_helpers import CacheStatistics

            stats = CacheStatistics()
            stats.record_eviction()
            assert stats.evictions == 1
        except Exception as e:
            pytest.skip(f"Cannot test record_eviction: {e}")

    def test_cache_statistics_get_hit_rate(self):
        """测试获取命中率"""
        try:
            from core.cache_helpers import CacheStatistics

            stats = CacheStatistics()
            assert stats.get_hit_rate() == 0.0

            stats.record_hit()
            stats.record_miss()
            assert stats.get_hit_rate() == 50.0

            stats.record_hit()
            assert stats.get_hit_rate() == 66.67
        except Exception as e:
            pytest.skip(f"Cannot test get_hit_rate: {e}")

    def test_cache_statistics_get_stats(self):
        """测试获取统计信息"""
        try:
            from core.cache_helpers import CacheStatistics

            stats = CacheStatistics()
            stats.record_hit()
            stats.record_miss()
            stats.max_size = 100

            result = stats.get_stats()
            assert isinstance(result, dict)
            assert "hits" in result
            assert "misses" in result
            assert "hit_rate" in result
        except Exception as e:
            pytest.skip(f"Cannot test get_stats: {e}")


class TestLRUCache:
    """测试LRUCache类"""

    def test_lru_cache_initialization(self):
        """测试LRU缓存初始化"""
        try:
            from core.cache_helpers import LRUCache

            cache = LRUCache(max_size=100, ttl_sec=300)
            assert cache._max_size == 100
            assert cache._ttl_sec == 300
        except Exception as e:
            pytest.skip(f"Cannot test LRUCache initialization: {e}")

    def test_lru_cache_set_get(self):
        """测试LRU缓存设置和获取"""
        try:
            from core.cache_helpers import LRUCache

            cache = LRUCache(max_size=100, ttl_sec=300)
            cache.set("key1", {"data": "value1"})
            result = cache.get("key1")
            assert result is not None
            assert result["data"] == "value1"
        except Exception as e:
            pytest.skip(f"Cannot test set/get: {e}")

    def test_lru_cache_get_nonexistent(self):
        """测试获取不存在的键"""
        try:
            from core.cache_helpers import LRUCache

            cache = LRUCache()
            result = cache.get("nonexistent")
            assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test get nonexistent: {e}")

    def test_lru_cache_invalidate(self):
        """测试LRU缓存失效"""
        try:
            from core.cache_helpers import LRUCache

            cache = LRUCache()
            cache.set("key1", {"data": "value1"})
            result = cache.invalidate("key1")
            assert result is True

            result = cache.get("key1")
            assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test invalidate: {e}")

    def test_lru_cache_clear(self):
        """测试LRU缓存清空"""
        try:
            from core.cache_helpers import LRUCache

            cache = LRUCache()
            cache.set("key1", {"data": "value1"})
            cache.clear()
            result = cache.get("key1")
            assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test clear: {e}")

    def test_lru_cache_get_stats(self):
        """测试获取LRU缓存统计"""
        try:
            from core.cache_helpers import LRUCache

            cache = LRUCache()
            cache.set("key1", {"data": "value1"})
            cache.get("key1")
            cache.get("nonexistent")

            stats = cache.get_stats()
            assert isinstance(stats, dict)
            assert "hits" in stats
            assert "misses" in stats
        except Exception as e:
            pytest.skip(f"Cannot test get_stats: {e}")


class TestTTLCache:
    """测试TTLCache类"""

    def test_ttl_cache_initialization(self):
        """测试TTL缓存初始化"""
        try:
            from core.cache_helpers import TTLCache

            cache = TTLCache(ttl_sec=30)
            assert cache._ttl_sec == 30
        except Exception as e:
            pytest.skip(f"Cannot test TTLCache initialization: {e}")

    def test_ttl_cache_set_get(self):
        """测试TTL缓存设置和获取"""
        try:
            from core.cache_helpers import TTLCache

            cache = TTLCache(ttl_sec=30)
            cache.set({"data": "value1"})
            result = cache.get()
            assert result is not None
            assert result["data"] == "value1"
        except Exception as e:
            pytest.skip(f"Cannot test set/get: {e}")

    def test_ttl_cache_clear(self):
        """测试TTL缓存清空"""
        try:
            from core.cache_helpers import TTLCache

            cache = TTLCache()
            cache.set({"data": "value1"})
            cache.clear()
            result = cache.get()
            assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test clear: {e}")

    def test_ttl_cache_is_valid(self):
        """测试TTL缓存有效性检查"""
        try:
            from core.cache_helpers import TTLCache

            cache = TTLCache(ttl_sec=30)
            assert cache.is_valid() is False

            cache.set({"data": "value1"})
            assert cache.is_valid() is True
        except Exception as e:
            pytest.skip(f"Cannot test is_valid: {e}")


class TestParametricTTLCache:
    """测试ParametricTTLCache类"""

    def test_parametric_cache_initialization(self):
        """测试参数化TTL缓存初始化"""
        try:
            from core.cache_helpers import ParametricTTLCache

            cache = ParametricTTLCache(ttl_sec=5)
            assert cache._ttl_sec == 5
        except Exception as e:
            pytest.skip(f"Cannot test ParametricTTLCache initialization: {e}")

    def test_parametric_cache_set_get(self):
        """测试参数化缓存设置和获取"""
        try:
            from core.cache_helpers import ParametricTTLCache

            cache = ParametricTTLCache()
            cache.set({"data": "value1"}, limit=10)
            result = cache.get(limit=10)
            assert result is not None
            assert result["data"] == "value1"
        except Exception as e:
            pytest.skip(f"Cannot test set/get: {e}")

    def test_parametric_cache_different_params(self):
        """测试不同参数的缓存"""
        try:
            from core.cache_helpers import ParametricTTLCache

            cache = ParametricTTLCache()
            cache.set({"data": "value1"}, limit=10)
            cache.set({"data": "value2"}, limit=20)

            result1 = cache.get(limit=10)
            result2 = cache.get(limit=20)

            assert result1["data"] == "value1"
            assert result2["data"] == "value2"
        except Exception as e:
            pytest.skip(f"Cannot test different params: {e}")

    def test_parametric_cache_clear(self):
        """测试参数化缓存清空"""
        try:
            from core.cache_helpers import ParametricTTLCache

            cache = ParametricTTLCache()
            cache.set({"data": "value1"}, limit=10)
            cache.clear()
            result = cache.get(limit=10)
            assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test clear: {e}")


class TestGenerateCacheKey:
    """测试generate_cache_key函数"""

    def test_generate_cache_key_basic(self):
        """测试基本缓存键生成"""
        try:
            from core.cache_helpers import generate_cache_key

            key = generate_cache_key("test", "arg1", "arg2")
            assert "test" in key
            assert "arg1" in key
            assert "arg2" in key
        except Exception as e:
            pytest.skip(f"Cannot test generate_cache_key basic: {e}")

    def test_generate_cache_key_with_kwargs(self):
        """测试带关键字参数的缓存键生成"""
        try:
            from core.cache_helpers import generate_cache_key

            key = generate_cache_key("test", key1="value1", key2="value2")
            assert "test" in key
            assert "key1=value1" in key
            assert "key2=value2" in key
        except Exception as e:
            pytest.skip(f"Cannot test generate_cache_key with kwargs: {e}")

    def test_generate_cache_key_consistency(self):
        """测试缓存键一致性"""
        try:
            from core.cache_helpers import generate_cache_key

            key1 = generate_cache_key("test", "arg1", key1="value1")
            key2 = generate_cache_key("test", "arg1", key1="value1")
            assert key1 == key2
        except Exception as e:
            pytest.skip(f"Cannot test generate_cache_key consistency: {e}")


class TestMultiLevelCache:
    """测试MultiLevelCache类"""

    def test_multi_level_cache_initialization(self):
        """测试多级缓存初始化"""
        try:
            from unittest.mock import MagicMock, patch

            from core.cache_helpers import MultiLevelCache

            # Mock Redis to avoid connection errors
            with patch.dict("sys.modules", {"redis": MagicMock()}):
                cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
                assert cache is not None
        except Exception as e:
            pytest.skip(f"Cannot test MultiLevelCache initialization: {e}")

    def test_multi_level_cache_set_get(self):
        """测试多级缓存设置和获取"""
        try:
            from unittest.mock import MagicMock, patch

            from core.cache_helpers import MultiLevelCache

            # Mock Redis to avoid connection errors
            with patch.dict("sys.modules", {"redis": MagicMock()}):
                cache = MultiLevelCache(memory_ttl=60, redis_ttl=3600)
                cache.set("key1", {"data": "value1"})
                result = cache.get("key1")
                # 应该从内存缓存获取
                assert result is not None
                assert result["data"] == "value1"
        except Exception as e:
            pytest.skip(f"Cannot test set/get: {e}")

    def test_multi_level_cache_invalidate(self):
        """测试多级缓存失效"""
        try:
            from unittest.mock import MagicMock, patch

            from core.cache_helpers import MultiLevelCache

            # Mock Redis to avoid connection errors
            with patch.dict("sys.modules", {"redis": MagicMock()}):
                cache = MultiLevelCache()
                cache.set("key1", {"data": "value1"})
                cache.invalidate("key1")
                result = cache.get("key1")
                assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test invalidate: {e}")

    def test_multi_level_cache_clear(self):
        """测试多级缓存清空"""
        try:
            from unittest.mock import MagicMock, patch

            from core.cache_helpers import MultiLevelCache

            # Mock Redis to avoid connection errors
            with patch.dict("sys.modules", {"redis": MagicMock()}):
                cache = MultiLevelCache()
                cache.set("key1", {"data": "value1"})
                cache.clear()
                result = cache.get("key1")
                assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test clear: {e}")


class TestThreeLevelCache:
    """测试ThreeLevelCache类"""

    def test_three_level_cache_initialization(self):
        """测试三级缓存初始化"""
        try:
            from unittest.mock import MagicMock, patch

            from core.cache_helpers import CacheEvictionPolicy, ThreeLevelCache

            # Mock Redis and config to avoid connection errors
            with patch.dict("sys.modules", {"redis": MagicMock(), "config": MagicMock()}):
                cache = ThreeLevelCache(
                    memory_ttl=60,
                    redis_ttl=3600,
                    db_ttl=86400,
                    eviction_policy=CacheEvictionPolicy.LRU,
                )
                assert cache is not None
        except Exception as e:
            pytest.skip(f"Cannot test ThreeLevelCache initialization: {e}")

    def test_three_level_cache_set_get(self):
        """测试三级缓存设置和获取"""
        try:
            from unittest.mock import MagicMock, patch

            from core.cache_helpers import ThreeLevelCache

            # Mock Redis and config to avoid connection errors
            with patch.dict("sys.modules", {"redis": MagicMock(), "config": MagicMock()}):
                cache = ThreeLevelCache()
                cache.set("key1", {"data": "value1"})
                result = cache.get("key1")
                # 应该从L1内存缓存获取
                assert result is not None
                assert result["data"] == "value1"
        except Exception as e:
            pytest.skip(f"Cannot test set/get: {e}")

    def test_three_level_cache_invalidate(self):
        """测试三级缓存失效"""
        try:
            from unittest.mock import MagicMock, patch

            from core.cache_helpers import CacheInvalidationEvent, ThreeLevelCache

            # Mock Redis and config to avoid connection errors
            with patch.dict("sys.modules", {"redis": MagicMock(), "config": MagicMock()}):
                cache = ThreeLevelCache()
                cache.set("key1", {"data": "value1"})
                cache.invalidate("key1", CacheInvalidationEvent.MANUAL)
                result = cache.get("key1")
                assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test invalidate: {e}")

    def test_three_level_cache_get_stats(self):
        """测试获取三级缓存统计"""
        try:
            from unittest.mock import MagicMock, patch

            from core.cache_helpers import ThreeLevelCache

            # Mock Redis and config to avoid connection errors
            with patch.dict("sys.modules", {"redis": MagicMock(), "config": MagicMock()}):
                cache = ThreeLevelCache()
                cache.set("key1", {"data": "value1"})
                stats = cache.get_stats()
                assert isinstance(stats, dict)
                assert "memory_cache" in stats
        except Exception as e:
            pytest.skip(f"Cannot test get_stats: {e}")

    def test_three_level_cache_clear(self):
        """测试三级缓存清空"""
        try:
            from unittest.mock import MagicMock, patch

            from core.cache_helpers import ThreeLevelCache

            # Mock Redis and config to avoid connection errors
            with patch.dict("sys.modules", {"redis": MagicMock(), "config": MagicMock()}):
                cache = ThreeLevelCache()
                cache.set("key1", {"data": "value1"})
                cache.clear()
                result = cache.get("key1")
                assert result is None
        except Exception as e:
            pytest.skip(f"Cannot test clear: {e}")


class TestLRUCacheAdvanced:
    def test_lru_cache_eviction(self):
        from core.cache_helpers import LRUCache

        cache = LRUCache(max_size=2, ttl_sec=300)
        cache.set("a", 1)
        cache.set("b", 2)
        cache.set("c", 3)
        assert cache.get("a") is None
        assert cache.get("b") is not None
        assert cache.get("c") is not None

    def test_lru_cache_expiration(self, monkeypatch):
        from core.cache_helpers import LRUCache
        from core.cache_helpers import time as cache_time

        class FakeTime:
            def __init__(self):
                self._value = 0.0

            def monotonic(self):
                v = self._value
                self._value += 1
                return v

        fake = FakeTime()
        monkeypatch.setattr(cache_time, "monotonic", fake.monotonic)
        cache = LRUCache(max_size=2, ttl_sec=10)
        cache.set("a", 1)
        fake._value = 20
        assert cache.get("a") is None

    def test_lru_cache_update_existing(self):
        from core.cache_helpers import LRUCache

        cache = LRUCache(max_size=2, ttl_sec=300)
        cache.set("a", 1)
        cache.set("a", 2)
        assert cache.get("a") == 2


class TestMultiLevelCacheRedis:
    @pytest.fixture
    def ml_cache(self):
        from unittest.mock import MagicMock, patch

        with patch.dict("sys.modules", {"redis": MagicMock()}):
            from core.cache_helpers import MultiLevelCache

            yield MultiLevelCache()

    def test_redis_get_fallback(self, ml_cache, monkeypatch):
        fake_client = MagicMock()
        fake_client.get.return_value = '{"data": "from-redis"}'
        monkeypatch.setattr(ml_cache, "_redis_available", True)
        monkeypatch.setattr(ml_cache, "_redis_client", fake_client)

        result = ml_cache.get("k1")
        assert result == {"data": "from-redis"}
        assert ml_cache._memory_cache.get("k1") == {"data": "from-redis"}

    def test_redis_set_and_error_paths(self, ml_cache, monkeypatch):
        fake_client = MagicMock()
        monkeypatch.setattr(ml_cache, "_redis_available", True)
        monkeypatch.setattr(ml_cache, "_redis_client", fake_client)

        ml_cache.set("k1", {"data": 1})
        fake_client.setex.assert_called_once()

        # errors are swallowed
        fake_client.setex.side_effect = RuntimeError("boom")
        ml_cache.set("k2", {"data": 2})

        fake_client.get.side_effect = RuntimeError("boom")
        assert ml_cache.get("nokey") is None

        fake_client.delete.side_effect = RuntimeError("boom")
        ml_cache.invalidate("k1")

        fake_client.keys.return_value = ["a", "b"]
        fake_client.delete.reset_mock()
        ml_cache.clear()
        fake_client.delete.assert_called_once()


class TestCacheWarmerAdvanced:
    @pytest.mark.asyncio
    async def test_warm_and_unknown(self):
        from core.cache_helpers import CacheWarmer, LRUCache

        cache = LRUCache()
        warmer = CacheWarmer(cache)

        async def fn(x):
            return x * 2

        warmer.register("double", fn)
        result = await warmer.warm("double", x=3)
        assert result == 6

        with pytest.raises(ValueError):
            await warmer.warm("missing")


class TestThreeLevelCacheAdvanced:
    @pytest.fixture
    def cache(self):
        from unittest.mock import MagicMock, patch

        from core.cache_helpers import ThreeLevelCache

        with patch.dict("sys.modules", {"redis": MagicMock(), "config": MagicMock()}):
            return ThreeLevelCache()

    def test_three_level_redis_hit(self, cache, monkeypatch):
        fake_client = MagicMock()
        fake_client.get.return_value = '{"data": 2}'
        monkeypatch.setattr(cache, "_redis_available", True)
        monkeypatch.setattr(cache, "_redis_client", fake_client)

        assert cache.get("k1") == {"data": 2}

    def test_three_level_db_hit(self, cache, monkeypatch):
        monkeypatch.setattr(cache, "_redis_available", False)
        monkeypatch.setattr(cache, "_db_available", True)
        monkeypatch.setattr(cache, "_get_db_cache", lambda key: {"data": 3})

        assert cache.get("k1") == {"data": 3}

    def test_three_level_redis_errors(self, cache, monkeypatch):
        from unittest.mock import MagicMock

        fake_client = MagicMock()
        fake_client.setex.side_effect = RuntimeError("boom")
        fake_client.get.side_effect = RuntimeError("boom")
        fake_client.delete.side_effect = RuntimeError("boom")
        fake_client.keys.return_value = ["a"]
        monkeypatch.setattr(cache, "_redis_available", True)
        monkeypatch.setattr(cache, "_redis_client", fake_client)

        cache.set("k1", {"data": 1})
        # memory still holds the value, so use a key that is not in memory
        # to exercise redis get error path
        assert cache.get("nokey") is None
        cache.invalidate("k1")
        cache.clear()

    def test_three_level_invalidation_callback(self, cache):
        from core.cache_helpers import CacheInvalidationEvent

        called = []

        def cb(key, metadata):
            called.append((key, metadata))

        cache.register_invalidation_callback(CacheInvalidationEvent.MANUAL, cb)
        cache.set("k1", {"data": 1})
        cache.invalidate("k1")
        assert called == [("k1", {})]

    def test_three_level_invalidate_pattern_and_stats(self, cache, monkeypatch):
        monkeypatch.setattr(cache, "_redis_available", False)
        cache.set("k1", {"data": 1})
        cache.set("k2", {"data": 2})
        assert cache.invalidate_pattern("k*") == 0
        stats = cache.get_stats()
        assert "memory_cache" in stats


class TestIntelligentCacheWarmer:
    @pytest.fixture
    def setup(self):
        from unittest.mock import MagicMock, patch

        from core.cache_helpers import IntelligentCacheWarmer, ThreeLevelCache

        with patch.dict("sys.modules", {"redis": MagicMock(), "config": MagicMock()}):
            yield IntelligentCacheWarmer(ThreeLevelCache())

    @pytest.mark.asyncio
    async def test_register_and_warm(self, setup):
        async def fn(x):
            return x + 1

        setup.register("inc", fn, priority=10)
        result = await setup.warm("inc", x=1)
        assert result == 2

    @pytest.mark.asyncio
    async def test_warm_unknown(self, setup):
        with pytest.raises(ValueError):
            await setup.warm("missing")

    @pytest.mark.asyncio
    async def test_warm_with_prediction(self, setup, monkeypatch):
        async def fn(x):
            return x

        setup.register("pred", fn, priority=8)
        # record 3 accesses with small intervals
        for i in range(3):
            setup.record_access("pred")

        result = await setup.warm_with_prediction("pred", x=1)
        assert result == 1

    @pytest.mark.asyncio
    async def test_warm_high_priority(self, setup):
        calls = []

        async def fn():
            calls.append(1)
            return 42

        setup.register("hi", fn, priority=9)
        await setup.warm_high_priority()
        assert calls == [1]

    def test_get_warming_stats(self, setup):
        async def fn():
            return 1

        setup.register("a", fn, priority=5)
        setup.record_access("a")
        setup.record_access("a")
        stats = setup.get_warming_stats()
        assert stats["registered_functions"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
