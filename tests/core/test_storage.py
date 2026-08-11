# -*- coding: utf-8 -*-
"""Unit tests for storage and database modules."""

import core.db_engine as db_engine
import core.db_optimization as db_optimization
import core.db_replication as db_replication
from core.db_query_optimization import BatchQueryOptimizer, QueryCache
from core.db_read_write_router import ReadWriteRouter
from core.storage.l4.storage_manager import get_l4_storage_manager


def test_db_engine_alert_functions():
    count = db_engine.count_alerts()
    assert isinstance(count, int)
    cleared = db_engine.clear_alerts()
    assert isinstance(cleared, int)


def test_db_optimization_functions():
    assert isinstance(db_optimization.is_db_optimization_enabled(), bool)
    summary = db_optimization.get_performance_summary()
    assert isinstance(summary, dict)
    suggestions = db_optimization.suggest_optimizations()
    assert isinstance(suggestions, list)


def test_query_cache():
    cache = QueryCache()
    cache.set("q1", "result")
    assert cache.get("q1") == "result"


def test_batch_query_optimizer():
    optimizer = BatchQueryOptimizer()
    assert optimizer is not None


def test_read_write_router():
    router = ReadWriteRouter()
    decision = router.route_query("SELECT * FROM users")
    assert decision is not None


def test_db_replication_status():
    status = db_replication.get_replication_status()
    assert isinstance(status, dict)


def test_l4_storage_manager():
    manager = get_l4_storage_manager()
    assert manager is None or hasattr(manager, "connect")
