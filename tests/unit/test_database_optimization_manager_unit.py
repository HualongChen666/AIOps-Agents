# -*- coding: utf-8 -*-
# tests/unit/test_database_optimization_manager_unit.py
# Database Optimization Manager模块单元测试
from datetime import datetime, timezone

import pytest  # noqa: F401


class TestDatabaseOptimizationStatus:
    """测试数据库优化状态"""

    def test_database_optimization_status_creation(self):
        """测试数据库优化状态创建"""
        from core.database_optimization_manager import DatabaseOptimizationStatus

        status = DatabaseOptimizationStatus()

        assert status.query_optimization_enabled is False
        assert status.connection_optimization_enabled is False
        assert status.cache_optimization_enabled is False
        assert status.last_optimization_run is None
        assert status.total_optimizations_applied == 0
        assert status.performance_improvement_percent == 0.0

    def test_database_optimization_status_with_values(self):
        """测试带值的数据库优化状态"""
        from core.database_optimization_manager import DatabaseOptimizationStatus

        status = DatabaseOptimizationStatus(
            query_optimization_enabled=True,
            connection_optimization_enabled=True,
            cache_optimization_enabled=True,
            last_optimization_run=datetime.now(timezone.utc),
            total_optimizations_applied=10,
            performance_improvement_percent=25.5,
        )

        assert status.query_optimization_enabled
        assert status.connection_optimization_enabled
        assert status.cache_optimization_enabled
        assert status.last_optimization_run is not None
        assert status.total_optimizations_applied == 10
        assert status.performance_improvement_percent == 25.5


class TestDatabaseOptimizationManager:
    """测试数据库优化管理器"""

    def test_database_optimization_manager_initialization(self):
        """测试数据库优化管理器初始化"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()

        assert manager is not None
        assert manager.status is not None

    def test_database_optimization_manager_status(self):
        """测试数据库优化管理器状态"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()

        assert isinstance(manager.status, object)
        assert hasattr(manager.status, "query_optimization_enabled")
