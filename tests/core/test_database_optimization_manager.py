# -*- coding: utf-8 -*-
"""测试数据库优化管理器模块"""


class TestDatabaseOptimizationManager:
    """测试数据库优化管理器"""

    def test_database_optimization_manager_class_exists(self):
        """测试数据库优化管理器类存在"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        assert DatabaseOptimizationManager is not None

    def test_database_optimization_manager_initialization(self):
        """测试数据库优化管理器初始化"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()
        assert manager is not None
        assert hasattr(manager, "query_optimizer")
        assert hasattr(manager, "connection_optimizer")
        assert hasattr(manager, "cache_optimizer")

    def test_analyze_slow_queries(self):
        """测试分析慢查询"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()
        result = manager.analyze_slow_queries(limit=10)
        assert result is not None
        assert isinstance(result, dict)

    def test_optimize_connection_pool(self):
        """测试优化连接池"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()
        result = manager.optimize_connection_pool("test_pool")
        assert result is not None
        assert isinstance(result, dict)

    def test_setup_query_caching(self):
        """测试设置查询缓存"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()
        result = manager.setup_query_caching(ttl_seconds=300)
        assert result is not None
        assert isinstance(result, dict)

    def test_run_comprehensive_optimization(self):
        """测试运行综合优化"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()
        result = manager.run_comprehensive_optimization()
        assert result is not None
        assert isinstance(result, dict)

    def test_get_optimization_status(self):
        """测试获取优化状态"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()
        status = manager.get_optimization_status()
        assert status is not None
        assert isinstance(status, dict)

    def test_record_query_execution(self):
        """测试记录查询执行"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()
        manager.record_query_execution(
            query="SELECT * FROM alerts", duration_ms=100, timestamp="2024-01-01 00:00:00"
        )
        # Should not raise an error
        assert True

    def test_get_optimization_recommendations(self):
        """测试获取优化建议"""
        from core.database_optimization_manager import DatabaseOptimizationManager

        manager = DatabaseOptimizationManager()
        recommendations = manager.get_optimization_recommendations()
        assert recommendations is not None
        assert isinstance(recommendations, list)


class TestModuleExports:
    """测试模块导出"""

    def test_module_exports(self):
        """测试模块导出"""
        from core.database_optimization_manager import __all__

        expected_exports = [
            "DatabaseOptimizationManager",
        ]

        for export in expected_exports:
            assert export in __all__
