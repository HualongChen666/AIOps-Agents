# -*- coding: utf-8 -*-
# tests/test_db_replication.py
# 数据库复制单元测试
import pytest

from core.db_replication import (  # noqa: F401
    check_all_replicas_health,
    check_primary_health,
    check_replica_health,
    configure_replication,
    get_current_primary,
    get_healthy_replicas,
    get_primary_config,
    get_replica_configs,
    get_replica_health,
    get_replication_status,
    is_failover_enabled,
    is_read_write_splitting_enabled,
    is_replication_enabled,
    perform_failover,
    promote_replica_to_primary,
)


class TestReplicationConfiguration:
    """数据库复制配置测试"""

    def test_configure_replication(self):
        """测试配置数据库复制"""
        primary_config = {
            "host": "primary.db",
            "port": 5432,
            "database": "aiops",
            "username": "user",
            "password": "pass",
        }
        replicas_config = [
            {
                "host": "replica1.db",
                "port": 5432,
                "database": "aiops",
                "username": "user",
                "password": "pass",
            }
        ]

        configure_replication(
            primary_config,
            replicas_config,
            read_write_splitting=True,
            failover_enabled=True,
        )

        assert is_replication_enabled() is True
        assert is_read_write_splitting_enabled() is True
        assert is_failover_enabled() is True

    def test_get_primary_config(self):
        """测试获取主数据库配置"""
        primary_config = {
            "host": "primary.db",
            "port": 5432,
            "database": "aiops",
            "username": "user",
            "password": "pass",
        }

        configure_replication(primary_config, [])

        config = get_primary_config()
        assert config is not None
        assert config["host"] == "primary.db"

    def test_get_replica_configs(self):
        """测试获取副本数据库配置"""
        primary_config = {"host": "primary.db"}
        replicas_config = [
            {"host": "replica1.db"},
            {"host": "replica2.db"},
        ]

        configure_replication(primary_config, replicas_config)

        configs = get_replica_configs()
        assert len(configs) == 2
        assert configs[0]["host"] == "replica1.db"


class TestReplicationHealthChecks:
    """数据库复制健康检查测试"""

    @pytest.mark.asyncio
    async def test_check_primary_health(self):
        """测试检查主数据库健康状态"""
        primary_config = {"host": "primary.db"}
        configure_replication(primary_config, [])

        health = await check_primary_health()

        assert health is not None
        assert "status" in health
        assert "last_check" in health

    @pytest.mark.asyncio
    async def test_check_replica_health(self):
        """测试检查副本数据库健康状态"""
        primary_config = {"host": "primary.db"}
        replicas_config = [{"host": "replica1.db"}]

        configure_replication(primary_config, replicas_config)

        health = await check_replica_health(0)

        assert health is not None
        assert "status" in health
        assert "last_check" in health

    @pytest.mark.asyncio
    async def test_check_all_replicas_health(self):
        """测试检查所有副本健康状态"""
        primary_config = {"host": "primary.db"}
        replicas_config = [
            {"host": "replica1.db"},
            {"host": "replica2.db"},
        ]

        configure_replication(primary_config, replicas_config)

        health_results = await check_all_replicas_health()

        assert "primary" in health_results
        assert "replica_0" in health_results
        assert "replica_1" in health_results


class TestReplicationFailover:
    """数据库复制故障转移测试"""

    def test_get_healthy_replicas(self):
        """测试获取健康副本"""
        primary_config = {"host": "primary.db"}
        replicas_config = [{"host": "replica1.db"}]

        configure_replication(primary_config, replicas_config, failover_enabled=True)

        healthy = get_healthy_replicas()
        assert isinstance(healthy, list)
        assert "primary" in healthy

    def test_get_current_primary(self):
        """测试获取当前主数据库"""
        primary_config = {"host": "primary.db"}
        replicas_config = [{"host": "replica1.db"}]

        configure_replication(primary_config, replicas_config, failover_enabled=True)

        current = get_current_primary()
        assert current == "primary"

    @pytest.mark.asyncio
    async def test_promote_replica_to_primary(self):
        """测试提升副本为主数据库"""
        primary_config = {"host": "primary.db"}
        replicas_config = [{"host": "replica1.db"}]

        configure_replication(primary_config, replicas_config, failover_enabled=True)

        result = await promote_replica_to_primary(0)

        assert result is True
        assert get_current_primary() == "replica_0"

    @pytest.mark.asyncio
    async def test_promote_replica_without_failover_enabled(self):
        """测试在未启用故障转移时提升副本"""
        primary_config = {"host": "primary.db"}
        replicas_config = [{"host": "replica1.db"}]

        configure_replication(primary_config, replicas_config, failover_enabled=False)

        result = await promote_replica_to_primary(0)

        assert result is False

    @pytest.mark.asyncio
    async def test_perform_failover(self):
        """测试执行自动故障转移"""
        primary_config = {"host": "primary.db"}
        replicas_config = [{"host": "replica1.db"}]

        configure_replication(primary_config, replicas_config, failover_enabled=True)

        result = await perform_failover()

        # With healthy primary, should return True but no actual failover
        assert result is True


class TestReplicationStatus:
    """数据库复制状态测试"""

    def test_get_replication_status(self):
        """测试获取复制状态"""
        primary_config = {"host": "primary.db"}
        replicas_config = [{"host": "replica1.db"}]

        configure_replication(primary_config, replicas_config, failover_enabled=True)

        status = get_replication_status()

        assert status["enabled"] is True
        assert status["failover_enabled"] is True
        assert status["replica_count"] == 1
        assert "health_status" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
