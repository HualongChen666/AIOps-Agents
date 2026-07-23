# -*- coding: utf-8 -*-
"""测试集成管理器模块"""

import asyncio
import hmac
import json
from hashlib import sha256
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestIntegrationManagerModule:
    """测试集成管理器模块"""

    def test_integration_manager_module_exists(self):
        """测试集成管理器模块存在"""
        from core import integration_manager

        assert integration_manager is not None

    def test_integration_manager_has_functions(self):
        """测试集成管理器模块有函数"""
        from core import integration_manager

        # 检查模块有函数或类
        assert len(dir(integration_manager)) > 0


class FakeAsyncClient:
    """Replace httpx.AsyncClient to avoid real HTTP calls."""

    def __init__(self, *args, **kwargs):
        self.get = AsyncMock(
            return_value=MagicMock(
                status_code=200,
                json=MagicMock(return_value={"data": {"result": []}}),
            )
        )
        self.post = AsyncMock(return_value=MagicMock(raise_for_status=MagicMock()))


@pytest.fixture
def manager(monkeypatch):
    from core import integration_manager

    monkeypatch.setattr(integration_manager, "HTTP_AVAILABLE", True)
    monkeypatch.setattr(integration_manager, "httpx", MagicMock(AsyncClient=FakeAsyncClient))

    from core.integration_manager import IntegrationManager

    mgr = IntegrationManager()
    return mgr


class TestIntegrationRegistration:
    def test_register_prometheus_success(self, manager):
        from core.integration_manager import IntegrationType

        integration = asyncio.run(
            manager.register_integration(
                IntegrationType.MONITORING,
                "prometheus",
                {"url": "http://localhost:9090"},
            )
        )
        assert integration.name == "prometheus"
        assert integration.status.name == "ACTIVE"

    def test_register_prometheus_invalid_config(self, manager):
        from core.integration_manager import IntegrationType

        with pytest.raises(ValueError):
            asyncio.run(
                manager.register_integration(
                    IntegrationType.MONITORING,
                    "prometheus",
                    {},
                )
            )

    def test_register_cloud_success(self, manager):
        from core.integration_manager import IntegrationType

        integration = asyncio.run(
            manager.register_integration(
                IntegrationType.CLOUD,
                "aws",
                {
                    "access_key_id": "a",
                    "secret_access_key": "s",
                    "region": "r",
                },
            )
        )
        assert integration.name == "aws"
        assert integration.status.name == "ACTIVE"

    def test_test_integration_not_found(self, manager):
        result = asyncio.run(manager.test_integration("missing"))
        assert result["success"] is False


class TestIntegrationQueries:
    def test_query_prometheus_metrics(self, manager):
        from core.integration_manager import IntegrationType

        integration = asyncio.run(
            manager.register_integration(
                IntegrationType.MONITORING,
                "prometheus",
                {"url": "http://localhost:9090"},
            )
        )
        result = asyncio.run(manager.query_prometheus_metrics(integration.integration_id, "up"))
        assert "data" in result

    def test_query_prometheus_not_found(self, manager):
        result = asyncio.run(manager.query_prometheus_metrics("missing", "up"))
        assert "error" in result

    def test_trigger_jenkins_job(self, manager):
        from core.integration_manager import IntegrationType

        integration = asyncio.run(
            manager.register_integration(
                IntegrationType.CICD,
                "jenkins",
                {"url": "http://jenkins", "username": "u", "api_token": "t"},
            )
        )
        result = asyncio.run(manager.trigger_jenkins_job(integration.integration_id, "job"))
        assert result["success"] is True

    def test_create_jira_issue(self, manager):
        from core.integration_manager import IntegrationType

        integration = asyncio.run(
            manager.register_integration(
                IntegrationType.ITSM,
                "jira",
                {"url": "http://jira", "username": "u", "api_token": "t"},
            )
        )
        result = asyncio.run(
            manager.create_jira_issue(integration.integration_id, "summary", "desc")
        )
        assert result["success"] is True


class TestNotificationAndWebhook:
    def test_send_notification_success(self, manager):
        manager.notification_channels["slack"] = {
            "name": "slack",
            "type": "webhook",
            "config": {"url": "http://slack"},
            "enabled": True,
        }
        message = asyncio.run(manager.send_notification("slack", "#ops", "Test", "Body"))
        assert message.sent is True

    def test_send_notification_channel_not_found(self, manager):
        message = asyncio.run(manager.send_notification("missing", "x", "Test", "Body"))
        assert message.error is not None

    def test_send_notification_channel_disabled(self, manager):
        manager.notification_channels["slack"] = {
            "name": "slack",
            "type": "webhook",
            "config": {"url": "http://slack"},
            "enabled": False,
        }
        message = asyncio.run(manager.send_notification("slack", "#ops", "Test", "Body"))
        assert message.error is not None

    def test_register_and_handle_webhook(self, manager):
        webhook_id = asyncio.run(
            manager.register_webhook("github", "alert", "http://endpoint", "secret")
        )

        payload = {"foo": "bar"}
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new("secret".encode(), payload_str.encode(), sha256).hexdigest()

        result = asyncio.run(manager.handle_webhook(webhook_id, payload, signature))
        assert result["success"] is True

    def test_handle_webhook_invalid_signature(self, manager):
        webhook_id = asyncio.run(
            manager.register_webhook("github", "alert", "http://endpoint", "secret")
        )
        result = asyncio.run(manager.handle_webhook(webhook_id, {"foo": "bar"}, "bad"))
        assert result["success"] is False

    def test_handle_webhook_not_found(self, manager):
        result = asyncio.run(manager.handle_webhook("missing", {}, None))
        assert result["success"] is False

    def test_webhook_event_types(self, manager):
        for event_type in ["alert", "deployment", "incident"]:
            webhook_id = asyncio.run(
                manager.register_webhook("source", event_type, "http://e", None)
            )
            result = asyncio.run(manager.handle_webhook(webhook_id, {"k": "v"}, None))
            assert result["success"] is True


class TestIntegrationSummary:
    def test_get_integration_summary(self, manager):
        from core.integration_manager import IntegrationType

        asyncio.run(
            manager.register_integration(
                IntegrationType.MONITORING,
                "prometheus",
                {"url": "http://localhost:9090"},
            )
        )
        manager.notification_channels["slack"] = {
            "name": "slack",
            "type": "webhook",
            "config": {},
            "enabled": True,
        }
        summary = manager.get_integration_summary()
        assert summary["total_integrations"] == 1
        assert summary["notification_channels"] == 1

    def test_validate_config_directly(self, manager):
        schema = {"url": {"type": "string", "required": True}}
        result = manager._validate_config({"url": "http://x"}, schema)
        assert result["valid"] is True

        result = manager._validate_config({}, schema)
        assert result["valid"] is False

    def test_integration_templates_loaded(self, manager):
        assert "prometheus" in manager.integration_templates
        assert "slack" in manager.integration_templates


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
