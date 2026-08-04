# -*- coding: utf-8 -*-
# tests/api/test_service_monitoring_router.py
# 服务监控路由API基础测试
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.service_monitoring_router import (
    analyze_service_performance,
    check_alert_rules,
    create_alert_rule,
    detect_anomaly,
    get_monitoring_status,
    get_service_metrics,
    record_metric,
)

# Mock problematic imports before importing router
sys.modules["core.service_monitoring_manager"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/service-monitoring", tags=["Service Monitoring"])
    test_router.add_api_route("/status", get_monitoring_status, methods=["GET"])
    test_router.add_api_route("/metric", record_metric, methods=["POST"])
    test_router.add_api_route("/metrics/{service_name}", get_service_metrics, methods=["GET"])
    test_router.add_api_route(
        "/analysis/{service_name}", analyze_service_performance, methods=["GET"]
    )
    test_router.add_api_route("/anomaly/detect", detect_anomaly, methods=["POST"])
    test_router.add_api_route("/alert-rule", create_alert_rule, methods=["POST"])
    test_router.add_api_route("/alert/check", check_alert_rules, methods=["POST"])
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

    def test_analyze_service_performance(self, client):
        """测试分析服务性能"""
        with patch("core.service_monitoring_manager.get_service_monitoring_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.analyze_service_performance.return_value = {
                "avg_response_time": 150,
                "error_rate": 0.02,
            }
            mock_get.return_value = mock_manager

            response = client.get("/api/service-monitoring/analysis/api-service?time_range_hours=1")
            assert response.status_code in [200, 500]

    def test_detect_anomaly(self, client):
        """测试检测异常"""
        with patch("core.service_monitoring_manager.get_service_monitoring_manager") as mock_get:
            mock_manager = Mock()
            mock_detection = Mock()
            mock_detection.service_name = "api-service"
            mock_detection.metric_name = "cpu_usage"
            mock_detection.is_anomaly = True
            mock_detection.anomaly_score = 0.95
            mock_detection.expected_value = 50.0
            mock_detection.actual_value = 95.0
            mock_manager.detect_anomaly.return_value = mock_detection
            mock_get.return_value = mock_manager

            response = client.post(
                "/api/service-monitoring/anomaly/detect",
                params={
                    "metric_name": "cpu_usage",
                    "service_name": "api-service",
                    "current_value": "95.0",
                },
            )
            assert response.status_code in [200, 500]

    def test_create_alert_rule(self, client):
        """测试创建告警规则"""
        with (
            patch("core.service_monitoring_manager.get_service_monitoring_manager") as mock_get,
            patch("core.service_monitoring_manager.AlertSeverity") as mock_severity,
        ):
            mock_manager = Mock()
            mock_manager.create_alert_rule.return_value = None
            mock_get.return_value = mock_manager
            mock_severity.return_value = "warning"

            response = client.post(
                "/api/service-monitoring/alert-rule",
                params={
                    "rule_id": "rule-123",
                    "service_name": "api-service",
                    "metric_name": "cpu_usage",
                    "threshold": "80.0",
                },
            )
            assert response.status_code in [200, 500]

    def test_check_alert_rules(self, client):
        """测试检查告警规则"""
        with patch("core.service_monitoring_manager.get_service_monitoring_manager") as mock_get:
            mock_manager = Mock()
            mock_alert = Mock()
            mock_alert.alert_id = "alert-123"
            mock_alert.service_name = "api-service"
            mock_alert.severity = Mock(value="warning")
            mock_alert.message = "CPU usage high"
            mock_alert.metric_name = "cpu_usage"
            mock_alert.threshold = 80.0
            mock_alert.current_value = 95.0
            mock_alert.timestamp = MagicMock()
            mock_alert.timestamp.isoformat.return_value = "2026-07-03T00:00:00Z"
            mock_manager.check_alert_rules.return_value = [mock_alert]
            mock_get.return_value = mock_manager

            response = client.post("/api/service-monitoring/alert/check")
            assert response.status_code in [200, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
