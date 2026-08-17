# -*- coding: utf-8 -*-
import pytest  # noqa: F401  # Imported for test setup

from core.db_optimization import (
    clear_slow_queries,
    get_performance_summary,
    get_query_cache_statistics,
    get_slow_queries,
    record_query_cache_hit,
    record_query_cache_miss,
    record_slow_query,
    reset_query_cache,
    suggest_optimizations,
)


@pytest.fixture(autouse=True)
def reset_state():
    reset_query_cache()
    clear_slow_queries()
    yield


def test_record_and_get_slow_queries():
    record_slow_query("SELECT * FROM users", 150.0)
    record_slow_query("SELECT * FROM orders", 80.0)
    slow = get_slow_queries(limit=10)
    assert len(slow) == 2
    assert any(s["is_slow"] for s in slow)
    assert not all(s["is_slow"] for s in slow)


def test_query_cache_statistics():
    record_query_cache_hit("SELECT 1")
    record_query_cache_hit("SELECT 1")
    record_query_cache_miss("SELECT 2")
    stats = get_query_cache_statistics()
    assert stats["hits"] == 2
    assert stats["misses"] == 1
    assert 0.0 < stats["hit_rate"] <= 1.0


def test_suggest_optimizations_with_index_hint():
    record_slow_query("SELECT * FROM users WHERE status = 'active'", 200.0)
    record_slow_query("SELECT * FROM users WHERE status = 'active'", 210.0)
    suggestions = suggest_optimizations()
    assert any("status" in s and "index" in s for s in suggestions)


def test_performance_summary():
    record_slow_query("SELECT 1", 50.0)
    record_query_cache_hit("SELECT 1")
    summary = get_performance_summary()
    assert summary["query_time_avg"] >= 0.0
    assert summary["slow_query_count"] >= 0
