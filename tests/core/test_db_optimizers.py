# -*- coding: utf-8 -*-
"""Tests for db_optimization and database_*_optimizer modules."""

import pytest

import core.database_cache_optimizer
import core.database_connection_optimizer
import core.database_query_optimizer
import core.db_optimization


def test_db_optimization_validation():
    assert core.db_optimization.validate_sql_identifier("alerts") == "alerts"
    assert core.db_optimization.validate_table_name("alerts") == "alerts"
    assert core.db_optimization.validate_sql_query_structure("SELECT * FROM alerts") is True
    with pytest.raises(ValueError):
        core.db_optimization.validate_sql_identifier("DROP")
    with pytest.raises(ValueError):
        core.db_optimization.validate_sql_query_structure("; DROP TABLE alerts")


def test_db_optimization_state():
    core.db_optimization.reset_query_cache()
    core.db_optimization.clear_slow_queries()
    core.db_optimization.configure_db_optimization({"enabled": True, "level": 3})
    assert core.db_optimization.is_db_optimization_enabled() is True
    assert core.db_optimization.get_db_optimization_config()["level"] == 3

    core.db_optimization.record_query_cache_hit("q1")
    stats = core.db_optimization.get_query_cache_statistics()
    assert stats["hits"] == 1
    core.db_optimization.record_query_cache_miss("q2")
    assert core.db_optimization.get_query_cache_statistics()["misses"] == 1

    core.db_optimization.record_connection_pool_usage(20, 5)
    pool_stats = core.db_optimization.get_connection_pool_statistics()
    assert pool_stats["active_connections"] == 5

    core.db_optimization.record_slow_query("SELECT 1", 9999.0)
    assert len(core.db_optimization.get_slow_queries()) == 1

    summary = core.db_optimization.get_performance_summary()
    assert "cache_hit_rate" in summary

    suggestions = core.db_optimization.suggest_optimizations()
    assert isinstance(suggestions, list)

    core.db_optimization.reset_query_cache()
    assert core.db_optimization.get_query_cache_statistics()["hits"] == 0


def test_database_cache_optimizer():
    optimizer = core.database_cache_optimizer.get_database_cache_optimizer()
    cache = optimizer.get_cache("test")
    cache.set("k", 123)
    assert cache.get("k") == 123
    assert cache.get("missing") is None
    assert optimizer.get_statistics() is not None


def test_database_connection_optimizer():
    optimizer = core.database_connection_optimizer.get_database_connection_optimizer()
    optimizer.create_pool("test_pool", pool_size=2)
    metrics = optimizer.get_pool_metrics("test_pool")
    assert metrics is not None
    assert metrics.total_connections == 2
    conn = optimizer.get_connection("test_pool")
    assert conn is not None


def test_database_query_optimizer():
    optimizer = core.database_query_optimizer.DatabaseQueryOptimizer()
    assert optimizer.classify_query_pattern("SELECT * FROM users") != "unknown"
    stats = optimizer.get_cache_statistics()
    assert isinstance(stats, dict)
    analysis = optimizer.analyze_query_performance("SELECT * FROM users", 10.0)
    assert "pattern" in analysis
