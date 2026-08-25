# -*- coding: utf-8 -*-
"""
Test cases for Notification Advanced Router
Comprehensive test coverage for notification management API
"""

import pytest
from datetime import datetime
from uuid import uuid4
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.notify_advanced_router import (
    router,
    ChannelCreate,
    ChannelUpdate,
    TemplateCreate,
    TemplateUpdate,
    RuleCreate,
    RuleUpdate,
    NotificationSettings,
    _channels,
    _templates,
    _rules,
    _history,
    _settings,
)


@pytest.fixture
def client():
    """Create a test client for the router"""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_storage():
    """Reset in-memory storage before each test"""
    _channels.clear()
    _templates.clear()
    _rules.clear()
    _history.clear()
    _settings.update({
        "enabled": True,
        "min_level": "info",
        "rate_limit_enabled": True,
        "rate_limit_per_minute": 10,
        "batch_enabled": False,
        "batch_interval": 60,
        "metadata": {},
    })
    yield
    _channels.clear()
    _templates.clear()
    _rules.clear()
    _history.clear()


@pytest.fixture
def sample_channel():
    """Create a sample channel for testing"""
    return {
        "id": str(uuid4()),
        "name": "Email Channel",
        "type": "email",
        "enabled": True,
        "config": {
            "smtp_host": "smtp.example.com",
            "smtp_port": 587,
            "from_address": "alerts@example.com",
        },
        "priority": 10,
        "retry_count": 3,
        "timeout": 30,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_template():
    """Create a sample template for testing"""
    return {
        "id": str(uuid4()),
        "name": "Alert Template",
        "subject": "Alert: {{alert_title}}",
        "body": "Alert Details:\n\nTitle: {{alert_title}}",
        "type": "email",
        "variables": ["alert_title", "alert_level"],
        "enabled": True,
        "metadata": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_rule(sample_channel, sample_template):
    """Create a sample rule for testing"""
    return {
        "id": str(uuid4()),
        "name": "Critical Alert Rule",
        "condition": "alert_level == 'critical'",
        "channels": [sample_channel["id"]],
        "template_id": sample_template["id"],
        "enabled": True,
        "priority": 10,
        "metadata": {},
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }


@pytest.fixture
def sample_history(sample_channel, sample_template):
    """Create a sample history record for testing"""
    return {
        "id": str(uuid4()),
        "channel_id": sample_channel["id"],
        "channel_name": sample_channel["name"],
        "rule_id": str(uuid4()),
        "template_id": sample_template["id"],
        "status": "sent",
        "error_message": None,
        "sent_at": datetime.utcnow(),
        "metadata": {},
    }


# ============================================================================
# Channel Endpoints Tests
# ============================================================================

class TestChannelEndpoints:
    """Test cases for channel endpoints"""

    def test_get_channels_empty(self, client):
        """Test getting channels when storage is empty"""
        response = client.get("/api/v1/notify/channels")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_channels_with_data(self, client, sample_channel):
        """Test getting channels with data"""
        _channels[sample_channel["id"]] = sample_channel
        response = client.get("/api/v1/notify/channels")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_channels_filter_enabled(self, client, sample_channel):
        """Test getting channels filtered by enabled status"""
        sample_channel["enabled"] = True
        _channels[sample_channel["id"]] = sample_channel
        
        disabled_channel = sample_channel.copy()
        disabled_channel["id"] = str(uuid4())
        disabled_channel["enabled"] = False
        _channels[disabled_channel["id"]] = disabled_channel
        
        response = client.get("/api/v1/notify/channels?enabled=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["enabled"] == True

    def test_get_channels_filter_type(self, client, sample_channel):
        """Test getting channels filtered by type"""
        _channels[sample_channel["id"]] = sample_channel
        
        response = client.get("/api/v1/notify/channels?type=email")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_channels_priority_sorting(self, client, sample_channel):
        """Test that channels are sorted by priority"""
        channel1 = sample_channel.copy()
        channel1["id"] = str(uuid4())
        channel1["priority"] = 5
        _channels[channel1["id"]] = channel1
        
        channel2 = sample_channel.copy()
        channel2["id"] = str(uuid4())
        channel2["priority"] = 10
        _channels[channel2["id"]] = channel2
        
        response = client.get("/api/v1/notify/channels")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["priority"] >= data[1]["priority"]

    def test_create_channel_success(self, client):
        """Test creating a channel successfully"""
        channel_data = {
            "name": "Slack Channel",
            "type": "slack",
            "enabled": True,
            "config": {
                "webhook_url": "https://hooks.slack.com/services/xxx",
                "channel": "#alerts"
            },
            "priority": 5,
            "retry_count": 3,
            "timeout": 30
        }
        response = client.post("/api/v1/notify/channels", json=channel_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Slack Channel"
        assert data["type"] == "slack"
        assert "id" in data

    def test_create_channel_invalid_type(self, client):
        """Test creating a channel with invalid type"""
        channel_data = {
            "name": "Invalid Channel",
            "type": "invalid_type",
            "enabled": True
        }
        response = client.post("/api/v1/notify/channels", json=channel_data)
        assert response.status_code == 422  # Validation error

    def test_create_channel_valid_types(self, client):
        """Test creating channels with all valid types"""
        valid_types = ["email", "slack", "pagerduty", "sms", "webhook", "teams"]
        for channel_type in valid_types:
            channel_data = {
                "name": f"{channel_type.capitalize()} Channel",
                "type": channel_type,
                "enabled": True
            }
            response = client.post("/api/v1/notify/channels", json=channel_data)
            assert response.status_code == 200

    def test_get_channel_success(self, client, sample_channel):
        """Test getting a channel by ID successfully"""
        _channels[sample_channel["id"]] = sample_channel
        response = client.get(f"/api/v1/notify/channels/{sample_channel['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Email Channel"

    def test_get_channel_not_found(self, client):
        """Test getting a non-existent channel"""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/notify/channels/{fake_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_channel_success(self, client, sample_channel):
        """Test updating a channel successfully"""
        _channels[sample_channel["id"]] = sample_channel
        
        update_data = {
            "name": "Email Channel Updated",
            "enabled": False,
            "priority": 15
        }
        response = client.patch(f"/api/v1/notify/channels/{sample_channel['id']}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Email Channel Updated"
        assert data["enabled"] == False

    def test_update_channel_not_found(self, client):
        """Test updating a non-existent channel"""
        fake_id = str(uuid4())
        update_data = {"name": "Updated"}
        response = client.patch(f"/api/v1/notify/channels/{fake_id}", json=update_data)
        assert response.status_code == 404

    def test_delete_channel_success(self, client, sample_channel):
        """Test deleting a channel successfully"""
        _channels[sample_channel["id"]] = sample_channel
        
        response = client.delete(f"/api/v1/notify/channels/{sample_channel['id']}")
        assert response.status_code == 200
        assert sample_channel["id"] not in _channels

    def test_delete_channel_not_found(self, client):
        """Test deleting a non-existent channel"""
        fake_id = str(uuid4())
        response = client.delete(f"/api/v1/notify/channels/{fake_id}")
        assert response.status_code == 404

    def test_delete_channel_used_by_rule(self, client, sample_channel, sample_rule):
        """Test deleting a channel that is used by a rule (should fail)"""
        _channels[sample_channel["id"]] = sample_channel
        _rules[sample_rule["id"]] = sample_rule
        
        response = client.delete(f"/api/v1/notify/channels/{sample_channel['id']}")
        assert response.status_code == 400
        assert "used by one or more notification rules" in response.json()["detail"]


# ============================================================================
# Template Endpoints Tests
# ============================================================================

class TestTemplateEndpoints:
    """Test cases for template endpoints"""

    def test_get_templates_empty(self, client):
        """Test getting templates when storage is empty"""
        response = client.get("/api/v1/notify/templates")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_templates_with_data(self, client, sample_template):
        """Test getting templates with data"""
        _templates[sample_template["id"]] = sample_template
        response = client.get("/api/v1/notify/templates")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_templates_filter_enabled(self, client, sample_template):
        """Test getting templates filtered by enabled status"""
        sample_template["enabled"] = True
        _templates[sample_template["id"]] = sample_template
        
        disabled_template = sample_template.copy()
        disabled_template["id"] = str(uuid4())
        disabled_template["enabled"] = False
        _templates[disabled_template["id"]] = disabled_template
        
        response = client.get("/api/v1/notify/templates?enabled=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_templates_filter_type(self, client, sample_template):
        """Test getting templates filtered by type"""
        _templates[sample_template["id"]] = sample_template
        
        response = client.get("/api/v1/notify/templates?type=email")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_create_template_success(self, client):
        """Test creating a template successfully"""
        template_data = {
            "name": "SMS Template",
            "subject": "Alert: {{alert_title}}",
            "body": "Alert: {{alert_title}} - {{alert_description}}",
            "type": "sms",
            "variables": ["alert_title", "alert_description"],
            "enabled": True,
            "metadata": {}
        }
        response = client.post("/api/v1/notify/templates", json=template_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "SMS Template"
        assert data["type"] == "sms"

    def test_create_template_missing_required_field(self, client):
        """Test creating a template with missing required field"""
        template_data = {
            "name": "Incomplete Template"
            # Missing subject, body
        }
        response = client.post("/api/v1/notify/templates", json=template_data)
        assert response.status_code == 422

    def test_get_template_success(self, client, sample_template):
        """Test getting a template by ID successfully"""
        _templates[sample_template["id"]] = sample_template
        response = client.get(f"/api/v1/notify/templates/{sample_template['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Alert Template"

    def test_get_template_not_found(self, client):
        """Test getting a non-existent template"""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/notify/templates/{fake_id}")
        assert response.status_code == 404

    def test_update_template_success(self, client, sample_template):
        """Test updating a template successfully"""
        _templates[sample_template["id"]] = sample_template
        
        update_data = {
            "name": "Updated Template",
            "subject": "Updated: {{alert_title}}",
            "enabled": False
        }
        response = client.patch(f"/api/v1/notify/templates/{sample_template['id']}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Template"

    def test_update_template_not_found(self, client):
        """Test updating a non-existent template"""
        fake_id = str(uuid4())
        update_data = {"name": "Updated"}
        response = client.patch(f"/api/v1/notify/templates/{fake_id}", json=update_data)
        assert response.status_code == 404

    def test_delete_template_success(self, client, sample_template):
        """Test deleting a template successfully"""
        _templates[sample_template["id"]] = sample_template
        
        response = client.delete(f"/api/v1/notify/templates/{sample_template['id']}")
        assert response.status_code == 200
        assert sample_template["id"] not in _templates

    def test_delete_template_not_found(self, client):
        """Test deleting a non-existent template"""
        fake_id = str(uuid4())
        response = client.delete(f"/api/v1/notify/templates/{fake_id}")
        assert response.status_code == 404

    def test_delete_template_used_by_rule(self, client, sample_template, sample_rule):
        """Test deleting a template that is used by a rule (should fail)"""
        _templates[sample_template["id"]] = sample_template
        _rules[sample_rule["id"]] = sample_rule
        
        response = client.delete(f"/api/v1/notify/templates/{sample_template['id']}")
        assert response.status_code == 400
        assert "used by one or more notification rules" in response.json()["detail"]


# ============================================================================
# Rule Endpoints Tests
# ============================================================================

class TestRuleEndpoints:
    """Test cases for rule endpoints"""

    def test_get_rules_empty(self, client):
        """Test getting rules when storage is empty"""
        response = client.get("/api/v1/notify/rules")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_rules_with_data(self, client, sample_rule):
        """Test getting rules with data"""
        _rules[sample_rule["id"]] = sample_rule
        response = client.get("/api/v1/notify/rules")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_rules_filter_enabled(self, client, sample_rule):
        """Test getting rules filtered by enabled status"""
        sample_rule["enabled"] = True
        _rules[sample_rule["id"]] = sample_rule
        
        disabled_rule = sample_rule.copy()
        disabled_rule["id"] = str(uuid4())
        disabled_rule["enabled"] = False
        _rules[disabled_rule["id"]] = disabled_rule
        
        response = client.get("/api/v1/notify/rules?enabled=true")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_rules_priority_sorting(self, client, sample_rule):
        """Test that rules are sorted by priority"""
        rule1 = sample_rule.copy()
        rule1["id"] = str(uuid4())
        rule1["priority"] = 5
        _rules[rule1["id"]] = rule1
        
        rule2 = sample_rule.copy()
        rule2["id"] = str(uuid4())
        rule2["priority"] = 10
        _rules[rule2["id"]] = rule2
        
        response = client.get("/api/v1/notify/rules")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["priority"] >= data[1]["priority"]

    def test_create_rule_success(self, client, sample_channel, sample_template):
        """Test creating a rule successfully"""
        _channels[sample_channel["id"]] = sample_channel
        _templates[sample_template["id"]] = sample_template
        
        rule_data = {
            "name": "Warning Alert Rule",
            "condition": "alert_level == 'warning'",
            "channels": [sample_channel["id"]],
            "template_id": sample_template["id"],
            "enabled": True,
            "priority": 5,
            "metadata": {}
        }
        response = client.post("/api/v1/notify/rules", json=rule_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Warning Alert Rule"

    def test_create_rule_template_not_found(self, client, sample_channel):
        """Test creating a rule with non-existent template"""
        _channels[sample_channel["id"]] = sample_channel
        
        rule_data = {
            "name": "Test Rule",
            "condition": "alert_level == 'critical'",
            "channels": [sample_channel["id"]],
            "template_id": str(uuid4()),
            "enabled": True
        }
        response = client.post("/api/v1/notify/rules", json=rule_data)
        assert response.status_code == 400
        assert "Template not found" in response.json()["detail"]

    def test_create_rule_channel_not_found(self, client, sample_template):
        """Test creating a rule with non-existent channel"""
        _templates[sample_template["id"]] = sample_template
        
        rule_data = {
            "name": "Test Rule",
            "condition": "alert_level == 'critical'",
            "channels": [str(uuid4())],
            "template_id": sample_template["id"],
            "enabled": True
        }
        response = client.post("/api/v1/notify/rules", json=rule_data)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_get_rule_success(self, client, sample_rule):
        """Test getting a rule by ID successfully"""
        _rules[sample_rule["id"]] = sample_rule
        response = client.get(f"/api/v1/notify/rules/{sample_rule['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Critical Alert Rule"

    def test_get_rule_not_found(self, client):
        """Test getting a non-existent rule"""
        fake_id = str(uuid4())
        response = client.get(f"/api/v1/notify/rules/{fake_id}")
        assert response.status_code == 404

    def test_update_rule_success(self, client, sample_rule):
        """Test updating a rule successfully"""
        _rules[sample_rule["id"]] = sample_rule
        
        update_data = {
            "name": "Updated Rule",
            "condition": "alert_level == 'error'",
            "enabled": False
        }
        response = client.patch(f"/api/v1/notify/rules/{sample_rule['id']}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Rule"

    def test_update_rule_not_found(self, client):
        """Test updating a non-existent rule"""
        fake_id = str(uuid4())
        update_data = {"name": "Updated"}
        response = client.patch(f"/api/v1/notify/rules/{fake_id}", json=update_data)
        assert response.status_code == 404

    def test_update_rule_invalid_channel(self, client, sample_rule):
        """Test updating a rule with invalid channel"""
        _rules[sample_rule["id"]] = sample_rule
        
        update_data = {
            "channels": [str(uuid4())]
        }
        response = client.patch(f"/api/v1/notify/rules/{sample_rule['id']}", json=update_data)
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_update_rule_invalid_template(self, client, sample_rule):
        """Test updating a rule with invalid template"""
        _rules[sample_rule["id"]] = sample_rule
        
        update_data = {
            "template_id": str(uuid4())
        }
        response = client.patch(f"/api/v1/notify/rules/{sample_rule['id']}", json=update_data)
        assert response.status_code == 400
        assert "Template not found" in response.json()["detail"]

    def test_delete_rule_success(self, client, sample_rule):
        """Test deleting a rule successfully"""
        _rules[sample_rule["id"]] = sample_rule
        
        response = client.delete(f"/api/v1/notify/rules/{sample_rule['id']}")
        assert response.status_code == 200
        assert sample_rule["id"] not in _rules

    def test_delete_rule_not_found(self, client):
        """Test deleting a non-existent rule"""
        fake_id = str(uuid4())
        response = client.delete(f"/api/v1/notify/rules/{fake_id}")
        assert response.status_code == 404


# ============================================================================
# History Endpoints Tests
# ============================================================================

class TestHistoryEndpoints:
    """Test cases for history endpoints"""

    def test_get_history_empty(self, client):
        """Test getting history when storage is empty"""
        response = client.get("/api/v1/notify/history")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_history_with_data(self, client, sample_history):
        """Test getting history with data"""
        _history.append(sample_history)
        response = client.get("/api/v1/notify/history")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_history_filter_channel_id(self, client, sample_history):
        """Test getting history filtered by channel ID"""
        _history.append(sample_history)
        
        response = client.get(f"/api/v1/notify/history?channel_id={sample_history['channel_id']}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_history_filter_status(self, client, sample_history):
        """Test getting history filtered by status"""
        _history.append(sample_history)
        
        response = client.get("/api/v1/notify/history?status=sent")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_history_limit(self, client, sample_history):
        """Test getting history with limit"""
        for i in range(10):
            history_item = sample_history.copy()
            history_item["id"] = str(uuid4())
            _history.append(history_item)
        
        response = client.get("/api/v1/notify/history?limit=5")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 5

    def test_get_history_invalid_limit(self, client):
        """Test getting history with invalid limit"""
        response = client.get("/api/v1/notify/history?limit=0")
        assert response.status_code == 422

    def test_get_history_limit_exceeds_max(self, client):
        """Test getting history with limit exceeding maximum"""
        response = client.get("/api/v1/notify/history?limit=2000")
        assert response.status_code == 422


# ============================================================================
# Settings Endpoints Tests
# ============================================================================

class TestSettingsEndpoints:
    """Test cases for settings endpoints"""

    def test_get_settings(self, client):
        """Test getting notification settings"""
        response = client.get("/api/v1/notify/settings")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "min_level" in data
        assert "rate_limit_enabled" in data

    def test_update_settings_success(self, client):
        """Test updating notification settings successfully"""
        settings_data = {
            "enabled": False,
            "min_level": "warning",
            "rate_limit_per_minute": 20,
            "batch_enabled": True
        }
        response = client.patch("/api/v1/notify/settings", json=settings_data)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False
        assert data["min_level"] == "warning"
        assert data["rate_limit_per_minute"] == 20

    def test_update_settings_partial(self, client):
        """Test updating notification settings partially"""
        settings_data = {
            "enabled": False
        }
        response = client.patch("/api/v1/notify/settings", json=settings_data)
        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] == False
        # Other fields should remain unchanged
        assert data["min_level"] == "info"


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Test cases for error handling"""

    @patch('api.notify_advanced_router.logger')
    def test_get_channels_exception_handling(self, mock_logger, client):
        """Test exception handling in get_channels"""
        with patch('api.notify_advanced_router.ChannelResponse', side_effect=Exception("Test error")):
            sample_channel = {
                "id": str(uuid4()),
                "name": "Test Channel",
                "type": "email",
                "enabled": True,
                "config": {},
                "priority": 10,
                "retry_count": 3,
                "timeout": 30,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            _channels[sample_channel["id"]] = sample_channel
            response = client.get("/api/v1/notify/channels")
            assert response.status_code == 500

    @patch('api.notify_advanced_router.logger')
    def test_create_channel_exception_handling(self, mock_logger, client):
        """Test exception handling in create_channel"""
        with patch('api.notify_advanced_router.ChannelResponse', side_effect=Exception("Test error")):
            channel_data = {
                "name": "Test Channel",
                "type": "email"
            }
            response = client.post("/api/v1/notify/channels", json=channel_data)
            assert response.status_code == 500

    @patch('api.notify_advanced_router.logger')
    def test_get_channel_exception_handling(self, mock_logger, client):
        """Test exception handling in get_channel"""
        with patch('api.notify_advanced_router.ChannelResponse', side_effect=Exception("Test error")):
            sample_channel = {
                "id": str(uuid4()),
                "name": "Test Channel",
                "type": "email",
                "enabled": True,
                "config": {},
                "priority": 10,
                "retry_count": 3,
                "timeout": 30,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
            _channels[sample_channel["id"]] = sample_channel
            response = client.get(f"/api/v1/notify/channels/{sample_channel['id']}")
            assert response.status_code == 500


# ============================================================================
# Data Validation Tests
# ============================================================================

class TestDataValidation:
    """Test cases for data validation"""

    def test_channel_create_missing_required_field(self, client):
        """Test channel creation with missing required field"""
        channel_data = {
            "name": "Test Channel"
            # Missing type
        }
        response = client.post("/api/v1/notify/channels", json=channel_data)
        assert response.status_code == 422

    def test_channel_create_invalid_type(self, client):
        """Test channel creation with invalid type"""
        channel_data = {
            "name": "Test Channel",
            "type": "invalid_type"
        }
        response = client.post("/api/v1/notify/channels", json=channel_data)
        assert response.status_code == 422

    def test_template_create_missing_required_field(self, client):
        """Test template creation with missing required field"""
        template_data = {
            "name": "Test Template"
            # Missing subject, body
        }
        response = client.post("/api/v1/notify/templates", json=template_data)
        assert response.status_code == 422

    def test_rule_create_missing_required_field(self, client):
        """Test rule creation with missing required field"""
        rule_data = {
            "name": "Test Rule"
            # Missing condition, channels, template_id
        }
        response = client.post("/api/v1/notify/rules", json=rule_data)
        assert response.status_code == 422

    def test_review_rating_validation(self, client):
        """Test review rating validation (1-5)"""
        # This would be for review endpoints if they existed
        pass


# ============================================================================
# Mock Tests
# ============================================================================

class TestMockDependencies:
    """Test cases with mocked dependencies"""

    @patch('api.notify_advanced_router.datetime')
    def test_create_channel_with_mocked_datetime(self, mock_datetime, client):
        """Test channel creation with mocked datetime"""
        mock_datetime.utcnow.return_value = datetime(2024, 1, 1, 12, 0, 0)
        
        channel_data = {
            "name": "Test Channel",
            "type": "email"
        }
        response = client.post("/api/v1/notify/channels", json=channel_data)
        assert response.status_code == 200

    @patch('api.notify_advanced_router.uuid4')
    def test_create_channel_with_mocked_uuid(self, mock_uuid, client):
        """Test channel creation with mocked UUID"""
        mock_uuid.return_value = "test-uuid-123"
        
        channel_data = {
            "name": "Test Channel",
            "type": "email"
        }
        response = client.post("/api/v1/notify/channels", json=channel_data)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-uuid-123"


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration test cases"""

    def test_full_channel_workflow(self, client):
        """Test complete channel workflow: create, read, update, delete"""
        # Create
        channel_data = {
            "name": "Test Channel",
            "type": "email",
            "enabled": True
        }
        create_response = client.post("/api/v1/notify/channels", json=channel_data)
        assert create_response.status_code == 200
        channel_id = create_response.json()["id"]
        
        # Read
        get_response = client.get(f"/api/v1/notify/channels/{channel_id}")
        assert get_response.status_code == 200
        
        # Update
        update_data = {"name": "Updated Channel"}
        update_response = client.patch(f"/api/v1/notify/channels/{channel_id}", json=update_data)
        assert update_response.status_code == 200
        
        # Delete
        delete_response = client.delete(f"/api/v1/notify/channels/{channel_id}")
        assert delete_response.status_code == 200

    def test_full_template_workflow(self, client):
        """Test complete template workflow: create, read, update, delete"""
        # Create
        template_data = {
            "name": "Test Template",
            "subject": "Test Subject",
            "body": "Test Body",
            "type": "email"
        }
        create_response = client.post("/api/v1/notify/templates", json=template_data)
        assert create_response.status_code == 200
        template_id = create_response.json()["id"]
        
        # Read
        get_response = client.get(f"/api/v1/notify/templates/{template_id}")
        assert get_response.status_code == 200
        
        # Update
        update_data = {"name": "Updated Template"}
        update_response = client.patch(f"/api/v1/notify/templates/{template_id}", json=update_data)
        assert update_response.status_code == 200
        
        # Delete
        delete_response = client.delete(f"/api/v1/notify/templates/{template_id}")
        assert delete_response.status_code == 200

    def test_full_rule_workflow(self, client, sample_channel, sample_template):
        """Test complete rule workflow: create, read, update, delete"""
        _channels[sample_channel["id"]] = sample_channel
        _templates[sample_template["id"]] = sample_template
        
        # Create
        rule_data = {
            "name": "Test Rule",
            "condition": "alert_level == 'critical'",
            "channels": [sample_channel["id"]],
            "template_id": sample_template["id"],
            "enabled": True
        }
        create_response = client.post("/api/v1/notify/rules", json=rule_data)
        assert create_response.status_code == 200
        rule_id = create_response.json()["id"]
        
        # Read
        get_response = client.get(f"/api/v1/notify/rules/{rule_id}")
        assert get_response.status_code == 200
        
        # Update
        update_data = {"name": "Updated Rule"}
        update_response = client.patch(f"/api/v1/notify/rules/{rule_id}", json=update_data)
        assert update_response.status_code == 200
        
        # Delete
        delete_response = client.delete(f"/api/v1/notify/rules/{rule_id}")
        assert delete_response.status_code == 200

    def test_channel_template_rule_integration(self, client):
        """Test integration between channels, templates, and rules"""
        # Create channel
        channel_data = {"name": "Test Channel", "type": "email"}
        channel_response = client.post("/api/v1/notify/channels", json=channel_data)
        channel_id = channel_response.json()["id"]
        
        # Create template
        template_data = {
            "name": "Test Template",
            "subject": "Test",
            "body": "Test",
            "type": "email"
        }
        template_response = client.post("/api/v1/notify/templates", json=template_data)
        template_id = template_response.json()["id"]
        
        # Create rule using channel and template
        rule_data = {
            "name": "Test Rule",
            "condition": "test",
            "channels": [channel_id],
            "template_id": template_id,
            "enabled": True
        }
        rule_response = client.post("/api/v1/notify/rules", json=rule_data)
        assert rule_response.status_code == 200
        
        # Verify rule references
        rule = rule_response.json()
        assert channel_id in rule["channels"]
        assert rule["template_id"] == template_id


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.notify_advanced_router", "--cov-report=html"])
