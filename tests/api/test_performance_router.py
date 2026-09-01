# -*- coding: utf-8 -*-
"""
Tests for Performance Router
测试性能路由器
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from api.performance_router import router


# ============================================================================
# Test Client Setup
# ============================================================================

@pytest.fixture
def client():
    """Create test client"""
    from main import app
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user"""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.role = "admin"
    return user


# ============================================================================
# Helper Function Tests
# ============================================================================

class TestSafeInt:
    """测试安全整数解析函数"""
    
    def test_safe_int_valid(self):
        """测试有效整数"""
        from api.performance_router import _safe_int
        with patch.dict(os.environ, {"TEST_INT": "42"}):
            assert _safe_int("TEST_INT") == 42
    
    def test_safe_int_default(self):
        """测试默认值"""
        from api.performance_router import _safe_int
        assert _safe_int("NONEXISTENT_INT", default=100) == 100


class TestSafeFloat:
    """测试安全浮点数解析函数"""
    
    def test_safe_float_valid(self):
        """测试有效浮点数"""
        from api.performance_router import _safe_float
        with patch.dict(os.environ, {"TEST_FLOAT": "3.14"}):
            assert _safe_float("TEST_FLOAT") == 3.14
    
    def test_safe_float_default(self):
        """测试默认值"""
        from api.performance_router import _safe_float
        assert _safe_float("NONEXISTENT_FLOAT", default=1.0) == 1.0


class TestSafeBool:
    """测试安全布尔值解析函数"""
    
    def test_safe_bool_true(self):
        """测试解析为True"""
        from api.performance_router import _safe_bool
        with patch.dict(os.environ, {"TEST_BOOL": "true"}):
            assert _safe_bool("TEST_BOOL") is True
    
    def test_safe_bool_false(self):
        """测试解析为False"""
        from api.performance_router import _safe_bool
        with patch.dict(os.environ, {"TEST_BOOL": "false"}):
            assert _safe_bool("TEST_BOOL") is False
    
    def test_safe_bool_default(self):
        """测试默认值"""
        from api.performance_router import _safe_bool
        assert _safe_bool("NONEXISTENT_BOOL", default=True) is True


# ============================================================================
# Rate Limiting Endpoint Tests
# ============================================================================

class TestGetRateLimiting:
    """测试速率限制端点"""
    
    def test_get_rate_limiting_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/rate-limiting")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Concurrent Control Endpoint Tests
# ============================================================================

class TestGetConcurrentControl:
    """测试并发控制端点"""
    
    def test_get_concurrent_control_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/concurrent-control")
        # We expect 401 or 500 due to auth, but endpoint should exist
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Cache Preheat Endpoint Tests
# ============================================================================

class TestGetCachePreheat:
    """测试缓存预热端点"""
    
    def test_get_cache_preheat_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/cache-preheat")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Smart Cache Endpoint Tests
# ============================================================================

class TestGetSmartCache:
    """测试智能缓存端点"""
    
    def test_get_smart_cache_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/smart-cache")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Cache Strategy Endpoint Tests
# ============================================================================

class TestGetCacheStrategy:
    """测试缓存策略端点"""
    
    def test_get_cache_strategy_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/cache-strategy")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Memory Monitor Endpoint Tests
# ============================================================================

class TestGetMemoryMonitor:
    """测试内存监控端点"""
    
    def test_get_memory_monitor_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/memory-monitor")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Memory Optimization Endpoint Tests
# ============================================================================

class TestGetMemoryOptimization:
    """测试内存优化端点"""
    
    def test_get_memory_optimization_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/memory-optimization")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# CPU Optimization Endpoint Tests
# ============================================================================

class TestGetCpuOptimization:
    """测试CPU优化端点"""
    
    def test_get_cpu_optimization_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/cpu-optimization")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# API Resources Endpoint Tests
# ============================================================================

class TestGetApiResources:
    """测试API资源端点"""
    
    def test_get_api_resources_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/api-resources")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# API Throughput Endpoint Tests
# ============================================================================

class TestGetApiThroughput:
    """测试API吞吐量端点"""
    
    def test_get_api_throughput_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/api-throughput")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# API Response Time Endpoint Tests
# ============================================================================

class TestGetApiResponseTime:
    """测试API响应时间端点"""
    
    def test_get_api_response_time_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/api-response-time")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# API Performance Endpoint Tests
# ============================================================================

class TestGetApiPerformance:
    """测试API性能综合端点"""
    
    def test_get_api_performance_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/api-performance")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Integration Testing Endpoint Tests
# ============================================================================

class TestGetIntegrationTesting:
    """测试集成测试端点"""
    
    def test_get_integration_testing_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/integration-testing")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Regression Detection Endpoint Tests
# ============================================================================

class TestGetRegressionDetection:
    """测试回归检测端点"""
    
    def test_get_regression_detection_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/regression-detection")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Performance Report Endpoint Tests
# ============================================================================

class TestGetPerformanceReport:
    """测试性能报告端点"""
    
    def test_get_performance_report_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/performance-report?hours=24")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Performance Optimizer Endpoint Tests
# ============================================================================

class TestGetPerformanceOptimizer:
    """测试性能优化器端点"""
    
    def test_get_performance_optimizer_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/performance-optimizer")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Performance Data Endpoint Tests
# ============================================================================

class TestGetPerformanceData:
    """测试性能数据端点"""
    
    def test_get_performance_data_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/performance-data?metric=response_time&hours=24")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Performance Monitoring Endpoint Tests
# ============================================================================

class TestGetPerformanceMonitoring:
    """测试性能监控端点"""
    
    def test_get_performance_monitoring_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/performance-monitoring")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Performance Tuning Endpoint Tests
# ============================================================================

class TestGetPerformanceTuning:
    """测试性能调优端点"""
    
    def test_get_performance_tuning_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/performance-tuning")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]


# ============================================================================
# Query Optimization Endpoint Tests
# ============================================================================

class TestGetQueryOptimization:
    """测试查询优化端点"""
    
    def test_get_query_optimization_endpoint_exists(self, client):
        """测试端点存在"""
        response = client.get("/api/performance/query-optimization")
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_500_INTERNAL_SERVER_ERROR]
