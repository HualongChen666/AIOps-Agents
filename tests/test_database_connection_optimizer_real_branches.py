# -*- coding: utf-8 -*-
"""Real-branch coverage tests for core/database_connection_optimizer.py.

These tests exercise the optimizer with real object instantiations and safe
sqlite database URLs (``sqlite:///:memory:``) without mocks or stubs.
"""

import sqlite3
import time  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta, timezone

from core.database_connection_optimizer import (
    ConnectionStatus,
    DatabaseConnectionOptimizer,
    PoolStrategy,
    ReadWriteStrategy,
    ReplicaConfig,
    TransactionIsolationLevel,
    TransactionMetrics,
    _begin_transaction,
    _commit_transaction,
    _get_transaction_stats,
    _rollback_transaction,
    add_replica_config,
    begin_transaction,
    check_pool_health,
    commit_transaction,
    configure_read_write_splitting,
    create_connection_pool,
    get_database_connection_optimizer,
    get_pool_stats,
    get_read_connection,
    get_transaction_stats,
    get_write_connection,
    monitor_replication_lag,
    rollback_transaction,
)

SAFE_SQLITE_URL = "sqlite:///:memory:"


def _sqlite_conn():
    """Open a real, safe sqlite connection and return it."""
    return sqlite3.connect(":memory:")


def test_get_database_connection_optimizer_real():
    opt = get_database_connection_optimizer({"default_pool_size": 10})
    assert isinstance(opt, DatabaseConnectionOptimizer)
    assert opt.default_pool_size == 10


def test_create_pool_non_fixed_strategy_and_duplicate():
    """Non-FIXED strategies skip pre-creation; duplicate pool names warn."""
    opt = DatabaseConnectionOptimizer()
    create_connection_pool(opt, "dynamic", url=SAFE_SQLITE_URL, strategy=PoolStrategy.DYNAMIC)
    assert "dynamic" in opt.pools
    assert opt.pools["dynamic"]["connections"] == []

    create_connection_pool(opt, "simple", url=SAFE_SQLITE_URL, strategy=PoolStrategy.SIMPLE)
    assert opt.pools["simple"]["connections"] == []

    # Duplicate pool creation branch (warn and return)
    create_connection_pool(opt, "dynamic", url=SAFE_SQLITE_URL)
    assert opt.pools["dynamic"]["strategy"] == PoolStrategy.DYNAMIC


def test_release_connection_various_branches():
    opt = DatabaseConnectionOptimizer()
    create_connection_pool(opt, "primary", url=SAFE_SQLITE_URL)

    # Missing pool branch
    opt.release_connection("missing", "foo")

    # Connection not found branch
    opt.release_connection("primary", "nonexistent")

    # Release with query duration and waiting queue processing
    create_connection_pool(opt, "rel", url=SAFE_SQLITE_URL, pool_size=1)
    opt.pools["rel"]["max_overflow"] = 0
    conn = opt.get_connection("rel")
    _ = opt.get_connection("rel")  # adds to waiting queue
    opt.release_connection("rel", conn, query_duration_ms=5.0)
    assert conn in opt.connection_metrics
    assert len(opt.pools["rel"]["waiting_queue"]) == 0


def test_close_connection_various_branches():
    opt = DatabaseConnectionOptimizer()
    create_connection_pool(opt, "pool1", url=SAFE_SQLITE_URL, pool_size=1)
    create_connection_pool(opt, "pool2", url=SAFE_SQLITE_URL, pool_size=1)
    conn2 = opt.get_connection("pool2")
    assert conn2 is not None

    # Missing pool branch
    opt.close_connection("missing", "foo")

    # Connection exists in metrics but not in the named pool branch
    opt.close_connection("pool1", conn2)
    assert conn2 not in opt.connection_metrics

    # Connection not found in metrics branch
    opt.close_connection("pool1", "not_a_conn")


def test_recycle_old_connections_various_branches():
    opt = DatabaseConnectionOptimizer()
    create_connection_pool(opt, "primary", url=SAFE_SQLITE_URL, pool_size=2)
    conn1 = opt.get_connection("primary")
    conn2 = opt.get_connection("primary")
    opt.release_connection("primary", conn1)
    opt.release_connection("primary", conn2)

    # Make one connection old enough to recycle, leave the other fresh.
    metrics = opt.connection_metrics[conn1]
    metrics.created_at = datetime.now(timezone.utc) - timedelta(
        seconds=opt.pool_recycle_seconds + 1
    )

    recycled = opt.recycle_old_connections("primary")
    assert recycled == 1
    assert conn1 not in opt.connection_metrics
    assert conn2 in opt.connection_metrics

    # Missing pool returns 0
    assert opt.recycle_old_connections("missing") == 0


def test_get_pool_metrics_active_and_missing():
    """Exercise active connection branch and missing-pool return."""
    opt = DatabaseConnectionOptimizer()
    create_connection_pool(opt, "primary", url=SAFE_SQLITE_URL, pool_size=2)
    conn = opt.get_connection("primary")
    metrics = opt.get_pool_metrics("primary")
    assert metrics is not None
    assert metrics.active_connections == 1
    assert metrics.idle_connections == 1
    opt.release_connection("primary", conn)

    assert opt.get_pool_metrics("missing") is None


def test_optimize_pool_size_branches():
    opt = DatabaseConnectionOptimizer()

    # Missing pool
    assert opt.optimize_pool_size("missing") == {"error": "Pool not found"}

    # No historical data
    create_connection_pool(opt, "nohist", url=SAFE_SQLITE_URL)
    assert opt.optimize_pool_size("nohist") == {"error": "No historical data available"}

    # High waiting -> increase_pool_size
    create_connection_pool(opt, "busy", url=SAFE_SQLITE_URL, pool_size=1, max_overflow=0)
    # The source treats a max_overflow of 0 as the default, so force it to 0
    # directly on the pool to exercise the waiting queue.
    opt.pools["busy"]["max_overflow"] = 0
    _ = opt.get_connection("busy")
    _ = opt.get_connection("busy")  # adds to waiting queue
    opt.get_pool_metrics("busy")  # record waiting > 0
    rec = opt.optimize_pool_size("busy")
    assert rec["recommendations"][0]["type"] == "increase_pool_size"

    # Underutilized -> decrease_pool_size
    opt2 = DatabaseConnectionOptimizer()
    create_connection_pool(opt2, "idle", url=SAFE_SQLITE_URL, pool_size=20)
    opt2.get_pool_metrics("idle")
    rec2 = opt2.optimize_pool_size("idle")
    assert rec2["recommendations"][0]["type"] == "decrease_pool_size"

    # Optimal -> no_change
    opt3 = DatabaseConnectionOptimizer()
    create_connection_pool(opt3, "just", url=SAFE_SQLITE_URL, pool_size=2)
    _ = opt3.get_connection("just")
    opt3.get_pool_metrics("just")
    rec3 = opt3.optimize_pool_size("just")
    assert rec3["recommendations"][0]["type"] == "no_change"


def test_add_primary_replica_and_lag():
    opt = DatabaseConnectionOptimizer()
    create_connection_pool(opt, "primary", url=SAFE_SQLITE_URL)
    add_replica_config(
        opt,
        replica_id="rep0",
        host="rep0.local",
        port=5432,
        database="db",
        is_primary=True,
        lag_ms=10,
    )
    assert opt.primary_pool_name == "replica_rep0"

    lag = monitor_replication_lag(opt)
    healthy_replica = next(r for r in lag["replicas"] if r["replica_id"] == "rep0")
    assert healthy_replica["status"] == "healthy"

    add_replica_config(
        opt,
        replica_id="slow",
        host="slow.local",
        port=5432,
        database="db",
        is_primary=False,
        lag_ms=6000,
    )
    lag2 = monitor_replication_lag(opt)
    assert lag2["healthy"] is False


def test_read_connection_strategies():
    opt = DatabaseConnectionOptimizer()
    create_connection_pool(opt, "primary", url=SAFE_SQLITE_URL)

    # Writes always go to primary
    write_conn = get_read_connection(opt, "insert")
    assert write_conn is not None

    # NONE strategy -> primary
    opt.read_write_strategy = ReadWriteStrategy.NONE
    none_conn = get_read_connection(opt, "select")
    assert none_conn is not None

    # PRIMARY_REPLICA with no replicas -> primary
    opt.read_write_strategy = ReadWriteStrategy.PRIMARY_REPLICA
    conn = get_read_connection(opt, "select")
    assert conn is not None

    # High-lag replica -> primary fallback
    add_replica_config(
        opt,
        replica_id="slow",
        host="slow.local",
        port=5432,
        database="db",
        lag_ms=2000,
    )
    conn2 = get_read_connection(opt, "select")
    assert conn2 is not None

    # PRIMARY_REPLICA with a healthy replica selects the replica
    add_replica_config(
        opt,
        replica_id="fast",
        host="fast.local",
        port=5432,
        database="db",
        lag_ms=10,
    )
    conn3 = get_read_connection(opt, "select")
    assert conn3 is not None and conn3.startswith("replica_")

    # ROUND_ROBIN with no non-primary replicas -> primary
    opt.read_write_strategy = ReadWriteStrategy.ROUND_ROBIN
    conn4 = get_read_connection(opt, "select")
    assert conn4 is not None

    # ROUND_ROBIN with a non-primary replica selects it
    opt2 = DatabaseConnectionOptimizer()
    create_connection_pool(opt2, "primary", url=SAFE_SQLITE_URL)
    add_replica_config(
        opt2,
        replica_id="rr",
        host="rr.local",
        port=5432,
        database="db",
        lag_ms=10,
    )
    opt2.read_write_strategy = ReadWriteStrategy.ROUND_ROBIN
    conn_rr = get_read_connection(opt2, "select")
    assert conn_rr is not None

    # WEIGHTED with no non-primary replicas -> primary
    opt3 = DatabaseConnectionOptimizer()
    create_connection_pool(opt3, "primary", url=SAFE_SQLITE_URL)
    opt3.read_write_strategy = ReadWriteStrategy.WEIGHTED
    conn_w = get_read_connection(opt3, "select")
    assert conn_w is not None

    # WEIGHTED with a non-primary replica selects it
    opt4 = DatabaseConnectionOptimizer()
    create_connection_pool(opt4, "primary", url=SAFE_SQLITE_URL)
    add_replica_config(
        opt4,
        replica_id="w1",
        host="w1.local",
        port=5432,
        database="db",
        lag_ms=10,
        weight=1,
    )
    opt4.read_write_strategy = ReadWriteStrategy.WEIGHTED
    conn_w2 = get_read_connection(opt4, "select")
    assert conn_w2 is not None

    # Unhandled strategy falls through to primary
    opt.read_write_strategy = ReadWriteStrategy.GEOGRAPHICAL
    conn_geo = get_read_connection(opt, "select")
    assert conn_geo is not None

    # get_write_connection alias
    write_alias = get_write_connection(opt)
    assert write_alias is not None


def test_configure_read_write_splitting_branches():
    opt = DatabaseConnectionOptimizer()

    # Primary missing and no strategy
    configure_read_write_splitting(opt, primary="new_primary", replicas=None, strategy=None)
    assert "new_primary" in opt.pools
    assert opt.read_write_strategy == ReadWriteStrategy.PRIMARY_REPLICA  # unchanged default

    # Invalid strategy is swallowed gracefully
    configure_read_write_splitting(
        opt, primary="new_primary", replicas=["r1"], strategy="not_a_strategy"
    )
    assert "r1" in opt.replicas


def test_private_transaction_lifecycle():
    opt = DatabaseConnectionOptimizer()
    txn = _begin_transaction(opt, TransactionIsolationLevel.SERIALIZABLE)
    assert txn in opt.active_transactions
    assert opt.active_transactions[txn].isolation_level == TransactionIsolationLevel.SERIALIZABLE

    assert _commit_transaction(opt, txn) is True
    assert txn not in opt.active_transactions
    assert len(opt.transaction_history) == 1

    bad = _commit_transaction(opt, "missing")
    assert bad is False

    bad2 = _rollback_transaction(opt, "missing")
    assert bad2 is False


def test_transaction_history_trim_and_stats():
    opt = DatabaseConnectionOptimizer()

    # Empty private stats branch
    empty_stats = _get_transaction_stats(opt)
    assert empty_stats["total_transactions"] == 0

    # Zero-duration history branch
    opt.transaction_history.append(
        TransactionMetrics(
            transaction_id="zero_txn",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            duration_ms=0.0,
            status="committed",
        )
    )
    zero_stats = _get_transaction_stats(opt)
    assert zero_stats["total_transactions"] == 1
    assert zero_stats["avg_duration_ms"] == 0.0

    # Positive duration history branch
    txn = _begin_transaction(opt)
    time.sleep(0.001)
    _commit_transaction(opt, txn)
    pos_stats = _get_transaction_stats(opt)
    assert pos_stats["total_transactions"] >= 1
    assert pos_stats["avg_duration_ms"] > 0.0

    # Commit enough transactions to trigger history trim
    for _ in range(1002):
        txn = _begin_transaction(opt)
        _commit_transaction(opt, txn)
    assert len(opt.transaction_history) == 1000

    # Rollback enough transactions to trigger rollback history trim
    opt2 = DatabaseConnectionOptimizer()
    for _ in range(1002):
        txn = _begin_transaction(opt2)
        _rollback_transaction(opt2, txn)
    assert len(opt2.transaction_history) == 1000


def test_public_commit_and_rollback_branches():
    opt = DatabaseConnectionOptimizer()

    # Commit by id branch
    txn = begin_transaction(opt)
    assert commit_transaction(opt, txn) is True

    # Commit with arbitrary name while active falls into the for loop
    txn2 = begin_transaction(opt)
    assert commit_transaction(opt, "not_an_id") is True
    assert txn2 not in opt.active_transactions

    # Rollback by id branch
    txn3 = begin_transaction(opt)
    assert rollback_transaction(opt, txn3) is True

    # Rollback with no active transactions
    assert rollback_transaction(opt) is False

    # Rollback with arbitrary name while active falls into the for loop
    txn4 = begin_transaction(opt)
    assert rollback_transaction(opt, "not_an_id") is True
    assert txn4 not in opt.active_transactions


def test_transaction_stats_public_branches():
    opt = DatabaseConnectionOptimizer()

    # Empty history
    stats_empty = get_transaction_stats(opt)
    assert stats_empty["total_transactions"] == 0
    assert stats_empty["avg_duration_ms"] == 0.0

    # Non-empty history with all zero durations
    opt.transaction_history.append(
        TransactionMetrics(
            transaction_id="zero_txn",
            started_at=datetime.now(timezone.utc),
            ended_at=datetime.now(timezone.utc),
            duration_ms=0.0,
            status="committed",
        )
    )
    stats_zero = get_transaction_stats(opt)
    assert stats_zero["total_transactions"] == 1
    assert stats_zero["avg_duration_ms"] == 0.0

    # Non-empty history with positive durations
    txn = begin_transaction(opt)
    time.sleep(0.001)
    commit_transaction(opt, txn)
    stats_pos = get_transaction_stats(opt)
    assert stats_pos["total_transactions"] >= 1
    assert stats_pos["avg_duration_ms"] > 0.0


def test_pool_health_and_stats_branches():
    opt = DatabaseConnectionOptimizer()

    # Missing pool
    assert opt.monitor_connection_health("missing") == {"error": "Pool not found"}

    # Healthy pool (no stale, no error)
    create_connection_pool(opt, "healthy", url=SAFE_SQLITE_URL, pool_size=1)
    health = opt.monitor_connection_health("healthy")
    assert health["status"] == "healthy"

    # Stale connection -> warning
    create_connection_pool(opt, "stale", url=SAFE_SQLITE_URL, pool_size=1)
    stale_conn = opt.get_connection("stale")
    opt.release_connection("stale", stale_conn)
    opt.connection_metrics[stale_conn].created_at = datetime.now(timezone.utc) - timedelta(
        seconds=opt.pool_recycle_seconds * 3
    )
    stale_health = opt.monitor_connection_health("stale")
    assert stale_health["status"] == "warning"

    # Error connection -> critical
    create_connection_pool(opt, "error", url=SAFE_SQLITE_URL, pool_size=1)
    err_conn = opt.get_connection("error")
    opt.connection_metrics[err_conn].status = ConnectionStatus.ERROR
    error_health = opt.monitor_connection_health("error")
    assert error_health["status"] == "critical"

    # get_statistics
    stats = opt.get_statistics()
    assert stats["total_pools"] == len(opt.pools)

    # get_pool_stats missing pool
    assert get_pool_stats(opt, "missing") == {
        "pool_name": "missing",
        "total_connections": 0,
    }

    # get_pool_stats existing pool
    existing_stats = get_pool_stats(opt, "healthy")
    assert existing_stats["total_connections"] > 0


def test_final_gap_fill():
    """Cover the few remaining line/branch gaps."""
    opt = DatabaseConnectionOptimizer()

    # get_connection missing pool (278-279)
    assert opt.get_connection("nope") is None

    # ROUND_ROBIN with only a primary replica -> primary fallback (703)
    create_connection_pool(opt, "primary", url=SAFE_SQLITE_URL)
    add_replica_config(
        opt,
        replica_id="primary_only",
        host="primary.local",
        port=5432,
        database="db",
        is_primary=True,
        lag_ms=10,
    )
    opt.read_write_strategy = ReadWriteStrategy.ROUND_ROBIN
    rr_conn = get_read_connection(opt, "select")
    assert rr_conn is not None

    # commit_transaction with no active transactions -> return False (1008)
    assert commit_transaction(opt) is False
