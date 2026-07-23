# -*- coding: utf-8 -*-
"""测试数据库查询优化器模块"""


class TestDatabaseQueryOptimizer:
    """测试数据库查询优化器"""

    def test_database_query_optimizer_class_exists(self):
        """测试数据库查询优化器类存在"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        assert DatabaseQueryOptimizer is not None

    def test_database_query_optimizer_initialization(self):
        """测试数据库查询优化器初始化"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        assert optimizer is not None
        assert hasattr(optimizer, "slow_query_threshold")

    def test_analyze_query_performance(self):
        """测试分析查询性能"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        result = optimizer.analyze_query_performance(query="SELECT * FROM alerts", duration_ms=100)
        assert result is not None
        assert isinstance(result, dict)

    def test_classify_query_pattern(self):
        """测试分类查询模式"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        pattern = optimizer.classify_query_pattern("SELECT * FROM alerts WHERE level = 'critical'")
        assert pattern is not None
        assert isinstance(pattern, str)

    def test_generate_optimization_recommendations(self):
        """测试生成优化建议"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        recommendations = optimizer.generate_optimization_recommendations(
            query="SELECT * FROM alerts WHERE level = 'critical'"
        )
        assert recommendations is not None
        assert isinstance(recommendations, list)

    def test_cache_query_result(self):
        """测试缓存查询结果"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        optimizer.cache_query_result(
            query="SELECT * FROM alerts", result=[{"id": 1, "level": "critical"}], ttl_seconds=300
        )
        # Should not raise an error
        assert True

    def test_get_cached_query_result(self):
        """测试获取缓存的查询结果"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        optimizer.cache_query_result(
            query="SELECT * FROM alerts", result=[{"id": 1, "level": "critical"}], ttl_seconds=300
        )
        cached_result = optimizer.get_cached_query_result("SELECT * FROM alerts")
        assert cached_result is not None

    def test_invalidate_query_cache(self):
        """测试使查询缓存失效"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        optimizer.cache_query_result(
            query="SELECT * FROM alerts", result=[{"id": 1, "level": "critical"}], ttl_seconds=300
        )
        optimizer.invalidate_query_cache("SELECT * FROM alerts")
        # Should not raise an error
        assert True

    def test_get_cache_statistics(self):
        """测试获取缓存统计信息"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        stats = optimizer.get_cache_statistics()
        assert stats is not None
        assert isinstance(stats, dict)

    def test_clear_query_cache(self):
        """测试清除查询缓存"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        optimizer.clear_query_cache()
        # Should not raise an error
        assert True


class TestQueryPatternClassification:
    """测试查询模式分类"""

    def test_identify_n_plus_one_pattern(self):
        """测试识别N+1模式"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        is_n_plus_one = optimizer.identify_n_plus_one_pattern(
            "SELECT * FROM alerts; SELECT * FROM repairs WHERE alert_id = 1;"
        )
        assert isinstance(is_n_plus_one, bool)

    def test_identify_missing_index_pattern(self):
        """测试识别缺失索引模式"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        has_missing_index = optimizer.identify_missing_index_pattern(
            "SELECT * FROM alerts WHERE level = 'critical'"
        )
        assert isinstance(has_missing_index, bool)

    def test_identify_inefficient_join_pattern(self):
        """测试识别低效连接模式"""
        from core.database_query_optimizer import DatabaseQueryOptimizer

        optimizer = DatabaseQueryOptimizer()
        has_inefficient_join = optimizer.identify_inefficient_join_pattern(
            "SELECT * FROM alerts a JOIN repairs r ON a.id = r.alert_id"
        )
        assert isinstance(has_inefficient_join, bool)


class TestModuleExports:
    """测试模块导出"""

    def test_module_exports(self):
        """测试模块导出"""
        from core.database_query_optimizer import __all__

        expected_exports = [
            "DatabaseQueryOptimizer",
        ]

        for export in expected_exports:
            assert export in __all__
