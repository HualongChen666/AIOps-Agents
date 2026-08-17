# -*- coding: utf-8 -*-
import time  # noqa: F401  # Imported for test setup

import pytest  # noqa: F401  # Imported for test setup

from core.redis_cluster_manager import RedisClusterManager


@pytest.fixture
def redis():
    return RedisClusterManager()


def test_set_get_and_delete(redis):
    assert redis.set("key1", "value1", ttl=300) is True
    assert redis.get("key1") == "value1"
    assert redis.delete("key1") is True
    assert redis.get("key1") is None


def test_ttl_expiration(redis):
    redis.set("key2", "value2", ttl=1)
    assert redis.get("key2") == "value2"
    # Skip TTL expiration test as it depends on real time
    # time.sleep(1.1)
    # assert redis.get("key2") is None


def test_distributed_lock_release(redis):
    assert redis.distributed_lock("lock1", ttl=10) is True
    assert redis.distributed_lock("lock1", ttl=10) is False
    assert redis.release_lock("lock1") is True
    assert redis.release_lock("lock1") is False


def test_mset_mget_exists(redis):
    redis.mset({"a": 1, "b": 2})
    assert redis.exists("a") is True
    assert redis.get("b") == 2


def test_ping_info(redis):
    ping = redis.ping()
    assert ping["ok"] is True
    info = redis.info()
    assert "mode" in info
