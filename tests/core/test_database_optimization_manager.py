# -*- coding: utf-8 -*-
"""Tests for core/database_optimization_manager.py."""

from core.database_optimization_manager import (
    DatabaseOptimizationStatus,
    get_database_optimization_manager,
)


def test_database_optimization_status():
    status = DatabaseOptimizationStatus()
    assert status.query_optimization_enabled is False
    assert status.total_optimizations_applied == 0


def test_optimization_manager_singleton():
    mgr1 = get_database_optimization_manager()
    mgr2 = get_database_optimization_manager()
    assert mgr1 is mgr2
    status = mgr1.get_optimization_status()
    assert "query_optimization_enabled" in status


def test_record_and_recommendations():
    mgr = get_database_optimization_manager()
    mgr.record_query("SELECT 1", 10.0)
    recs = mgr.get_optimization_recommendations()
    assert isinstance(recs, list)


def test_run_comprehensive_optimization():
    mgr = get_database_optimization_manager()
    result = mgr.run_comprehensive_optimization()
    assert "timestamp" in result
    assert result["overall_status"] in ("complete", "partial", "failed")
