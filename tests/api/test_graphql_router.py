# -*- coding: utf-8 -*-
"""
Tests for GraphQL Router
测试GraphQL路由器
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from api.graphql_router import (
    _get_active_subscriptions,
    _get_dataloader_config,
    _get_dataloader_registry,
    _get_graphql_api_config,
    _get_graphql_api_endpoints,
    _get_graphql_health_status,
    _get_graphql_schema_summary,
    _get_graphql_usage_stats,
    _get_resolver_methods,
    _get_schema_size,
    _get_subscription_config,
    _safe_bool,
    _safe_int,
    router,
    subscription_manager,
)
from core.auth_db import User


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestSafeBool:
    """测试安全布尔值解析函数"""

    def test_safe_bool_true_values(self):
        """测试解析为True的值"""
        with patch.dict(os.environ, {"TEST_BOOL": "true"}):
            assert _safe_bool("TEST_BOOL") is True
        with patch.dict(os.environ, {"TEST_BOOL": "1"}):
            assert _safe_bool("TEST_BOOL") is True
        with patch.dict(os.environ, {"TEST_BOOL": "yes"}):
            assert _safe_bool("TEST_BOOL") is True
        with patch.dict(os.environ, {"TEST_BOOL": "on"}):
            assert _safe_bool("TEST_BOOL") is True

    def test_safe_bool_false_values(self):
        """测试解析为False的值"""
        with patch.dict(os.environ, {"TEST_BOOL": "false"}):
            assert _safe_bool("TEST_BOOL") is False
        with patch.dict(os.environ, {"TEST_BOOL": "0"}):
            assert _safe_bool("TEST_BOOL") is False
        with patch.dict(os.environ, {"TEST_BOOL": "no"}):
            assert _safe_bool("TEST_BOOL") is False
        with patch.dict(os.environ, {"TEST_BOOL": "off"}):
            assert _safe_bool("TEST_BOOL") is False

    def test_safe_bool_default(self):
        """测试默认值"""
        assert _safe_bool("NONEXISTENT_BOOL") is False
        assert _safe_bool("NONEXISTENT_BOOL", default=True) is True


class TestSafeInt:
    """测试安全整数解析函数"""

    def test_safe_int_valid(self):
        """测试有效整数"""
        with patch.dict(os.environ, {"TEST_INT": "42"}):
            assert _safe_int("TEST_INT") == 42

    def test_safe_int_min_bound(self):
        """测试最小值边界"""
        with patch.dict(os.environ, {"TEST_INT": "5"}):
            assert _safe_int("TEST_INT", min_val=10) == 10

    def test_safe_int_max_bound(self):
        """测试最大值边界"""
        with patch.dict(os.environ, {"TEST_INT": "150"}):
            assert _safe_int("TEST_INT", max_val=100) == 100

    def test_safe_int_invalid(self):
        """测试无效值"""
        with patch.dict(os.environ, {"TEST_INT": "invalid"}):
            assert _safe_int("TEST_INT", default=10) == 10

    def test_safe_int_default(self):
        """测试默认值"""
        assert _safe_int("NONEXISTENT_INT", default=100) == 100


class TestGetSubscriptionConfig:
    """测试获取订阅配置"""

    def test_get_subscription_config_defaults(self):
        """测试默认配置"""
        config = _get_subscription_config()
        assert config.enabled is True
        assert config.websocket_endpoint == "ws://localhost:8000/graphql"
        assert config.max_subscriptions == 100
        assert config.heartbeat_interval == 30
        assert config.connection_timeout == 60

    def test_get_subscription_config_custom(self):
        """测试自定义配置"""
        with patch.dict(os.environ, {
            "GRAPHQL_SUBSCRIPTION_ENABLED": "false",
            "GRAPHQL_WEBSOCKET_ENDPOINT": "ws://custom:9000/graphql",
            "GRAPHQL_MAX_SUBSCRIPTIONS": "200",
            "GRAPHQL_HEARTBEAT_INTERVAL": "60",
            "GRAPHQL_CONNECTION_TIMEOUT": "120",
        }):
            config = _get_subscription_config()
            assert config.enabled is False
            assert config.websocket_endpoint == "ws://custom:9000/graphql"
            assert config.max_subscriptions == 200
            assert config.heartbeat_interval == 60
            assert config.connection_timeout == 120


class TestGetActiveSubscriptions:
    """测试获取活跃订阅"""

    def test_get_active_subscriptions_empty(self):
        """测试无活跃订阅"""
        # Mock subscription manager with no subscribers
        subscription_manager.alert_subscription._subscribers = []
        subscription_manager.metrics_subscription._subscribers = []
        
        subs = _get_active_subscriptions()
        assert len(subs) == 0

    def test_get_active_subscriptions_with_alerts(self):
        """测试有告警订阅"""
        # Mock subscription manager with alert subscribers
        subscription_manager.alert_subscription._subscribers = [MagicMock(), MagicMock()]
        subscription_manager.metrics_subscription._subscribers = []
        
        subs = _get_active_subscriptions()
        assert len(subs) == 2
        assert all(sub.subscription_type == "alert_stream" for sub in subs)

    def test_get_active_subscriptions_with_metrics(self):
        """测试有指标订阅"""
        # Mock subscription manager with metrics subscribers
        subscription_manager.alert_subscription._subscribers = []
        subscription_manager.metrics_subscription._subscribers = [MagicMock()]
        
        subs = _get_active_subscriptions()
        assert len(subs) == 1
        assert subs[0].subscription_type == "metrics_stream"

    def test_get_active_subscriptions_mixed(self):
        """测试混合订阅"""
        # Mock subscription manager with both types
        subscription_manager.alert_subscription._subscribers = [MagicMock()]
        subscription_manager.metrics_subscription._subscribers = [MagicMock(), MagicMock()]
        
        subs = _get_active_subscriptions()
        assert len(subs) == 3
        assert sum(1 for sub in subs if sub.subscription_type == "alert_stream") == 1
        assert sum(1 for sub in subs if sub.subscription_type == "metrics_stream") == 2


# ============================================================================
# GraphQL API Management Endpoint Tests
# ============================================================================


@pytest.mark.asyncio
class TestGetGraphQLAPIConfig:
    """测试获取GraphQL API配置"""

    def test_get_graphql_api_config_defaults(self):
        """测试默认配置"""
        config = _get_graphql_api_config()
        assert config.enabled is True
        assert config.path == "/graphql"
        assert config.graphql_ide == "graphiql"
        assert config.rate_limit_enabled is False

    def test_get_graphql_api_config_custom(self):
        """测试自定义配置"""
        with patch.dict(os.environ, {
            "GRAPHQL_RATE_LIMIT_ENABLED": "true",
            "GRAPHQL_RATE_LIMIT_REQUESTS": "200",
            "GRAPHQL_RATE_LIMIT_PERIOD": "120",
            "GRAPHQL_MAX_QUERY_COMPLEXITY": "2000",
            "GRAPHQL_MAX_DEPTH": "15",
        }):
            config = _get_graphql_api_config()
            assert config.rate_limit_enabled is True
            assert config.rate_limit_requests == 200
            assert config.rate_limit_period == 120
            assert config.max_query_complexity == 2000
            assert config.max_depth == 15


class TestGetGraphQLEndpoints:
    """测试获取GraphQL端点列表"""

    def test_get_graphql_endpoints_enabled(self):
        """测试GraphQL启用时的端点列表"""
        with patch("config.GRAPHQL_ENABLED", True):
            endpoints = _get_graphql_api_endpoints()
            assert len(endpoints) > 0
            # 检查主要端点
            endpoint_paths = [e.path for e in endpoints]
            assert "/api/graphql/graphql-api" in endpoint_paths
            assert "/api/graphql/graphql-auth" in endpoint_paths

    def test_get_graphql_endpoints_disabled(self):
        """测试GraphQL禁用时的端点列表"""
        with patch("config.GRAPHQL_ENABLED", False):
            endpoints = _get_graphql_api_endpoints()
            # 管理端点应该仍然可用
            endpoint_paths = [e.path for e in endpoints]
            assert "/api/graphql/graphql-api" in endpoint_paths


@pytest.mark.asyncio
class TestGetGraphQLUsageStats:
    """测试获取GraphQL使用统计"""

    async def test_get_graphql_usage_stats_empty_db(self, db_session):
        """测试空数据库的统计信息"""
        stats = _get_graphql_usage_stats(db_session)
        assert stats.total_queries == 0
        assert stats.total_mutations == 0
        assert stats.total_errors == 0
        assert stats.avg_query_duration_ms == 0.0
        assert stats.avg_mutation_duration_ms == 0.0
        assert stats.most_used_queries == []
        assert stats.most_used_mutations == []

    async def test_get_graphql_usage_stats_with_data(self, db_session):
        """测试有数据的统计信息"""
        from core.models import Config

        # 添加测试配置
        db_session.add(Config(key="graphql_total_queries", value="100", category="graphql"))
        db_session.add(Config(key="graphql_total_mutations", value="50", category="graphql"))
        db_session.add(Config(key="graphql_total_errors", value="5", category="graphql"))
        db_session.add(Config(key="graphql_avg_query_duration", value="150.5", category="graphql"))
        db_session.add(Config(key="graphql_avg_mutation_duration", value="200.3", category="graphql"))
        db_session.commit()

        stats = _get_graphql_usage_stats(db_session)
        assert stats.total_queries == 100
        assert stats.total_mutations == 50
        assert stats.total_errors == 5
        assert stats.avg_query_duration_ms == 150.5
        assert stats.avg_mutation_duration_ms == 200.3


class TestGetGraphQLSchemaSummary:
    """测试获取GraphQL Schema摘要"""

    def test_get_graphql_schema_summary(self):
        """测试Schema摘要"""
        summary = _get_graphql_schema_summary()
        assert "query_type" in summary
        assert "mutation_type" in summary
        assert "subscription_type" in summary
        assert "total_types" in summary
        assert "total_queries" in summary
        assert "total_mutations" in summary
        assert summary["query_type"] == "Query"
        assert summary["mutation_type"] == "Mutation"


class TestGetGraphQLHealthStatus:
    """测试获取GraphQL健康状态"""

    def test_get_graphql_health_status_enabled(self):
        """测试GraphQL启用时的健康状态"""
        with patch("config.GRAPHQL_ENABLED", True):
            status = _get_graphql_health_status()
            assert status in ["healthy", "degraded", "unhealthy"]

    def test_get_graphql_health_status_disabled(self):
        """测试GraphQL禁用时的健康状态"""
        with patch("config.GRAPHQL_ENABLED", False):
            status = _get_graphql_health_status()
            assert status == "disabled"


@pytest.mark.asyncio
class TestGetGraphQLAPIInfoEndpoint:
    """测试GraphQL API信息端点"""

    async def test_get_graphql_api_info_success(self, client: AsyncClient):
        """测试成功获取API信息"""
        mock_user = User(
            id=1,
            username="testuser",
            password_hash="hashed",
            role="viewer",
            is_active=True
        )

        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.get("/api/graphql/graphql-api")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "configuration" in data
            assert "endpoints" in data
            assert "usage_statistics" in data
            assert "schema_info" in data
            assert "health_status" in data
            assert "last_updated" in data

    async def test_get_graphql_api_info_without_stats(self, client: AsyncClient):
        """测试不包含统计信息的API信息"""
        mock_user = User(
            id=1,
            username="testuser",
            password_hash="hashed",
            role="viewer",
            is_active=True
        )

        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.get("/api/graphql/graphql-api?include_usage_stats=false")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["usage_statistics"]["total_queries"] == 0
            assert data["usage_statistics"]["total_mutations"] == 0

    async def test_get_graphql_api_info_unauthorized(self, client: AsyncClient):
        """测试未授权访问"""
        with patch("api.graphql_router.get_current_user", side_effect=Exception("Unauthorized")):
            response = await client.get("/api/graphql/graphql-api")

            # Should fail due to authentication
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]

    async def test_get_graphql_api_info_admin(self, client: AsyncClient):
        """测试管理员访问"""
        mock_user = User(
            id=1,
            username="admin",
            password_hash="hashed",
            role="admin",
            is_active=True
        )

        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.get("/api/graphql/graphql-api")

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "configuration" in data
            assert data["configuration"]["enabled"] is True


# ============================================================================
# API Endpoint Tests
# ============================================================================

@pytest.mark.asyncio
class TestGetSubscriptionStatus:
    """测试获取订阅状态端点"""

    async def test_get_subscription_status_success(self, client: AsyncClient):
        """测试成功获取订阅状态"""
        # Mock user
        mock_user = User(
            id=1,
            username="testuser",
            password_hash="hashed",
            role="viewer",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            with patch.dict(os.environ, {"GRAPHQL_SUBSCRIPTION_ENABLED": "true"}):
                response = await client.get("/api/graphql/graphql-subscription")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert "config" in data
                assert "active_subscriptions" in data
                assert "total_subscriptions" in data
                assert "websocket_url" in data
                assert "available_subscription_types" in data
                assert data["config"]["enabled"] is True

    async def test_get_subscription_status_disabled(self, client: AsyncClient):
        """测试订阅功能禁用时的响应"""
        mock_user = User(
            id=1,
            username="testuser",
            password_hash="hashed",
            role="viewer",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            with patch.dict(os.environ, {"GRAPHQL_SUBSCRIPTION_ENABLED": "false"}):
                response = await client.get("/api/graphql/graphql-subscription")
                
                assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
                assert "disabled" in response.json()["detail"].lower()

    async def test_get_subscription_status_unauthorized(self, client: AsyncClient):
        """测试未授权访问"""
        with patch("api.graphql_router.get_current_user", side_effect=Exception("Unauthorized")):
            response = await client.get("/api/graphql/graphql-subscription")
            
            # Should fail due to authentication
            assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


@pytest.mark.asyncio
class TestStartSubscriptions:
    """测试启动订阅服务端点"""

    async def test_start_subscriptions_admin(self, client: AsyncClient):
        """测试管理员启动订阅服务"""
        mock_user = User(
            id=1,
            username="admin",
            password_hash="hashed",
            role="admin",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            with patch.object(subscription_manager, "start_all", new_callable=AsyncMock):
                response = await client.post("/api/graphql/graphql-subscription/start")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "success"
                assert "started_at" in data
                assert data["started_by"] == "admin"

    async def test_start_subscriptions_operator(self, client: AsyncClient):
        """测试操作员启动订阅服务"""
        mock_user = User(
            id=1,
            username="operator",
            password_hash="hashed",
            role="operator",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            with patch.object(subscription_manager, "start_all", new_callable=AsyncMock):
                response = await client.post("/api/graphql/graphql-subscription/start")
                
                assert response.status_code == status.HTTP_200_OK

    async def test_start_subscriptions_viewer_forbidden(self, client: AsyncClient):
        """测试查看者启动订阅服务被拒绝"""
        mock_user = User(
            id=1,
            username="viewer",
            password_hash="hashed",
            role="viewer",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.post("/api/graphql/graphql-subscription/start")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "only operators and admins" in response.json()["detail"].lower()

    async def test_start_subscriptions_failure(self, client: AsyncClient):
        """测试启动失败"""
        mock_user = User(
            id=1,
            username="admin",
            password_hash="hashed",
            role="admin",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            with patch.object(subscription_manager, "start_all", new_callable=AsyncMock, side_effect=Exception("Failed")):
                response = await client.post("/api/graphql/graphql-subscription/start")
                
                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


@pytest.mark.asyncio
class TestStopSubscriptions:
    """测试停止订阅服务端点"""

    async def test_stop_subscriptions_admin(self, client: AsyncClient):
        """测试管理员停止订阅服务"""
        mock_user = User(
            id=1,
            username="admin",
            password_hash="hashed",
            role="admin",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            with patch.object(subscription_manager, "stop_all", new_callable=AsyncMock):
                response = await client.post("/api/graphql/graphql-subscription/stop")
                
                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == "success"
                assert "stopped_at" in data
                assert data["stopped_by"] == "admin"

    async def test_stop_subscriptions_operator(self, client: AsyncClient):
        """测试操作员停止订阅服务"""
        mock_user = User(
            id=1,
            username="operator",
            password_hash="hashed",
            role="operator",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            with patch.object(subscription_manager, "stop_all", new_callable=AsyncMock):
                response = await client.post("/api/graphql/graphql-subscription/stop")
                
                assert response.status_code == status.HTTP_200_OK

    async def test_stop_subscriptions_viewer_forbidden(self, client: AsyncClient):
        """测试查看者停止订阅服务被拒绝"""
        mock_user = User(
            id=1,
            username="viewer",
            password_hash="hashed",
            role="viewer",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            response = await client.post("/api/graphql/graphql-subscription/stop")
            
            assert response.status_code == status.HTTP_403_FORBIDDEN
            assert "only operators and admins" in response.json()["detail"].lower()

    async def test_stop_subscriptions_failure(self, client: AsyncClient):
        """测试停止失败"""
        mock_user = User(
            id=1,
            username="admin",
            password_hash="hashed",
            role="admin",
            is_active=True
        )
        
        with patch("api.graphql_router.get_current_user", return_value=mock_user):
            with patch.object(subscription_manager, "stop_all", new_callable=AsyncMock, side_effect=Exception("Failed")):
                response = await client.post("/api/graphql/graphql-subscription/stop")
                
                assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR


# ============================================================================
# Router Configuration Tests
# ============================================================================

def test_router_prefix():
    """测试路由器前缀"""
    assert router.prefix == "/api/graphql"

def test_router_tags():
    """测试路由器标签"""
    assert "GraphQL" in router.tags


# ============================================================================
# Integration Tests
# ============================================================================

@pytest.mark.asyncio
class TestSubscriptionManagerIntegration:
    """测试订阅管理器集成"""

    async def test_subscription_manager_initialization(self):
        """测试订阅管理器初始化"""
        assert subscription_manager is not None
        assert hasattr(subscription_manager, "alert_subscription")
        assert hasattr(subscription_manager, "metrics_subscription")

    async def test_subscription_manager_start_stop(self):
        """测试订阅管理器启动和停止"""
        # Mock the start_all and stop_all methods
        with patch.object(subscription_manager, "start_all", new_callable=AsyncMock) as mock_start:
            with patch.object(subscription_manager, "stop_all", new_callable=AsyncMock) as mock_stop:
                await subscription_manager.start_all()
                mock_start.assert_called_once()
                
                await subscription_manager.stop_all()
                mock_stop.assert_called_once()
