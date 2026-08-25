# -*- coding: utf-8 -*-
"""
监控高级API路由测试用例
测试35个监控相关的API端点
"""

import random
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# 导入router
from api.monitoring_advanced_router import router


@pytest.fixture
def client():
    """创建测试客户端"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ============================================================
# 1. Log Alerting Tests
# ============================================================


class TestLogAlerting:
    """日志告警测试"""

    def test_get_log_alerting_success(self, client):
        """测试获取日志告警 - 成功"""
        response = client.get("/api/v1/monitoring/log-alerting")
        assert response.status_code == 200
        data = response.json()
        assert "total_rules" in data
        assert "active_rules" in data
        assert "rules" in data

    def test_get_log_alerting_with_status_filter(self, client):
        """测试获取日志告警 - 带状态过滤"""
        response = client.get("/api/v1/monitoring/log-alerting?status=active")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data

    def test_get_log_alerting_invalid_status(self, client):
        """测试获取日志告警 - 无效状态"""
        response = client.get("/api/v1/monitoring/log-alerting?status=invalid")
        assert response.status_code == 422

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
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "rule_id" in data

    def test_create_or_update_log_alerting_validation_error(self, client):
        """测试创建/更新日志告警 - 验证错误"""
        payload = {"name": "", "pattern": "test"}  # 空名称
        response = client.post("/api/v1/monitoring/log-alerting", json=payload)
        assert response.status_code == 422

    def test_create_or_update_log_alerting_invalid_severity(self, client):
        """测试创建/更新日志告警 - 无效严重级别"""
        payload = {"name": "Test", "pattern": "test", "severity": "invalid"}
        response = client.post("/api/v1/monitoring/log-alerting", json=payload)
        assert response.status_code == 422


# ============================================================
# 2. Log Analysis Tests
# ============================================================


class TestLogAnalysis:
    """日志分析测试"""

    def test_get_log_analysis_success(self, client):
        """测试获取日志分析 - 成功"""
        response = client.get("/api/v1/monitoring/log-analysis")
        assert response.status_code == 200
        data = response.json()
        assert "total_logs_analyzed" in data
        assert "unique_patterns" in data
        assert "patterns" in data

    def test_get_log_analysis_with_filters(self, client):
        """测试获取日志分析 - 带过滤"""
        response = client.get("/api/v1/monitoring/log-analysis?time_range=24h&severity=error")
        assert response.status_code == 200
        data = response.json()
        assert "patterns" in data

    def test_get_log_analysis_invalid_time_range(self, client):
        """测试获取日志分析 - 无效时间范围"""
        response = client.get("/api/v1/monitoring/log-analysis?time_range=invalid")
        assert response.status_code == 422

    def test_run_log_analysis_success(self, client):
        """测试执行日志分析 - 成功"""
        payload = {"time_range": "24h", "log_sources": ["app.log", "system.log"]}
        response = client.post("/api/v1/monitoring/log-analysis", json=payload)
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert "es_url" in data
        assert "es_version" in data
        assert "logs" in data

    def test_get_elasticsearch_logs_with_params(self, client):
        """测试获取Elasticsearch日志 - 带参数"""
        response = client.get("/api/v1/monitoring/elasticsearch?query=ERROR&time_range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data

    def test_get_elasticsearch_logs_invalid_time_range(self, client):
        """测试获取Elasticsearch日志 - 无效时间范围"""
        response = client.get("/api/v1/monitoring/elasticsearch?time_range=invalid")
        assert response.status_code == 422


# ============================================================
# 4. Tempo Tests
# ============================================================


class TestTempo:
    """Tempo测试"""

    def test_get_tempo_traces_success(self, client):
        """测试获取Tempo追踪 - 成功"""
        response = client.get("/api/v1/monitoring/tempo")
        assert response.status_code == 200
        data = response.json()
        assert "tempo_url" in data
        assert "tempo_version" in data
        assert "traces" in data

    def test_get_tempo_traces_with_params(self, client):
        """测试获取Tempo追踪 - 带参数"""
        response = client.get(
            "/api/v1/monitoring/tempo?service=api&trace_id=test-123&time_range=1h"
        )
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert "loki_url" in data
        assert "loki_version" in data
        assert "logs" in data

    def test_get_loki_logs_with_params(self, client):
        """测试获取Loki日志 - 带参数"""
        response = client.get('/api/v1/monitoring/loki?query={job="api"}&time_range=1h')
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert "vm_url" in data
        assert "vm_version" in data
        assert "metrics" in data

    def test_get_victoriametrics_with_params(self, client):
        """测试获取VictoriaMetrics - 带参数"""
        response = client.get("/api/v1/monitoring/victoriametrics?query=up&time_range=1h")
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        assert "nodes" in data
        assert "edges" in data

    def test_get_tracing_visualization_with_params(self, client):
        """测试获取追踪可视化 - 带参数"""
        response = client.get(
            "/api/v1/monitoring/tracing-visualization?trace_id=test-123&service=api&time_range=1h"
        )
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert "trace_id" in data
        assert "service_calls" in data

    def test_get_cross_service_tracing_with_params(self, client):
        """测试获取跨服务追踪 - 带参数"""
        response = client.get(
            "/api/v1/monitoring/cross-service-tracing?trace_id=test-123&time_range=1h"
        )
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert "fastapi_version" in data
        assert "total_requests" in data
        assert "endpoints" in data

    def test_get_fastapi_telemetry_with_params(self, client):
        """测试获取FastAPI遥测 - 带参数"""
        response = client.get(
            "/api/v1/monitoring/fastapi-telemetry?endpoint=/api/v1/metrics&time_range=1h"
        )
        assert response.status_code == 200
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
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_post_telemetry_core_success(self, mock_metrics, client):
        """测试上报核心遥测 - 成功"""
        mock_metrics.push = Mock()
        mock_metrics.push_metric = Mock()

        payload = {"metric_name": "cpu", "metric_value": 75.5, "labels": {"host": "server-01"}}
        response = client.post("/api/v1/monitoring/telemetry-core", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    def test_post_telemetry_core_validation_error(self, client):
        """测试上报核心遥测 - 验证错误"""
        payload = {"metric_name": "", "metric_value": 75.5}  # 空名称
        response = client.post("/api/v1/monitoring/telemetry-core", json=payload)
        assert response.status_code == 422


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
        assert response.status_code == 200
        data = response.json()
        assert data["query_type"] == "metrics"
        assert "data" in data

    def test_get_observability_query_logs(self, client):
        """测试可观测性查询 - 日志"""
        response = client.get("/api/v1/monitoring/observability-query?query_type=logs&query=ERROR")
        assert response.status_code == 200
        data = response.json()
        assert data["query_type"] == "logs"
        assert "data" in data

    def test_get_observability_query_traces(self, client):
        """测试可观测性查询 - 追踪"""
        response = client.get("/api/v1/monitoring/observability-query?query_type=traces&query=api")
        assert response.status_code == 200
        data = response.json()
        assert data["query_type"] == "traces"
        assert "data" in data

    def test_get_observability_query_invalid_type(self, client):
        """测试可观测性查询 - 无效类型"""
        response = client.get("/api/v1/monitoring/observability-query?query_type=invalid")
        assert response.status_code == 422


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
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "checks" in data

    def test_post_readiness_check_success(self, client):
        """测试更新就绪状态 - 成功"""
        payload = {"ready": True, "reason": "Service is ready"}
        response = client.post("/api/v1/monitoring/readiness-check", json=payload)
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "checks" in data

    def test_post_health_check_success(self, client):
        """测试执行健康检查 - 成功"""
        payload = {"service_name": "api-server"}
        response = client.post("/api/v1/monitoring/health-check", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "status" in data

    def test_post_health_check_validation_error(self, client):
        """测试执行健康检查 - 验证错误"""
        payload = {"service_name": ""}  # 空名称
        response = client.post("/api/v1/monitoring/health-check", json=payload)
        assert response.status_code == 422


# ============================================================
# 15. OTEL Collector Tests
# ============================================================


class TestOTELCollector:
    """OTEL Collector测试"""

    def test_get_otel_collector_success(self, client):
        """测试获取OTEL Collector状态 - 成功"""
        response = client.get("/api/v1/monitoring/otel-collector")
        assert response.status_code == 200
        data = response.json()
        assert "otel_collector_url" in data
        assert "otel_collector_version" in data
        assert "status" in data

    def test_configure_otel_collector_success(self, client):
        """测试配置OTEL Collector - 成功"""
        payload = {"exporters": ["otlp", "prometheus"], "sampling_rate": 0.1}
        response = client.post("/api/v1/monitoring/otel-collector", json=payload)
        assert response.status_code == 200
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
        assert response.status_code == 200
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
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "data" in data

    def test_convert_metrics_invalid_format(self, client):
        """测试转换指标格式 - 无效格式"""
        payload = {"source_format": "invalid", "target_format": "prometheus", "metrics_data": {}}
        response = client.post("/api/v1/monitoring/metrics-converter", json=payload)
        assert response.status_code == 422


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
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @patch("api.monitoring_advanced_router.collect_all")
    def test_export_metrics_success(self, mock_collect, client):
        """测试导出指标 - 成功"""
        mock_collect.return_value = {
            "cpu": {"usage_percent": 50.0},
            "memory": {"usage_percent": 60.0},
        }

        payload = {"endpoint": "http://prometheus:9090/metrics", "metrics": {"cpu": 50.0}}
        response = client.post("/api/v1/monitoring/metrics-exporter", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 18. Prometheus Metrics Tests
# ============================================================


class TestPrometheusMetrics:
    """Prometheus指标测试"""

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_prometheus_metrics_success(self, mock_metrics, client):
        """测试获取Prometheus指标 - 成功"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get("/api/v1/monitoring/prometheus-metrics")
        assert response.status_code == 200
        data = response.json()
        assert "prometheus_url" in data
        assert "metrics" in data

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_prometheus_metrics_with_query(self, mock_metrics, client):
        """测试获取Prometheus指标 - 带查询"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get("/api/v1/monitoring/prometheus-metrics?query=up")
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data


# ============================================================
# 19. Anomaly Analysis Tests
# ============================================================


class TestAnomalyAnalysis:
    """异常分析测试"""

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_anomaly_analysis_success(self, mock_metrics, client):
        """测试获取异常分析 - 成功"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0, 60.0, 70.0, 80.0, 90.0],
            "memory": [40.0, 50.0, 60.0],
            "net_in": [10.0, 20.0],
            "timestamps": ["00:00:00", "00:01:00", "00:02:00", "00:03:00", "00:04:00"],
        }

        response = client.get("/api/v1/monitoring/anomaly-analysis")
        assert response.status_code == 200
        data = response.json()
        assert "total_anomalies" in data
        assert "anomalies" in data

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_anomaly_analysis_with_filters(self, mock_metrics, client):
        """测试获取异常分析 - 带过滤"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get(
            "/api/v1/monitoring/anomaly-analysis?time_range=24h&severity=critical"
        )
        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data

    def test_run_anomaly_analysis_success(self, client):
        """测试执行异常分析 - 成功"""
        payload = {"time_range": "24h", "metrics": ["cpu", "memory"]}
        response = client.post("/api/v1/monitoring/anomaly-analysis", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "task_id" in data


# ============================================================
# 20. Anomaly Detection Tests
# ============================================================


class TestAnomalyDetection:
    """异常检测测试"""

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_anomaly_detection_success(self, mock_metrics, client):
        """测试获取异常检测 - 成功"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get("/api/v1/monitoring/anomaly-detection")
        assert response.status_code == 200
        data = response.json()
        assert "total_anomalies" in data
        assert "anomalies" in data

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_anomaly_detection_with_filters(self, mock_metrics, client):
        """测试获取异常检测 - 带过滤"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get(
            "/api/v1/monitoring/anomaly-detection?time_range=24h&severity=critical"
        )
        assert response.status_code == 200
        data = response.json()
        assert "anomalies" in data

    def test_run_anomaly_detection_success(self, client):
        """测试执行异常检测 - 成功"""
        payload = {"time_range": "24h", "algorithm": "isolation_forest"}
        response = client.post("/api/v1/monitoring/anomaly-detection", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "task_id" in data


# ============================================================
# 21. Linux Logs Tests
# ============================================================


class TestLinuxLogs:
    """Linux日志测试"""

    @patch("api.monitoring_advanced_router.get_linux_logs")
    @patch("api.monitoring_advanced_router.LINUX_HOSTS", [])
    def test_get_linux_logs_no_hosts(self, mock_get_logs, client):
        """测试获取Linux日志 - 无配置主机"""
        response = client.get("/api/v1/monitoring/linux-logs?host_name=test")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data

    @patch("api.monitoring_advanced_router.get_linux_logs")
    @patch("api.monitoring_advanced_router.LINUX_HOSTS", [{"name": "test", "host": "192.168.1.1"}])
    async def test_get_linux_logs_success(self, mock_get_logs, client):
        """测试获取Linux日志 - 成功"""
        mock_get_logs.return_value = [{"timestamp": "2024-01-01T00:00:00", "message": "Test log"}]

        response = client.get(
            "/api/v1/monitoring/linux-logs?host_name=test&source=syslog&newest=10"
        )
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data

    @patch("api.monitoring_advanced_router.LINUX_HOSTS", [{"name": "test", "host": "192.168.1.1"}])
    def test_get_linux_logs_host_not_found(self, client):
        """测试获取Linux日志 - 主机不存在"""
        response = client.get("/api/v1/monitoring/linux-logs?host_name=nonexistent")
        assert response.status_code == 404

    def test_get_linux_logs_invalid_source(self, client):
        """测试获取Linux日志 - 无效源"""
        response = client.get("/api/v1/monitoring/linux-logs?host_name=test&source=invalid")
        assert response.status_code == 422


# ============================================================
# 22. Log Search Tests
# ============================================================


class TestLogSearch:
    """日志搜索测试"""

    @patch("api.monitoring_advanced_router.search_logs")
    async def test_search_logs_success(self, mock_search, client):
        """测试搜索日志 - 成功"""
        mock_search.return_value = [
            {"TimeGenerated": "2024-01-01T00:00:00", "Message": "Test error"}
        ]

        response = client.get("/api/v1/monitoring/log-search?keyword=ERROR&time_range=1h&newest=10")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data

    def test_search_logs_invalid_keyword(self, client):
        """测试搜索日志 - 无效关键词"""
        response = client.get("/api/v1/monitoring/log-search?keyword=ab")  # 少于3个字符
        assert response.status_code == 422


# ============================================================
# 23. Error Logs Tests
# ============================================================


class TestErrorLogs:
    """错误日志测试"""

    @patch("api.monitoring_advanced_router.get_system_errors")
    @patch("api.monitoring_advanced_router.get_linux_errors")
    @patch("api.monitoring_advanced_router.LINUX_HOSTS", [])
    async def test_get_error_logs_success(self, mock_linux_errors, mock_system_errors, client):
        """测试获取错误日志 - 成功"""
        mock_system_errors.return_value = [
            {"TimeGenerated": "2024-01-01T00:00:00", "Message": "System error"}
        ]
        mock_linux_errors.return_value = []

        response = client.get("/api/v1/monitoring/error-logs?platform=all&newest=10")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data

    @patch("api.monitoring_advanced_router.get_system_errors")
    @patch("api.monitoring_advanced_router.get_linux_errors")
    @patch("api.monitoring_advanced_router.LINUX_HOSTS", [])
    async def test_get_error_logs_windows_only(self, mock_linux_errors, mock_system_errors, client):
        """测试获取错误日志 - 仅Windows"""
        mock_system_errors.return_value = []
        mock_linux_errors.return_value = []

        response = client.get("/api/v1/monitoring/error-logs?platform=windows&newest=10")
        assert response.status_code == 200
        data = response.json()
        assert "logs" in data

    def test_post_error_logs_success(self, client):
        """测试上报错误日志 - 成功"""
        payload = {
            "timestamp": "2024-01-01T00:00:00",
            "level": "error",
            "message": "Test error",
            "source": "test",
        }
        response = client.post("/api/v1/monitoring/error-logs", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 24. Log Collection Tests
# ============================================================


class TestLogCollection:
    """日志采集测试"""

    def test_get_log_collection_status_success(self, client):
        """测试获取日志采集状态 - 成功"""
        response = client.get("/api/v1/monitoring/log-collection")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "total_sources" in data
        assert "sources" in data

    def test_configure_log_collection_success(self, client):
        """测试配置日志采集 - 成功"""
        payload = {"enabled": True, "interval_seconds": 60, "retention_days": 30}
        response = client.post("/api/v1/monitoring/log-collection", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    def test_configure_log_collection_validation_error(self, client):
        """测试配置日志采集 - 验证错误"""
        payload = {"enabled": True, "interval_seconds": 5}  # 小于最小值10
        response = client.post("/api/v1/monitoring/log-collection", json=payload)
        assert response.status_code == 422


# ============================================================
# 25. API Performance Tests
# ============================================================


class TestAPIPerformance:
    """API性能测试"""

    def test_get_api_performance_success(self, client):
        """测试获取API性能 - 成功"""
        response = client.get("/api/v1/monitoring/api-performance")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "endpoints" in data

    def test_get_api_performance_with_filter(self, client):
        """测试获取API性能 - 带过滤"""
        response = client.get(
            "/api/v1/monitoring/api-performance?endpoint=/api/v1/metrics&time_range=1h"
        )
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data


# ============================================================
# 26. APM Tests
# ============================================================


class TestAPM:
    """APM测试"""

    def test_get_apm_data_success(self, client):
        """测试获取APM数据 - 成功"""
        response = client.get("/api/v1/monitoring/apm")
        assert response.status_code == 200
        data = response.json()
        assert "total_services" in data
        assert "services" in data

    def test_get_apm_data_with_filter(self, client):
        """测试获取APM数据 - 带过滤"""
        response = client.get("/api/v1/monitoring/apm?service=api-service&time_range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "services" in data


# ============================================================
# 27. Cloud Monitoring Tests
# ============================================================


class TestCloudMonitoring:
    """云监控测试"""

    def test_get_cloud_monitoring_success(self, client):
        """测试获取云监控 - 成功"""
        response = client.get("/api/v1/monitoring/cloud-monitoring")
        assert response.status_code == 200
        data = response.json()
        assert "total_instances" in data
        assert "clouds" in data

    def test_get_cloud_monitoring_with_filter(self, client):
        """测试获取云监控 - 带过滤"""
        response = client.get("/api/v1/monitoring/cloud-monitoring?provider=aws&time_range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "clouds" in data

    def test_get_cloud_monitoring_invalid_provider(self, client):
        """测试获取云监控 - 无效提供商"""
        response = client.get("/api/v1/monitoring/cloud-monitoring?provider=invalid")
        assert response.status_code == 422

    def test_configure_cloud_monitoring_success(self, client):
        """测试配置云监控 - 成功"""
        payload = {"enabled": True, "interval_seconds": 60}
        response = client.post("/api/v1/monitoring/cloud-monitoring", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 28. K8s Monitoring Tests
# ============================================================


class TestK8sMonitoring:
    """K8s监控测试"""

    def test_get_k8s_monitoring_success(self, client):
        """测试获取K8s监控 - 成功"""
        response = client.get("/api/v1/monitoring/k8s-monitoring")
        assert response.status_code == 200
        data = response.json()
        assert "total_pods" in data
        assert "namespaces" in data

    def test_get_k8s_monitoring_with_filter(self, client):
        """测试获取K8s监控 - 带过滤"""
        response = client.get("/api/v1/monitoring/k8s-monitoring?namespace=default&time_range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "namespaces" in data

    def test_configure_k8s_monitoring_success(self, client):
        """测试配置K8s监控 - 成功"""
        payload = {"enabled": True, "interval_seconds": 60}
        response = client.post("/api/v1/monitoring/k8s-monitoring", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 29. Docker Monitoring Tests
# ============================================================


class TestDockerMonitoring:
    """Docker监控测试"""

    def test_get_docker_monitoring_success(self, client):
        """测试获取Docker监控 - 成功"""
        response = client.get("/api/v1/monitoring/docker-monitoring")
        assert response.status_code == 200
        data = response.json()
        assert "total_containers" in data
        assert "containers" in data

    def test_get_docker_monitoring_with_filter(self, client):
        """测试获取Docker监控 - 带过滤"""
        response = client.get(
            "/api/v1/monitoring/docker-monitoring?container=aiops-api&time_range=1h"
        )
        assert response.status_code == 200
        data = response.json()
        assert "containers" in data

    def test_configure_docker_monitoring_success(self, client):
        """测试配置Docker监控 - 成功"""
        payload = {"enabled": True, "interval_seconds": 60}
        response = client.post("/api/v1/monitoring/docker-monitoring", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 30. macOS Monitoring Tests
# ============================================================


class TestMacOSMonitoring:
    """macOS监控测试"""

    @patch("api.monitoring_advanced_router.collect_all")
    @patch("api.monitoring_advanced_router.get_top_processes")
    async def test_get_macos_monitoring_success(self, mock_processes, mock_collect, client):
        """测试获取macOS监控 - 成功"""
        mock_collect.return_value = {
            "cpu": {"usage_percent": 50.0},
            "memory": {"usage_percent": 60.0},
            "disk": {"usage_percent": 70.0},
            "network": {"recv_speed_mb": 10.0, "sent_speed_mb": 5.0},
        }
        mock_processes.return_value = []

        response = client.get("/api/v1/monitoring/macos-monitoring")
        assert response.status_code == 200
        data = response.json()
        assert "platform" in data
        assert "cpu_usage" in data

    def test_configure_macos_monitoring_success(self, client):
        """测试配置macOS监控 - 成功"""
        payload = {"enabled": True, "interval_seconds": 60}
        response = client.post("/api/v1/monitoring/macos-monitoring", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 31. Windows Monitoring Tests
# ============================================================


class TestWindowsMonitoring:
    """Windows监控测试"""

    @patch("api.monitoring_advanced_router.collect_all")
    @patch("api.monitoring_advanced_router.get_top_processes")
    async def test_get_windows_monitoring_success(self, mock_processes, mock_collect, client):
        """测试获取Windows监控 - 成功"""
        mock_collect.return_value = {
            "cpu": {"usage_percent": 50.0},
            "memory": {"usage_percent": 60.0},
            "disk": {"usage_percent": 70.0},
            "network": {"recv_speed_mb": 10.0, "sent_speed_mb": 5.0},
        }
        mock_processes.return_value = []

        response = client.get("/api/v1/monitoring/windows-monitoring")
        assert response.status_code == 200
        data = response.json()
        assert "platform" in data
        assert "cpu_usage" in data

    def test_configure_windows_monitoring_success(self, client):
        """测试配置Windows监控 - 成功"""
        payload = {"enabled": True, "interval_seconds": 60}
        response = client.post("/api/v1/monitoring/windows-monitoring", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 32. Linux Monitoring Tests
# ============================================================


class TestLinuxMonitoring:
    """Linux监控测试"""

    @patch("api.monitoring_advanced_router.collect_all")
    @patch("api.monitoring_advanced_router.LINUX_HOSTS", [])
    async def test_get_linux_monitoring_no_hosts(self, mock_collect, client):
        """测试获取Linux监控 - 无配置主机"""
        mock_collect.return_value = {
            "cpu": {"usage_percent": 50.0},
            "memory": {"usage_percent": 60.0},
            "disk": {"usage_percent": 70.0},
            "network": {"recv_speed_mb": 10.0, "sent_speed_mb": 5.0},
        }

        response = client.get("/api/v1/monitoring/linux-monitoring")
        assert response.status_code == 200
        data = response.json()
        assert "platform" in data

    @patch("api.monitoring_advanced_router.LINUX_HOSTS", [{"name": "test", "host": "192.168.1.1"}])
    def test_get_linux_monitoring_with_host(self, client):
        """测试获取Linux监控 - 带主机"""
        response = client.get("/api/v1/monitoring/linux-monitoring?host_name=test&time_range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "platform" in data

    @patch("api.monitoring_advanced_router.LINUX_HOSTS", [{"name": "test", "host": "192.168.1.1"}])
    def test_get_linux_monitoring_host_not_found(self, client):
        """测试获取Linux监控 - 主机不存在"""
        response = client.get("/api/v1/monitoring/linux-monitoring?host_name=nonexistent")
        assert response.status_code == 404

    def test_configure_linux_monitoring_success(self, client):
        """测试配置Linux监控 - 成功"""
        payload = {"enabled": True, "interval_seconds": 60}
        response = client.post("/api/v1/monitoring/linux-monitoring", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 33. Process Monitoring Tests
# ============================================================


class TestProcessMonitoring:
    """进程监控测试"""

    @patch("api.monitoring_advanced_router.get_top_processes")
    async def test_get_process_monitoring_success(self, mock_processes, client):
        """测试获取进程监控 - 成功"""
        mock_processes.return_value = [
            {"pid": 1, "name": "init", "cpu_percent": 0.1, "memory_percent": 0.1}
        ]

        response = client.get("/api/v1/monitoring/process-monitoring")
        assert response.status_code == 200
        data = response.json()
        assert "total_processes" in data
        assert "processes" in data

    @patch("api.monitoring_advanced_router.get_top_processes")
    async def test_get_process_monitoring_with_limit(self, mock_processes, client):
        """测试获取进程监控 - 带限制"""
        mock_processes.return_value = []

        response = client.get("/api/v1/monitoring/process-monitoring?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "processes" in data

    def test_get_process_monitoring_invalid_limit(self, client):
        """测试获取进程监控 - 无效限制"""
        response = client.get("/api/v1/monitoring/process-monitoring?limit=200")
        assert response.status_code == 422

    def test_configure_process_monitoring_success(self, client):
        """测试配置进程监控 - 成功"""
        payload = {"enabled": True, "interval_seconds": 60}
        response = client.post("/api/v1/monitoring/process-monitoring", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True


# ============================================================
# 34. Metrics History Tests
# ============================================================


class TestMetricsHistory:
    """指标历史测试"""

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_metrics_history_success(self, mock_metrics, client):
        """测试获取指标历史 - 成功"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0, 60.0, 70.0],
            "memory": [40.0, 50.0, 60.0],
            "net_in": [10.0, 20.0, 30.0],
            "timestamps": ["00:00:00", "00:01:00", "00:02:00"],
        }

        response = client.get("/api/v1/monitoring/metrics-history")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "data_points" in data

    @patch("api.monitoring_advanced_router.metrics_history")
    def test_get_metrics_history_with_filter(self, mock_metrics, client):
        """测试获取指标历史 - 带过滤"""
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get("/api/v1/monitoring/metrics-history?metric=cpu&time_range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data


# ============================================================
# 35. Metrics Snapshot Tests
# ============================================================


class TestMetricsSnapshot:
    """指标快照测试"""

    @patch("api.monitoring_advanced_router.collect_all")
    async def test_get_metrics_snapshot_success(self, mock_collect, client):
        """测试获取指标快照 - 成功"""
        mock_collect.return_value = {
            "cpu": {"usage_percent": 50.0},
            "memory": {"usage_percent": 60.0},
            "disk": {"usage_percent": 70.0},
        }

        response = client.get("/api/v1/monitoring/metrics-snapshot")
        assert response.status_code == 200
        data = response.json()
        assert "timestamp" in data
        assert "snapshot" in data


# ============================================================
# 36. Metrics Tests
# ============================================================


class TestMetrics:
    """指标测试"""

    @patch("api.monitoring_advanced_router.collect_all")
    @patch("api.monitoring_advanced_router.metrics_history")
    async def test_get_metrics_success(self, mock_metrics, mock_collect, client):
        """测试获取系统指标 - 成功"""
        mock_collect.return_value = {
            "cpu": {"usage_percent": 50.0},
            "memory": {"usage_percent": 60.0},
        }
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get("/api/v1/monitoring/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "current" in data
        assert "history" in data

    @patch("api.monitoring_advanced_router.collect_all")
    @patch("api.monitoring_advanced_router.metrics_history")
    async def test_get_metrics_with_time_range(self, mock_metrics, mock_collect, client):
        """测试获取系统指标 - 带时间范围"""
        mock_collect.return_value = {}
        mock_metrics.to_dict.return_value = {
            "cpu": [50.0],
            "memory": [40.0],
            "net_in": [10.0],
            "timestamps": ["00:00:00"],
        }

        response = client.get("/api/v1/monitoring/metrics?time_range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "current" in data


# ============================================================
# Data Validation Tests
# ============================================================


class TestDataValidation:
    """数据验证测试"""

    def test_log_alert_rule_invalid_severity(self, client):
        """测试日志告警规则 - 无效严重级别"""
        payload = {"name": "Test", "pattern": "test", "severity": "invalid"}
        response = client.post("/api/v1/monitoring/log-alerting", json=payload)
        assert response.status_code == 422

    def test_metrics_converter_invalid_format(self, client):
        """测试指标转换 - 无效格式"""
        payload = {"source_format": "invalid", "target_format": "prometheus", "metrics_data": {}}
        response = client.post("/api/v1/monitoring/metrics-converter", json=payload)
        assert response.status_code == 422

    def test_monitoring_config_invalid_interval(self, client):
        """测试监控配置 - 无效间隔"""
        payload = {"enabled": True, "interval_seconds": 5}  # 小于最小值10
        response = client.post("/api/v1/monitoring/log-collection", json=payload)
        assert response.status_code == 422


# ============================================================
# Error Handling Tests
# ============================================================


class TestErrorHandling:
    """错误处理测试"""

    def test_invalid_json_payload(self, client):
        """测试无效JSON负载"""
        response = client.post("/api/v1/monitoring/log-alerting", data="invalid json")
        assert response.status_code == 422

    def test_invalid_endpoint(self, client):
        """测试无效端点"""
        response = client.get("/api/v1/monitoring/invalid-endpoint")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """测试不允许的方法"""
        response = client.put("/api/v1/monitoring/log-alerting")
        assert response.status_code == 405

    def test_missing_required_field(self, client):
        """测试缺少必填字段"""
        payload = {
            "name": "Test"
            # 缺少pattern
        }
        response = client.post("/api/v1/monitoring/log-alerting", json=payload)
        assert response.status_code == 422
