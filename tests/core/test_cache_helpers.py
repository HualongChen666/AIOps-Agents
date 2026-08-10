# -*- coding: utf-8 -*-
import pytest

from core.cache_manager import (
    cache_result,
    flush_all,
    get_cache_stats,
    invalidate_cache,
)


@pytest.fixture(autouse=True)
def clean_cache():
    flush_all()
    yield
    flush_all()


def test_cache_result_decorator():
    call_count = {"n": 0}

    @cache_result(ttl=300, track_stats=True)
    def add(a, b):
        call_count["n"] += 1
        return a + b

    assert add(2, 3) == 5
    assert add(2, 3) == 5
    assert call_count["n"] == 1
    stats = get_cache_stats("add")
    assert stats["total_hits"] >= 1


def test_invalidate_cache():
    @cache_result(ttl=300)
    def greet(name):
        return f"hi {name}"

    greet("alice")
    removed = invalidate_cache("greet")
    assert removed == 1


def test_flush_all():
    @cache_result(ttl=300)
    def one():
        return 1

    one()
    assert flush_all() is True
    stats = get_cache_stats("one")
    assert stats["cache_size"] == 0
