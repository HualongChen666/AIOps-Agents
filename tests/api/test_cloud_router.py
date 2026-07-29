# -*- coding: utf-8 -*-
"""Cloud Router Tests
云平台路由API基础测试
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# isort: off
# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.cloud_collector"] = MagicMock()
sys.modules["core.cloud_collector"].CLOUD_PROVIDERS = [{"provider": "aws", "region": "us-east-1"}]
sys.modules["core.cloud_repair"] = MagicMock()

from api.cloud_router import (
    cloud_history,
    collect_one,
    collect_provider,
    get_cloud_metrics,
    get_provider_metrics,
    provider_history,
    provider_repair_history,
    repair_provider,
)

# isort: on


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/platforms/cloud", tags=["Cloud"])
    test_router.add_api_route("/metrics", get_cloud_metrics, methods=["GET"])
    test_router.add_api_route("/collect", collect_one, methods=["POST"])
    test_router.add_api_route("/history", cloud_history, methods=["GET"])
    test_router.add_api_route("/{provider}/metrics", get_provider_metrics, methods=["GET"])
    test_router.add_api_route("/{provider}/collect", collect_provider, methods=["POST"])
    test_router.add_api_route("/{provider}/history", provider_history, methods=["GET"])
    test_router.add_api_route("/{provider}/repair", repair_provider, methods=["POST"])
    test_router.add_api_route(
        "/{provider}/repair/history", provider_repair_history, methods=["GET"]
    )
    app.include_router(test_router)
    return TestClient(app)


class TestCloudRouter:
    """测试云平台路由"""

    def test_get_cloud_metrics(self, client):
        """测试批量采集所有云平台指标"""
        with patch("api.cloud_router.collect_all_cloud") as mock_collect:
            mock_collect.return_value = [{"provider": "aws", "cpu": 45.2, "memory": 68.3}]
            response = client.get("/api/v1/platforms/cloud/metrics")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_collect_one(self, client):
        """测试手动触发单个云平台采集"""
        with patch("api.cloud_router.collect_cloud") as mock_collect:
            mock_collect.return_value = {"provider": "aws", "cpu": 45.2}
            response = client.post(
                "/api/v1/platforms/cloud/collect", json={"provider": "aws", "region": "us-east-1"}
            )
            assert response.status_code == 200
            data = response.json()
            assert "provider" in data

    def test_cloud_history(self, client):
        """测试获取云平台采集历史"""
        with patch("api.cloud_router.get_cloud_collect_history") as mock_history:
            mock_history.return_value = [{"provider": "aws", "timestamp": "2026-07-03T10:00:00Z"}]
            response = client.get("/api/v1/platforms/cloud/history")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_get_provider_metrics(self, client):
        """测试采集指定云平台指标"""
        with patch("api.cloud_router.collect_cloud") as mock_collect:
            mock_collect.return_value = {"provider": "aws", "cpu": 45.2}
            response = client.get("/api/v1/platforms/cloud/aws/metrics")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    def test_repair_provider(self, client):
        """测试执行云平台修复操作"""
        with patch("core.cloud_repair.execute_cloud_repair") as mock_repair:

            async def mock_repair_func(cfg, action, **params):
                return {"success": True, "action": action}

            mock_repair.side_effect = mock_repair_func
            response = client.post(
                "/api/v1/platforms/cloud/aws/repair",
                json={"action": "restart_instance", "params": {"instance_id": "i-12345678"}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_provider_repair_history(self, client):
        """测试获取云平台修复历史"""
        with patch("core.cloud_repair.get_cloud_repair_history") as mock_history:
            mock_history.return_value = [
                {
                    "provider": "aws",
                    "action": "restart_instance",
                    "timestamp": "2026-07-03T10:00:00Z",
                }
            ]
            response = client.get("/api/v1/platforms/cloud/aws/repair/history")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
