# -*- coding: utf-8 -*-
"""Tests for core/database, db_query_optimization, db_read_write_router, db_replication."""

import time

import core.database
import core.db_query_optimization
import core.db_read_write_router
import core.db_replication


def test_database_base():
    assert core.database.Base is not None


def test_query_cache():
    cache = core.db_query_optimization.QueryCache(ttl_seconds=1)
    cache.set("k", 123)
    assert cache.get("k") == 123
    cache.invalidate("k")
    assert cache.get("k") is None
    cache.set("k", 456)
    time.sleep(1.1)
    assert cache.get("k") is None
    cache.cleanup_expired()


async def test_cache_query_result():
    calls = []

    async def dummy():
        calls.append(1)
        return 42

    @core.db_query_optimization.cache_query_result(ttl_seconds=1)
    async def compute():
        return await dummy()

    assert await compute() == 42
    assert await compute() == 42
    assert len(calls) == 1


def test_read_write_router():
    router = core.db_read_write_router.ReadWriteRouter()
    assert router.classify_query("SELECT * FROM users") == core.db_read_write_router.QueryType.READ
    assert (
        router.classify_query("INSERT INTO users VALUES (1)")
        == core.db_read_write_router.QueryType.WRITE
    )
    decision = router.route_query("SELECT 1")
    assert decision.target_host == "localhost"
    decision2 = router.route_query("UPDATE users SET x=1")
    assert decision2.query_type == core.db_read_write_router.QueryType.WRITE


def test_db_replication():
    core.db_replication.configure_replication(
        primary_config={"host": "db1"},
        replicas_config=[{"host": "db2"}],
        read_write_splitting=True,
        failover_enabled=True,
    )
    assert core.db_replication.is_replication_enabled() is True
    assert core.db_replication.is_read_write_splitting_enabled() is True
    assert core.db_replication.is_failover_enabled() is True
    assert core.db_replication.get_primary_config()["host"] == "db1"
    assert len(core.db_replication.get_replica_configs()) == 1
    assert core.db_replication.get_current_primary() == "primary"
    status = core.db_replication.get_replication_status()
    assert status["enabled"] is True
