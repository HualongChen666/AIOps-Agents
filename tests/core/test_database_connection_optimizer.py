# -*- coding: utf-8 -*-
"""Tests for core/database_connection_optimizer.py."""

from core.database_connection_optimizer import (
    DatabaseConnectionOptimizer,
    ReadWriteStrategy,
    _commit_transaction,
    _rollback_transaction,
    add_replica_config,
    begin_transaction,
    check_pool_health,
    create_connection_pool,
    get_database_connection_optimizer,
    get_pool_stats,
    get_read_connection,
    get_transaction_stats,
    get_write_connection,
    monitor_replication_lag,
)


def test_get_database_connection_optimizer():
    opt = get_database_connection_optimizer()
    assert isinstance(opt, DatabaseConnectionOptimizer)


def test_pool_and_connection():
    opt = DatabaseConnectionOptimizer()
    create_connection_pool(opt, "primary", url="postgresql://localhost/db")
    assert "primary" in opt.pools

    stats = get_pool_stats(opt, "primary")
    assert stats["total_connections"] > 0

    health = check_pool_health(opt, "primary")
    assert "status" in health or "error" in health

    conn = opt.get_connection("primary")
    assert conn is not None
    opt.release_connection("primary", conn, query_duration_ms=10.0)

    write_conn = get_write_connection(opt)
    assert write_conn is not None


def test_replica_and_read_connection():
    opt = DatabaseConnectionOptimizer()
    create_connection_pool(opt, "primary")
    add_replica_config(opt, "r1", "replica1", 5432, "db", lag_ms=10)
    opt.read_write_strategy = ReadWriteStrategy.PRIMARY_REPLICA
    read_conn = get_read_connection(opt, "select")
    assert read_conn is not None

    lag = monitor_replication_lag(opt)
    assert "replicas" in lag


def test_transactions():
    opt = DatabaseConnectionOptimizer()
    txn = begin_transaction(opt)
    assert txn in opt.active_transactions

    assert _commit_transaction(opt, txn) is True
    assert txn not in opt.active_transactions

    txn2 = begin_transaction(opt)
    assert _rollback_transaction(opt, txn2) is True

    stats = get_transaction_stats(opt)
    assert "total_transactions" in stats
