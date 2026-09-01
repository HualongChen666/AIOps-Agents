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

from api.graphql_router import (
    _get_active_subscriptions,
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

class TestSubscriptionManagerIntegration:
    """测试订阅管理器集成"""

    def test_subscription_manager_initialization(self):
        """测试订阅管理器初始化"""
        assert subscription_manager is not None
        assert hasattr(subscription_manager, "alert_subscription")
        assert hasattr(subscription_manager, "metrics_subscription")

    @pytest.mark.asyncio
    async def test_subscription_manager_start_stop(self):
        """测试订阅管理器启动和停止"""
        # Mock the start_all and stop_all methods
        with patch.object(subscription_manager, "start_all", new_callable=AsyncMock) as mock_start:
            with patch.object(subscription_manager, "stop_all", new_callable=AsyncMock) as mock_stop:
                await subscription_manager.start_all()
                mock_start.assert_called_once()
                
                await subscription_manager.stop_all()
                mock_stop.assert_called_once()
