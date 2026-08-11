# -*- coding: utf-8 -*-
"""Tests for core/caching_strategy.py."""

from core.caching_strategy import (
    cache_decorator,
    clear_cache,
    configure_caching_strategy,
    delete_cache,
    generate_cache_key,
    get_cache,
    get_cache_config,
    get_cache_info,
    get_cache_statistics,
    invalidate_pattern,
    is_caching_enabled,
    reset_cache_statistics,
    set_cache,
)


def test_configure_and_status():
    configure_caching_strategy(default_ttl_seconds=60, max_size=100)
    assert is_caching_enabled() is True
    assert get_cache_config()["default_ttl_seconds"] == 60


def test_set_get_delete_cache():
    configure_caching_strategy()
    assert set_cache("key1", {"x": 1}) is True
    assert get_cache("key1") == {"x": 1}
    assert delete_cache("key1") is True
    assert get_cache("key1") is None


def test_cache_key_and_pattern():
    configure_caching_strategy(cache_key_prefix="aiops")
    assert "aiops" in generate_cache_key("mykey")
    set_cache("mykey", 1)
    set_cache("mykey2", 2)
    assert invalidate_pattern("aiops:mykey") >= 0
    reset_cache_statistics()
    assert "hits" in get_cache_statistics()
    assert clear_cache() >= 0
    assert "memory_usage_bytes" in get_cache_info()


def test_cache_decorator():
    configure_caching_strategy()

    @cache_decorator(ttl_seconds=60)
    def compute(x):
        return x * 2

    assert compute(3) == 6
    assert compute(3) == 6
