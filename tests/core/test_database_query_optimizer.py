# -*- coding: utf-8 -*-
"""Tests for core/database_query_optimizer.py."""

from core.database_query_optimizer import (
    DatabaseQueryOptimizer,
    get_database_query_optimizer,
)


def test_get_database_query_optimizer():
    opt = get_database_query_optimizer()
    assert isinstance(opt, DatabaseQueryOptimizer)


def test_analyze_and_classify():
    opt = DatabaseQueryOptimizer()
    result = opt.analyze_query_performance("SELECT * FROM users", duration_ms=1500)  # noqa: F841  # Variable for test verification
    assert "recommendations" in result
    assert result["pattern"] == "select_star"


def test_recommendations_and_cache():
    opt = DatabaseQueryOptimizer()
    recs = opt.generate_optimization_recommendations("SELECT * FROM users")
    assert isinstance(recs, list)

    opt.cache_query_result("SELECT 1", "value", params={})
    assert opt.get_cached_query_result("SELECT 1", params={}) == "value"
    opt.invalidate_query_cache("SELECT 1")
    assert opt.get_cached_query_result("SELECT 1", params={}) is None

    opt.clear_query_cache()
    stats = opt.get_cache_statistics()
    assert "hits" in stats


def test_pattern_detection():
    opt = DatabaseQueryOptimizer()
    assert opt.identify_n_plus_one_pattern("SELECT * FROM users") is False
    assert opt.identify_missing_index_pattern("WHERE name LIKE '%x%'") is True
    assert (
        opt.identify_inefficient_join_pattern("SELECT a.id FROM a JOIN b ON a.id=b.id ORDER BY x")
        is True
    )


def test_cache_result_methods():
    opt = DatabaseQueryOptimizer()
    opt.cache_result("q1", [1, 2, 3], ttl=60)
    assert opt.get_cached_result("q1") == [1, 2, 3]
    opt.invalidate_cache("q1")
    assert opt.get_cached_result("q1") is None
    assert "hits" in opt.get_cache_stats()


def test_record_and_analyze():
    opt = DatabaseQueryOptimizer()
    opt.record_query_execution(
        query_id="q1",
        query_text="SELECT * FROM users",
        database="default",
        table_name="users",
        duration_ms=1500,
    )
    slow = opt.analyze_slow_queries()
    assert isinstance(slow, list)
    assert len(slow) == 1
    assert isinstance(opt.generate_optimizations(), list)
