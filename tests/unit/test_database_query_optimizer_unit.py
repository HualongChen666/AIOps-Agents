# -*- coding: utf-8 -*-
# tests/unit/test_database_query_optimizer_unit.py
# Database Query Optimizer模块单元测试
from datetime import datetime, timezone

import pytest  # noqa: F401


class TestQueryOptimizationType:
    """测试查询优化类型枚举"""

    def test_query_optimization_type_values(self):
        """测试查询优化类型枚举值"""
        from core.database_query_optimizer import QueryOptimizationType

        assert QueryOptimizationType.INDEX_ADDITION.value == "index_addition"
        assert QueryOptimizationType.QUERY_REWRITE.value == "query_rewrite"
        assert QueryOptimizationType.NPLUS_ONE_FIX.value == "nplus_one_fix"
        assert QueryOptimizationType.JOIN_OPTIMIZATION.value == "join_optimization"
        assert QueryOptimizationType.SUBQUERY_OPTIMIZATION.value == "subquery_optimization"
        assert QueryOptimizationType.CACHING_STRATEGY.value == "caching_strategy"


class TestOptimizationPriority:
    """测试优化优先级枚举"""

    def test_optimization_priority_values(self):
        """测试优化优先级枚举值"""
        from core.database_query_optimizer import OptimizationPriority

        assert OptimizationPriority.CRITICAL.value == "critical"
        assert OptimizationPriority.HIGH.value == "high"
        assert OptimizationPriority.MEDIUM.value == "medium"
        assert OptimizationPriority.LOW.value == "low"


class TestSlowQuery:
    """测试慢查询数据"""

    def test_slow_query_creation(self):
        """测试慢查询数据创建"""
        from core.database_query_optimizer import SlowQuery

        query = SlowQuery(
            query_id="test_id",
            query_hash="test_hash",
            query_text="SELECT * FROM test",
            database="test_db",
            table_name="test_table",
            execution_count=10,
            avg_duration_ms=100.0,
            max_duration_ms=200.0,
            total_duration_ms=1000.0,
            last_executed=datetime.now(timezone.utc),
        )

        assert query.query_id == "test_id"
        assert query.query_hash == "test_hash"
        assert query.query_text == "SELECT * FROM test"
        assert query.database == "test_db"
        assert query.table_name == "test_table"
        assert query.execution_count == 10
        assert query.avg_duration_ms == 100.0
        assert query.max_duration_ms == 200.0
        assert query.total_duration_ms == 1000.0
        assert isinstance(query.last_executed, datetime)
        assert isinstance(query.metadata, dict)
