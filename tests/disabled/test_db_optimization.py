# -*- coding: utf-8 -*-
# tests/test_db_optimization.py
# 数据库优化单元测试
import pytest

from core.db_optimization import (
    clear_slow_queries,
    configure_db_optimization,
    get_connection_pool_config,
    get_connection_pool_statistics,
    get_db_optimization_config,
    get_performance_summary,
    get_query_cache_config,
    get_query_cache_statistics,
    get_slow_queries,
    is_db_optimization_enabled,
    record_connection_pool_usage,
    record_query_cache_hit,
    record_query_cache_miss,
    record_slow_query,
    reset_query_cache_statistics,
    suggest_optimizations,
)


class TestDbOptimizationConfiguration:
    """数据库优化配置测试"""

    def test_configure_db_optimization(self):
        """测试配置数据库优化"""
        configure_db_optimization(
            connection_pool_size=30,
            max_overflow=15,
            query_cache_size=2000,
            slow_query_threshold_seconds=0.5,
        )

        assert is_db_optimization_enabled() is True
        config = get_db_optimization_config()
        assert config["connection_pool_size"] == 30
        assert config["query_cache_size"] == 2000

    def test_get_db_optimization_config(self):
        """测试获取数据库优化配置"""
        configure_db_optimization()

        config = get_db_optimization_config()
        assert config["enabled"] is True
        assert "connection_pool_size" in config
        assert "query_cache_enabled" in config

    def test_is_db_optimization_enabled(self):
        """测试检查数据库优化是否启用"""
        # Reset state first
        from core.db_optimization import _db_optimization_config

        _db_optimization_config["enabled"] = False

        assert is_db_optimization_enabled() is False

        configure_db_optimization()
        assert is_db_optimization_enabled() is True


class TestConnectionPool:
    """连接池配置测试"""

    def test_get_connection_pool_config(self):
        """测试获取连接池配置"""
        configure_db_optimization(connection_pool_size=25, max_overflow=5)

        pool_config = get_connection_pool_config()
        assert pool_config["pool_size"] == 25
        assert pool_config["max_overflow"] == 5
        assert "pool_timeout" in pool_config


class TestQueryCache:
    """查询缓存配置测试"""

    def test_get_query_cache_config(self):
        """测试获取查询缓存配置"""
        configure_db_optimization(query_cache_enabled=True, query_cache_size=500)

        cache_config = get_query_cache_config()
        assert cache_config["enabled"] is True
        assert cache_config["cache_size"] == 500


class TestSlowQueryTracking:
    """慢查询跟踪测试"""

    def test_record_slow_query(self):
        """测试记录慢查询"""
        configure_db_optimization(slow_query_threshold_seconds=0.5)

        record_slow_query("SELECT * FROM users", 1.5, {"limit": 100})

        slow_queries = get_slow_queries()
        assert len(slow_queries) > 0
        assert slow_queries[0]["execution_time"] == 1.5

    def test_record_fast_query_not_logged(self):
        """测试快速查询不被记录为慢查询"""
        configure_db_optimization(slow_query_threshold_seconds=1.0)

        initial_count = len(get_slow_queries())
        record_slow_query("SELECT * FROM users", 0.3)

        # Fast query should not be recorded
        assert len(get_slow_queries()) == initial_count

    def test_get_slow_queries_limit(self):
        """测试获取限制数量的慢查询"""
        configure_db_optimization()

        # Record multiple slow queries
        for i in range(5):
            record_slow_query(f"SELECT * FROM table_{i}", 2.0)

        limited_queries = get_slow_queries(limit=3)
        assert len(limited_queries) <= 3

    def test_clear_slow_queries(self):
        """测试清除慢查询历史"""
        configure_db_optimization()
        record_slow_query("SELECT * FROM users", 2.0)

        clear_slow_queries()

        assert len(get_slow_queries()) == 0


class TestQueryCacheStatistics:
    """查询缓存统计测试"""

    def test_record_query_cache_hit(self):
        """测试记录查询缓存命中"""
        reset_query_cache_statistics()

        record_query_cache_hit()
        record_query_cache_hit()

        stats = get_query_cache_statistics()
        assert stats["hits"] == 2

    def test_record_query_cache_miss(self):
        """测试记录查询缓存未命中"""
        reset_query_cache_statistics()

        record_query_cache_miss()

        stats = get_query_cache_statistics()
        assert stats["misses"] == 1

    def test_get_query_cache_statistics(self):
        """测试获取查询缓存统计"""
        reset_query_cache_statistics()
        record_query_cache_hit()
        record_query_cache_hit()
        record_query_cache_miss()

        stats = get_query_cache_statistics()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["total"] == 3
        assert stats["hit_rate"] == (2 / 3) * 100

    def test_reset_query_cache_statistics(self):
        """测试重置查询缓存统计"""
        record_query_cache_hit()
        record_query_cache_miss()

        reset_query_cache_statistics()

        stats = get_query_cache_statistics()
        assert stats["hits"] == 0
        assert stats["misses"] == 0


class TestConnectionPoolStatistics:
    """连接池统计测试"""

    def test_record_connection_pool_usage(self):
        """测试记录连接池使用情况"""
        configure_db_optimization(connection_pool_size=20)

        record_connection_pool_usage(active_connections=15, available_connections=5)

        stats = get_connection_pool_statistics()
        assert stats["current_usage"] is not None
        assert stats["current_usage"]["active"] == 15

    def test_get_connection_pool_statistics(self):
        """测试获取连接池统计"""
        configure_db_optimization()

        # Record some usage data
        record_connection_pool_usage(10, 10)
        record_connection_pool_usage(15, 5)
        record_connection_pool_usage(12, 8)

        stats = get_connection_pool_statistics()
        assert stats["average_active"] > 0
        assert stats["peak_active"] == 15


class TestPerformanceSummary:
    """性能摘要测试"""

    def test_get_performance_summary(self):
        """测试获取性能摘要"""
        configure_db_optimization()
        record_slow_query("SELECT * FROM users", 2.0)
        record_query_cache_hit()
        record_connection_pool_usage(10, 10)

        summary = get_performance_summary()

        assert summary["optimization_enabled"] is True
        assert summary["slow_query_count"] > 0
        assert "query_cache_stats" in summary
        assert "connection_pool_stats" in summary


class TestOptimizationSuggestions:
    """优化建议测试"""

    def test_suggest_optimizations_normal(self):
        """测试正常情况下的优化建议"""
        configure_db_optimization()

        suggestions = suggest_optimizations()

        assert isinstance(suggestions, list)
        assert len(suggestions) > 0

    def test_suggest_optimizations_high_slow_queries(self):
        """测试高慢查询数量的优化建议"""
        configure_db_optimization()

        # Clear existing slow queries first
        clear_slow_queries()

        # Record many slow queries
        for i in range(51):
            record_slow_query(f"SELECT * FROM table_{i}", 2.0)

        # Verify slow queries were recorded
        assert len(get_slow_queries()) >= 51

        suggestions = suggest_optimizations()

        # Check that we got suggestions
        assert len(suggestions) > 0
        # The suggestion should mention slow queries or optimization
        assert any("slow" in s.lower() or "optimization" in s.lower() for s in suggestions)

    def test_suggest_optimizations_low_cache_hit_rate(self):
        """测试低缓存命中率的优化建议"""
        configure_db_optimization()
        reset_query_cache_statistics()

        # Record many cache misses
        for i in range(101):
            record_query_cache_miss()
        record_query_cache_hit()

        suggestions = suggest_optimizations()

        assert any("cache" in s.lower() for s in suggestions)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
