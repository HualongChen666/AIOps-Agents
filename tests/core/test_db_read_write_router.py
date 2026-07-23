# -*- coding: utf-8 -*-
"""测试数据库读写路由模块"""

import pytest


class TestDbReadWriteRouterModule:
    """测试数据库读写路由模块"""

    def test_db_read_write_router_module_exists(self):
        """测试数据库读写路由模块存在"""
        from core import db_read_write_router

        assert db_read_write_router is not None

    def test_db_read_write_router_has_functions(self):
        """测试数据库读写路由模块有函数"""
        from core import db_read_write_router

        # 检查模块有函数或类
        assert len(dir(db_read_write_router)) > 0


class TestQueryTypeEnum:
    """测试QueryType枚举"""

    def test_query_type_enum_exists(self):
        """测试QueryType枚举存在"""
        from core.db_read_write_router import QueryType

        assert QueryType is not None

    def test_query_type_enum_values(self):
        """测试QueryType枚举值"""
        from core.db_read_write_router import QueryType

        assert QueryType.READ.value == "read"
        assert QueryType.WRITE.value == "write"
        assert QueryType.TRANSACTION.value == "transaction"
        assert QueryType.SCHEMA.value == "schema"


class TestReplicaStateEnum:
    """测试ReplicaState枚举"""

    def test_replica_state_enum_exists(self):
        """测试ReplicaState枚举存在"""
        from core.db_read_write_router import ReplicaState

        assert ReplicaState is not None

    def test_replica_state_enum_values(self):
        """测试ReplicaState枚举值"""
        from core.db_read_write_router import ReplicaState

        assert ReplicaState.HEALTHY.value == "healthy"
        assert ReplicaState.UNHEALTHY.value == "unhealthy"
        assert ReplicaState.DRAINING.value == "draining"
        assert ReplicaState.MAINTENANCE.value == "maintenance"


class TestReplicaInfoDataclass:
    """测试ReplicaInfo数据类"""

    def test_replica_info_dataclass_exists(self):
        """测试ReplicaInfo数据类存在"""
        from core.db_read_write_router import ReplicaInfo

        assert ReplicaInfo is not None

    def test_replica_info_initialization(self):
        """测试ReplicaInfo初始化"""
        from core.db_read_write_router import ReplicaInfo

        replica = ReplicaInfo(host="localhost", port=5433)
        assert replica.host == "localhost"
        assert replica.port == 5433
        assert replica.state.value == "healthy"

    def test_replica_info_is_available(self):
        """测试ReplicaInfo.is_available方法"""
        from core.db_read_write_router import ReplicaInfo, ReplicaState

        # 健康的副本应该可用
        healthy_replica = ReplicaInfo(
            host="localhost", port=5433, state=ReplicaState.HEALTHY, lag=1.0
        )
        assert healthy_replica.is_available() is True

        # 不健康的副本应该不可用
        unhealthy_replica = ReplicaInfo(host="localhost", port=5433, state=ReplicaState.UNHEALTHY)
        assert unhealthy_replica.is_available() is False

        # 延迟过高的副本应该不可用
        high_lag_replica = ReplicaInfo(host="localhost", port=5433, lag=10.0)
        assert high_lag_replica.is_available() is False


class TestRoutingDecisionDataclass:
    """测试RoutingDecision数据类"""

    def test_routing_decision_dataclass_exists(self):
        """测试RoutingDecision数据类存在"""
        from core.db_read_write_router import RoutingDecision

        assert RoutingDecision is not None

    def test_routing_decision_initialization(self):
        """测试RoutingDecision初始化"""
        from core.db_read_write_router import QueryType, RoutingDecision

        decision = RoutingDecision(
            target_host="localhost", target_port=5432, query_type=QueryType.READ
        )
        assert decision.target_host == "localhost"
        assert decision.target_port == 5432
        assert decision.query_type == QueryType.READ


class TestReadWriteRouter:
    """测试ReadWriteRouter类"""

    def test_read_write_router_class_exists(self):
        """测试ReadWriteRouter类存在"""
        from core.db_read_write_router import ReadWriteRouter

        assert ReadWriteRouter is not None

    def test_read_write_router_initialization(self):
        """测试ReadWriteRouter初始化"""
        from core.db_read_write_router import ReadWriteRouter

        router = ReadWriteRouter()
        assert router.primary_host == "localhost"
        assert router.primary_port == 5432
        assert router.read_write_splitting_enabled is True

    def test_read_write_router_initialization_with_config(self):
        """测试ReadWriteRouter使用配置初始化"""
        from core.db_read_write_router import ReadWriteRouter

        config = {
            "primary_host": "primary.example.com",
            "primary_port": 5432,
            "read_write_splitting_enabled": False,
        }
        router = ReadWriteRouter(config)
        assert router.primary_host == "primary.example.com"
        assert router.read_write_splitting_enabled is False

    def test_classify_query_select(self):
        """测试分类SELECT查询"""
        from core.db_read_write_router import QueryType, ReadWriteRouter

        router = ReadWriteRouter()
        query_type = router.classify_query("SELECT * FROM users")
        assert query_type == QueryType.READ

    def test_classify_query_insert(self):
        """测试分类INSERT查询"""
        from core.db_read_write_router import QueryType, ReadWriteRouter

        router = ReadWriteRouter()
        query_type = router.classify_query("INSERT INTO users VALUES (1, 'test')")
        assert query_type == QueryType.WRITE

    def test_classify_query_update(self):
        """测试分类UPDATE查询"""
        from core.db_read_write_router import QueryType, ReadWriteRouter

        router = ReadWriteRouter()
        query_type = router.classify_query("UPDATE users SET name = 'test'")
        assert query_type == QueryType.WRITE

    def test_classify_query_delete(self):
        """测试分类DELETE查询"""
        from core.db_read_write_router import QueryType, ReadWriteRouter

        router = ReadWriteRouter()
        query_type = router.classify_query("DELETE FROM users WHERE id = 1")
        assert query_type == QueryType.WRITE

    def test_classify_query_begin(self):
        """测试分类BEGIN事务查询"""
        from core.db_read_write_router import QueryType, ReadWriteRouter

        router = ReadWriteRouter()
        query_type = router.classify_query("BEGIN TRANSACTION")
        assert query_type == QueryType.TRANSACTION

    def test_classify_query_create(self):
        """测试分类CREATE查询"""
        from core.db_read_write_router import QueryType, ReadWriteRouter

        router = ReadWriteRouter()
        query_type = router.classify_query("CREATE TABLE test (id INT)")
        assert query_type == QueryType.SCHEMA

    def test_route_query_write_to_primary(self):
        """测试路由写查询到主库"""
        from core.db_read_write_router import ReadWriteRouter

        router = ReadWriteRouter()
        decision = router.route_query("INSERT INTO users VALUES (1, 'test')")
        assert decision.target_host == router.primary_host
        assert decision.target_port == router.primary_port
        assert decision.replica_used is False

    def test_route_query_read_with_splitting_enabled(self):
        """测试路由读查询（读写分离启用）"""
        from core.db_read_write_router import ReadWriteRouter

        config = {
            "replicas": [
                {"host": "replica1.example.com", "port": 5433},
            ]
        }
        router = ReadWriteRouter(config)
        decision = router.route_query("SELECT * FROM users")
        # 如果有可用的副本，应该路由到副本
        # 如果没有可用副本，应该路由到主库
        assert decision.target_host in [router.primary_host, "replica1.example.com"]

    def test_route_query_read_with_splitting_disabled(self):
        """测试路由读查询（读写分离禁用）"""
        from core.db_read_write_router import ReadWriteRouter

        config = {"read_write_splitting_enabled": False}
        router = ReadWriteRouter(config)
        decision = router.route_query("SELECT * FROM users")
        assert decision.target_host == router.primary_host
        assert decision.replica_used is False

    def test_enable_read_write_splitting(self):
        """测试启用读写分离"""
        from core.db_read_write_router import ReadWriteRouter

        router = ReadWriteRouter({"read_write_splitting_enabled": False})
        router.enable_read_write_splitting(True)
        assert router.read_write_splitting_enabled is True

    def test_disable_read_write_splitting(self):
        """测试禁用读写分离"""
        from core.db_read_write_router import ReadWriteRouter

        router = ReadWriteRouter({"read_write_splitting_enabled": True})
        router.enable_read_write_splitting(False)
        assert router.read_write_splitting_enabled is False

    def test_get_routing_stats(self):
        """测试获取路由统计信息"""
        from core.db_read_write_router import ReadWriteRouter

        router = ReadWriteRouter()
        stats = router.get_routing_stats()
        assert isinstance(stats, dict)
        assert "total_queries" in stats
        assert "read_write_splitting_enabled" in stats
        assert "replicas_count" in stats

    def test_update_replica_state(self):
        """测试更新副本状态"""
        from core.db_read_write_router import ReadWriteRouter, ReplicaState

        config = {
            "replicas": [
                {"host": "replica1.example.com", "port": 5433},
            ]
        }
        router = ReadWriteRouter(config)
        router.update_replica_state("replica_0", ReplicaState.UNHEALTHY)

        # 获取副本状态验证
        stats = router.get_routing_stats()
        assert stats["replicas"]["replica_0"]["state"] == "unhealthy"


class TestGetReadWriteRouter:
    """测试get_read_write_router工厂函数"""

    def test_get_read_write_router_function_exists(self):
        """测试get_read_write_router函数存在"""
        from core.db_read_write_router import get_read_write_router

        assert get_read_write_router is not None
        assert callable(get_read_write_router)

    def test_get_read_write_router_default(self):
        """测试获取默认读写路由器"""
        from core.db_read_write_router import get_read_write_router

        router = get_read_write_router()
        assert router is not None
        assert isinstance(router, object)

    def test_get_read_write_router_with_config(self):
        """测试获取带配置的读写路由器"""
        from core.db_read_write_router import get_read_write_router

        config = {
            "primary_host": "custom.example.com",
            "primary_port": 5433,
        }
        router = get_read_write_router(config)
        assert router.primary_host == "custom.example.com"
        assert router.primary_port == 5433


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
