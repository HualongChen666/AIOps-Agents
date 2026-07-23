# -*- coding: utf-8 -*-
"""Unit tests for database operation modules (task 10.3 coverage)."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from core.database_cache_optimizer import (
    CacheEntry,
    CacheInvalidationPolicy,
    CacheMetrics,
    CacheStrategy,
    DatabaseCacheOptimizer,
    get_database_cache_optimizer,
)
from core.database_connection_optimizer import (
    ConnectionStatus,
    DatabaseConnectionOptimizer,
    PoolStrategy,
    ReadWriteStrategy,
    TransactionIsolationLevel,
    TransactionMetrics,
    get_database_connection_optimizer,
)
from core.database_optimization_manager import (
    DatabaseOptimizationManager,
    get_database_optimization_manager,
)
from core.database_query_optimizer import (
    DatabaseQueryOptimizer,
    OptimizationPriority,
    QueryOptimizationType,
    get_database_query_optimizer,
)


class TestDatabaseCacheOptimizerCoverage:
    """Tests for database cache optimizer."""

    @pytest.mark.parametrize(
        "strategy",
        [
            CacheStrategy.LRU,
            CacheStrategy.LFU,
            CacheStrategy.TTL,
            CacheStrategy.WRITE_THROUGH,
            CacheStrategy.WRITE_BACK,
            CacheStrategy.WRITE_AROUND,
        ],
    )
    def test_get_cache_creates_cache_with_strategy(self, strategy):
        optimizer = DatabaseCacheOptimizer()
        cache = optimizer.get_cache("test_cache", strategy=strategy)
        assert cache is not None
        assert optimizer.get_cache("test_cache", strategy=strategy) is cache

    def test_create_cache_and_get_cache(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache(
            "my_cache", cache_size=10, strategy=CacheStrategy.LRU, ttl_seconds=60
        )
        assert "my_cache" in optimizer.caches
        assert optimizer.cache_configs["my_cache"]["size"] == 10
        assert optimizer.cache_configs["my_cache"]["ttl_seconds"] == 60

    def test_create_cache_existing(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("dup")
        optimizer.create_cache("dup")
        assert optimizer.caches["dup"] is not None

    def test_set_and_get(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.set("c", "SELECT * FROM a", ["data"])
        assert optimizer.get("c", "SELECT * FROM a") == ["data"]

    def test_get_cache_not_found(self):
        optimizer = DatabaseCacheOptimizer()
        assert optimizer.get("missing", "SELECT * FROM a") is None

    def test_set_cache_not_found(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.set("missing", "SELECT * FROM a", ["data"])
        assert "missing" not in optimizer.caches

    def test_get_expired_entry(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.set("c", "SELECT * FROM a", ["data"], ttl_seconds=-1)
        assert optimizer.get("c", "SELECT * FROM a") is None

    def test_get_with_params(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.set("c", "SELECT * FROM a", ["data"], params={"id": 1})
        assert optimizer.get("c", "SELECT * FROM a", params={"id": 1}) == ["data"]
        assert optimizer.get("c", "SELECT * FROM a") is None

    def test_invalidate_all(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.set("c", "SELECT * FROM a", ["data"])
        optimizer.set("c", "SELECT * FROM b", ["data2"])
        count = optimizer.invalidate("c")
        assert count == 2
        assert len(optimizer.caches["c"]) == 0

    def test_invalidate_specific(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.set("c", "SELECT * FROM a", ["data"])
        assert optimizer.invalidate("c", "SELECT * FROM a") == 1
        assert optimizer.get("c", "SELECT * FROM a") is None

    def test_invalidate_missing(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        assert optimizer.invalidate("c", "SELECT * FROM a") == 0

    def test_invalidate_cache_not_found(self):
        optimizer = DatabaseCacheOptimizer()
        assert optimizer.invalidate("missing") == 0

    def test_evict_oldest_lru(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c", cache_size=2)
        optimizer.set("c", "q1", "v1")
        optimizer.set("c", "q2", "v2")
        optimizer.set("c", "q3", "v3")
        assert len(optimizer.caches["c"]) == 2

    def test_evict_oldest_lfu(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c", cache_size=2, strategy=CacheStrategy.LFU)
        optimizer.set("c", "q1", "v1")
        optimizer.set("c", "q2", "v2")
        optimizer.get("c", "q1")  # access q1
        optimizer.set("c", "q3", "v3")
        assert len(optimizer.caches["c"]) == 2

    def test_evict_oldest_ttl(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c", cache_size=2, strategy=CacheStrategy.TTL)
        optimizer.set("c", "q1", "v1")
        optimizer.set("c", "q2", "v2")
        optimizer.set("c", "q3", "v3")
        assert len(optimizer.caches["c"]) == 2

    def test_cleanup_expired_entries(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.set("c", "q1", "v1", ttl_seconds=-1)
        count = optimizer.cleanup_expired_entries("c")
        assert count == 1

    def test_cleanup_expired_cache_not_found(self):
        optimizer = DatabaseCacheOptimizer()
        assert optimizer.cleanup_expired_entries("missing") == 0

    def test_get_cache_metrics(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.set("c", "q1", "v1")
        optimizer.get("c", "q1")
        metrics = optimizer.get_cache_metrics("c")
        assert metrics is not None
        assert metrics.cache_name == "c"
        assert metrics.hit_count >= 1

    def test_get_cache_metrics_not_found(self):
        optimizer = DatabaseCacheOptimizer()
        assert optimizer.get_cache_metrics("missing") is None

    def test_get_all_cache_metrics(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c1")
        optimizer.create_cache("c2")
        optimizer.set("c1", "q", "v")
        metrics = optimizer.get_all_cache_metrics()
        assert "c1" in metrics
        assert "c2" in metrics

    def test_optimize_cache_size_increase(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c", cache_size=10)
        optimizer.get("c", "q1")
        result = optimizer.optimize_cache_size("c", target_hit_rate=0.9)
        assert result["recommendations"][0]["type"] == "increase_size"

    def test_optimize_cache_size_decrease(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c", cache_size=10)
        optimizer.set("c", "q", "v")
        optimizer.get("c", "q")
        result = optimizer.optimize_cache_size("c", target_hit_rate=0.1)
        assert result["recommendations"][0]["type"] == "decrease_size"

    def test_optimize_cache_size_no_change(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c", cache_size=10)
        optimizer.set("c", "q", "v")
        optimizer.get("c", "q")
        result = optimizer.optimize_cache_size("c", target_hit_rate=0.9)
        assert result["recommendations"][0]["type"] == "no_change"

    def test_optimize_cache_size_not_found(self):
        optimizer = DatabaseCacheOptimizer()
        assert "error" in optimizer.optimize_cache_size("missing")

    def test_preload_cache_with_dict(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        count = optimizer.preload_cache("c", {"k1": "v1", "k2": "v2"})
        assert count == 2

    def test_preload_cache_with_loader(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.add_preload_query("c", "SELECT * FROM a", params={"id": 1})

        def loader(query, params):
            return {"query": query, "params": params}

        count = optimizer.preload_cache("c", loader)
        assert count == 1
        assert optimizer.get("c", "SELECT * FROM a", params={"id": 1})["query"] == "SELECT * FROM a"

    def test_preload_cache_with_loader_exception(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.add_preload_query("c", "SELECT * FROM a")

        def loader(query, params):
            raise RuntimeError("boom")

        count = optimizer.preload_cache("c", loader)
        assert count == 0

    def test_add_preload_query(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.add_preload_query("c", "SELECT * FROM a", params={"id": 1}, priority=5)
        assert len(optimizer.preload_queries["c"]) == 1

    def test_get_statistics(self):
        optimizer = DatabaseCacheOptimizer()
        optimizer.create_cache("c")
        optimizer.set("c", "q", "v")
        stats = optimizer.get_statistics()
        assert stats["total_caches"] == 1
        assert stats["total_cache_hits"] == 0

    def test_get_stats_alias(self):
        optimizer = DatabaseCacheOptimizer()
        assert "total_caches" in optimizer.get_stats()

    def test_factory_get_database_cache_optimizer(self):
        optimizer = get_database_cache_optimizer({"default_cache_size": 50})
        assert optimizer is not None
        assert optimizer.default_cache_size == 50


class TestCacheEntryCoverage:
    """Tests for CacheEntry and CacheMetrics."""

    @pytest.mark.parametrize(
        "ttl,expected",
        [
            (None, False),
            (-1, True),
            (3600, False),
        ],
    )
    def test_cache_entry_is_expired(self, ttl, expected):
        entry = CacheEntry(cache_key="k", data="v", ttl_seconds=ttl)
        assert entry.is_expired() is expected

    def test_cache_entry_touch(self):
        entry = CacheEntry(cache_key="k", data="v")
        before = entry.last_accessed
        before_count = entry.access_count
        entry.touch()
        assert entry.last_accessed >= before
        assert entry.access_count == before_count + 1

    def test_cache_metrics_hits_and_misses(self):
        metrics = CacheMetrics(cache_name="c")
        assert metrics.hits == metrics.hit_count
        assert metrics.misses == metrics.miss_count

    @pytest.mark.parametrize(
        "policy",
        [
            CacheInvalidationPolicy.TIME_BASED,
            CacheInvalidationPolicy.EVENT_BASED,
            CacheInvalidationPolicy.MANUAL,
            CacheInvalidationPolicy.HYBRID,
        ],
    )
    def test_cache_invalidation_policy_values(self, policy):
        assert policy.value is not None

    @pytest.mark.parametrize(
        "strategy",
        [
            CacheStrategy.LRU,
            CacheStrategy.LFU,
            CacheStrategy.TTL,
            CacheStrategy.WRITE_THROUGH,
            CacheStrategy.WRITE_BACK,
            CacheStrategy.WRITE_AROUND,
        ],
    )
    def test_cache_strategy_values(self, strategy):
        assert strategy.value is not None


class TestDatabaseConnectionOptimizerCoverage:
    """Tests for database connection optimizer."""

    def test_create_pool_fixed(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=2, strategy=PoolStrategy.FIXED)
        assert len(optimizer.pools["p"]["connections"]) == 2

    def test_create_pool_dynamic(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=2, strategy=PoolStrategy.DYNAMIC)
        assert len(optimizer.pools["p"]["connections"]) == 0

    def test_create_pool_existing(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p")
        optimizer.create_pool("p")
        assert len(optimizer.pools["p"]["connections"]) == 20

    def test_get_connection_no_pool(self):
        optimizer = DatabaseConnectionOptimizer()
        assert optimizer.get_connection("missing") is None

    def test_get_connection_overflow(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=1, max_overflow=1, strategy=PoolStrategy.FIXED)
        conn1 = optimizer.get_connection("p")
        assert conn1 is not None
        conn2 = optimizer.get_connection("p")
        assert conn2 is not None
        conn3 = optimizer.get_connection("p")
        assert conn3 is None
        assert len(optimizer.pools["p"]["waiting_queue"]) == 1

    def test_release_connection(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=1, strategy=PoolStrategy.FIXED)
        conn = optimizer.get_connection("p")
        optimizer.release_connection("p", conn, query_duration_ms=10.0)
        assert optimizer.connection_metrics[conn].status == ConnectionStatus.IDLE

    def test_release_connection_not_found(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p")
        optimizer.release_connection("p", "missing_conn")

    def test_close_connection(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=1, strategy=PoolStrategy.FIXED)
        conn = optimizer.get_connection("p")
        optimizer.close_connection("p", conn)
        assert conn not in optimizer.connection_metrics

    def test_close_connection_not_found(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p")
        optimizer.close_connection("p", "missing_conn")
        optimizer.close_connection("missing", "missing_conn")

    def test_recycle_old_connections(self):
        optimizer = DatabaseConnectionOptimizer({"pool_recycle_seconds": -1})
        optimizer.create_pool("p", pool_size=1, strategy=PoolStrategy.FIXED)
        count = optimizer.recycle_old_connections("p")
        assert count == 1
        assert len(optimizer.pools["p"]["connections"]) == 0

    def test_get_pool_metrics(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=2, strategy=PoolStrategy.FIXED)
        metrics = optimizer.get_pool_metrics("p")
        assert metrics is not None
        assert metrics.total_connections == 2

    def test_get_pool_metrics_no_pool(self):
        optimizer = DatabaseConnectionOptimizer()
        assert optimizer.get_pool_metrics("missing") is None

    def test_optimize_pool_size_increase(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=1, max_overflow=1, strategy=PoolStrategy.FIXED)
        optimizer.get_connection("p")
        optimizer.get_connection("p")
        optimizer.get_connection("p")  # adds to waiting queue
        optimizer.get_pool_metrics("p")
        result = optimizer.optimize_pool_size("p")
        assert result["recommendations"][0]["type"] == "increase_pool_size"

    def test_optimize_pool_size_decrease(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=2, strategy=PoolStrategy.FIXED)
        optimizer.get_pool_metrics("p")
        result = optimizer.optimize_pool_size("p")
        assert result["recommendations"][0]["type"] == "decrease_pool_size"

    def test_optimize_pool_size_no_change(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=2, max_overflow=0, strategy=PoolStrategy.FIXED)
        optimizer.get_connection("p")
        optimizer.get_pool_metrics("p")
        result = optimizer.optimize_pool_size("p")
        assert result["recommendations"][0]["type"] == "no_change"

    def test_optimize_pool_size_no_pool(self):
        optimizer = DatabaseConnectionOptimizer()
        result = optimizer.optimize_pool_size("missing")
        assert "error" in result

    def test_optimize_pool_size_no_history(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p")
        result = optimizer.optimize_pool_size("p")
        assert "error" in result

    def test_monitor_connection_health_healthy(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=1, strategy=PoolStrategy.FIXED)
        health = optimizer.monitor_connection_health("p")
        assert health["status"] == "healthy"

    def test_monitor_connection_health_warning(self):
        optimizer = DatabaseConnectionOptimizer({"pool_recycle_seconds": -1})
        optimizer.create_pool("p", pool_size=1, strategy=PoolStrategy.FIXED)
        health = optimizer.monitor_connection_health("p")
        assert health["status"] == "warning"
        assert "Recycle stale connections" in health["recommendations"]

    def test_monitor_connection_health_critical(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=1, strategy=PoolStrategy.FIXED)
        conn = optimizer.get_connection("p")
        optimizer.connection_metrics[conn].status = ConnectionStatus.ERROR
        health = optimizer.monitor_connection_health("p")
        assert health["status"] == "critical"

    def test_get_pool_stats(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=1, strategy=PoolStrategy.FIXED)
        stats = optimizer.get_pool_stats("p")
        assert stats["total_connections"] == 1

    def test_get_pool_stats_no_pool(self):
        optimizer = DatabaseConnectionOptimizer()
        stats = optimizer.get_pool_stats("missing")
        assert stats["total_connections"] == 0

    def test_check_pool_health(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p")
        assert "status" in optimizer.check_pool_health("p")

    def test_configure_read_write_splitting(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.configure_read_write_splitting(
            primary="primary_db",
            replicas=["replica1"],
            strategy="round_robin",
        )
        assert optimizer.primary_pool_name == "primary_db"
        assert "replica1" in optimizer.replicas
        assert optimizer.read_write_strategy == ReadWriteStrategy.ROUND_ROBIN

    def test_configure_read_write_splitting_invalid_strategy(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.configure_read_write_splitting(
            primary="primary_db",
            replicas=["replica1"],
            strategy="invalid",
        )
        assert optimizer.read_write_strategy == ReadWriteStrategy.PRIMARY_REPLICA

    @pytest.mark.parametrize(
        "strategy",
        [
            ReadWriteStrategy.NONE,
            ReadWriteStrategy.PRIMARY_ONLY,
            ReadWriteStrategy.PRIMARY_REPLICA,
            ReadWriteStrategy.ROUND_ROBIN,
            ReadWriteStrategy.WEIGHTED,
        ],
    )
    def test_get_read_connection_strategies(self, strategy):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.configure_read_write_splitting(
            primary="primary_db",
            replicas=["replica1"],
            strategy=strategy.value,
        )
        conn = optimizer.get_read_connection("select")
        assert conn is not None

    def test_get_read_connection_write_operation(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.configure_read_write_splitting(
            primary="primary_db",
            replicas=["replica1"],
        )
        conn = optimizer.get_read_connection("insert")
        assert conn is not None

    def test_get_write_connection(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.configure_read_write_splitting(
            primary="primary_db",
            replicas=["replica1"],
        )
        conn = optimizer.get_write_connection()
        assert conn is not None

    def test_add_replica_config(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("primary_db")
        optimizer.add_replica_config(
            replica_id="replica1",
            host="host1",
            port=5432,
            database="db1",
            is_primary=False,
            lag_ms=100,
        )
        assert "replica1" in optimizer.replicas
        assert optimizer.replica_pools["replica1"] == "replica_replica1"

    def test_add_replica_config_primary(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.add_replica_config(
            replica_id="primary",
            host="host1",
            port=5432,
            database="db1",
            is_primary=True,
        )
        assert optimizer.primary_pool_name == "replica_primary"

    def test_begin_transaction(self):
        optimizer = DatabaseConnectionOptimizer()
        txn_id = optimizer.begin_transaction()
        assert txn_id is not None
        assert txn_id in optimizer.active_transactions

    def test_begin_transaction_isolation(self):
        optimizer = DatabaseConnectionOptimizer()
        txn_id = optimizer.begin_transaction(isolation_level=TransactionIsolationLevel.SERIALIZABLE)
        assert (
            optimizer.active_transactions[txn_id].isolation_level
            == TransactionIsolationLevel.SERIALIZABLE
        )

    def test_get_transaction_stats(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.begin_transaction()
        stats = optimizer.get_transaction_stats()
        assert stats["active_transactions"] == 1

    def test_get_transaction_stats_with_history(self):
        optimizer = DatabaseConnectionOptimizer()
        txn = TransactionMetrics(
            transaction_id="txn_1",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            duration_ms=10.0,
            status="committed",
        )
        optimizer.transaction_history.append(txn)
        stats = optimizer.get_transaction_stats()
        assert stats["total_transactions"] == 1
        assert stats["committed"] == 1
        assert stats["success_rate"] == 100.0

    def test_monitor_replication_lag(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.add_replica_config(
            replica_id="r1", host="h1", port=5432, database="d1", lag_ms=100
        )
        optimizer.add_replica_config(
            replica_id="r2", host="h2", port=5432, database="d1", lag_ms=5001
        )
        status = optimizer.monitor_replication_lag()
        assert status["healthy"] is False
        assert status["max_lag_ms"] == 5001

    def test_create_connection_pool(self):
        optimizer = DatabaseConnectionOptimizer()
        pool = optimizer.create_connection_pool("p", "postgresql://localhost/db", pool_size=2)
        assert pool is not None
        assert pool["name"] == "p"

    def test_get_statistics(self):
        optimizer = DatabaseConnectionOptimizer()
        optimizer.create_pool("p", pool_size=2, strategy=PoolStrategy.FIXED)
        stats = optimizer.get_statistics()
        assert stats["total_pools"] == 1
        assert stats["total_connections"] == 2

    def test_get_database_connection_optimizer(self):
        optimizer = get_database_connection_optimizer({"default_pool_size": 5})
        assert optimizer is not None
        assert optimizer.default_pool_size == 5

    @pytest.mark.parametrize(
        "status",
        [
            ConnectionStatus.IDLE,
            ConnectionStatus.ACTIVE,
            ConnectionStatus.CHECKED_OUT,
            ConnectionStatus.CLOSED,
            ConnectionStatus.ERROR,
        ],
    )
    def test_connection_status_values(self, status):
        assert status.value is not None

    @pytest.mark.parametrize(
        "strategy",
        [
            PoolStrategy.FIXED,
            PoolStrategy.DYNAMIC,
            PoolStrategy.ADAPTIVE,
            PoolStrategy.SIMPLE,
            PoolStrategy.PRE_PING,
            PoolStrategy.RECYCLE,
        ],
    )
    def test_pool_strategy_values(self, strategy):
        assert strategy.value is not None

    @pytest.mark.parametrize(
        "strategy",
        [
            ReadWriteStrategy.NONE,
            ReadWriteStrategy.PRIMARY_REPLICA,
            ReadWriteStrategy.PRIMARY_ONLY,
            ReadWriteStrategy.ROUND_ROBIN,
            ReadWriteStrategy.WEIGHTED,
            ReadWriteStrategy.GEOGRAPHICAL,
        ],
    )
    def test_read_write_strategy_values(self, strategy):
        assert strategy.value is not None

    @pytest.mark.parametrize(
        "level",
        [
            TransactionIsolationLevel.READ_UNCOMMITTED,
            TransactionIsolationLevel.READ_COMMITTED,
            TransactionIsolationLevel.REPEATABLE_READ,
            TransactionIsolationLevel.SERIALIZABLE,
        ],
    )
    def test_transaction_isolation_level_values(self, level):
        assert level.value is not None


class TestDatabaseQueryOptimizerCoverage:
    """Tests for database query optimizer."""

    def test_analyze_query_performance(self):
        optimizer = DatabaseQueryOptimizer()
        result = optimizer.analyze_query_performance(
            "SELECT * FROM alerts WHERE level = 'critical'", 100
        )
        assert result["duration_ms"] == 100
        assert result["pattern"] == "select_star"

    def test_analyze_query_performance_not_slow(self):
        optimizer = DatabaseQueryOptimizer()
        result = optimizer.analyze_query_performance(
            "SELECT * FROM alerts WHERE level = 'critical'", 10
        )
        assert result["duration_ms"] == 10
        assert result["pattern"] == "select_star"

    def test_record_query_execution(self):
        optimizer = DatabaseQueryOptimizer()
        optimizer.record_query_execution(
            query_id="q1",
            query_text="SELECT * FROM alerts WHERE level LIKE '%c%'",
            database="db",
            table_name="alerts",
            duration_ms=100.0,
        )
        assert "q1" in optimizer.slow_queries
        assert optimizer.total_queries_analyzed == 1

    def test_record_query_execution_update_existing(self):
        optimizer = DatabaseQueryOptimizer()
        optimizer.record_query_execution(
            query_id="q1",
            query_text="SELECT * FROM alerts WHERE level LIKE '%c%'",
            database="db",
            table_name="alerts",
            duration_ms=100.0,
        )
        optimizer.record_query_execution(
            query_id="q1",
            query_text="SELECT * FROM alerts WHERE level LIKE '%c%'",
            database="db",
            table_name="alerts",
            duration_ms=200.0,
        )
        assert optimizer.slow_queries["q1"].execution_count == 1
        assert optimizer.slow_queries["q1"].avg_duration_ms == 300.0

    def test_analyze_slow_queries(self):
        optimizer = DatabaseQueryOptimizer({"slow_query_threshold_ms": 10})
        optimizer.record_query_execution(
            query_id="q1",
            query_text="SELECT * FROM alerts WHERE level LIKE '%c%'",
            database="db",
            table_name="alerts",
            duration_ms=100.0,
        )
        slow = optimizer.analyze_slow_queries()
        assert len(slow) == 1

    def test_generate_optimizations(self):
        optimizer = DatabaseQueryOptimizer({"slow_query_threshold_ms": 10})
        optimizer.record_query_execution(
            query_id="q1",
            query_text="SELECT id FROM alerts WHERE level LIKE '%c%' AND status = 'ok'",
            database="db",
            table_name="alerts",
            duration_ms=100.0,
        )
        opts = optimizer.generate_optimizations()
        assert len(opts) == 1
        assert opts[0].optimization_type == QueryOptimizationType.INDEX_ADDITION

    def test_generate_optimizations_no_slow(self):
        optimizer = DatabaseQueryOptimizer()
        opts = optimizer.generate_optimizations()
        assert opts == []

    def test_get_query_analysis(self):
        optimizer = DatabaseQueryOptimizer({"slow_query_threshold_ms": 10})
        optimizer.record_query_execution(
            query_id="q1",
            query_text="SELECT * FROM alerts WHERE level LIKE '%c%'",
            database="db",
            table_name="alerts",
            duration_ms=100.0,
        )
        analysis = optimizer.get_query_analysis("q1")
        assert analysis is not None
        assert analysis["query_id"] == "q1"

    def test_get_query_analysis_not_found(self):
        optimizer = DatabaseQueryOptimizer()
        assert optimizer.get_query_analysis("missing") is None

    def test_get_statistics(self):
        optimizer = DatabaseQueryOptimizer()
        optimizer.record_query_execution(
            query_id="q1",
            query_text="SELECT * FROM a",
            database="db",
            table_name="a",
            duration_ms=10.0,
        )
        stats = optimizer.get_statistics()
        assert stats["total_queries_analyzed"] == 1

    @pytest.mark.parametrize(
        "query,expected",
        [
            ("SELECT * FROM alerts", "select_star"),
            ("SELECT id FROM alerts WHERE level LIKE '%c%'", "missing_index"),
            (
                "SELECT a.id FROM alerts a JOIN repairs r ON a.id = r.id ORDER BY a.id",
                "inefficient_join",
            ),
            (
                (
                    "SELECT id FROM departments WHERE EXISTS (SELECT 1 FROM employees WHERE dept_id"
                    " = id)"
                ),
                "subquery",
            ),
            ("SELECT id FROM alerts", "unknown"),
        ],
    )
    def test_classify_query_pattern(self, query, expected):
        optimizer = DatabaseQueryOptimizer()
        assert optimizer.classify_query_pattern(query) == expected
        assert optimizer._classify_query_pattern(query) == expected

    def test_identify_indexable_columns(self):
        optimizer = DatabaseQueryOptimizer()
        cols = optimizer._identify_indexable_columns(
            "SELECT id FROM alerts WHERE level LIKE '%c%' AND status = 'ok' ORDER BY created_at"
        )
        assert "status" in cols
        assert "created_at" in cols

    def test_rewrite_with_joins(self):
        optimizer = DatabaseQueryOptimizer()
        result = optimizer._rewrite_with_joins("SELECT * FROM a")
        assert "Optimized with joins" in result

    def test_rewrite_join(self):
        optimizer = DatabaseQueryOptimizer()
        result = optimizer._rewrite_join("SELECT * FROM a")
        assert "Optimized join" in result

    def test_replace_select_star(self):
        optimizer = DatabaseQueryOptimizer()
        result = optimizer._replace_select_star("SELECT * FROM alerts")
        assert "SELECT id, created_at, updated_at" in result

    def test_rewrite_subquery(self):
        optimizer = DatabaseQueryOptimizer()
        result = optimizer._rewrite_subquery("SELECT * FROM a")
        assert result == "SELECT * FROM a"

    def test_cache_query_result_and_get(self):
        optimizer = DatabaseQueryOptimizer()
        optimizer.cache_query_result("SELECT * FROM a", [{"id": 1}], ttl_seconds=300)
        result = optimizer.get_cached_query_result("SELECT * FROM a")
        assert result == [{"id": 1}]

    def test_cache_result_disabled(self):
        optimizer = DatabaseQueryOptimizer({"cache_enabled": False})
        optimizer.cache_query_result("SELECT * FROM a", [{"id": 1}])
        assert optimizer.get_cached_query_result("SELECT * FROM a") is None

    def test_invalidate_query_cache(self):
        optimizer = DatabaseQueryOptimizer()
        optimizer.cache_query_result("SELECT * FROM a", [{"id": 1}])
        assert optimizer.invalidate_query_cache("SELECT * FROM a") == 1
        assert optimizer.get_cached_query_result("SELECT * FROM a") is None

    def test_invalidate_query_cache_pattern(self):
        optimizer = DatabaseQueryOptimizer()
        optimizer.cache_query_result("SELECT * FROM a", [{"id": 1}])
        optimizer.cache_query_result("SELECT * FROM b", [{"id": 2}])
        optimizer.l2_redis_client = MagicMock()
        optimizer.l2_redis_client.keys.return_value = ["db_query:one"]
        optimizer.l2_redis_client.delete.return_value = 1
        assert optimizer.invalidate_query_cache(pattern="db_query:*") == 1

    def test_clear_query_cache(self):
        optimizer = DatabaseQueryOptimizer()
        optimizer.cache_query_result("SELECT * FROM a", [{"id": 1}])
        optimizer.clear_query_cache()
        assert optimizer.get_cached_query_result("SELECT * FROM a") is None

    def test_get_cache_statistics(self):
        optimizer = DatabaseQueryOptimizer()
        optimizer.cache_query_result("SELECT * FROM a", [{"id": 1}])
        optimizer.get_cached_query_result("SELECT * FROM a")
        stats = optimizer.get_cache_statistics()
        assert stats["enabled"] is True
        assert stats["hits"] >= 1

    def test_generate_optimization_recommendations(self):
        optimizer = DatabaseQueryOptimizer({"slow_query_threshold_ms": 10})
        optimizer.record_query_execution(
            query_id="q1",
            query_text="SELECT * FROM alerts WHERE level LIKE '%c%'",
            database="db",
            table_name="alerts",
            duration_ms=100.0,
        )
        recommendations = optimizer.generate_optimization_recommendations()
        assert len(recommendations) == 1

    def test_generate_optimization_recommendations_no_query(self):
        optimizer = DatabaseQueryOptimizer()
        recommendations = optimizer.generate_optimization_recommendations()
        assert recommendations == []

    def test_get_database_query_optimizer(self):
        optimizer = get_database_query_optimizer({"slow_query_threshold_ms": 500})
        assert optimizer is not None
        assert optimizer.slow_query_threshold_ms == 500

    @pytest.mark.parametrize(
        "opt_type",
        [
            QueryOptimizationType.INDEX_ADDITION,
            QueryOptimizationType.QUERY_REWRITE,
            QueryOptimizationType.NPLUS_ONE_FIX,
            QueryOptimizationType.JOIN_OPTIMIZATION,
            QueryOptimizationType.SUBQUERY_OPTIMIZATION,
            QueryOptimizationType.CACHING_STRATEGY,
        ],
    )
    def test_query_optimization_type_values(self, opt_type):
        assert opt_type.value is not None

    @pytest.mark.parametrize(
        "priority",
        [
            OptimizationPriority.CRITICAL,
            OptimizationPriority.HIGH,
            OptimizationPriority.MEDIUM,
            OptimizationPriority.LOW,
        ],
    )
    def test_optimization_priority_values(self, priority):
        assert priority.value is not None


class TestDatabaseOptimizationManagerCoverage:
    """Tests for database optimization manager."""

    def test_get_optimization_status(self):
        manager = DatabaseOptimizationManager()
        status = manager.get_optimization_status()
        assert "query_optimization_enabled" in status

    def test_get_optimization_recommendations(self):
        manager = DatabaseOptimizationManager()
        recs = manager.get_optimization_recommendations()
        assert isinstance(recs, list)

    def test_record_query_execution(self):
        manager = DatabaseOptimizationManager()
        manager.record_query_execution(
            query_text="SELECT * FROM a", duration_ms=100.0, database="db", table_name="a"
        )

    def test_record_query(self):
        manager = DatabaseOptimizationManager()
        manager.record_query("SELECT * FROM a", 100.0)

    def test_analyze_slow_queries(self):
        manager = DatabaseOptimizationManager()
        manager.record_query("SELECT * FROM a", 100.0)
        result = manager.analyze_slow_queries()
        assert "slow_queries_count" in result

    def test_optimize_connection_pool(self):
        manager = DatabaseOptimizationManager()
        result = manager.optimize_connection_pool("missing")
        assert "current_metrics" in result

    def test_setup_query_cache(self):
        manager = DatabaseOptimizationManager()
        result = manager.setup_query_cache(300)
        assert result["cache_enabled"] is True

    def test_setup_query_caching(self):
        manager = DatabaseOptimizationManager()
        result = manager.setup_query_caching(300)
        assert result["cache_enabled"] is True

    def test_run_comprehensive_optimization(self):
        manager = DatabaseOptimizationManager()
        result = manager.run_comprehensive_optimization()
        assert result["overall_status"] in {"complete", "partial", "failed"}

    def test_get_database_optimization_manager(self):
        manager = get_database_optimization_manager()
        manager2 = get_database_optimization_manager()
        assert manager is manager2
