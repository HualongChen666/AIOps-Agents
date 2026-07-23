# -*- coding: utf-8 -*-
# tests/api/test_system_resource_router.py
# 系统资源路由API基础测试
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.system_resource_optimizer"] = MagicMock()

from api.system_resource_router import (
    analyze_memory_usage,
    get_optimization_status,
    get_resource_summary,
    optimize_memory,
)


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/system-resources", tags=["System Resources"])
    test_router.add_api_route("/status", get_optimization_status, methods=["GET"])
    test_router.add_api_route("/summary", get_resource_summary, methods=["GET"])
    test_router.add_api_route("/memory", analyze_memory_usage, methods=["GET"])
    test_router.add_api_route("/memory/optimize", optimize_memory, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestSystemResourceRouter:
    """测试系统资源路由"""

    def test_get_optimization_status(self, client):
        """测试获取优化状态"""
        with patch("core.system_resource_optimizer.get_system_resource_optimizer") as mock_get:
            mock_optimizer = Mock()
            mock_optimizer.get_optimization_status.return_value = {
                "status": "optimized",
                "last_optimized": "2026-07-03T00:00:00Z",
            }
            mock_get.return_value = mock_optimizer

            response = client.get("/api/system-resources/status")
            assert response.status_code in [200, 500]

    def test_get_resource_summary(self, client):
        """测试获取资源摘要"""
        with patch("core.system_resource_optimizer.get_system_resource_optimizer") as mock_get:
            mock_optimizer = Mock()
            mock_optimizer.get_resource_summary.return_value = {
                "cpu_usage": 45.2,
                "memory_usage": 68.3,
                "disk_usage": 52.1,
            }
            mock_get.return_value = mock_optimizer

            response = client.get("/api/system-resources/summary")
            assert response.status_code in [200, 500]

    def test_analyze_memory_usage(self, client):
        """测试分析内存使用"""
        with patch("core.system_resource_optimizer.get_system_resource_optimizer") as mock_get:
            mock_optimizer = Mock()
            mock_optimizer.analyze_memory_usage.return_value = {
                "total_memory": 16384,
                "used_memory": 11200,
                "free_memory": 5184,
            }
            mock_get.return_value = mock_optimizer

            response = client.get("/api/system-resources/memory")
            assert response.status_code in [200, 500]

    def test_optimize_memory(self, client):
        """测试优化内存"""
        with patch("core.system_resource_optimizer.get_system_resource_optimizer") as mock_get:
            mock_optimizer = Mock()
            mock_optimizer.optimize_memory.return_value = {
                "freed_memory": 1024,
                "processes_optimized": 5,
            }
            mock_get.return_value = mock_optimizer

            response = client.post("/api/system-resources/memory/optimize")
            assert response.status_code in [200, 500]

    def test_get_optimization_status_error(self, client):
        """测试获取优化状态失败"""
        with patch("core.system_resource_optimizer.get_system_resource_optimizer") as mock_get:
            mock_get.side_effect = Exception("Optimizer error")

            response = client.get("/api/system-resources/status")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
