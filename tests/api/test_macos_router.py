# -*- coding: utf-8 -*-
"""
macOS Router Tests
macOS监控路由API基础测试
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.macos_collector"] = MagicMock()
sys.modules["core.macos_repair"] = MagicMock()

from api.macos_router import get_macos_metrics, post_macos_repair


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/macos", tags=["macOS"])
    test_router.add_api_route("/metrics", get_macos_metrics, methods=["GET"])
    test_router.add_api_route("/repair", post_macos_repair, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestMacOSRouter:
    """测试macOS监控路由"""

    def test_get_macos_metrics_success(self, client):
        """测试成功获取macOS指标"""
        with patch(
            "api.macos_router.collect_macos_metrics", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = {
                "host1": {"cpu": 0.23, "mem": 0.56, "disk": 0.45},
                "host2": {"cpu": 0.35, "mem": 0.68, "disk": 0.52},
            }

            response = client.get("/api/macos/metrics")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)

    def test_get_macos_metrics_error(self, client):
        """测试获取macOS指标失败"""
        with patch(
            "api.macos_router.collect_macos_metrics", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.side_effect = Exception("macOS collection error")

            response = client.get("/api/macos/metrics")
            assert response.status_code == 500

    def test_get_macos_metrics_with_hosts(self, client):
        """测试获取指定主机的macOS指标"""
        with patch(
            "api.macos_router.collect_macos_metrics", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = {"host1": {"cpu": 0.23, "mem": 0.56, "disk": 0.45}}

            response = client.get("/api/macos/metrics?hosts=host1")
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, dict)

    def test_get_macos_metrics_empty(self, client):
        """测试获取空的macOS指标"""
        with patch(
            "api.macos_router.collect_macos_metrics", new_callable=AsyncMock
        ) as mock_collect:
            mock_collect.return_value = {}

            response = client.get("/api/macos/metrics")
            assert response.status_code == 200
            data = response.json()
            assert data == {}

    def test_post_macos_repair_success(self, client):
        """测试成功执行macOS修复"""
        with patch("api.macos_router.execute_macos_repair", new_callable=AsyncMock) as mock_repair:
            mock_repair.return_value = {"success": True, "output": "Repair completed"}

            response = client.post("/api/macos/repair?host=macbook-01&script_name=clear_cache")
            assert response.status_code == 200
            data = response.json()
            assert "host" in data
            assert "script" in data

    def test_post_macos_repair_with_args(self, client):
        """测试带参数执行macOS修复"""
        with patch("api.macos_router.execute_macos_repair", new_callable=AsyncMock) as mock_repair:
            mock_repair.return_value = {"success": True, "output": "Repair completed"}

            response = client.post(
                "/api/macos/repair?host=macbook-01&script_name=clear_cache", json={"force": True}
            )
            assert response.status_code == 200

    def test_post_macos_repair_error(self, client):
        """测试执行macOS修复失败"""
        with patch("api.macos_router.execute_macos_repair", new_callable=AsyncMock) as mock_repair:
            mock_repair.side_effect = Exception("Repair error")

            response = client.post("/api/macos/repair?host=macbook-01&script_name=clear_cache")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
