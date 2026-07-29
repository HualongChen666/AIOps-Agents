# -*- coding: utf-8 -*-
"""测试分布式存储模块"""

import pytest

from core.distributed_storage import (
    DatabaseInstance,
    DatabaseRole,
    DatabaseType,
    DistributedStorageManager,
    ReadWriteRouter,
    RedisClusterAdapter,
    get_distributed_storage_manager,
)


class FakeRedis:
    """A fake Redis client for testing RedisClusterAdapter without network."""

    def __init__(self, *args, **kwargs):
        self._store = {}

    def ping(self):
        return True

    def get(self, key):
        return self._store.get(key)

    def set(self, key, value):
        self._store[key] = value
        return True

    def setex(self, key, ttl, value):
        self._store[key] = value
        return True

    def delete(self, key):
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    def exists(self, key):
        return 1 if key in self._store else 0


class FakeRedisModule:
    """Fake module for redis.cluster.RedisCluster references."""

    Redis = FakeRedis

    class RedisCluster:
        def __init__(self, *args, **kwargs):
            pass


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """Patch Redis dependencies so tests do not need a real Redis server."""
    monkeypatch.setattr("core.distributed_storage.REDIS_AVAILABLE", True)
    monkeypatch.setattr("core.distributed_storage.redis", FakeRedisModule)
    monkeypatch.setattr("core.distributed_storage.RedisCluster", FakeRedisModule.RedisCluster)


class TestEnumsAndDataclass:
    """测试枚举和数据类"""

    def test_database_role_values(self):
        assert DatabaseRole.MASTER.value == "master"
        assert DatabaseRole.SLAVE.value == "slave"

    def test_database_type_values(self):
        assert DatabaseType.POSTGRESQL.value == "postgresql"
        assert DatabaseType.REDIS.value == "redis"

    def test_database_instance_defaults(self):
        inst = DatabaseInstance(
            host="localhost",
            port=5432,
            role=DatabaseRole.MASTER,
            database_type=DatabaseType.POSTGRESQL,
        )
        assert inst.is_available is True
        assert inst.weight == 1


class TestReadWriteRouter:
    """测试读写分离路由器"""

    def test_set_master_and_get_write_connection(self):
        router = ReadWriteRouter()
        master = DatabaseInstance(
            host="pg",
            port=5432,
            role=DatabaseRole.MASTER,
            database_type=DatabaseType.POSTGRESQL,
        )
        router.set_master(master)
        assert router.get_write_connection() is master

    def test_get_read_connection_falls_back_to_master(self):
        router = ReadWriteRouter()
        master = DatabaseInstance(
            host="pg",
            port=5432,
            role=DatabaseRole.MASTER,
            database_type=DatabaseType.POSTGRESQL,
        )
        router.set_master(master)
        assert router.get_read_connection() is master

    def test_get_read_connection_with_slaves(self):
        router = ReadWriteRouter()
        master = DatabaseInstance(
            host="pg",
            port=5432,
            role=DatabaseRole.MASTER,
            database_type=DatabaseType.POSTGRESQL,
        )
        slave = DatabaseInstance(
            host="pg-slave",
            port=5433,
            role=DatabaseRole.SLAVE,
            database_type=DatabaseType.POSTGRESQL,
            weight=2,
        )
        router.set_master(master)
        router.add_slave(slave)
        assert router.get_read_connection() is slave

    def test_get_read_connection_no_master_raises(self):
        router = ReadWriteRouter()
        with pytest.raises(Exception):
            router.get_read_connection()

    def test_check_health_updates_slaves(self):
        router = ReadWriteRouter()
        master = DatabaseInstance(
            host="pg",
            port=5432,
            role=DatabaseRole.MASTER,
            database_type=DatabaseType.POSTGRESQL,
        )
        slave = DatabaseInstance(
            host="pg-slave",
            port=5433,
            role=DatabaseRole.SLAVE,
            database_type=DatabaseType.POSTGRESQL,
            is_available=False,
        )
        router.set_master(master)
        router.add_slave(slave)
        router.check_health()
        assert slave.is_available is True


class TestRedisClusterAdapter:
    """测试 Redis 集群适配器（component 模式）"""

    def test_non_stub_operations(self):
        adapter = RedisClusterAdapter()
        assert adapter.stub_enabled is False
        assert adapter.set("key", "value") is True
        assert adapter.get("key") == "value"
        assert adapter.exists("key") is True
        assert adapter.delete("key") is True
        assert adapter.exists("key") is False

    def test_stub_mode_operations(self, monkeypatch):
        class BadRedis(FakeRedis):
            def ping(self):
                raise RuntimeError("no redis")

        monkeypatch.setattr("core.distributed_storage.redis.Redis", BadRedis)
        adapter = RedisClusterAdapter()
        assert adapter.stub_enabled is True
        assert adapter.set("key", "value") is True
        assert adapter.get("key") == "value"


class TestDistributedStorageManager:
    """测试分布式存储管理器"""

    def test_configure_master_slave(self):
        manager = DistributedStorageManager()
        manager.configure_master_slave("pg", 5432, [("pg-slave", 5433)])
        assert manager.read_write_router.master is not None
        assert len(manager.read_write_router.slaves) == 1

    def test_get_read_write_connection_info(self):
        manager = DistributedStorageManager()
        manager.configure_master_slave("pg", 5432, [])
        read_info = manager.get_read_connection_info()
        write_info = manager.get_write_connection_info()
        assert read_info["host"] == "pg"
        assert write_info["role"] == "master"

    def test_health_check(self):
        manager = DistributedStorageManager()
        manager.configure_master_slave("pg", 5432, [("pg-slave", 5433)])
        health = manager.health_check()
        assert health["master_available"] is True
        assert health["slaves_count"] == 1

    def test_configure_redis_cluster_stub(self, caplog):
        manager = DistributedStorageManager()
        # Should not raise when Redis is unavailable
        manager.configure_redis_cluster([("localhost", 7000)])


class TestFactory:
    """测试工厂函数"""

    def test_get_distributed_storage_manager(self):
        m1 = get_distributed_storage_manager()
        m2 = get_distributed_storage_manager()
        assert m1 is m2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
