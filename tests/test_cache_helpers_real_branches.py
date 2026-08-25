# -*- coding: utf-8 -*-
"""Real in-memory branch-coverage tests for core/cache_helpers.py.

These tests exercise the cache helpers using real function calls and
in-memory data only (no mocks).  An in-memory Redis-compatible store is
used where needed so the Redis serialization / fallback / error branches
are reached without requiring a live Redis server.
"""

import asyncio  # noqa: F401  # Imported for test setup
import fnmatch
import json  # noqa: F401  # Imported for test setup
import time  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta

import pytest  # noqa: F401  # Imported for test setup

from core.cache_helpers import (
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


class InMemoryRedis:
    """A real in-memory key/value store that implements the Redis methods
    the cache helpers actually call: get, setex, delete, keys.
    """

    def __init__(self):
        self._data = {}

    def get(self, key):
        item = self._data.get(key)
        if item is None:
            return None
        if time.time() > item["expires_at"]:
            self._data.pop(key, None)
            return None
        return item["value"]

    def setex(self, key, ttl, value):
        self._data[key] = {"value": value, "expires_at": time.time() + int(ttl)}

    def delete(self, *keys):
        count = 0
        for key in keys:
            if key in self._data:
                self._data.pop(key, None)
                count += 1
        return count

    def keys(self, pattern):
        return [k for k in self._data if fnmatch.fnmatch(k, pattern)]


class FailingRedis:
    """Real in-memory store that raises on the configured methods."""

    def __init__(self, *fail_methods):
        self._fail_methods = set(fail_methods)

    def _maybe_fail(self, name):
        if name in self._fail_methods:
            raise RuntimeError(f"Redis {name} failure")

    def get(self, key):
        self._maybe_fail("get")
        return None

    def setex(self, key, ttl, value):
        self._maybe_fail("setex")

    def delete(self, *keys):
        self._maybe_fail("delete")
        return 0

    def keys(self, pattern):
        self._maybe_fail("keys")
        return []


# ============================================================
# CacheStatistics
# ============================================================


def test_cache_statistics_zero_hit_rate():
    stats = CacheStatistics()
    assert stats.get_hit_rate() == 0.0
    assert "0.00%" in stats.get_stats()["hit_rate"]


def test_cache_statistics_full_usage():
    stats = CacheStatistics()
    for _ in range(5):
        stats.record_hit()
    for _ in range(3):
        stats.record_miss()
    stats.record_eviction()
    stats.max_size = 100
    stats.size = 4
    s = stats.get_stats()
    assert s["hits"] == 5
    assert s["misses"] == 3
    assert s["evictions"] == 1
    assert "62.50%" in s["hit_rate"]


# ============================================================
# generate_cache_key
# ============================================================


def test_generate_cache_key_scalar():
    key1 = generate_cache_key("svc", "a", 1, 2.5, True, tag="x")
    key2 = generate_cache_key("svc", "a", 1, 2.5, True, tag="x")
    assert key1 == key2
    assert key1.startswith("svc")


def test_generate_cache_key_non_scalar():
    key1 = generate_cache_key("svc", [1, 2], {"a": 3}, obj=[1, 2])
    key2 = generate_cache_key("svc", [1, 2], {"a": 3}, obj=[1, 2])
    assert key1 == key2
    assert len(key1.split(":")) == 4


# ============================================================
# LRUCache
# ============================================================


def test_lru_cache_hit_miss_ttl_eviction():
    cache = LRUCache(max_size=2, ttl_sec=0.2)
    assert cache.get("missing") is None
    cache.set("a", 1)
    cache.set("b", 2)
    assert cache.get("a") == 1
    assert cache.get("b") == 2
    cache.set("c", 3)
    assert cache.get("b") == 2
    assert cache.get("a") is None  # evicted
    time.sleep(0.25)
    assert cache.get("b") is None  # expired


def test_lru_cache_update_existing_and_invalidate():
    cache = LRUCache(max_size=3, ttl_sec=10.0)
    cache.set("a", 1)
    cache.set("a", 10)
    assert cache.get("a") == 10
    assert cache.invalidate("a") is True
    assert cache.invalidate("a") is False
    cache.clear()
    assert cache.get("a") is None
    assert isinstance(cache.get_stats(), dict)


# ============================================================
# TTLCache
# ============================================================


def test_ttl_cache_valid_and_clear():
    cache = TTLCache(ttl_sec=0.5)
    assert cache.get() is None
    assert cache.is_valid() is False
    cache.set({"value": 42})
    assert cache.get()["value"] == 42
    assert cache.is_valid() is True
    cache.clear()
    assert cache.get() is None
    assert cache.is_valid() is False


def test_ttl_cache_ts_zero():
    cache = TTLCache(ttl_sec=10.0)
    cache._cache["data"] = {"value": 1}
    cache._cache["ts"] = 0.0
    assert cache.get() is None
    assert cache.is_valid() is False


def test_ttl_cache_data_none():
    cache = TTLCache(ttl_sec=10.0)
    cache._cache["data"] = None
    cache._cache["ts"] = time.monotonic()
    assert cache.get() is None
    assert cache.is_valid() is False


def test_ttl_cache_negative_elapsed():
    cache = TTLCache(ttl_sec=10.0)
    cache._cache["data"] = {"value": 1}
    cache._cache["ts"] = time.monotonic() + 100
    assert cache.get() is None
    assert cache.is_valid() is False


# ============================================================
# ParametricTTLCache
# ============================================================


def test_parametric_ttl_cache_basic():
    cache = ParametricTTLCache(ttl_sec=0.5)
    assert cache.get(param="x") is None
    cache.set({"value": 1}, param="x")
    assert cache.get(param="x")["value"] == 1
    assert cache.get(param="y") is None
    cache.clear()
    assert cache.get(param="x") is None


def test_parametric_ttl_cache_invalid_states():
    cache = ParametricTTLCache(ttl_sec=10.0)
    cache.set({"value": 1}, param="x")
    key = cache._make_key(param="x")

    # ts <= 0
    cache._cache[key]["ts"] = 0.0
    assert cache.get(param="x") is None

    cache.set({"value": 2}, param="x")
    key = cache._make_key(param="x")
    # data is None
    cache._cache[key]["data"] = None
    assert cache.get(param="x") is None

    cache.set({"value": 3}, param="x")
    key = cache._make_key(param="x")
    # negative elapsed
    cache._cache[key]["ts"] = time.monotonic() + 100
    assert cache.get(param="x") is None

    # expired
    cache.set({"value": 4}, param="x")
    time.sleep(0.02)
    # give it a very short ttl by creating a new short cache
    short = ParametricTTLCache(ttl_sec=0.01)
    short.set({"value": 5}, p="a")
    time.sleep(0.02)
    assert short.get(p="a") is None


# ============================================================
# CacheWarmer
# ============================================================


@pytest.mark.asyncio
async def test_cache_warmer_register_and_warm():
    cache = LRUCache()
    warmer = CacheWarmer(cache)

    async def double(x):
        return x * 2

    warmer.register("double", double)
    assert await warmer.warm("double", 7) == 14
    assert cache.get("warm_double:7") == 14


@pytest.mark.asyncio
async def test_cache_warmer_unknown_raises():
    cache = LRUCache()
    warmer = CacheWarmer(cache)
    with pytest.raises(ValueError, match="Unknown warm function"):
        await warmer.warm("missing")


# ============================================================
# MultiLevelCache
# ============================================================


def _attach_redis(cache, store):
    cache._redis_client = store
    cache._redis_available = True


def test_multi_level_memory_only():
    cache = MultiLevelCache(memory_ttl=0.5, redis_ttl=3600)
    assert cache.get("missing") is None
    cache.set("k", "v")
    assert cache.get("k") == "v"
    cache.invalidate("k")
    assert cache.get("k") is None
    cache.clear()


def test_multi_level_redis_scalar_and_dict():
    store = InMemoryRedis()
    cache = MultiLevelCache(memory_ttl=0.1, redis_ttl=3600)
    _attach_redis(cache, store)

    cache.set("str", "hello")
    cache.set("num", 42)
    cache.set("flag", True)
    cache.set("obj", {"a": 1})

    # force L1 misses to read from Redis
    cache._memory_cache.clear()
    assert cache.get("str") == "hello"
    assert cache.get("num") == 42
    assert cache.get("flag") is True
    assert cache.get("obj") == {"a": 1}


def test_multi_level_redis_invalid_json_fallback():
    store = InMemoryRedis()
    cache = MultiLevelCache(memory_ttl=0.1, redis_ttl=3600)
    _attach_redis(cache, store)

    # Put a string that starts with '{' but is not valid JSON
    redis_key = cache._make_redis_key("badjson")
    store.setex(redis_key, 3600, "{not json")
    cache._memory_cache.clear()
    assert cache.get("badjson") == "{not json"


def test_multi_level_redis_get_error():
    cache = MultiLevelCache(memory_ttl=0.1, redis_ttl=3600)
    _attach_redis(cache, FailingRedis("get"))
    cache._memory_cache.set("x", "y")  # ensure memory is not involved
    cache._memory_cache.clear()
    assert cache.get("x") is None


def test_multi_level_redis_set_error():
    cache = MultiLevelCache(memory_ttl=10.0, redis_ttl=3600)
    _attach_redis(cache, FailingRedis("setex"))
    cache.set("x", "y")
    assert cache.get("x") == "y"  # memory still has it


def test_multi_level_redis_invalidate_and_clear_error():
    cache = MultiLevelCache(memory_ttl=10.0, redis_ttl=3600)
    _attach_redis(cache, InMemoryRedis())
    cache.set("a", 1)
    _attach_redis(cache, FailingRedis("delete"))
    cache.invalidate("a")

    _attach_redis(cache, FailingRedis("keys"))
    cache.clear()


# ============================================================
# ThreeLevelCache
# ============================================================


def _attach_tlc_redis(cache, store):
    cache._redis_client = store
    cache._redis_available = True


def test_three_level_l1_and_l3():
    cache = ThreeLevelCache(memory_ttl=0.1, redis_ttl=3600, db_ttl=10.0)
    assert cache.get("missing") is None
    cache.set("k", {"v": 1})
    assert cache.get("k") == {"v": 1}

    # force L1 miss, L2 absent, L3 hit
    cache._memory_cache.clear()
    assert cache.get("k") == {"v": 1}

    # L3 not found
    assert cache.get("other") is None


def test_three_level_l2_hit():
    store = InMemoryRedis()
    cache = ThreeLevelCache(memory_ttl=0.1, redis_ttl=3600, db_ttl=10.0)
    _attach_tlc_redis(cache, store)

    # Seed L2 directly, then read from a cache with an empty L1
    redis_key = cache._make_redis_key("k")
    store.setex(redis_key, 3600, json.dumps({"v": 2}))
    assert cache.get("k") == {"v": 2}


def test_three_level_l2_invalid_json():
    store = InMemoryRedis()
    cache = ThreeLevelCache(memory_ttl=0.1, redis_ttl=3600, db_ttl=10.0)
    _attach_tlc_redis(cache, store)
    redis_key = cache._make_redis_key("bad")
    store.setex(redis_key, 3600, "{not json")
    assert cache.get("bad") == "{not json"


def test_three_level_l3_ttl_expiration():
    cache = ThreeLevelCache(memory_ttl=0.05, redis_ttl=3600, db_ttl=0.01)
    cache.set("k", {"v": 1})
    cache._memory_cache.clear()
    time.sleep(0.03)
    assert cache.get("k") is None


def test_three_level_l3_scalar_promotion():
    cache = ThreeLevelCache(memory_ttl=0.1, redis_ttl=3600, db_ttl=10.0)
    _attach_tlc_redis(cache, InMemoryRedis())
    cache.set("n", 123)
    cache._memory_cache.clear()
    # clear L2 too
    cache._redis_client.delete(cache._make_redis_key("n"))
    assert cache.get("n") == 123


def test_three_level_redis_and_db_errors():
    cache = ThreeLevelCache(memory_ttl=10.0, redis_ttl=3600, db_ttl=10.0)
    _attach_tlc_redis(cache, FailingRedis("setex"))
    cache.set("x", "y")
    assert cache.get("x") == "y"

    _attach_tlc_redis(cache, FailingRedis("get"))
    cache._memory_cache.clear()
    assert cache.get("x") == "y"  # falls back to db when L2 fails

    _attach_tlc_redis(cache, FailingRedis("delete", "keys"))
    cache.invalidate("x")
    cache.clear()


def test_three_level_invalidation_callbacks():
    cache = ThreeLevelCache(memory_ttl=10.0, redis_ttl=3600, db_ttl=10.0)
    events = []

    def callback(key, meta):
        events.append((key, meta))

    def bad_callback(key, meta):
        raise RuntimeError("callback boom")

    cache.register_invalidation_callback(CacheInvalidationEvent.MANUAL, callback)
    cache.register_invalidation_callback(CacheInvalidationEvent.MANUAL, bad_callback)
    cache.set("k", 1)
    cache.invalidate("k", event=CacheInvalidationEvent.MANUAL, metadata={"reason": "test"})
    assert events == [("k", {"reason": "test"})]


def test_three_level_invalidate_pattern_and_stats():
    store = InMemoryRedis()
    cache = ThreeLevelCache(memory_ttl=10.0, redis_ttl=3600, db_ttl=10.0)
    _attach_tlc_redis(cache, store)
    cache.set("pfx:one", 1)
    cache.set("pfx:two", 2)

    events = []
    cache.register_invalidation_callback(
        CacheInvalidationEvent.EVENT_BASED,
        lambda key, meta: events.append((key, meta)),
    )
    count = cache.invalidate_pattern("pfx:*")
    assert count == 2
    assert events == [("pfx:*", {"pattern": "pfx:*"})]

    stats = cache.get_stats()
    assert stats["db_cache_available"] is True
    assert "eviction_policy" in stats


def test_three_level_db_not_available_branch():
    cache = ThreeLevelCache(memory_ttl=10.0, redis_ttl=3600, db_ttl=10.0)
    cache._db_available = False
    cache.set("k", 1)
    assert cache.get("k") == 1
    cache.invalidate("k")
    cache.clear()


# ============================================================
# IntelligentCacheWarmer
# ============================================================


@pytest.mark.asyncio
async def test_intelligent_warmer_basic():
    cache = ThreeLevelCache(memory_ttl=10.0, redis_ttl=3600, db_ttl=10.0)
    warmer = IntelligentCacheWarmer(cache)

    async def double(x):
        return x * 2

    warmer.register("double", double, priority=8)
    assert await warmer.warm("double", 5) == 10
    assert cache.get("warm_double:5") == 10

    assert warmer.predict_next_access("double") == 0.0
    result = await warmer.warm_with_prediction(
        "double", 3
    )  # noqa: F841  # Variable for test verification
    assert result == 6  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_intelligent_warmer_prediction():
    cache = ThreeLevelCache(memory_ttl=10.0, redis_ttl=3600, db_ttl=10.0)
    warmer = IntelligentCacheWarmer(cache)

    async def inc(x):
        return x + 1

    warmer.register("inc", inc, priority=5)
    # Record 3+ accesses with real time deltas
    warmer.record_access("inc")
    time.sleep(0.02)
    warmer.record_access("inc")
    time.sleep(0.02)
    warmer.record_access("inc")
    time.sleep(0.02)
    warmer.record_access("inc")

    interval = warmer.predict_next_access("inc")
    assert interval > 0.0

    result = await warmer.warm_with_prediction(
        "inc", 5
    )  # noqa: F841  # Variable for test verification
    assert result == 6  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_intelligent_warmer_high_priority_and_stats():
    cache = ThreeLevelCache(memory_ttl=10.0, redis_ttl=3600, db_ttl=10.0)
    warmer = IntelligentCacheWarmer(cache)

    async def a():
        return "a"

    async def b():
        return "b"

    async def c():
        raise RuntimeError("low priority")

    warmer.register("a", a, priority=10)
    warmer.register("b", b, priority=8)
    warmer.register("c", c, priority=3)

    await warmer.warm_high_priority()
    stats = warmer.get_warming_stats()
    assert stats["registered_functions"] == 3
    assert stats["priorities"]["a"] == 10


@pytest.mark.asyncio
async def test_intelligent_warmer_unknown():
    cache = ThreeLevelCache(memory_ttl=10.0, redis_ttl=3600, db_ttl=10.0)
    warmer = IntelligentCacheWarmer(cache)
    with pytest.raises(ValueError, match="Unknown warm function"):
        await warmer.warm("missing")


@pytest.mark.asyncio
async def test_intelligent_warmer_access_pruning():
    cache = ThreeLevelCache(memory_ttl=10.0, redis_ttl=3600, db_ttl=10.0)
    warmer = IntelligentCacheWarmer(cache)
    warmer.register("x", lambda: None, priority=5)
    for _ in range(105):
        warmer.record_access("x")
    assert len(warmer._access_patterns["x"]) == 100
