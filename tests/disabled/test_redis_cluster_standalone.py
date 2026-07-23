# -*- coding: utf-8 -*-
# tests/test_redis_cluster.py
# Redis集群单元测试
import pytest

from core.redis_cluster import (  # noqa: F401
    check_all_nodes_health,
    check_node_health,
    configure_redis_cluster,
    get_cluster_status,
    get_connection_string,
    get_current_master,
    get_healthy_nodes,
    get_master_nodes,
    get_node_health,
    get_redis_cluster_config,
    get_redis_mode,
    get_replica_nodes,
    is_redis_cluster_enabled,
    perform_failover,
    promote_replica_to_master,
)


class TestRedisClusterConfiguration:
    """Redis集群配置测试"""

    def test_configure_redis_cluster_standalone(self):
        """测试配置独立Redis模式"""
        nodes = [{"host": "localhost", "port": 6379, "role": "master"}]

        configure_redis_cluster(mode="standalone", nodes=nodes)

        assert is_redis_cluster_enabled() is True
        assert get_redis_mode() == "standalone"

    def test_configure_redis_cluster_sentinel(self):
        """测试配置哨兵模式"""
        nodes = [{"host": "localhost", "port": 6379, "role": "master"}]
        sentinel_config = {
            "master_name": "mymaster",
            "sentinels": [{"host": "sentinel1", "port": 26379}],
        }

        configure_redis_cluster(mode="sentinel", nodes=nodes, sentinel_config=sentinel_config)

        assert is_redis_cluster_enabled() is True
        assert get_redis_mode() == "sentinel"

    def test_configure_redis_cluster_cluster_mode(self):
        """测试配置集群模式"""
        nodes = [
            {"host": "node1", "port": 6379, "role": "master"},
            {"host": "node2", "port": 6379, "role": "replica"},
        ]
        cluster_config = {"slots": 16384, "replicas": 1}

        configure_redis_cluster(mode="cluster", nodes=nodes, cluster_config=cluster_config)

        assert is_redis_cluster_enabled() is True
        assert get_redis_mode() == "cluster"

    def test_get_redis_cluster_config(self):
        """测试获取Redis集群配置"""
        nodes = [{"host": "localhost", "port": 6379}]
        configure_redis_cluster(mode="standalone", nodes=nodes)

        config = get_redis_cluster_config()
        assert config["enabled"] is True
        assert config["mode"] == "standalone"


class TestRedisNodeHealth:
    """Redis节点健康检查测试"""

    @pytest.mark.asyncio
    async def test_check_node_health(self):
        """测试检查Redis节点健康状态"""
        nodes = [{"host": "localhost", "port": 6379, "role": "master"}]
        configure_redis_cluster(mode="standalone", nodes=nodes)

        health = await check_node_health(0)

        assert health is not None
        assert "status" in health
        assert "last_check" in health

    @pytest.mark.asyncio
    async def test_check_all_nodes_health(self):
        """测试检查所有节点健康状态"""
        nodes = [
            {"host": "node1", "port": 6379, "role": "master"},
            {"host": "node2", "port": 6379, "role": "replica"},
        ]
        configure_redis_cluster(mode="cluster", nodes=nodes)

        health_results = await check_all_nodes_health()

        assert "node_0" in health_results
        assert "node_1" in health_results


class TestRedisNodeManagement:
    """Redis节点管理测试"""

    def test_get_healthy_nodes(self):
        """测试获取健康节点"""
        nodes = [{"host": "localhost", "port": 6379, "role": "master"}]
        configure_redis_cluster(mode="standalone", nodes=nodes)

        healthy = get_healthy_nodes()
        assert isinstance(healthy, list)

    def test_get_master_nodes(self):
        """测试获取主节点"""
        nodes = [
            {"host": "master", "port": 6379, "role": "master"},
            {"host": "replica", "port": 6379, "role": "replica"},
        ]
        configure_redis_cluster(mode="cluster", nodes=nodes)

        masters = get_master_nodes()
        assert len(masters) == 1

    def test_get_replica_nodes(self):
        """测试获取副本节点"""
        nodes = [
            {"host": "master", "port": 6379, "role": "master"},
            {"host": "replica", "port": 6379, "role": "replica"},
        ]
        configure_redis_cluster(mode="cluster", nodes=nodes)

        replicas = get_replica_nodes()
        assert len(replicas) == 1


class TestRedisFailover:
    """Redis故障转移测试"""

    @pytest.mark.asyncio
    async def test_promote_replica_to_master(self):
        """测试提升副本为主节点"""
        nodes = [
            {"host": "master", "port": 6379, "role": "master"},
            {"host": "replica", "port": 6379, "role": "replica"},
        ]
        configure_redis_cluster(mode="cluster", nodes=nodes)

        result = await promote_replica_to_master(1)

        assert result is True

    def test_get_current_master(self):
        """测试获取当前主节点"""
        nodes = [{"host": "master", "port": 6379, "role": "master"}]
        configure_redis_cluster(mode="standalone", nodes=nodes)

        current = get_current_master()
        assert isinstance(current, str)

    @pytest.mark.asyncio
    async def test_perform_failover(self):
        """测试执行自动故障转移"""
        nodes = [
            {"host": "master", "port": 6379, "role": "master"},
            {"host": "replica", "port": 6379, "role": "replica"},
        ]
        configure_redis_cluster(mode="cluster", nodes=nodes)

        # Check node health to mark nodes as healthy
        await check_all_nodes_health()

        result = await perform_failover()

        # With healthy master, should return True (no failover needed)
        assert result is True


class TestRedisClusterStatus:
    """Redis集群状态测试"""

    def test_get_cluster_status(self):
        """测试获取集群状态"""
        nodes = [{"host": "localhost", "port": 6379}]
        configure_redis_cluster(mode="standalone", nodes=nodes)

        status = get_cluster_status()

        assert status["enabled"] is True
        assert status["mode"] == "standalone"
        assert "health_status" in status

    def test_get_connection_string_standalone(self):
        """测试获取独立模式连接字符串"""
        nodes = [{"host": "localhost", "port": 6379}]
        configure_redis_cluster(mode="standalone", nodes=nodes)

        conn_str = get_connection_string()

        assert conn_str is not None
        assert "redis://" in conn_str

    def test_get_connection_string_cluster(self):
        """测试获取集群模式连接字符串"""
        nodes = [
            {"host": "node1", "port": 6379},
            {"host": "node2", "port": 6379},
        ]
        configure_redis_cluster(mode="cluster", nodes=nodes)

        conn_str = get_connection_string()

        assert conn_str is not None
        assert "redis-cluster://" in conn_str

    def test_get_connection_string_disabled(self):
        """测试未启用时获取连接字符串"""
        # Reset cluster configuration
        from core.redis_cluster import _redis_cluster_config

        _redis_cluster_config["enabled"] = False

        conn_str = get_connection_string()
        assert conn_str is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
