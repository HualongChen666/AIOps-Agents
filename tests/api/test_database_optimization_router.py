# -*- coding: utf-8 -*-
"""
Database Optimization Router Tests
数据库优化路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.database_optimization_router import (
    analyze_slow_queries,
    get_database_metrics,
    get_optimization_status,
    optimize_connection_pool,
    record_query_execution,
    run_optimization,
    setup_query_cache,
)

# Mock problematic imports before importing router
sys.modules["core.database_optimization_manager"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/database-optimization", tags=["Database Optimization"])
    test_router.add_api_route("/status", get_optimization_status, methods=["GET"])
    test_router.add_api_route("/optimize", run_optimization, methods=["POST"])
    test_router.add_api_route("/slow-queries", analyze_slow_queries, methods=["GET"])
    test_router.add_api_route(
        "/connection-pool/optimize", optimize_connection_pool, methods=["POST"]
    )
    test_router.add_api_route("/cache/setup", setup_query_cache, methods=["POST"])
    test_router.add_api_route("/query/record", record_query_execution, methods=["POST"])
    test_router.add_api_route("/metrics", get_database_metrics, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestDatabaseOptimizationRouter:
    """测试数据库优化路由"""

    def test_get_optimization_status(self, client):
        """测试获取数据库优化状态"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.get_optimization_status.return_value = {
                "optimization_enabled": True,
                "last_optimization": "2026-07-03T09:00:00Z",
            }
            mock_manager.return_value = mock_instance

            response = client.get("/api/database-optimization/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_optimization_status_error(self, client):
        """测试获取数据库优化状态失败"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_manager.side_effect = Exception("Database optimization error")

            response = client.get("/api/database-optimization/status")
            assert response.status_code == 500

    def test_run_optimization(self, client):
        """测试运行数据库优化"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.run_comprehensive_optimization.return_value = {
                "optimized_queries": 10,
                "improved_connections": 5,
            }
            mock_manager.return_value = mock_instance
            response = client.post("/api/database-optimization/optimize")
            assert response.status_code == 200

    def test_analyze_slow_queries(self, client):
        """测试分析慢查询"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.analyze_slow_queries.return_value = {
                "total_slow_queries": 5,
                "queries": [{"query": "SELECT * FROM users", "duration": 2.5}],
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/database-optimization/slow-queries?limit=10")
            assert response.status_code == 200

    def test_optimize_connection_pool(self, client):
        """测试优化连接池"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.optimize_connection_pool.return_value = {"pool_size": 20}
            mock_manager.return_value = mock_instance
            response = client.post("/api/database-optimization/connection-pool/optimize")
            assert response.status_code == 200

    def test_setup_query_cache(self, client):
        """测试设置查询缓存"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.setup_query_cache.return_value = {"cache_enabled": True}
            mock_manager.return_value = mock_instance
            response = client.post("/api/database-optimization/cache/setup?ttl_seconds=300")
            assert response.status_code == 200

    def test_record_query_execution(self, client):
        """测试记录查询执行"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.record_query_execution.return_value = None
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/database-optimization/query/record?query_text=SELECT&duration_ms=100"
            )
            assert response.status_code == 200

    def test_get_database_metrics(self, client):
        """测试获取数据库性能指标"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.get_optimization_status.return_value = {"enabled": True}
            mock_instance.analyze_slow_queries.return_value = {"total": 0}
            mock_instance.optimize_connection_pool.return_value = {"size": 10}
            mock_manager.return_value = mock_instance
            response = client.get("/api/database-optimization/metrics")
            assert response.status_code == 200

    def test_run_optimization_with_options(self, client):
        """测试带选项的数据库优化"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.run_comprehensive_optimization.return_value = {
                "optimized_queries": 15,
                "improved_connections": 8,
                "cache_setup": True,
            }
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/database-optimization/optimize",
                json={"optimize_queries": True, "optimize_pool": True, "setup_cache": True},
            )
            assert response.status_code == 200

    def test_run_optimization_error(self, client):
        """测试优化失败场景"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.run_comprehensive_optimization.side_effect = Exception(
                "Optimization failed"
            )
            mock_manager.return_value = mock_instance
            response = client.post("/api/database-optimization/optimize")
            assert response.status_code == 500

    def test_analyze_slow_queries_with_limit(self, client):
        """测试带限制的慢查询分析"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.analyze_slow_queries.return_value = {
                "total_slow_queries": 3,
                "queries": [{"query": "SELECT * FROM users", "duration": 2.5}],
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/database-optimization/slow-queries?limit=5")
            assert response.status_code == 200

    def test_analyze_slow_queries_no_queries(self, client):
        """测试无慢查询场景"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.analyze_slow_queries.return_value = {
                "total_slow_queries": 0,
                "queries": [],
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/database-optimization/slow-queries")
            assert response.status_code == 200

    def test_optimize_connection_pool_with_config(self, client):
        """测试带配置的连接池优化"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.optimize_connection_pool.return_value = {
                "pool_size": 25,
                "max_overflow": 10,
            }
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/database-optimization/connection-pool/optimize",
                json={"pool_size": 25, "max_overflow": 10},
            )
            assert response.status_code == 200

    def test_setup_query_cache_with_custom_ttl(self, client):
        """测试自定义TTL的查询缓存设置"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.setup_query_cache.return_value = {"cache_enabled": True, "ttl": 600}
            mock_manager.return_value = mock_instance
            response = client.post("/api/database-optimization/cache/setup?ttl_seconds=600")
            assert response.status_code == 200

    def test_setup_query_cache_error(self, client):
        """测试缓存设置失败"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.setup_query_cache.side_effect = Exception("Cache setup failed")
            mock_manager.return_value = mock_instance
            response = client.post("/api/database-optimization/cache/setup")
            assert response.status_code == 500

    def test_record_query_execution_with_details(self, client):
        """测试带详细信息的查询记录"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.record_query_execution.return_value = {"recorded": True}
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/database-optimization/query/record?query_text=SELECT * FROM users WHERE id ="
                " 1&duration_ms=150&table_name=users"
            )
            assert response.status_code == 200

    def test_get_optimization_status_disabled(self, client):
        """测试优化功能禁用状态"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.get_optimization_status.return_value = {
                "optimization_enabled": False,
                "reason": "Disabled by admin",
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/database-optimization/status")
            assert response.status_code == 200

    def test_get_database_metrics_with_filter(self, client):
        """测试带过滤条件的指标获取"""
        with patch(
            "core.database_optimization_manager.get_database_optimization_manager"
        ) as mock_manager:
            mock_instance = Mock()
            mock_instance.get_optimization_status.return_value = {"enabled": True}
            mock_instance.analyze_slow_queries.return_value = {"total": 5}
            mock_instance.optimize_connection_pool.return_value = {"pool_size": 10}
            mock_manager.return_value = mock_instance
            response = client.get("/api/database-optimization/metrics?include_slow_queries=true")
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
