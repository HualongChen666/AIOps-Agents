# -*- coding: utf-8 -*-
# tests/unit/test_database_connection_optimizer_unit.py
# Database Connection Optimizer模块单元测试
from datetime import datetime, timezone

import pytest  # noqa: F401


class TestConnectionStatus:
    """测试连接状态枚举"""

    def test_connection_status_values(self):
        """测试连接状态枚举值"""
        from core.database_connection_optimizer import ConnectionStatus

        assert ConnectionStatus.IDLE.value == "idle"
        assert ConnectionStatus.ACTIVE.value == "active"
        assert ConnectionStatus.CHECKED_OUT.value == "checked_out"
        assert ConnectionStatus.CLOSED.value == "closed"
        assert ConnectionStatus.ERROR.value == "error"


class TestPoolStrategy:
    """测试池策略枚举"""

    def test_pool_strategy_values(self):
        """测试池策略枚举值"""
        from core.database_connection_optimizer import PoolStrategy

        assert PoolStrategy.FIXED.value == "fixed"
        assert PoolStrategy.DYNAMIC.value == "dynamic"
        assert PoolStrategy.ADAPTIVE.value == "adaptive"


class TestConnectionMetrics:
    """测试连接指标"""

    def test_connection_metrics_creation(self):
        """测试连接指标创建"""
        from core.database_connection_optimizer import ConnectionMetrics, ConnectionStatus

        metrics = ConnectionMetrics(
            connection_id="test_id",
            created_at=datetime.now(timezone.utc),
            last_used=datetime.now(timezone.utc),
        )

        assert metrics.connection_id == "test_id"
        assert metrics.total_queries == 0
        assert metrics.total_duration_ms == 0.0
        assert metrics.avg_duration_ms == 0.0
        assert metrics.status == ConnectionStatus.IDLE
        assert isinstance(metrics.metadata, dict)


class TestPoolMetrics:
    """测试池指标"""

    def test_pool_metrics_creation(self):
        """测试池指标创建"""
        from core.database_connection_optimizer import PoolMetrics

        metrics = PoolMetrics(pool_name="test_pool")

        assert metrics.pool_name == "test_pool"
        assert metrics.total_connections == 0
