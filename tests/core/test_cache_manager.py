# -*- coding: utf-8 -*-
"""Tests for core/cache_manager.py public API."""

import pytest  # noqa: F401  # Imported for test setup

from core.cache_manager import (
    MemoryCacheBackend,
    backup_cache,
    cache_result,
    configure_backend,
    flush_all,
    get_cache_metrics,
    get_cache_stats,
    invalidate_cache,
    restore_cache,
)


@pytest.fixture(autouse=True)
def _reset_backend():
    configure_backend("memory")
    flush_all()
    yield
    flush_all()
    configure_backend("memory")


def test_cache_result_decorator():
    call_count = 0

    @cache_result(ttl=300)
    def square(x):
        nonlocal call_count
        call_count += 1
        return x * x

    assert square(3) == 9
    assert square(3) == 9
    assert call_count == 1
    square(4)
    assert call_count == 2


def test_invalidate_cache_and_stats():
    @cache_result(ttl=300)
    def greet(name):
        return f"hello {name}"

    greet("alice")
    greet("bob")
    stats = get_cache_stats("greet")
    assert stats["function_size"] == 2
    removed = invalidate_cache("greet")
    assert removed == 2
    assert get_cache_metrics("greet")["function_size"] == 0


def test_backup_and_restore():
    @cache_result(ttl=300)
    def identity(x):
        return x

    identity(1)
    data = backup_cache("identity")
    assert isinstance(data, dict)
    assert len(data) == 1
    flush_all()
    assert get_cache_stats("identity")["function_size"] == 0
    restore_cache(data)
    assert get_cache_stats("identity")["function_size"] == 1


def test_configure_backend():
    assert configure_backend("memory") is True
    assert configure_backend("redis") is True
    flush_all()
    assert configure_backend("memory") is True


def test_backend_classes():
    backend = MemoryCacheBackend()
    backend.set("k", "v", ttl=60)
    assert backend.get("k") == "v"
    assert backend.delete("k") is True
    assert backend.delete("k") is False
