# -*- coding: utf-8 -*-
# tests/test_api_integration.py
# API集成测试
import os
import sys

import pytest

from core.api_response_standard import APIResponse, ErrorCode, PaginationParams  # noqa: F401
from core.business_metrics import BusinessMetricsCollector
from core.error_recovery import CircuitBreaker, CircuitBreakerConfig, RetryConfig, RetryPolicy
from core.memory_monitor import MemoryMonitor
from core.query_optimization import BatchQueryOptimizer, QueryCache

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestAPIIntegration:
    """API集成测试"""

    def test_api_response_format_consistency(self):
        """测试API响应格式一致性"""
        response1 = APIResponse.success_response(data={"test": "data"})
        response2 = APIResponse.error_response(
            error="Test error", error_code=ErrorCode.INTERNAL_ERROR
        )

        assert "success" in response1
        assert "success" in response2
        assert response1["success"] is True
        assert response2["success"] is False


class TestQueryOptimizationIntegration:
    """查询优化集成测试"""

    def test_query_cache_integration(self):
        """测试查询缓存集成"""
        cache = QueryCache()

        # 测试缓存设置和获取
        cache.set("test_key", {"data": "value"})
        result = cache.get("test_key")

        assert result == {"data": "value"}

        # 测试缓存失效
        cache.invalidate("test_key")
        result = cache.get("test_key")

        assert result is None

    def test_batch_query_optimizer(self):
        """测试批量查询优化器"""
        optimizer = BatchQueryOptimizer()

        # 测试批量获取
        result = optimizer.batch_get_by_ids(session=None, model=None, ids=[1, 2, 3], id_field="id")

        # 由于session和model为mock，应该返回空字典
        assert isinstance(result, dict)


class TestMemoryMonitorIntegration:
    """内存监控集成测试"""

    def test_memory_monitor_initialization(self):
        """测试内存监控初始化"""
        monitor = MemoryMonitor(max_memory_mb=512)

        assert monitor.max_memory_mb == 512
        assert monitor.warning_threshold == 0.8

    def test_memory_monitor_check(self):
        """测试内存监控检查"""
        monitor = MemoryMonitor(max_memory_mb=512)

        # 检查内存使用
        result = monitor.check_memory_usage()

        assert "status" in result
        assert "memory_info" in result


class TestErrorRecoveryIntegration:
    """错误恢复集成测试"""

    def test_circuit_breaker(self):
        """测试断路器"""

        config = CircuitBreakerConfig(failure_threshold=5, recovery_timeout=60)
        breaker = CircuitBreaker(config)

        assert breaker.get_state().value == "closed"
        assert breaker.get_stats()["failure_threshold"] == 5

    def test_retry_policy(self):
        """测试重试策略"""

        config = RetryConfig(max_attempts=3, base_delay=1.0)
        policy = RetryPolicy(config)

        assert policy.config.max_attempts == 3
        assert policy.config.base_delay == 1.0


class TestBusinessMetricsIntegration:
    """业务指标集成测试"""

    def test_metrics_collector_initialization(self):
        """测试指标收集器初始化"""

        collector = BusinessMetricsCollector(retention_days=30)

        assert collector.retention_days == 30

    def test_metrics_calculation(self):
        """测试指标计算"""

        collector = BusinessMetricsCollector()
        metrics = collector.calculate_metrics()

        assert metrics.total_alerts == 0  # 无数据时为0
        assert "alert_resolution_rate" in metrics


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
