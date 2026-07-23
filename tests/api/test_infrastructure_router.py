# -*- coding: utf-8 -*-
"""Infrastructure Router Tests
基础设施路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.config_center"] = MagicMock()
sys.modules["core.distributed_storage"] = MagicMock()
sys.modules["core.flink_stream_processor"] = MagicMock()
sys.modules["core.kafka_stream_processor"] = MagicMock()
sys.modules["core.l1l2_data_flow_integrator"] = MagicMock()
sys.modules["core.monitoring_infrastructure"] = MagicMock()
sys.modules["core.monitoring_system_integrator"] = MagicMock()

from api.infrastructure_router import router


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestInfrastructureRouter:
    """测试基础设施路由"""

    def test_send_kafka_message(self, client):
        """测试发送Kafka消息"""
        with patch("api.infrastructure_router.get_kafka_processor") as mock_kafka:
            mock_processor = Mock()
            mock_processor.send_message.return_value = True
            mock_kafka.return_value = mock_processor

            response = client.post(
                "/api/v1/infrastructure/kafka/send",
                json={"topic": "test", "key": "key1", "value": {"data": "test"}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_get_kafka_status(self, client):
        """测试获取Kafka状态"""
        with patch("api.infrastructure_router.get_kafka_processor") as mock_kafka:
            mock_processor = Mock()
            mock_processor.stub_enabled = True
            mock_processor.get_stub_messages.return_value = []
            mock_kafka.return_value = mock_processor

            response = client.get("/api/v1/infrastructure/kafka/status")
            assert response.status_code == 200
            data = response.json()
            assert "stub_enabled" in data

    def test_create_flink_job(self, client):
        """测试创建Flink作业"""
        with patch("api.infrastructure_router.get_flink_job_manager") as mock_flink:
            mock_manager = Mock()
            mock_flink.return_value = mock_manager

            response = client.post(
                "/api/v1/infrastructure/flink/job",
                json={"job_name": "test-job", "job_type": "streaming"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["job_name"] == "test-job"

    def test_list_flink_jobs(self, client):
        """测试列出Flink作业"""
        with patch("api.infrastructure_router.get_flink_job_manager") as mock_flink:
            mock_manager = Mock()
            mock_manager.jobs = {}
            mock_manager.get_job_status.return_value = {"job_name": "test-job", "status": "running"}
            mock_flink.return_value = mock_manager

            response = client.get("/api/v1/infrastructure/flink/jobs")
            assert response.status_code == 200
            data = response.json()
            assert "jobs" in data

    def test_get_storage_health(self, client):
        """测试获取存储健康状态"""
        with patch("api.infrastructure_router.get_distributed_storage_manager") as mock_storage:
            mock_manager = Mock()
            mock_manager.health_check.return_value = {"status": "healthy"}
            mock_storage.return_value = mock_manager

            response = client.get("/api/v1/infrastructure/storage/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_set_config(self, client):
        """测试设置配置"""
        with patch("api.infrastructure_router.get_config_center") as mock_config:
            mock_center = Mock()
            mock_center.set_config.return_value = True
            mock_config.return_value = mock_center

            response = client.post(
                "/api/v1/infrastructure/config", json={"key": "test-key", "value": "test-value"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["key"] == "test-key"

    def test_get_config(self, client):
        """测试获取配置"""
        with patch("api.infrastructure_router.get_config_center") as mock_config:
            mock_center = Mock()
            mock_center.get_config.return_value = "test-value"
            mock_config.return_value = mock_center

            response = client.get("/api/v1/infrastructure/config/test-key")
            assert response.status_code == 200
            data = response.json()
            assert data["key"] == "test-key"

    def test_get_infrastructure_health(self, client):
        """测试获取基础设施健康状态"""
        with (
            patch("api.infrastructure_router.get_kafka_processor") as mock_kafka,
            patch("api.infrastructure_router.get_flink_job_manager") as mock_flink,
            patch("api.infrastructure_router.get_distributed_storage_manager") as mock_storage,
            patch("api.infrastructure_router.get_config_center") as mock_config,
            patch("api.infrastructure_router.get_monitoring_infrastructure") as mock_monitoring,
            patch("api.infrastructure_router.get_l1l2_data_flow_integrator") as mock_dataflow,
        ):

            mock_kafka.return_value = Mock(stub_enabled=True)
            mock_flink.return_value = Mock(stub_enabled=True)
            mock_storage.return_value = Mock()
            mock_config.return_value = Mock(stub_enabled=True)
            mock_monitoring.return_value = Mock(metrics_collector=Mock(stub_enabled=True))
            mock_dataflow.return_value = Mock()

            response = client.get("/api/v1/infrastructure/health")
            assert response.status_code == 200
            data = response.json()
            assert "kafka" in data
            assert "flink" in data

    def test_get_infrastructure_health_error(self, client):
        """测试基础设施健康状态异常"""
        with patch("api.infrastructure_router.get_kafka_processor") as mock_kafka:
            mock_kafka.side_effect = RuntimeError("kafka error")
            response = client.get("/api/v1/infrastructure/health")
            assert response.status_code == 500

    def test_get_read_connection(self, client):
        """测试获取读连接信息"""
        with patch("api.infrastructure_router.get_distributed_storage_manager") as mock_storage:
            mock_storage.return_value = Mock(
                get_read_connection_info=Mock(return_value={"host": "localhost"})
            )
            response = client.get("/api/v1/infrastructure/storage/read-connection")
            assert response.status_code == 200

    def test_get_write_connection(self, client):
        """测试获取写连接信息"""
        with patch("api.infrastructure_router.get_distributed_storage_manager") as mock_storage:
            mock_storage.return_value = Mock(
                get_write_connection_info=Mock(return_value={"host": "localhost"})
            )
            response = client.get("/api/v1/infrastructure/storage/write-connection")
            assert response.status_code == 200

    def test_get_storage_health_error(self, client):
        """测试存储健康异常"""
        with patch("api.infrastructure_router.get_distributed_storage_manager") as mock_storage:
            mock_storage.side_effect = RuntimeError("storage error")
            response = client.get("/api/v1/infrastructure/storage/health")
            assert response.status_code == 500

    def test_get_all_configs(self, client):
        """测试获取所有配置"""
        with patch("api.infrastructure_router.get_config_center") as mock_config:
            mock_center = Mock()
            mock_center.get_all_configs.return_value = {"a": 1}
            mock_config.return_value = mock_center
            response = client.get("/api/v1/infrastructure/config")
            assert response.status_code == 200
            assert "configs" in response.json()

    def test_get_config_error(self, client):
        """测试获取单个配置异常"""
        with patch("api.infrastructure_router.get_config_center") as mock_config:
            mock_config.side_effect = RuntimeError("config error")
            response = client.get("/api/v1/infrastructure/config/test-key")
            assert response.status_code == 500

    def test_set_config_error(self, client):
        """测试设置配置失败500"""
        with patch("api.infrastructure_router.get_config_center") as mock_config:
            mock_center = Mock()
            mock_center.set_config.return_value = False
            mock_config.return_value = mock_center
            response = client.post("/api/v1/infrastructure/config", json={"key": "k", "value": "v"})
            assert response.status_code == 500

    def test_get_monitoring_status(self, client):
        """测试获取监控状态"""
        with patch("api.infrastructure_router.get_monitoring_infrastructure") as mock_monitoring:
            mock_monitoring.return_value = Mock(
                get_monitoring_status=Mock(return_value={"status": "ok"})
            )
            response = client.get("/api/v1/infrastructure/monitoring/status")
            assert response.status_code == 200

    def test_record_metric(self, client):
        """测试记录指标"""
        with patch("api.infrastructure_router.get_monitoring_infrastructure") as mock_monitoring:
            mock_monitoring.return_value = Mock(metrics_collector=Mock(increment_counter=Mock()))
            response = client.post("/api/v1/infrastructure/monitoring/metrics")
            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_get_data_flow_stats(self, client):
        """测试获取数据流统计"""
        with patch("api.infrastructure_router.get_l1l2_data_flow_integrator") as mock_df:
            mock_df.return_value = Mock(
                get_data_flow_stats=Mock(
                    return_value={
                        "total_processed": 1,
                        "total_analyzed": 1,
                        "total_errors": 0,
                        "avg_processing_time_ms": 0.0,
                        "error_rate": 0.0,
                        "analysis_rate": 0.0,
                    }
                )
            )
            response = client.get("/api/v1/infrastructure/data-flow/stats")
            assert response.status_code == 200

    def test_start_data_flow(self, client):
        """测试启动数据流"""
        with patch("api.infrastructure_router.get_l1l2_data_flow_integrator") as mock_df:
            mock_df.return_value = Mock(start_data_flow=Mock(return_value=True))
            response = client.post("/api/v1/infrastructure/data-flow/start")
            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_stop_data_flow(self, client):
        """测试停止数据流"""
        with patch("api.infrastructure_router.get_l1l2_data_flow_integrator") as mock_df:
            mock_df.return_value = Mock(stop_data_flow=Mock(return_value=True))
            response = client.post("/api/v1/infrastructure/data-flow/stop")
            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_get_monitoring_summary(self, client):
        """测试获取监控摘要"""
        with patch("api.infrastructure_router.get_monitoring_system_integrator") as mock_ms:
            mock_ms.return_value = Mock(
                get_monitoring_summary=Mock(
                    return_value={
                        "total_alerts": 0,
                        "active_alerts": 0,
                        "critical_alerts": 0,
                        "error_alerts": 0,
                        "warning_alerts": 0,
                        "total_dashboards": 0,
                    }
                )
            )
            response = client.get("/api/v1/infrastructure/monitoring/summary")
            assert response.status_code == 200

    def test_get_alerts(self, client):
        """测试获取告警列表"""
        with patch("api.infrastructure_router.get_monitoring_system_integrator") as mock_ms:
            mock_ms.return_value = Mock(get_active_alerts=Mock(return_value=[{"id": "a1"}]))
            response = client.get("/api/v1/infrastructure/alerts")
            assert response.status_code == 200
            assert "alerts" in response.json()

    def test_resolve_alert(self, client):
        """测试解决告警"""
        with patch("api.infrastructure_router.get_monitoring_system_integrator") as mock_ms:
            mock_ms.return_value = Mock(resolve_alert=Mock())
            response = client.post("/api/v1/infrastructure/alerts/a1/resolve")
            assert response.status_code == 200
            assert response.json()["success"] is True

    def test_resolve_alert_error(self, client):
        """测试解决告警异常"""
        with patch("api.infrastructure_router.get_monitoring_system_integrator") as mock_ms:
            mock_ms.side_effect = RuntimeError("alert error")
            response = client.post("/api/v1/infrastructure/alerts/a1/resolve")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
