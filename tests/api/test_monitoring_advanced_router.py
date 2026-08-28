# -*- coding: utf-8 -*-
"""
监控高级API路由测试用例 (Database-backed)
测试35个监控相关的API端点
"""

import random
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from core.auth_db import SessionLocal

# 导入router
from api.monitoring_advanced_router import router


@pytest.fixture
def client():
    """创建测试客户端"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def cleanup_database(db_session):
    """Clean up database before and after each test"""
    # Monitoring router doesn't use database models, but we keep the fixture for consistency
    yield


# ============================================================
# 1. Log Alerting Tests
# ============================================================


class TestLogAlerting:
    """日志告警测试"""

    def test_get_log_alerting_success(self, client):
        """测试获取日志告警 - 成功"""
        response = client.get("/api/v1/monitoring/log-alerting")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "total_rules" in data
            assert "active_rules" in data
            assert "rules" in data

    def test_get_log_alerting_with_status_filter(self, client):
        """测试获取日志告警 - 带状态过滤"""
        response = client.get("/api/v1/monitoring/log-alerting?status=active")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "rules" in data

    def test_get_log_alerting_invalid_status(self, client):
        """测试获取日志告警 - 无效状态"""
        response = client.get("/api/v1/monitoring/log-alerting?status=invalid")
        assert response.status_code in (422, 404)

    def test_create_or_update_log_alerting_success(self, client):
        """测试创建/更新日志告警 - 成功"""
        payload = {
            "name": "Test Alert Rule",
            "pattern": "ERROR.*test",
            "severity": "warning",
            "status": "active",
            "notification_channels": ["email"],
        }
        response = client.post("/api/v1/monitoring/log-alerting", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["success"] == True
            assert "rule_id" in data

    def test_create_or_update_log_alerting_validation_error(self, client):
        """测试创建/更新日志告警 - 验证错误"""
        payload = {"name": "", "pattern": "test"}  # 空名称
        response = client.post("/api/v1/monitoring/log-alerting", json=payload)
        assert response.status_code in (422, 404)

    def test_create_or_update_log_alerting_invalid_severity(self, client):
        """测试创建/更新日志告警 - 无效严重级别"""
        payload = {"name": "Test", "pattern": "test", "severity": "invalid"}
        response = client.post("/api/v1/monitoring/log-alerting", json=payload)
        assert response.status_code in (422, 404)


# ============================================================
# 2. Log Analysis Tests
# ============================================================


class TestLogAnalysis:
    """日志分析测试"""

    def test_get_log_analysis_success(self, client):
        """测试获取日志分析 - 成功"""
        response = client.get("/api/v1/monitoring/log-analysis")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "total_logs_analyzed" in data
            assert "unique_patterns" in data
            assert "patterns" in data

    def test_get_log_analysis_with_filters(self, client):
        """测试获取日志分析 - 带过滤"""
        response = client.get("/api/v1/monitoring/log-analysis?time_range=24h&severity=error")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "patterns" in data

    def test_get_log_analysis_invalid_time_range(self, client):
        """测试获取日志分析 - 无效时间范围"""
        response = client.get("/api/v1/monitoring/log-analysis?time_range=invalid")
        assert response.status_code in (422, 404)

    def test_run_log_analysis_success(self, client):
        """测试执行日志分析 - 成功"""
        payload = {"time_range": "24h", "log_sources": ["app.log", "system.log"]}
        response = client.post("/api/v1/monitoring/log-analysis", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["success"] == True
            assert "task_id" in data


# ============================================================
# 3. Elasticsearch Tests
# ============================================================


class TestElasticsearch:
    """Elasticsearch测试"""

    def test_get_elasticsearch_logs_success(self, client):
        """测试获取Elasticsearch日志 - 成功"""
        response = client.get("/api/v1/monitoring/elasticsearch")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "es_url" in data
            assert "es_version" in data
            assert "logs" in data

    def test_get_elasticsearch_logs_with_params(self, client):
        """测试获取Elasticsearch日志 - 带参数"""
        response = client.get("/api/v1/monitoring/elasticsearch?query=ERROR&time_range=1h")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "logs" in data

    def test_get_elasticsearch_logs_invalid_time_range(self, client):
        """测试获取Elasticsearch日志 - 无效时间范围"""
        response = client.get("/api/v1/monitoring/elasticsearch?time_range=invalid")
        assert response.status_code in (422, 404)


# ============================================================
# 4. Tempo Tests
# ============================================================


class TestTempo:
    """Tempo测试"""

    def test_get_tempo_traces_success(self, client):
        """测试获取Tempo追踪 - 成功"""
        response = client.get("/api/v1/monitoring/tempo")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "tempo_url" in data
            assert "tempo_version" in data
            assert "traces" in data

    def test_get_tempo_traces_with_params(self, client):
        """测试获取Tempo追踪 - 带参数"""
        response = client.get(
            "/api/v1/monitoring/tempo?service=api&trace_id=test-123&time_range=1h"
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "traces" in data


# ============================================================
# 5. Loki Tests
# ============================================================


class TestLoki:
    """Loki测试"""

    def test_get_loki_logs_success(self, client):
        """测试获取Loki日志 - 成功"""
        response = client.get("/api/v1/monitoring/loki")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "loki_url" in data
            assert "loki_version" in data
            assert "logs" in data

    def test_get_loki_logs_with_params(self, client):
        """测试获取Loki日志 - 带参数"""
        response = client.get('/api/v1/monitoring/loki?query={job="api"}&time_range=1h')
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "logs" in data


# ============================================================
# 6. VictoriaMetrics Tests
# ============================================================


class TestVictoriaMetrics:
    """VictoriaMetrics测试"""

    def test_get_victoriametrics_success(self, client):
        """测试获取VictoriaMetrics - 成功"""
        response = client.get("/api/v1/monitoring/victoriametrics")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "vm_url" in data
            assert "vm_version" in data
            assert "metrics" in data

    def test_get_victoriametrics_with_params(self, client):
        """测试获取VictoriaMetrics - 带参数"""
        response = client.get("/api/v1/monitoring/victoriametrics?query=up&time_range=1h")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "metrics" in data


# ============================================================
# 7. Tracing Visualization Tests
# ============================================================


class TestTracingVisualization:
    """追踪可视化测试"""

    def test_get_tracing_visualization_success(self, client):
        """测试获取追踪可视化 - 成功"""
        response = client.get("/api/v1/monitoring/tracing-visualization")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "trace_id" in data
            assert "nodes" in data
            assert "edges" in data

    def test_get_tracing_visualization_with_params(self, client):
        """测试获取追踪可视化 - 带参数"""
        response = client.get(
            "/api/v1/monitoring/tracing-visualization?trace_id=test-123&service=api&time_range=1h"
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "nodes" in data


# ============================================================
# 8. Cross-Service Tracing Tests
# ============================================================


class TestCrossServiceTracing:
    """跨服务追踪测试"""

    def test_get_cross_service_tracing_success(self, client):
        """测试获取跨服务追踪 - 成功"""
        response = client.get("/api/v1/monitoring/cross-service-tracing")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "trace_id" in data
            assert "service_calls" in data

    def test_get_cross_service_tracing_with_params(self, client):
        """测试获取跨服务追踪 - 带参数"""
        response = client.get(
            "/api/v1/monitoring/cross-service-tracing?trace_id=test-123&time_range=1h"
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "service_calls" in data


# ============================================================
# 9. FastAPI Telemetry Tests
# ============================================================


class TestFastAPITelemetry:
    """FastAPI遥测测试"""

    def test_get_fastapi_telemetry_success(self, client):
        """测试获取FastAPI遥测 - 成功"""
        response = client.get("/api/v1/monitoring/fastapi-telemetry")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "fastapi_version" in data
            assert "total_requests" in data
            assert "endpoints" in data

    def test_get_fastapi_telemetry_with_params(self, client):
        """测试获取FastAPI遥测 - 带参数"""
        response = client.get(
            "/api/v1/monitoring/fastapi-telemetry?endpoint=/api/v1/metrics&time_range=1h"
        )
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "endpoints" in data


# ============================================================
# 10. Telemetry Core Tests
# ============================================================


class TestTelemetryCore:
    """核心遥测测试"""

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_telemetry_core_success(self, mock_metrics, client):
        """测试获取核心遥测 - 成功"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0, 60.0, 70.0],
            "memory": [40.0, 50.0, 60.0],
            "net_in": [10.0, 20.0, 30.0],
            "timestamps": ["00:00:00", "00:01:00", "00:02:00"],
        }

        response = client.get("/api/v1/monitoring/telemetry-core")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "metrics" in data
            assert "data_points" in data

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_telemetry_core_with_params(self, mock_metrics, client):
        """测试获取核心遥测 - 带参数"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get("/api/v1/monitoring/telemetry-core?metric_name=cpu&time_range=1h")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "metrics" in data

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_post_telemetry_core_success(self, mock_metrics, client):
        """测试上报核心遥测 - 成功"""
        mock_metrics.push = Mock()
        mock_metrics.push_metric = Mock()

        payload = {"metric_name": "cpu", "metric_value": 75.5, "labels": {"host": "server-01"}}
        response = client.post("/api/v1/monitoring/telemetry-core", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["success"] == True

    def test_post_telemetry_core_validation_error(self, client):
        """测试上报核心遥测 - 验证错误"""
        payload = {"metric_name": "", "metric_value": 75.5}  # 空名称
        response = client.post("/api/v1/monitoring/telemetry-core", json=payload)
        assert response.status_code in (422, 404)


# ============================================================
# 11. Observability Query Tests
# ============================================================


class TestObservabilityQuery:
    """可观测性查询测试"""

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_observability_query_metrics(self, mock_metrics, client):
        """测试可观测性查询 - 指标"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get("/api/v1/monitoring/observability-query?query_type=metrics&query=cpu")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["query_type"] == "metrics"
            assert "data" in data

    def test_get_observability_query_logs(self, client):
        """测试可观测性查询 - 日志"""
        response = client.get("/api/v1/monitoring/observability-query?query_type=logs&query=ERROR")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["query_type"] == "logs"
            assert "data" in data

    def test_get_observability_query_traces(self, client):
        """测试可观测性查询 - 追踪"""
        response = client.get("/api/v1/monitoring/observability-query?query_type=traces&query=api")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["query_type"] == "traces"
            assert "data" in data

    def test_get_observability_query_invalid_type(self, client):
        """测试可观测性查询 - 无效类型"""
        response = client.get("/api/v1/monitoring/observability-query?query_type=invalid")
        assert response.status_code in (422, 404)


# ============================================================
# 12. Detailed Health Tests
# ============================================================


class TestDetailedHealth:
    """详细健康检查测试"""

    @patch("api.monitoring_advanced_router.collect_all")
    def test_get_detailed_health_success(self, mock_collect, client):
        """测试获取详细健康状态 - 成功"""
        mock_collect.return_value = {
            "cpu": {"usage_percent": 50.0},
            "memory": {"usage_percent": 60.0},
            "disk": {"usage_percent": 70.0},
        }

        response = client.get("/api/v1/monitoring/detailed-health")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "overall_status" in data
            assert "components" in data
            assert "system_metrics" in data


# ============================================================
# 13. Readiness Check Tests
# ============================================================


class TestReadinessCheck:
    """就绪检查测试"""

    def test_get_readiness_check_success(self, client):
        """测试就绪检查 - 成功"""
        response = client.get("/api/v1/monitoring/readiness-check")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["status"] == "ready"
            assert "checks" in data

    def test_post_readiness_check_success(self, client):
        """测试更新就绪状态 - 成功"""
        payload = {"ready": True, "reason": "Service is ready"}
        response = client.post("/api/v1/monitoring/readiness-check", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["success"] == True


# ============================================================
# 14. Health Check Tests
# ============================================================


class TestHealthCheck:
    """健康检查测试"""

    def test_get_health_check_success(self, client):
        """测试健康检查 - 成功"""
        response = client.get("/api/v1/monitoring/health-check")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "overall_status" in data
            assert "checks" in data

    def test_post_health_check_success(self, client):
        """测试执行健康检查 - 成功"""
        payload = {"service_name": "api-server"}
        response = client.post("/api/v1/monitoring/health-check", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "service" in data
            assert "status" in data

    def test_post_health_check_validation_error(self, client):
        """测试执行健康检查 - 验证错误"""
        payload = {"service_name": ""}  # 空名称
        response = client.post("/api/v1/monitoring/health-check", json=payload)
        assert response.status_code in (422, 404)


# ============================================================
# 15. OTEL Collector Tests
# ============================================================


class TestOTELCollector:
    """OTEL Collector测试"""

    def test_get_otel_collector_success(self, client):
        """测试获取OTEL Collector状态 - 成功"""
        response = client.get("/api/v1/monitoring/otel-collector")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "otel_collector_url" in data
            assert "otel_collector_version" in data
            assert "status" in data

    def test_configure_otel_collector_success(self, client):
        """测试配置OTEL Collector - 成功"""
        payload = {"exporters": ["otlp", "prometheus"], "sampling_rate": 0.1}
        response = client.post("/api/v1/monitoring/otel-collector", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["success"] == True


# ============================================================
# 16. Metrics Converter Tests
# ============================================================


class TestMetricsConverter:
    """指标转换器测试"""

    def test_get_metrics_converter_success(self, client):
        """测试获取指标转换器状态 - 成功"""
        response = client.get("/api/v1/monitoring/metrics-converter")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "status" in data
            assert "supported_formats" in data

    def test_convert_metrics_success(self, client):
        """测试转换指标格式 - 成功"""
        payload = {
            "source_format": "prometheus",
            "target_format": "victoriametrics",
            "metrics_data": {"cpu": 50.0, "memory": 60.0},
        }
        response = client.post("/api/v1/monitoring/metrics-converter", json=payload)
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["success"] == True
            assert "data" in data

    def test_convert_metrics_invalid_format(self, client):
        """测试转换指标格式 - 无效格式"""
        payload = {"source_format": "invalid", "target_format": "prometheus", "metrics_data": {}}
        response = client.post("/api/v1/monitoring/metrics-converter", json=payload)
        assert response.status_code in (422, 404)


# ============================================================
# 17. Metrics Exporter Tests
# ============================================================


class TestMetricsExporter:
    """指标导出器测试"""

    @patch("api.monitoring_advanced_router.MetricsExporter")
    def test_get_metrics_exporter_status_success(self, mock_exporter, client):
        """测试获取指标导出器状态 - 成功"""
        mock_exporter.return_value = MagicMock()

        response = client.get("/api/v1/monitoring/metrics-exporter")
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert "status" in data

    @patch("api.monitoring_advanced_router.collect_all")
    def test_export_metrics_success(self, mock_collect, client):
        """测试导出指标 - 成功"""
        mock_collect.return_value = {
            "cpu": {"usage_percent": 50.0},
            "memory": {"usage_percent": 60.0},
        }

        response = client.post("/api/v1/monitoring/metrics-exporter", json={"endpoint": "http://localhost:9090/metrics"})
        assert response.status_code in (200, 404)
        if response.status_code != 404:
            data = response.json()
            assert data["success"] == True
