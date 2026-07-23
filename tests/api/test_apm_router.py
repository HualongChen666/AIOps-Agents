# -*- coding: utf-8 -*-
"""
APM Router Tests
APM监控路由API基础测试
"""

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.telemetry_core"] = MagicMock()
sys.modules["core.health_check"] = MagicMock()

from api.apm_router import get_apm_metrics, get_application_health, reset_apm_metrics


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/apm", tags=["APM监控"])
    test_router.add_api_route("/metrics", get_apm_metrics, methods=["GET"])
    test_router.add_api_route("/health", get_application_health, methods=["GET"])
    test_router.add_api_route("/metrics/reset", reset_apm_metrics, methods=["POST"])
    app.include_router(test_router)
    return TestClient(app)


class TestAPMRouter:
    """测试APM监控路由"""

    def test_get_apm_metrics_success(self, client):
        """测试成功获取APM指标"""
        with patch("api.apm_router.telemetry") as mock_telemetry:
            mock_telemetry.get_apm_metrics.return_value = {
                "request_count": 1000,
                "error_rate": 0.01,
            }

            with patch(
                "core.health_check.check_system_resources", new_callable=AsyncMock
            ) as mock_check:
                mock_check.return_value = {
                    "status": "healthy",
                    "metrics": {"cpu": 45.2, "memory": 68.3},
                }

                response = client.get("/api/v1/apm/metrics")
                assert response.status_code == 200
                data = response.json()
                assert "apm_metrics" in data

    def test_get_apm_metrics_error(self, client):
        """测试获取APM指标失败"""
        with patch("api.apm_router.telemetry") as mock_telemetry:
            mock_telemetry.get_apm_metrics.side_effect = Exception("APM error")

            response = client.get("/api/v1/apm/metrics")
            assert response.status_code == 500

    def test_get_application_health(self, client):
        """测试获取应用健康状态"""
        with patch(
            "core.health_check.perform_health_checks", new_callable=AsyncMock
        ) as mock_health:
            mock_health.return_value = {"status": "healthy", "checks": {}}

            response = client.get("/api/v1/apm/health")
            assert response.status_code == 200
            data = response.json()
            assert "health_status" in data

    def test_get_application_health_error(self, client):
        """测试获取应用健康状态失败"""
        with patch("core.health_check.perform_health_checks") as mock_health:
            mock_health.side_effect = Exception("Health check error")

            response = client.get("/api/v1/apm/health")
            assert response.status_code == 500

    def test_reset_apm_metrics(self, client):
        """测试重置APM指标"""
        with patch("api.apm_router.telemetry") as mock_telemetry:
            mock_telemetry.reset_apm_metrics.return_value = None

            response = client.post("/api/v1/apm/metrics/reset")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
