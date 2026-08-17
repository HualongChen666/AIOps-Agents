# -*- coding: utf-8 -*-
"""Tests for core/distributed_storage.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.distributed_storage import (
    DatabaseInstance,
    DatabaseRole,
    DatabaseType,
    DistributedStorageManager,
    ReadWriteRouter,
    RedisClusterAdapter,
    get_distributed_storage_manager,
)


@pytest.fixture(autouse=True)
def disable_redis(monkeypatch):
    monkeypatch.setattr("core.distributed_storage.REDIS_AVAILABLE", False)
    monkeypatch.setattr("core.distributed_storage.redis", None)


def test_get_distributed_storage_manager():
    mgr = get_distributed_storage_manager()
    assert isinstance(mgr, DistributedStorageManager)


def test_read_write_router():
    router = ReadWriteRouter()
    master = DatabaseInstance(
        host="m", port=5432, role=DatabaseRole.MASTER, database_type=DatabaseType.POSTGRESQL
    )
    router.set_master(master)
    assert router.get_write_connection() == master
    assert router.get_read_connection() == master

    slave = DatabaseInstance(
        host="s1", port=5433, role=DatabaseRole.SLAVE, database_type=DatabaseType.POSTGRESQL
    )
    router.add_slave(slave)
    read = router.get_read_connection()
    assert read is not None
    router.check_health()
    assert master.last_check is not None


def test_distributed_storage_manager():
    mgr = DistributedStorageManager()
    mgr.configure_master_slave("master", 5432, [("slave1", 5433), ("slave2", 5434)])
    read = mgr.get_read_connection_info()
    assert read["role"] == DatabaseRole.SLAVE.value
    write = mgr.get_write_connection_info()
    assert write["role"] == DatabaseRole.MASTER.value
    health = mgr.health_check()
    assert health["slaves_count"] == 2

    # Redis not available in tests; should not raise
    mgr.configure_redis_cluster([("r1", 6379)])


def test_redis_cluster_adapter():
    adapter = RedisClusterAdapter()
    assert adapter.set("k", "v") is True
    assert adapter.get("k") == "v"
    assert adapter.exists("k") is True
    assert adapter.delete("k") is True
    assert adapter.exists("k") is False
    assert adapter.get_fallback_data() == {}
