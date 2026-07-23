# -*- coding: utf-8 -*-
"""测试增强缓存模块"""

from unittest.mock import patch

import pytest

from core.enhanced_caching import (
    CacheInvalidationStrategy,
    CacheWarmer,
    RedisCacheBackend,
    setup_enhanced_caching,
    smart_cache,
)


class FakeRedis:
    """A minimal in-memory Redis stub for testing."""

    def __init__(self, *args, **kwargs):
        self.store = {}

    def ping(self):
        return True

    def get(self, key):
        return self.store.get(key)

    def setex(self, key, ttl, value):
        self.store[key] = value
        return True

    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                count += 1
        return count

    def keys(self, pattern):
        # Very naive pattern matching for test keys.
        import fnmatch

        return [k for k in self.store if fnmatch.fnmatch(k, pattern)]

    def info(self):
        return {
            "connected_clients": 5,
            "used_memory_human": "10M",
            "db0": {"keys": len(self.store)},
            "keyspace_hits": 10,
            "keyspace_misses": 2,
        }


@pytest.fixture
def backend():
    with patch("core.enhanced_caching.redis.Redis", FakeRedis):
        yield RedisCacheBackend()


class TestRedisCacheBackend:
    """测试 RedisCacheBackend"""

    def test_init_without_redis(self):
        with patch("core.enhanced_caching.redis.Redis", side_effect=ImportError("no redis")):
            backend = RedisCacheBackend()
            assert backend.client is None

    def test_get_and_set(self, backend):
        assert backend.set("key", {"data": 1}) is True
        assert backend.get("key") == {"data": 1}

    def test_get_missing(self, backend):
        assert backend.get("missing") is None

    def test_delete(self, backend):
        backend.set("a", 1)
        assert backend.delete("a") == 1
        assert backend.get("a") is None

    def test_flush_pattern(self, backend):
        backend.set("user:1", 1)
        backend.set("user:2", 2)
        backend.set("other", 3)
        assert backend.flush_pattern("user:*") == 2
        assert backend.get("user:1") is None
        assert backend.get("other") is not None

    def test_get_stats(self, backend):
        backend.set("x", 1)
        stats = backend.get_stats()
        assert stats["connected_clients"] == 5
        assert "error" not in stats

    def test_get_stats_not_connected(self):
        with patch("core.enhanced_caching.redis.Redis", side_effect=ImportError("no redis")):
            backend = RedisCacheBackend()
            assert backend.get_stats() == {"error": "Not connected"}


class TestCacheWarmer:
    """测试 CacheWarmer"""

    @pytest.mark.asyncio
    async def test_warmup_cache(self, backend):
        warmer = CacheWarmer(backend)

        async def sample_task():
            return {"k1": "v1", "k2": "v2"}

        warmer.register_warmup_task(sample_task)
        await warmer.warmup_cache()
        assert backend.get("k1") == "v1"
        assert backend.get("k2") == "v2"

    @pytest.mark.asyncio
    async def test_warmup_task_error(self, backend):
        warmer = CacheWarmer(backend)

        async def bad_task():
            raise RuntimeError("fail")

        warmer.register_warmup_task(bad_task)
        # Should not raise
        await warmer.warmup_cache()


class TestCacheInvalidationStrategy:
    """测试 CacheInvalidationStrategy"""

    def test_invalidate_by_prefix(self, backend):
        backend.set("user:1", 1)
        backend.set("user:2", 2)
        CacheInvalidationStrategy.invalidate_by_prefix(backend, "user")
        assert backend.get("user:1") is None

    def test_invalidate_by_tags(self, backend):
        backend.set("tag:cache:1", 1)
        CacheInvalidationStrategy.invalidate_by_tags(backend, ["cache"])
        assert backend.get("tag:cache:1") is None

    def test_invalidate_by_time(self, backend):
        # Should not raise in non-implemented method
        CacheInvalidationStrategy.invalidate_by_time(backend, 60)


class TestSmartCache:
    """测试 smart_cache 装饰器"""

    @pytest.mark.asyncio
    async def test_smart_cache_hit_and_miss(self, backend):
        call_count = 0

        @smart_cache(cache_backend=backend, key_prefix="test")
        async def expensive(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        assert await expensive(3) == 6
        assert await expensive(3) == 6
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_smart_cache_condition(self, backend):
        call_count = 0

        @smart_cache(cache_backend=backend, condition=lambda x: x > 0)
        async def maybe_cached(x):
            nonlocal call_count
            call_count += 1
            return x

        assert await maybe_cached(-1) == -1
        assert await maybe_cached(5) == 5
        assert call_count == 2


class TestSetupEnhancedCaching:
    """测试 setup_enhanced_caching"""

    @pytest.mark.asyncio
    async def test_setup(self):
        with patch("core.enhanced_caching.redis.Redis", FakeRedis):
            result = await setup_enhanced_caching()
            assert result["status"] == "success"
            assert "cache_stats" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
