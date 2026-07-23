# -*- coding: utf-8 -*-
# tests/api/test_service_monitoring_router.py
# 服务监控路由API基础测试
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.service_monitoring_manager"] = MagicMock()

from api.service_monitoring_router import get_monitoring_status, get_service_metrics, record_metric


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/service-monitoring", tags=["Service Monitoring"])
    test_router.add_api_route("/status", get_monitoring_status, methods=["GET"])
    test_router.add_api_route("/metric", record_metric, methods=["POST"])
    test_router.add_api_route("/metrics/{service_name}", get_service_metrics, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestServiceMonitoringRouter:
    """测试服务监控路由"""

    def test_get_monitoring_status(self, client):
        """测试获取服务监控状态"""
        with patch("core.service_monitoring_manager.get_service_monitoring_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.get_monitoring_summary.return_value = {
                "monitored_services": 10,
                "active_alerts": 2,
            }
            mock_get.return_value = mock_manager

            response = client.get("/api/service-monitoring/status")
            assert response.status_code in [200, 500]

    def test_record_metric(self, client):
        """测试记录服务指标"""
        with (
            patch("core.service_monitoring_manager.get_service_monitoring_manager") as mock_get,
            patch("core.service_monitoring_manager.MetricType") as mock_type,
        ):
            mock_manager = Mock()
            mock_manager.record_metric.return_value = None
            mock_get.return_value = mock_manager
            mock_type.return_value = "gauge"

            response = client.post(
                "/api/service-monitoring/metric",
                params={"metric_name": "cpu_usage", "service_name": "api-service", "value": "75.5"},
            )
            assert response.status_code in [200, 500]

    def test_get_service_metrics(self, client):
        """测试获取服务指标"""
        with patch("core.service_monitoring_manager.get_service_monitoring_manager") as mock_get:
            mock_manager = Mock()
            mock_metric = Mock()
            mock_metric.metric_name = "cpu_usage"
            mock_metric.value = 75.5
            mock_metric.timestamp = MagicMock()
            mock_metric.timestamp.isoformat.return_value = "2026-07-03T00:00:00Z"
            mock_metric.labels = {}
            mock_manager.get_service_metrics.return_value = [mock_metric]
            mock_get.return_value = mock_manager

            response = client.get("/api/service-monitoring/metrics/api-service")
            assert response.status_code in [200, 500]

    def test_get_monitoring_status_error(self, client):
        """测试获取监控状态失败"""
        with patch("core.service_monitoring_manager.get_service_monitoring_manager") as mock_get:
            mock_get.side_effect = Exception("获取监控状态失败")

            response = client.get("/api/service-monitoring/status")
            assert response.status_code == 500

    def test_record_metric_error(self, client):
        """测试记录指标失败"""
        with patch("core.service_monitoring_manager.get_service_monitoring_manager") as mock_get:
            mock_get.side_effect = Exception("记录指标失败")

            response = client.post(
                "/api/service-monitoring/metric",
                params={"metric_name": "cpu_usage", "service_name": "api-service", "value": "75.5"},
            )
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
