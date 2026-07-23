# -*- coding: utf-8 -*-
"""K8s Router Tests
Kubernetes路由API基础测试
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["kubernetes"] = MagicMock()
sys.modules["kubernetes.client"] = MagicMock()
sys.modules["kubernetes.config"] = MagicMock()
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.k8s_collector"] = MagicMock()
sys.modules["core.k8s_repair"] = MagicMock()

from api.k8s_router import (
    get_k8s_history,
    get_k8s_metrics,
    get_k8s_repair_history_endpoint,
    post_k8s_repair,
    post_k8s_repair_all,
)


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/platforms/kubernetes", tags=["Kubernetes"])
    test_router.add_api_route("/metrics", get_k8s_metrics, methods=["GET"])
    test_router.add_api_route("/history", get_k8s_history, methods=["GET"])
    test_router.add_api_route("/repair", post_k8s_repair, methods=["POST"])
    test_router.add_api_route("/repair/all", post_k8s_repair_all, methods=["POST"])
    test_router.add_api_route("/repair/history", get_k8s_repair_history_endpoint, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestK8sRouter:
    """测试Kubernetes路由"""

    def test_get_k8s_metrics(self, client):
        """测试采集Kubernetes集群指标"""
        with patch("api.k8s_router.collect_all_k8s") as mock_collect:
            mock_collect.return_value = [{"cluster": "cluster-1", "cpu": 45.2, "memory": 68.3}]
            response = client.get("/api/v1/platforms/kubernetes/metrics")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_k8s_history(self, client):
        """测试获取Kubernetes采集历史"""
        with patch("api.k8s_router.get_k8s_collect_history") as mock_history:
            mock_history.return_value = [
                {"cluster": "cluster-1", "timestamp": "2026-07-03T10:00:00Z"}
            ]
            response = client.get("/api/v1/platforms/kubernetes/history")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_post_k8s_repair(self, client):
        """测试执行Kubernetes修复脚本"""
        with patch("api.k8s_router.execute_repair_sync") as mock_repair:
            mock_repair.return_value = {
                "success": True,
                "output": "Pod restarted successfully",
                "exit_code": 0,
            }
            response = client.post(
                "/api/v1/platforms/kubernetes/repair",
                json={"host": "cluster-1", "script_name": "restart_pod", "args": {}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_post_k8s_repair_all(self, client):
        """测试对所有Kubernetes集群执行修复脚本"""
        with patch("api.k8s_router.repair_all_k8s") as mock_repair_all:

            async def mock_repair_func(script_name, args):
                return [
                    {"cluster": "cluster-1", "success": True},
                    {"cluster": "cluster-2", "success": True},
                ]

            mock_repair_all.side_effect = mock_repair_func
            response = client.post(
                "/api/v1/platforms/kubernetes/repair/all",
                json={"host": "all", "script_name": "restart_pod", "args": {}},
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_k8s_repair_history(self, client):
        """测试获取Kubernetes修复历史"""
        with patch("api.k8s_router.get_k8s_repair_history") as mock_history:
            mock_history.return_value = [
                {
                    "cluster": "cluster-1",
                    "script": "restart_pod",
                    "timestamp": "2026-07-03T10:00:00Z",
                }
            ]
            response = client.get("/api/v1/platforms/kubernetes/repair/history")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_k8s_metrics_error(self, client):
        """测试采集指标异常分支"""
        with patch("api.k8s_router.collect_all_k8s") as mock_collect:
            mock_collect.side_effect = RuntimeError("k8s error")
            response = client.get("/api/v1/platforms/kubernetes/metrics")
            assert response.status_code == 500

    def test_post_k8s_repair_error(self, client):
        """测试修复执行异常分支"""
        with patch("api.k8s_router.execute_repair_sync") as mock_repair:
            mock_repair.side_effect = RuntimeError("repair error")
            response = client.post(
                "/api/v1/platforms/kubernetes/repair",
                json={"host": "cluster-1", "script_name": "restart_pod", "args": {}},
            )
            assert response.status_code == 500

    def test_post_k8s_repair_all_error(self, client):
        """测试全集群修复异常分支"""
        with patch("api.k8s_router.repair_all_k8s") as mock_repair_all:

            async def fail(*args, **kwargs):
                raise RuntimeError("repair all error")

            mock_repair_all.side_effect = fail
            response = client.post(
                "/api/v1/platforms/kubernetes/repair/all",
                json={"host": "all", "script_name": "restart_pod", "args": {}},
            )
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
