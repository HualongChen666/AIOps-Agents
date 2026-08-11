# -*- coding: utf-8 -*-
"""Tests for core/database_optimization_manager.py."""

from core.database_optimization_manager import (
    DatabaseOptimizationManager,
    get_database_optimization_manager,
)


def test_get_database_optimization_manager():
    mgr = get_database_optimization_manager()
    assert isinstance(mgr, DatabaseOptimizationManager)


def test_optimization_status_and_recommendations():
    mgr = DatabaseOptimizationManager()
    status = mgr.get_optimization_status()
    assert "query_optimization_enabled" in status
    recs = mgr.get_optimization_recommendations()
    assert isinstance(recs, list)


def test_analyze_and_optimize():
    mgr = DatabaseOptimizationManager()
    slow = mgr.analyze_slow_queries(limit=5)
    assert "slow_queries" in slow
    pool = mgr.optimize_connection_pool("default")
    assert "current_metrics" in pool or "error" in pool
    cache = mgr.setup_query_cache(120)
    assert cache["cache_enabled"] is True
    cache2 = mgr.setup_query_caching(120)
    assert cache2["setup_successful"] is True


def test_record_and_comprehensive():
    mgr = DatabaseOptimizationManager()
    mgr.record_query_execution("SELECT 1", 10.0, "default")
    mgr.record_query("SELECT 2", 20.0)
    result = mgr.run_comprehensive_optimization()
    assert "timestamp" in result
    assert "query_optimization" in result
