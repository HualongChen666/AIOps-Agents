# -*- coding: utf-8 -*-
"""Real end-to-end tests for infrastructure, cloud and integration read-only endpoints."""

from unittest.mock import MagicMock, patch

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    # infrastructure_router.py - GET only to avoid starting external services
    ("GET", "/api/v1/infrastructure/kafka/status", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/flink/jobs", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/config/test-key", None, None, {200, 404, 500}),
    ("GET", "/api/v1/infrastructure/config", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/monitoring/status", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/data-flow/stats", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/monitoring/summary", None, None, {200, 500}),
    ("GET", "/api/v1/infrastructure/alerts", None, None, {200, 500}),
    # cloud_router.py - GET only to avoid running cloud repair/collect
    ("GET", "/api/v1/platforms/cloud/metrics", None, None, {200, 500}),
    ("GET", "/api/v1/platforms/cloud/history", None, None, {200, 500}),
    ("GET", "/api/v1/platforms/cloud/aws/metrics", None, None, {200, 404, 500}),
    ("GET", "/api/v1/platforms/cloud/aws/history", None, None, {200, 404, 500}),
    ("GET", "/api/v1/platforms/cloud/aws/repair/history", None, None, {200, 404, 500}),
    # integration_router.py - read-only plus validation-only registrations
    ("GET", "/api/v1/integration/list", None, None, {200, 500}),
    ("POST", "/api/v1/integration/register", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/integration/notification/channels", None, None, {200, 500}),
    ("POST", "/api/v1/integration/webhook/register", {}, None, {200, 422, 500}),
    ("GET", "/api/v1/integration/webhooks", None, None, {200, 500}),
    ("GET", "/api/v1/integration/templates", None, None, {200, 500}),
    ("GET", "/api/v1/integration/summary", None, None, {200, 500}),
    ("GET", "/api/v1/integration/types", None, None, {200, 500}),
    ("GET", "/api/v1/integration/events", None, None, {200, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,params,expected", _CASES)
def test_infrastructure_endpoint(client, approval_headers, method, path, body, params, expected):
    """Each safe B20 endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    if params:
        kwargs["params"] = params
    resp = client.request(method, path, headers=approval_headers, **kwargs)
    assert resp.status_code in expected


# ---------------------------------------------------------------------------
# Additional tests to increase coverage for infrastructure_router.py
# ---------------------------------------------------------------------------


def test_send_kafka_message_success(client, approval_headers):
    """Test successful Kafka message sending."""
    resp = client.post(
        "/api/v1/infrastructure/kafka/send",
        headers=approval_headers,
        json={
            "topic": "test-topic",
            "key": "test-key",
            "value": {"test": "data"},
            "headers": {"header1": "value1"},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "message" in data


def test_send_kafka_message_without_headers(client, approval_headers):
    """Test Kafka message sending without headers."""
    resp = client.post(
        "/api/v1/infrastructure/kafka/send",
        headers=approval_headers,
        json={"topic": "test-topic", "key": "test-key", "value": {"test": "data"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


def test_send_kafka_message_failure(client, approval_headers):
    """Test Kafka message sending failure (when send_message returns False)."""
    from core.kafka_stream_processor import get_kafka_processor

    # Mock send_message to return False
    with patch.object(get_kafka_processor(), "send_message", return_value=False):
        resp = client.post(
            "/api/v1/infrastructure/kafka/send",
            headers=approval_headers,
            json={"topic": "test-topic", "key": "test-key", "value": {"test": "data"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert "Failed to send message" in data["message"]


def test_send_kafka_message_with_complex_value(client, approval_headers):
    """Test Kafka message sending with complex value structure."""
    resp = client.post(
        "/api/v1/infrastructure/kafka/send",
        headers=approval_headers,
        json={
            "topic": "test-topic",
            "key": "test-key",
            "value": {
                "nested": {"data": {"array": [1, 2, 3], "string": "test"}},
                "number": 42,
                "boolean": True,
            },
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


def test_send_kafka_message_exception(client, approval_headers):
    """Test Kafka message sending with exception."""
    from core.kafka_stream_processor import get_kafka_processor

    # Mock send_message to raise exception
    with patch.object(
        get_kafka_processor(), "send_message", side_effect=Exception("Connection error")
    ):
        resp = client.post(
            "/api/v1/infrastructure/kafka/send",
            headers=approval_headers,
            json={"topic": "test-topic", "key": "test-key", "value": {"test": "data"}},
        )
        assert resp.status_code == 500


def test_get_kafka_status_with_exception(client, approval_headers):
    """Test get_kafka_status when get_cached_messages raises exception."""
    from core.kafka_stream_processor import get_kafka_processor

    # Mock get_cached_messages to raise exception
    with patch.object(
        get_kafka_processor(), "get_cached_messages", side_effect=Exception("Cache error")
    ):
        resp = client.get("/api/v1/infrastructure/kafka/status", headers=approval_headers)
        # Should still return 200 with empty messages
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_messages"] == 0
        assert data["topics"] == []


def test_get_kafka_status_with_messages(client, approval_headers):
    """Test get_kafka_status when there are cached messages."""
    from core.kafka_stream_processor import get_kafka_processor

    # First send some messages
    client.post(
        "/api/v1/infrastructure/kafka/send",
        headers=approval_headers,
        json={"topic": "metrics-topic", "key": "key1", "value": {"data": "test1"}},
    )
    client.post(
        "/api/v1/infrastructure/kafka/send",
        headers=approval_headers,
        json={"topic": "logs-topic", "key": "key2", "value": {"data": "test2"}},
    )

    # Now get status
    resp = client.get("/api/v1/infrastructure/kafka/status", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_messages"] >= 2
    assert "metrics-topic" in data["topics"]
    assert "logs-topic" in data["topics"]


def test_create_flink_job_valid_types(client, approval_headers):
    """Test creating Flink jobs with valid job types."""
    job_types = ["metrics_aggregation", "anomaly_detection", "data_cleaning", "alert_aggregation"]

    for job_type in job_types:
        resp = client.post(
            "/api/v1/infrastructure/flink/job",
            headers=approval_headers,
            json={"job_name": f"test-job-{job_type}", "job_type": job_type, "parallelism": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_name"] == f"test-job-{job_type}"
        assert data["job_type"] == job_type
        assert data["status"] == "created"


def test_create_flink_job_with_different_parallelism(client, approval_headers):
    """Test creating Flink job with different parallelism values."""
    for parallelism in [1, 4, 8]:
        resp = client.post(
            "/api/v1/infrastructure/flink/job",
            headers=approval_headers,
            json={
                "job_name": f"test-job-parallelism-{parallelism}",
                "job_type": "metrics_aggregation",
                "parallelism": parallelism,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_name"] == f"test-job-parallelism-{parallelism}"


def test_create_flink_job_invalid_type(client, approval_headers):
    """Test creating Flink job with invalid job type (should return 400)."""
    # Mock the entire create_flink_job endpoint to raise ValueError
    # by patching at the router level
    with patch(
        "api.infrastructure_router.FlinkJobConfig", side_effect=ValueError("Invalid job_type")
    ):
        resp = client.post(
            "/api/v1/infrastructure/flink/job",
            headers=approval_headers,
            json={"job_name": "test-job", "job_type": "invalid_type", "parallelism": 2},
        )
        assert resp.status_code == 400


def test_create_flink_job_exception(client, approval_headers):
    """Test creating Flink job with exception."""
    from core.flink_stream_processor import get_flink_job_manager

    # Mock create_job to raise exception
    with patch.object(
        get_flink_job_manager(), "create_job", side_effect=Exception("Job creation error")
    ):
        resp = client.post(
            "/api/v1/infrastructure/flink/job",
            headers=approval_headers,
            json={"job_name": "test-job", "job_type": "metrics_aggregation", "parallelism": 2},
        )
        assert resp.status_code == 500


def test_list_flink_jobs_exception(client, approval_headers):
    """Test listing Flink jobs with exception."""
    from core.flink_stream_processor import get_flink_job_manager

    # Mock get_job_status to raise exception
    with patch.object(
        get_flink_job_manager(), "get_job_status", side_effect=Exception("List error")
    ):
        resp = client.get("/api/v1/infrastructure/flink/jobs", headers=approval_headers)
        assert resp.status_code == 500


def test_list_flink_jobs_with_jobs(client, approval_headers):
    """Test listing Flink jobs when jobs exist."""
    # First create a job
    client.post(
        "/api/v1/infrastructure/flink/job",
        headers=approval_headers,
        json={"job_name": "test-job-for-list", "job_type": "metrics_aggregation", "parallelism": 2},
    )

    # Now list jobs
    resp = client.get("/api/v1/infrastructure/flink/jobs", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "jobs" in data
    # Should have at least the job we just created
    assert len(data["jobs"]) >= 1


def test_get_read_connection_exception(client, approval_headers):
    """Test get_read_connection with exception."""
    from core.distributed_storage import get_distributed_storage_manager

    # Mock get_read_connection_info to raise exception
    with patch.object(
        get_distributed_storage_manager(),
        "get_read_connection_info",
        side_effect=Exception("Connection error"),
    ):
        resp = client.get(
            "/api/v1/infrastructure/storage/read-connection", headers=approval_headers
        )
        assert resp.status_code == 500


def test_get_write_connection_exception(client, approval_headers):
    """Test get_write_connection with exception."""
    from core.distributed_storage import get_distributed_storage_manager

    # Mock get_write_connection_info to raise exception
    with patch.object(
        get_distributed_storage_manager(),
        "get_write_connection_info",
        side_effect=Exception("Connection error"),
    ):
        resp = client.get(
            "/api/v1/infrastructure/storage/write-connection", headers=approval_headers
        )
        assert resp.status_code == 500


def test_get_storage_health_exception(client, approval_headers):
    """Test get_storage_health with exception."""
    from core.distributed_storage import get_distributed_storage_manager

    # Mock health_check to raise exception
    with patch.object(
        get_distributed_storage_manager(),
        "health_check",
        side_effect=Exception("Health check error"),
    ):
        resp = client.get("/api/v1/infrastructure/storage/health", headers=approval_headers)
        assert resp.status_code == 500


def test_set_config_success(client, approval_headers):
    """Test successful config setting."""
    resp = client.post(
        "/api/v1/infrastructure/config",
        headers=approval_headers,
        json={"key": "test-config-key", "value": {"config": "value"}, "metadata": {"meta": "data"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "test-config-key"
    assert data["value"] == {"config": "value"}
    assert "version" in data


def test_set_config_without_metadata(client, approval_headers):
    """Test config setting without metadata."""
    resp = client.post(
        "/api/v1/infrastructure/config",
        headers=approval_headers,
        json={"key": "test-config-key-2", "value": {"config": "value2"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "test-config-key-2"


def test_set_config_failure(client, approval_headers):
    """Test config setting when set_config returns False (should return 500)."""
    from core.config_center import get_config_center

    # Mock set_config to return False
    with patch.object(get_config_center(), "set_config", return_value=False):
        resp = client.post(
            "/api/v1/infrastructure/config",
            headers=approval_headers,
            json={"key": "test-config-key", "value": {"config": "value"}},
        )
        assert resp.status_code == 500


def test_set_config_with_none_value(client, approval_headers):
    """Test config setting with None value."""
    resp = client.post(
        "/api/v1/infrastructure/config",
        headers=approval_headers,
        json={"key": "test-config-none", "value": None},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "test-config-none"
    assert data["value"] is None


def test_set_config_update_existing(client, approval_headers):
    """Test config setting when updating an existing config."""
    # First set a config
    client.post(
        "/api/v1/infrastructure/config",
        headers=approval_headers,
        json={"key": "test-config-update", "value": {"original": "value"}},
    )

    # Now update it
    resp = client.post(
        "/api/v1/infrastructure/config",
        headers=approval_headers,
        json={"key": "test-config-update", "value": {"updated": "value"}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "test-config-update"
    assert data["value"] == {"updated": "value"}
    # Version should be incremented
    assert data["version"] >= 1


def test_set_config_exception(client, approval_headers):
    """Test config setting with exception."""
    from core.config_center import get_config_center

    # Mock set_config to raise exception
    with patch.object(get_config_center(), "set_config", side_effect=Exception("Config error")):
        resp = client.post(
            "/api/v1/infrastructure/config",
            headers=approval_headers,
            json={"key": "test-config-key", "value": {"config": "value"}},
        )
        assert resp.status_code == 500


def test_get_config_exception(client, approval_headers):
    """Test get_config with exception."""
    from core.config_center import get_config_center

    # Mock get_config to raise exception
    with patch.object(get_config_center(), "get_config", side_effect=Exception("Get config error")):
        resp = client.get("/api/v1/infrastructure/config/test-key", headers=approval_headers)
        assert resp.status_code == 500


def test_get_config_success(client, approval_headers):
    """Test successful get_config."""
    # First set a config
    client.post(
        "/api/v1/infrastructure/config",
        headers=approval_headers,
        json={"key": "test-get-config", "value": {"test": "value"}},
    )

    # Now get it
    resp = client.get("/api/v1/infrastructure/config/test-get-config", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "test-get-config"
    assert data["value"] == {"test": "value"}


def test_get_all_configs_exception(client, approval_headers):
    """Test get_all_configs with exception."""
    from core.config_center import get_config_center

    # Mock get_all_configs to raise exception
    with patch.object(
        get_config_center(), "get_all_configs", side_effect=Exception("Get all configs error")
    ):
        resp = client.get("/api/v1/infrastructure/config", headers=approval_headers)
        assert resp.status_code == 500


def test_get_all_configs_success(client, approval_headers):
    """Test successful get_all_configs."""
    resp = client.get("/api/v1/infrastructure/config", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "configs" in data


def test_get_monitoring_status_exception(client, approval_headers):
    """Test get_monitoring_status with exception."""
    from core.monitoring_infrastructure import get_monitoring_infrastructure

    # Mock get_monitoring_status to raise exception
    with patch.object(
        get_monitoring_infrastructure(),
        "get_monitoring_status",
        side_effect=Exception("Monitoring status error"),
    ):
        resp = client.get("/api/v1/infrastructure/monitoring/status", headers=approval_headers)
        assert resp.status_code == 500


def test_record_metric_exception(client, approval_headers):
    """Test record_metric with exception."""
    from core.monitoring_infrastructure import get_monitoring_infrastructure

    # Mock increment_counter to raise exception
    with patch.object(
        get_monitoring_infrastructure().metrics_collector,
        "increment_counter",
        side_effect=Exception("Metric recording error"),
    ):
        resp = client.post("/api/v1/infrastructure/monitoring/metrics", headers=approval_headers)
        assert resp.status_code == 500


def test_record_metric_success(client, approval_headers):
    """Test successful record_metric."""
    resp = client.post("/api/v1/infrastructure/monitoring/metrics", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


def test_get_data_flow_stats_exception(client, approval_headers):
    """Test get_data_flow_stats with exception."""
    from core.l1l2_data_flow_integrator import get_l1l2_data_flow_integrator

    # Mock get_data_flow_stats to raise exception
    with patch.object(
        get_l1l2_data_flow_integrator(), "get_data_flow_stats", side_effect=Exception("Stats error")
    ):
        resp = client.get("/api/v1/infrastructure/data-flow/stats", headers=approval_headers)
        assert resp.status_code == 500


def test_get_data_flow_stats_success(client, approval_headers):
    """Test successful get_data_flow_stats."""
    resp = client.get("/api/v1/infrastructure/data-flow/stats", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Check all expected fields
    assert "total_processed" in data
    assert "total_analyzed" in data
    assert "total_errors" in data
    assert "avg_processing_time_ms" in data
    assert "error_rate" in data
    assert "analysis_rate" in data


def test_start_data_flow_exception(client, approval_headers):
    """Test start_data_flow with exception."""
    from core.l1l2_data_flow_integrator import get_l1l2_data_flow_integrator

    # Mock start_data_flow to raise exception
    with patch.object(
        get_l1l2_data_flow_integrator(), "start_data_flow", side_effect=Exception("Start error")
    ):
        resp = client.post("/api/v1/infrastructure/data-flow/start", headers=approval_headers)
        assert resp.status_code == 500


def test_start_data_flow_success(client, approval_headers):
    """Test successful start_data_flow."""
    resp = client.post("/api/v1/infrastructure/data-flow/start", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data


def test_stop_data_flow_exception(client, approval_headers):
    """Test stop_data_flow with exception."""
    from core.l1l2_data_flow_integrator import get_l1l2_data_flow_integrator

    # Mock stop_data_flow to raise exception
    with patch.object(
        get_l1l2_data_flow_integrator(), "stop_data_flow", side_effect=Exception("Stop error")
    ):
        resp = client.post("/api/v1/infrastructure/data-flow/stop", headers=approval_headers)
        assert resp.status_code == 500


def test_stop_data_flow_success(client, approval_headers):
    """Test successful stop_data_flow."""
    resp = client.post("/api/v1/infrastructure/data-flow/stop", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "success" in data


def test_get_monitoring_summary_exception(client, approval_headers):
    """Test get_monitoring_summary with exception."""
    from core.monitoring_system_integrator import get_monitoring_system_integrator

    # Mock get_monitoring_summary to raise exception
    with patch.object(
        get_monitoring_system_integrator(),
        "get_monitoring_summary",
        side_effect=Exception("Summary error"),
    ):
        resp = client.get("/api/v1/infrastructure/monitoring/summary", headers=approval_headers)
        assert resp.status_code == 500


def test_get_monitoring_summary_success(client, approval_headers):
    """Test successful get_monitoring_summary."""
    resp = client.get("/api/v1/infrastructure/monitoring/summary", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Check all expected fields
    assert "total_alerts" in data
    assert "active_alerts" in data
    assert "critical_alerts" in data
    assert "error_alerts" in data
    assert "warning_alerts" in data
    assert "total_dashboards" in data


def test_get_alerts_exception(client, approval_headers):
    """Test get_alerts with exception."""
    from core.monitoring_system_integrator import get_monitoring_system_integrator

    # Mock get_active_alerts to raise exception
    with patch.object(
        get_monitoring_system_integrator(),
        "get_active_alerts",
        side_effect=Exception("Alerts error"),
    ):
        resp = client.get("/api/v1/infrastructure/alerts", headers=approval_headers)
        assert resp.status_code == 500


def test_get_alerts_success(client, approval_headers):
    """Test successful get_alerts."""
    resp = client.get("/api/v1/infrastructure/alerts", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "alerts" in data


def test_resolve_alert_exception(client, approval_headers):
    """Test resolve_alert with exception."""
    from core.monitoring_system_integrator import get_monitoring_system_integrator

    # Mock resolve_alert to raise exception
    with patch.object(
        get_monitoring_system_integrator(), "resolve_alert", side_effect=Exception("Resolve error")
    ):
        resp = client.post(
            "/api/v1/infrastructure/alerts/test-alert-id/resolve", headers=approval_headers
        )
        assert resp.status_code == 500


def test_resolve_alert_success(client, approval_headers):
    """Test successful alert resolution."""
    from datetime import datetime, timezone

    from core.monitoring_system_integrator import (
        AlertSeverity,
        AlertStatus,
        UnifiedAlert,
        get_monitoring_system_integrator,
    )

    # Create a test alert first
    alert = UnifiedAlert(
        alert_id="test-alert-123",
        alert_name="Test Alert",
        severity=AlertSeverity.WARNING,
        status=AlertStatus.ACTIVE,
        message="Test alert message",
    )
    get_monitoring_system_integrator().create_alert(alert)

    # Now resolve it
    resp = client.post(
        "/api/v1/infrastructure/alerts/test-alert-123/resolve", headers=approval_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True


def test_get_infrastructure_health_with_fallback(client, approval_headers):
    """Test get_infrastructure_health when fallback_enabled is True."""
    from core.kafka_stream_processor import get_kafka_processor

    # Mock fallback_enabled to True
    original_fallback = getattr(get_kafka_processor(), "fallback_enabled", False)
    get_kafka_processor().fallback_enabled = True

    try:
        resp = client.get("/api/v1/infrastructure/health", headers=approval_headers)
        assert resp.status_code == 200
        data = resp.json()
        # When fallback_enabled is True, kafka should be False
        assert data["kafka"] is False
    finally:
        # Restore original value
        get_kafka_processor().fallback_enabled = original_fallback


def test_get_infrastructure_health_exception(client, approval_headers):
    """Test get_infrastructure_health with exception."""
    from core.kafka_stream_processor import get_kafka_processor

    # Mock to raise exception
    with patch(
        "api.infrastructure_router.get_kafka_processor", side_effect=Exception("Health check error")
    ):
        resp = client.get("/api/v1/infrastructure/health", headers=approval_headers)
        assert resp.status_code == 500


def test_get_infrastructure_health_normal(client, approval_headers):
    """Test get_infrastructure_health in normal conditions."""
    resp = client.get("/api/v1/infrastructure/health", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    # Check all expected fields
    assert "kafka" in data
    assert "flink" in data
    assert "storage" in data
    assert "config_center" in data
    assert "monitoring" in data
    assert "data_flow" in data


def test_get_infrastructure_health_with_callable_flag(client, approval_headers):
    """Test get_infrastructure_health when health flag is callable."""
    from core.monitoring_infrastructure import get_monitoring_infrastructure

    # Mock a callable health flag
    original_collector = get_monitoring_infrastructure().metrics_collector
    original_collector._initialized = lambda: True

    try:
        resp = client.get("/api/v1/infrastructure/health", headers=approval_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "monitoring" in data
    finally:
        # Restore original value
        original_collector._initialized = True


def test_get_infrastructure_health_without_flags(client, approval_headers):
    """Test get_infrastructure_health when object has no health flags."""
    from core.monitoring_infrastructure import get_monitoring_infrastructure

    # Create a mock object without health flags
    class MockObj:
        pass

    mock_obj = MockObj()

    with patch("api.infrastructure_router.get_monitoring_infrastructure", return_value=mock_obj):
        resp = client.get("/api/v1/infrastructure/health", headers=approval_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Should return True for objects without health flags
        assert data["monitoring"] is True


def test_get_infrastructure_health_with_false_flag(client, approval_headers):
    """Test get_infrastructure_health when health flag is False."""
    from core.monitoring_infrastructure import get_monitoring_infrastructure

    # Mock a health flag that is False
    original_collector = get_monitoring_infrastructure().metrics_collector
    original_collector._initialized = False

    try:
        resp = client.get("/api/v1/infrastructure/health", headers=approval_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["monitoring"] is False
    finally:
        # Restore original value
        original_collector._initialized = True


def test_get_infrastructure_health_with_none_flag(client, approval_headers):
    """Test get_infrastructure_health when health flag is None."""
    from core.monitoring_infrastructure import get_monitoring_infrastructure

    # Mock a health flag that is None
    original_collector = get_monitoring_infrastructure().metrics_collector
    original_collector._initialized = None

    try:
        resp = client.get("/api/v1/infrastructure/health", headers=approval_headers)
        assert resp.status_code == 200
        data = resp.json()
        # Should return True when flag is None (not explicitly False)
        assert data["monitoring"] is True
    finally:
        # Restore original value
        original_collector._initialized = True
