# -*- coding: utf-8 -*-
"""
Test suite for Alerts Advanced Router
=====================================

Comprehensive tests for alert management advanced features including:
- Dashboard, configuration, notification channels
- Prediction, correlation, acknowledgements
- Escalation, suppression, forwarding rules
- Webhook configs, intelligent analysis
- Dynamic threshold, deduplication, aggregation rules
- Alert routing, rules, third-party integrations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import uuid

from api.alerts_advanced_router import router, AlertConfig, NotificationChannel, EscalationRule
from api.alerts_advanced_router import SuppressionRule, ForwardingRule, WebhookConfig
from api.alerts_advanced_router import DynamicThresholdRule, DeduplicationRule, AggregationRule
from api.alerts_advanced_router import AlertRoute, AlertRule, ThirdPartyConfig


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def client():
    """Create a test client for the alerts router"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    # Disable CORS for testing
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return TestClient(app)


@pytest.fixture
def sample_alert_config():
    """Sample alert configuration"""
    return AlertConfig(
        enabled=True,
        default_severity="high",
        auto_resolve_timeout=7200,
        max_alerts_per_source=2000,
        enable_intelligent_analysis=True,
        enable_prediction=True,
        enable_correlation=True,
        retention_days=60,
        notification_cooldown=600,
        escalation_enabled=True,
        suppression_enabled=True
    )


@pytest.fixture
def sample_notification_channel():
    """Sample notification channel"""
    return NotificationChannel(
        name="Test Channel",
        type="slack",
        enabled=True,
        config={"webhook_url": "https://hooks.slack.com/test"}
    )


@pytest.fixture
def sample_escalation_rule():
    """Sample escalation rule"""
    return EscalationRule(
        name="Test Escalation",
        description="Test escalation rule",
        enabled=True,
        match_conditions=[{"severity": "critical"}],
        escalation_levels=[
            {"level": 1, "notify": ["team-lead"]},
            {"level": 2, "notify": ["manager"]}
        ],
        max_escalation_level=3
    )


@pytest.fixture
def sample_suppression_rule():
    """Sample suppression rule"""
    return SuppressionRule(
        name="Test Suppression",
        description="Test suppression rule",
        enabled=True,
        match_conditions=[{"source": "maintenance"}],
        duration=3600,
        reason="Maintenance window"
    )


@pytest.fixture
def sample_forwarding_rule():
    """Sample forwarding rule"""
    return ForwardingRule(
        name="Test Forwarding",
        description="Test forwarding rule",
        enabled=True,
        source_type="prometheus",
        target_type="pagerduty",
        target_config={"service_key": "test-key"},
        filter_conditions=[{"severity": "critical"}]
    )


@pytest.fixture
def sample_webhook_config():
    """Sample webhook configuration"""
    return WebhookConfig(
        name="Test Webhook",
        description="Test webhook",
        enabled=True,
        url="https://example.com/webhook",
        method="POST",
        headers={"Content-Type": "application/json"},
        body_template='{"alert": "{{alert}}"}',
        timeout=30,
        retry_count=3,
        retry_interval=5
    )


@pytest.fixture
def sample_dynamic_threshold_rule():
    """Sample dynamic threshold rule"""
    return DynamicThresholdRule(
        name="Test Dynamic Threshold",
        description="Test dynamic threshold",
        enabled=True,
        metric="cpu_usage",
        algorithm="moving_average",
        window_size=300,
        sensitivity=0.5,
        min_threshold=0,
        max_threshold=100,
        adaptation_rate=0.1
    )


@pytest.fixture
def sample_deduplication_rule():
    """Sample deduplication rule"""
    return DeduplicationRule(
        name="Test Deduplication",
        description="Test deduplication rule",
        enabled=True,
        dedup_field="fingerprint",
        dedup_window=300,
        match_conditions=[{"source": "prometheus"}]
    )


@pytest.fixture
def sample_aggregation_rule():
    """Sample aggregation rule"""
    return AggregationRule(
        name="Test Aggregation",
        description="Test aggregation rule",
        enabled=True,
        group_by=["service", "severity"],
        aggregation_type="count",
        window=300,
        threshold=5,
        match_conditions=[{"severity": "high"}]
    )


@pytest.fixture
def sample_alert_route():
    """Sample alert route"""
    return AlertRoute(
        name="Test Route",
        description="Test alert route",
        enabled=True,
        priority=1,
        match_conditions=[{"service": "api-server"}],
        target={"type": "slack", "channel": "#alerts"},
        rate_limit={"max_per_minute": 10}
    )


@pytest.fixture
def sample_alert_rule():
    """Sample alert rule"""
    return AlertRule(
        name="Test Alert Rule",
        description="Test alert rule",
        severity="high",
        enabled=True,
        condition="cpu_usage > 80",
        threshold=80.0,
        operator=">",
        metric="cpu_usage",
        labels={"service": "api-server"},
        duration=60,
        notification_channels=["slack"]
    )


@pytest.fixture
def sample_third_party_config():
    """Sample third-party configuration"""
    return ThirdPartyConfig(
        url="https://example.com",
        username="test_user",
        password="test_pass",
        api_key="test_api_key",
        enabled=True
    )


# ============================================================================
# Dashboard Tests
# ============================================================================

class TestDashboardEndpoint:
    """Test suite for dashboard endpoint"""

    def test_get_dashboard_default_time_range(self, client):
        """Test getting dashboard data with default time range"""
        response = client.get("/api/v1/alerts/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert "total_alerts" in data
        assert "open_alerts" in data
        assert "resolved_alerts" in data
        assert "trend_data" in data
        assert data["total_alerts"] == 1247
        assert len(data["trend_data"]) == 24

    def test_get_dashboard_1h_time_range(self, client):
        """Test getting dashboard data with 1h time range"""
        response = client.get("/api/v1/alerts/dashboard?time_range=1h")
        assert response.status_code == 200
        data = response.json()
        assert "trend_data" in data
        assert len(data["trend_data"]) == 1

    def test_get_dashboard_7d_time_range(self, client):
        """Test getting dashboard data with 7d time range"""
        response = client.get("/api/v1/alerts/dashboard?time_range=7d")
        assert response.status_code == 200
        data = response.json()
        assert "trend_data" in data
        assert len(data["trend_data"]) == 24

    def test_get_dashboard_invalid_time_range(self, client):
        """Test getting dashboard data with invalid time range (should use default)"""
        response = client.get("/api/v1/alerts/dashboard?time_range=invalid")
        assert response.status_code == 200
        data = response.json()
        assert "trend_data" in data

    def test_get_dashboard_structure(self, client):
        """Test dashboard data structure"""
        response = client.get("/api/v1/alerts/dashboard")
        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "total_alerts", "open_alerts", "resolved_alerts",
            "critical_alerts", "high_alerts", "medium_alerts", "low_alerts",
            "avg_resolution_time", "alerts_by_source", "alerts_by_service",
            "recent_alerts", "trend_data"
        ]
        for field in required_fields:
            assert field in data


# ============================================================================
# Configuration Tests
# ============================================================================

class TestConfigurationEndpoint:
    """Test suite for configuration endpoint"""

    def test_get_configuration(self, client):
        """Test getting alert configuration"""
        response = client.get("/api/v1/alerts/configuration")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "default_severity" in data
        assert "auto_resolve_timeout" in data
        assert data["enabled"] == True

    def test_update_configuration(self, client, sample_alert_config):
        """Test updating alert configuration"""
        response = client.put("/api/v1/alerts/configuration", json=sample_alert_config.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config" in data
        assert data["config"]["default_severity"] == "high"

    def test_update_configuration_invalid_data(self, client):
        """Test updating configuration with invalid data"""
        response = client.put("/api/v1/alerts/configuration", json={"invalid": "data"})
        # Should fail validation
        assert response.status_code == 422

    def test_update_configuration_partial(self, client):
        """Test updating configuration with partial data"""
        partial_config = {"enabled": False, "default_severity": "low"}
        response = client.put("/api/v1/alerts/configuration", json=partial_config)
        # Pydantic should handle this with defaults
        assert response.status_code == 200


# ============================================================================
# Notification Channels Tests
# ============================================================================

class TestNotificationChannelsEndpoint:
    """Test suite for notification channels endpoint"""

    def test_get_notification_channels_empty(self, client):
        """Test getting notification channels when empty"""
        response = client.get("/api/v1/alerts/notification/channels")
        assert response.status_code == 200
        data = response.json()
        assert "channels" in data
        assert isinstance(data["channels"], list)

    def test_create_notification_channel(self, client, sample_notification_channel):
        """Test creating a notification channel"""
        response = client.post(
            "/api/v1/alerts/notification/channels",
            json=sample_notification_channel.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "channel" in data
        assert data["channel"]["name"] == "Test Channel"
        assert "id" in data["channel"]

    def test_create_notification_channel_invalid_type(self, client):
        """Test creating notification channel with invalid type"""
        invalid_channel = {
            "name": "Invalid Channel",
            "type": "invalid_type",
            "enabled": True
        }
        response = client.post(
            "/api/v1/alerts/notification/channels",
            json=invalid_channel
        )
        assert response.status_code == 422

    def test_create_notification_channel_missing_required_field(self, client):
        """Test creating notification channel without required field"""
        invalid_channel = {
            "type": "slack",
            "enabled": True
        }
        response = client.post(
            "/api/v1/alerts/notification/channels",
            json=invalid_channel
        )
        assert response.status_code == 422

    def test_update_notification_channel(self, client, sample_notification_channel):
        """Test updating a notification channel"""
        # First create a channel
        create_response = client.post(
            "/api/v1/alerts/notification/channels",
            json=sample_notification_channel.dict()
        )
        channel_id = create_response.json()["channel"]["id"]

        # Update the channel
        update_data = sample_notification_channel.dict()
        update_data["name"] = "Updated Channel"
        response = client.put(
            f"/api/v1/alerts/notification/channels/{channel_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["channel"]["name"] == "Updated Channel"

    def test_update_notification_channel_not_found(self, client, sample_notification_channel):
        """Test updating non-existent notification channel"""
        fake_id = str(uuid.uuid4())
        response = client.put(
            f"/api/v1/alerts/notification/channels/{fake_id}",
            json=sample_notification_channel.dict()
        )
        assert response.status_code == 404

    def test_delete_notification_channel(self, client, sample_notification_channel):
        """Test deleting a notification channel"""
        # First create a channel
        create_response = client.post(
            "/api/v1/alerts/notification/channels",
            json=sample_notification_channel.dict()
        )
        channel_id = create_response.json()["channel"]["id"]

        # Delete the channel
        response = client.delete(f"/api/v1/alerts/notification/channels/{channel_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_delete_notification_channel_not_found(self, client):
        """Test deleting non-existent notification channel"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/alerts/notification/channels/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Prediction Tests
# ============================================================================

class TestPredictionEndpoint:
    """Test suite for prediction endpoint"""

    def test_get_prediction_default(self, client):
        """Test getting prediction data with default time range"""
        response = client.get("/api/v1/alerts/prediction")
        assert response.status_code == 200
        data = response.json()
        assert "predictions" in data
        assert "stats" in data
        assert len(data["predictions"]) == 10

    def test_get_prediction_structure(self, client):
        """Test prediction data structure"""
        response = client.get("/api/v1/alerts/prediction")
        assert response.status_code == 200
        data = response.json()
        prediction = data["predictions"][0]
        required_fields = ["id", "metric", "predicted_value", "confidence", "predicted_at", "severity", "model"]
        for field in required_fields:
            assert field in prediction

    def test_get_prediction_stats(self, client):
        """Test prediction statistics"""
        response = client.get("/api/v1/alerts/prediction")
        assert response.status_code == 200
        data = response.json()
        stats = data["stats"]
        assert "total_predictions" in stats
        assert "accurate_predictions" in stats
        assert "accuracy_rate" in stats
        assert stats["accuracy_rate"] == 0.85


# ============================================================================
# Correlation Tests
# ============================================================================

class TestCorrelationEndpoint:
    """Test suite for correlation endpoint"""

    def test_get_correlation(self, client):
        """Test getting correlation data"""
        response = client.get("/api/v1/alerts/correlation")
        assert response.status_code == 200
        data = response.json()
        assert "correlations" in data
        assert "stats" in data
        assert len(data["correlations"]) == 5

    def test_get_correlation_structure(self, client):
        """Test correlation data structure"""
        response = client.get("/api/v1/alerts/correlation")
        assert response.status_code == 200
        data = response.json()
        correlation = data["correlations"][0]
        required_fields = ["id", "alert_id", "alert_title", "related_alerts", "correlation_group", "created_at"]
        for field in required_fields:
            assert field in correlation


# ============================================================================
# Acknowledgements Tests
# ============================================================================

class TestAcknowledgementsEndpoint:
    """Test suite for acknowledgements endpoint"""

    def test_get_acknowledgements_empty(self, client):
        """Test getting acknowledgements when empty"""
        response = client.get("/api/v1/alerts/acknowledgements")
        assert response.status_code == 200
        data = response.json()
        assert "acknowledgements" in data
        assert isinstance(data["acknowledgements"], list)


# ============================================================================
# Escalation Rules Tests
# ============================================================================

class TestEscalationRulesEndpoint:
    """Test suite for escalation rules endpoint"""

    def test_get_escalation_rules_empty(self, client):
        """Test getting escalation rules when empty"""
        response = client.get("/api/v1/alerts/escalation/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    def test_create_escalation_rule(self, client, sample_escalation_rule):
        """Test creating an escalation rule"""
        response = client.post(
            "/api/v1/alerts/escalation/rules",
            json=sample_escalation_rule.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "rule" in data
        assert data["rule"]["name"] == "Test Escalation"
        assert "id" in data["rule"]

    def test_create_escalation_rule_invalid_data(self, client):
        """Test creating escalation rule with invalid data"""
        response = client.post(
            "/api/v1/alerts/escalation/rules",
            json={"invalid": "data"}
        )
        assert response.status_code == 422

    def test_update_escalation_rule(self, client, sample_escalation_rule):
        """Test updating an escalation rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/escalation/rules",
            json=sample_escalation_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Update the rule
        update_data = sample_escalation_rule.dict()
        update_data["name"] = "Updated Escalation"
        response = client.put(
            f"/api/v1/alerts/escalation/rules/{rule_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["rule"]["name"] == "Updated Escalation"

    def test_update_escalation_rule_not_found(self, client, sample_escalation_rule):
        """Test updating non-existent escalation rule"""
        fake_id = str(uuid.uuid4())
        response = client.put(
            f"/api/v1/alerts/escalation/rules/{fake_id}",
            json=sample_escalation_rule.dict()
        )
        assert response.status_code == 404

    def test_delete_escalation_rule(self, client, sample_escalation_rule):
        """Test deleting an escalation rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/escalation/rules",
            json=sample_escalation_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Delete the rule
        response = client.delete(f"/api/v1/alerts/escalation/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_delete_escalation_rule_not_found(self, client):
        """Test deleting non-existent escalation rule"""
        fake_id = str(uuid.uuid4())
        response = client.delete(f"/api/v1/alerts/escalation/rules/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# Suppression Rules Tests
# ============================================================================

class TestSuppressionRulesEndpoint:
    """Test suite for suppression rules endpoint"""

    def test_get_suppression_rules_empty(self, client):
        """Test getting suppression rules when empty"""
        response = client.get("/api/v1/alerts/suppression/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    def test_create_suppression_rule(self, client, sample_suppression_rule):
        """Test creating a suppression rule"""
        response = client.post(
            "/api/v1/alerts/suppression/rules",
            json=sample_suppression_rule.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "rule" in data
        assert data["rule"]["name"] == "Test Suppression"
        assert "id" in data["rule"]

    def test_update_suppression_rule(self, client, sample_suppression_rule):
        """Test updating a suppression rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/suppression/rules",
            json=sample_suppression_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Update the rule
        update_data = sample_suppression_rule.dict()
        update_data["name"] = "Updated Suppression"
        response = client.put(
            f"/api/v1/alerts/suppression/rules/{rule_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["rule"]["name"] == "Updated Suppression"

    def test_delete_suppression_rule(self, client, sample_suppression_rule):
        """Test deleting a suppression rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/suppression/rules",
            json=sample_suppression_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Delete the rule
        response = client.delete(f"/api/v1/alerts/suppression/rules/{rule_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


# ============================================================================
# Trends Tests
# ============================================================================

class TestTrendsEndpoint:
    """Test suite for trends endpoint"""

    def test_get_trends_default(self, client):
        """Test getting trends with default time range"""
        response = client.get("/api/v1/alerts/trends")
        assert response.status_code == 200
        data = response.json()
        assert "daily_trends" in data
        assert "weekly_trends" in data
        assert "monthly_trends" in data

    def test_get_trends_30d(self, client):
        """Test getting trends with 30d time range"""
        response = client.get("/api/v1/alerts/trends?time_range=30d")
        assert response.status_code == 200
        data = response.json()
        assert "daily_trends" in data

    def test_get_trends_90d(self, client):
        """Test getting trends with 90d time range"""
        response = client.get("/api/v1/alerts/trends?time_range=90d")
        assert response.status_code == 200
        data = response.json()
        assert "daily_trends" in data


# ============================================================================
# Statistics Tests
# ============================================================================

class TestStatisticsEndpoint:
    """Test suite for statistics endpoint"""

    def test_get_statistics(self, client):
        """Test getting statistics"""
        response = client.get("/api/v1/alerts/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_alerts" in data
        assert "open_alerts" in data
        assert "resolved_alerts" in data
        assert "alerts_by_source" in data
        assert "alerts_by_service" in data

    def test_get_statistics_structure(self, client):
        """Test statistics data structure"""
        response = client.get("/api/v1/alerts/statistics")
        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "total_alerts", "open_alerts", "acknowledged_alerts",
            "resolved_alerts", "critical_alerts", "high_alerts",
            "medium_alerts", "low_alerts", "avg_resolution_time",
            "avg_acknowledgement_time", "alerts_by_source",
            "alerts_by_service", "alerts_by_hour", "alerts_by_day"
        ]
        for field in required_fields:
            assert field in data


# ============================================================================
# History Tests
# ============================================================================

class TestHistoryEndpoint:
    """Test suite for history endpoint"""

    def test_get_history_default(self, client):
        """Test getting history with default parameters"""
        response = client.get("/api/v1/alerts/history")
        assert response.status_code == 200
        data = response.json()
        assert "history" in data
        assert len(data["history"]) == 20

    def test_get_history_with_filters(self, client):
        """Test getting history with filters"""
        response = client.get(
            "/api/v1/alerts/history?severity=critical&status=open&source=Prometheus"
        )
        assert response.status_code == 200
        data = response.json()
        assert "history" in data

    def test_get_history_structure(self, client):
        """Test history data structure"""
        response = client.get("/api/v1/alerts/history")
        assert response.status_code == 200
        data = response.json()
        if len(data["history"]) > 0:
            history_item = data["history"][0]
            required_fields = ["id", "alert_id", "title", "severity", "status", "source", "created_at"]
            for field in required_fields:
                assert field in history_item


# ============================================================================
# Forwarding Rules Tests
# ============================================================================

class TestForwardingRulesEndpoint:
    """Test suite for forwarding rules endpoint"""

    def test_get_forwarding_rules_empty(self, client):
        """Test getting forwarding rules when empty"""
        response = client.get("/api/v1/alerts/forwarding/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    def test_create_forwarding_rule(self, client, sample_forwarding_rule):
        """Test creating a forwarding rule"""
        response = client.post(
            "/api/v1/alerts/forwarding/rules",
            json=sample_forwarding_rule.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "rule" in data
        assert data["rule"]["name"] == "Test Forwarding"

    def test_update_forwarding_rule(self, client, sample_forwarding_rule):
        """Test updating a forwarding rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/forwarding/rules",
            json=sample_forwarding_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Update the rule
        update_data = sample_forwarding_rule.dict()
        update_data["name"] = "Updated Forwarding"
        response = client.put(
            f"/api/v1/alerts/forwarding/rules/{rule_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_delete_forwarding_rule(self, client, sample_forwarding_rule):
        """Test deleting a forwarding rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/forwarding/rules",
            json=sample_forwarding_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Delete the rule
        response = client.delete(f"/api/v1/alerts/forwarding/rules/{rule_id}")
        assert response.status_code == 200


# ============================================================================
# Webhook Configs Tests
# ============================================================================

class TestWebhookConfigsEndpoint:
    """Test suite for webhook configs endpoint"""

    def test_get_webhook_configs_empty(self, client):
        """Test getting webhook configs when empty"""
        response = client.get("/api/v1/alerts/webhook/configs")
        assert response.status_code == 200
        data = response.json()
        assert "webhooks" in data
        assert isinstance(data["webhooks"], list)

    def test_create_webhook_config(self, client, sample_webhook_config):
        """Test creating a webhook config"""
        response = client.post(
            "/api/v1/alerts/webhook/configs",
            json=sample_webhook_config.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "webhook" in data
        assert data["webhook"]["name"] == "Test Webhook"

    def test_create_webhook_config_invalid_url(self, client):
        """Test creating webhook config with invalid URL"""
        invalid_config = {
            "name": "Invalid Webhook",
            "url": "not-a-valid-url",
            "method": "POST"
        }
        response = client.post(
            "/api/v1/alerts/webhook/configs",
            json=invalid_config
        )
        # Pydantic should validate URL
        assert response.status_code == 422

    def test_update_webhook_config(self, client, sample_webhook_config):
        """Test updating a webhook config"""
        # First create a config
        create_response = client.post(
            "/api/v1/alerts/webhook/configs",
            json=sample_webhook_config.dict()
        )
        config_id = create_response.json()["webhook"]["id"]

        # Update the config
        update_data = sample_webhook_config.dict()
        update_data["name"] = "Updated Webhook"
        response = client.put(
            f"/api/v1/alerts/webhook/configs/{config_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_delete_webhook_config(self, client, sample_webhook_config):
        """Test deleting a webhook config"""
        # First create a config
        create_response = client.post(
            "/api/v1/alerts/webhook/configs",
            json=sample_webhook_config.dict()
        )
        config_id = create_response.json()["webhook"]["id"]

        # Delete the config
        response = client.delete(f"/api/v1/alerts/webhook/configs/{config_id}")
        assert response.status_code == 200


# ============================================================================
# Intelligent Analysis Tests
# ============================================================================

class TestIntelligentAnalysisEndpoint:
    """Test suite for intelligent analysis endpoint"""

    def test_get_intelligent_analysis(self, client):
        """Test getting intelligent analysis results"""
        response = client.get("/api/v1/alerts/intelligent-analysis")
        assert response.status_code == 200
        data = response.json()
        assert "analyses" in data
        assert "stats" in data

    def test_run_intelligent_analysis(self, client):
        """Test running intelligent analysis"""
        response = client.post("/api/v1/alerts/intelligent-analysis")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "analysis" in data
        assert data["analysis"]["analysis_type"] == "root_cause"


# ============================================================================
# Dynamic Threshold Rules Tests
# ============================================================================

class TestDynamicThresholdRulesEndpoint:
    """Test suite for dynamic threshold rules endpoint"""

    def test_get_dynamic_threshold_rules_empty(self, client):
        """Test getting dynamic threshold rules when empty"""
        response = client.get("/api/v1/alerts/dynamic-threshold/rules")
        assert response.status_code == 200
        data = response.json()
        assert "thresholds" in data
        assert isinstance(data["thresholds"], list)

    def test_create_dynamic_threshold_rule(self, client, sample_dynamic_threshold_rule):
        """Test creating a dynamic threshold rule"""
        response = client.post(
            "/api/v1/alerts/dynamic-threshold/rules",
            json=sample_dynamic_threshold_rule.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "threshold" in data
        assert data["threshold"]["name"] == "Test Dynamic Threshold"

    def test_update_dynamic_threshold_rule(self, client, sample_dynamic_threshold_rule):
        """Test updating a dynamic threshold rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/dynamic-threshold/rules",
            json=sample_dynamic_threshold_rule.dict()
        )
        rule_id = create_response.json()["threshold"]["id"]

        # Update the rule
        update_data = sample_dynamic_threshold_rule.dict()
        update_data["name"] = "Updated Threshold"
        response = client.put(
            f"/api/v1/alerts/dynamic-threshold/rules/{rule_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_delete_dynamic_threshold_rule(self, client, sample_dynamic_threshold_rule):
        """Test deleting a dynamic threshold rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/dynamic-threshold/rules",
            json=sample_dynamic_threshold_rule.dict()
        )
        rule_id = create_response.json()["threshold"]["id"]

        # Delete the rule
        response = client.delete(f"/api/v1/alerts/dynamic-threshold/rules/{rule_id}")
        assert response.status_code == 200


# ============================================================================
# Deduplication Rules Tests
# ============================================================================

class TestDeduplicationRulesEndpoint:
    """Test suite for deduplication rules endpoint"""

    def test_get_deduplication_rules_empty(self, client):
        """Test getting deduplication rules when empty"""
        response = client.get("/api/v1/alerts/deduplication/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    def test_create_deduplication_rule(self, client, sample_deduplication_rule):
        """Test creating a deduplication rule"""
        response = client.post(
            "/api/v1/alerts/deduplication/rules",
            json=sample_deduplication_rule.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "rule" in data
        assert data["rule"]["name"] == "Test Deduplication"

    def test_update_deduplication_rule(self, client, sample_deduplication_rule):
        """Test updating a deduplication rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/deduplication/rules",
            json=sample_deduplication_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Update the rule
        update_data = sample_deduplication_rule.dict()
        update_data["name"] = "Updated Deduplication"
        response = client.put(
            f"/api/v1/alerts/deduplication/rules/{rule_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_delete_deduplication_rule(self, client, sample_deduplication_rule):
        """Test deleting a deduplication rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/deduplication/rules",
            json=sample_deduplication_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Delete the rule
        response = client.delete(f"/api/v1/alerts/deduplication/rules/{rule_id}")
        assert response.status_code == 200


# ============================================================================
# Aggregation Rules Tests
# ============================================================================

class TestAggregationRulesEndpoint:
    """Test suite for aggregation rules endpoint"""

    def test_get_aggregation_rules_empty(self, client):
        """Test getting aggregation rules when empty"""
        response = client.get("/api/v1/alerts/aggregation/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    def test_create_aggregation_rule(self, client, sample_aggregation_rule):
        """Test creating an aggregation rule"""
        response = client.post(
            "/api/v1/alerts/aggregation/rules",
            json=sample_aggregation_rule.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "rule" in data
        assert data["rule"]["name"] == "Test Aggregation"

    def test_update_aggregation_rule(self, client, sample_aggregation_rule):
        """Test updating an aggregation rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/aggregation/rules",
            json=sample_aggregation_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Update the rule
        update_data = sample_aggregation_rule.dict()
        update_data["name"] = "Updated Aggregation"
        response = client.put(
            f"/api/v1/alerts/aggregation/rules/{rule_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_delete_aggregation_rule(self, client, sample_aggregation_rule):
        """Test deleting an aggregation rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/aggregation/rules",
            json=sample_aggregation_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Delete the rule
        response = client.delete(f"/api/v1/alerts/aggregation/rules/{rule_id}")
        assert response.status_code == 200


# ============================================================================
# Alert Routing Tests
# ============================================================================

class TestAlertRoutingEndpoint:
    """Test suite for alert routing endpoint"""

    def test_get_routing_empty(self, client):
        """Test getting alert routes when empty"""
        response = client.get("/api/v1/alerts/routing")
        assert response.status_code == 200
        data = response.json()
        assert "routes" in data
        assert isinstance(data["routes"], list)

    def test_create_routing(self, client, sample_alert_route):
        """Test creating an alert route"""
        response = client.post(
            "/api/v1/alerts/routing",
            json=sample_alert_route.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "route" in data
        assert data["route"]["name"] == "Test Route"

    def test_update_routing(self, client, sample_alert_route):
        """Test updating an alert route"""
        # First create a route
        create_response = client.post(
            "/api/v1/alerts/routing",
            json=sample_alert_route.dict()
        )
        route_id = create_response.json()["route"]["id"]

        # Update the route
        update_data = sample_alert_route.dict()
        update_data["name"] = "Updated Route"
        response = client.put(
            f"/api/v1/alerts/routing/{route_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_delete_routing(self, client, sample_alert_route):
        """Test deleting an alert route"""
        # First create a route
        create_response = client.post(
            "/api/v1/alerts/routing",
            json=sample_alert_route.dict()
        )
        route_id = create_response.json()["route"]["id"]

        # Delete the route
        response = client.delete(f"/api/v1/alerts/routing/{route_id}")
        assert response.status_code == 200


# ============================================================================
# Alert Rules Tests
# ============================================================================

class TestAlertRulesEndpoint:
    """Test suite for alert rules endpoint"""

    def test_get_rules_empty(self, client):
        """Test getting alert rules when empty"""
        response = client.get("/api/v1/alerts/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert isinstance(data["rules"], list)

    def test_create_rule(self, client, sample_alert_rule):
        """Test creating an alert rule"""
        response = client.post(
            "/api/v1/alerts/rules",
            json=sample_alert_rule.dict()
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "rule" in data
        assert data["rule"]["name"] == "Test Alert Rule"

    def test_create_rule_invalid_severity(self, client):
        """Test creating alert rule with invalid severity"""
        invalid_rule = {
            "name": "Invalid Rule",
            "severity": "invalid",
            "metric": "cpu_usage"
        }
        response = client.post(
            "/api/v1/alerts/rules",
            json=invalid_rule
        )
        # Pydantic should validate
        assert response.status_code == 422

    def test_update_rule(self, client, sample_alert_rule):
        """Test updating an alert rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/rules",
            json=sample_alert_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Update the rule
        update_data = sample_alert_rule.dict()
        update_data["name"] = "Updated Rule"
        response = client.put(
            f"/api/v1/alerts/rules/{rule_id}",
            json=update_data
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_delete_rule(self, client, sample_alert_rule):
        """Test deleting an alert rule"""
        # First create a rule
        create_response = client.post(
            "/api/v1/alerts/rules",
            json=sample_alert_rule.dict()
        )
        rule_id = create_response.json()["rule"]["id"]

        # Delete the rule
        response = client.delete(f"/api/v1/alerts/rules/{rule_id}")
        assert response.status_code == 200


# ============================================================================
# Third-party Integration Tests
# ============================================================================

class TestThirdPartyIntegrations:
    """Test suite for third-party integration endpoints"""

    def test_get_zabbix(self, client):
        """Test getting Zabbix integration config"""
        response = client.get("/api/v1/alerts/zabbix")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data
        assert "triggers" in data

    def test_update_zabbix(self, client, sample_third_party_config):
        """Test updating Zabbix integration config"""
        response = client.put("/api/v1/alerts/zabbix", json=sample_third_party_config.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "config" in data

    def test_get_cloudwatch(self, client):
        """Test getting CloudWatch integration config"""
        response = client.get("/api/v1/alerts/cloudwatch")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data

    def test_update_cloudwatch(self, client, sample_third_party_config):
        """Test updating CloudWatch integration config"""
        response = client.put("/api/v1/alerts/cloudwatch", json=sample_third_party_config.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_pagerduty(self, client):
        """Test getting PagerDuty integration config"""
        response = client.get("/api/v1/alerts/pagerduty")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data

    def test_update_pagerduty(self, client, sample_third_party_config):
        """Test updating PagerDuty integration config"""
        response = client.put("/api/v1/alerts/pagerduty", json=sample_third_party_config.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_send_to_pagerduty(self, client):
        """Test sending alert to PagerDuty"""
        alert_data = {
            "title": "Test Alert",
            "severity": "critical",
            "description": "Test alert description"
        }
        response = client.post("/api/v1/alerts/pagerduty", json=alert_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_datadog(self, client):
        """Test getting Datadog integration config"""
        response = client.get("/api/v1/alerts/datadog")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data

    def test_update_datadog(self, client, sample_third_party_config):
        """Test updating Datadog integration config"""
        response = client.put("/api/v1/alerts/datadog", json=sample_third_party_config.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_grafana(self, client):
        """Test getting Grafana integration config"""
        response = client.get("/api/v1/alerts/grafana")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data

    def test_update_grafana(self, client, sample_third_party_config):
        """Test updating Grafana integration config"""
        response = client.put("/api/v1/alerts/grafana", json=sample_third_party_config.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    def test_get_prometheus(self, client):
        """Test getting Prometheus integration config"""
        response = client.get("/api/v1/alerts/prometheus")
        assert response.status_code == 200
        data = response.json()
        assert "config" in data

    def test_update_prometheus(self, client, sample_third_party_config):
        """Test updating Prometheus integration config"""
        response = client.put("/api/v1/alerts/prometheus", json=sample_third_party_config.dict())
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


# ============================================================================
# Data Validation Tests
# ============================================================================

class TestDataValidation:
    """Test suite for data validation"""

    def test_notification_channel_type_validation(self, client):
        """Test notification channel type validation"""
        valid_types = ["email", "slack", "pagerduty", "sms", "webhook", "teams"]
        for channel_type in valid_types:
            channel_data = {
                "name": f"Test {channel_type}",
                "type": channel_type,
                "enabled": True
            }
            response = client.post(
                "/api/v1/alerts/notification/channels",
                json=channel_data
            )
            assert response.status_code == 200

    def test_notification_channel_invalid_type(self, client):
        """Test notification channel with invalid type"""
        invalid_channel = {
            "name": "Invalid",
            "type": "invalid_type",
            "enabled": True
        }
        response = client.post(
            "/api/v1/alerts/notification/channels",
            json=invalid_channel
        )
        assert response.status_code == 422

    def test_webhook_timeout_validation(self, client):
        """Test webhook timeout validation"""
        webhook_data = {
            "name": "Test Webhook",
            "url": "https://example.com/webhook",
            "timeout": 1000  # Should be within reasonable range
        }
        response = client.post(
            "/api/v1/alerts/webhook/configs",
            json=webhook_data
        )
        assert response.status_code == 200


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test suite for error handling"""

    def test_404_on_nonexistent_resource(self, client):
        """Test 404 error for non-existent resources"""
        fake_id = str(uuid.uuid4())
        endpoints = [
            f"/api/v1/alerts/notification/channels/{fake_id}",
            f"/api/v1/alerts/escalation/rules/{fake_id}",
            f"/api/v1/alerts/suppression/rules/{fake_id}",
            f"/api/v1/alerts/forwarding/rules/{fake_id}",
            f"/api/v1/alerts/webhook/configs/{fake_id}",
            f"/api/v1/alerts/dynamic-threshold/rules/{fake_id}",
            f"/api/v1/alerts/deduplication/rules/{fake_id}",
            f"/api/v1/alerts/aggregation/rules/{fake_id}",
            f"/api/v1/alerts/routing/{fake_id}",
            f"/api/v1/alerts/rules/{fake_id}",
        ]
        for endpoint in endpoints:
            response = client.delete(endpoint)
            assert response.status_code == 404

    def test_validation_error_on_missing_required_fields(self, client):
        """Test validation error when required fields are missing"""
        response = client.post(
            "/api/v1/alerts/notification/channels",
            json={"enabled": True}
        )
        assert response.status_code == 422


# ============================================================================
# Performance Tests
# ============================================================================

class TestPerformance:
    """Test suite for performance"""

    def test_multiple_creates(self, client, sample_notification_channel):
        """Test creating multiple resources"""
        for i in range(10):
            channel_data = sample_notification_channel.dict()
            channel_data["name"] = f"Channel {i}"
            response = client.post(
                "/api/v1/alerts/notification/channels",
                json=channel_data
            )
            assert response.status_code == 200

    def test_get_after_multiple_creates(self, client, sample_notification_channel):
        """Test getting list after creating multiple resources"""
        # Create multiple channels
        for i in range(5):
            channel_data = sample_notification_channel.dict()
            channel_data["name"] = f"Channel {i}"
            client.post(
                "/api/v1/alerts/notification/channels",
                json=channel_data
            )

        # Get all channels
        response = client.get("/api/v1/alerts/notification/channels")
        assert response.status_code == 200
        data = response.json()
        assert len(data["channels"]) >= 5


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.alerts_advanced_router", "--cov-report=html"])
