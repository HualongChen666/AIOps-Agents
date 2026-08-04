# -*- coding: utf-8 -*-
"""
Integration Router Tests
集成生态路由API基础测试
"""

import sys
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# isort: off
# Mock problematic imports before importing router
sys.modules["core.integration_manager"] = MagicMock()
sys.modules["core.integration_manager"].INTEGRATION_AVAILABLE = True
sys.modules["core.integration_manager"].integration_manager = MagicMock()

from api.integration_router import router

# isort: on


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Include router without authentication dependencies
    app.include_router(router)
    return TestClient(app)


class TestIntegrationRouter:
    """测试集成生态路由"""

    def test_list_integrations(self, client):
        """测试列出集成"""
        with patch("api.integration_router.integration_manager") as mock_manager:
            mock_manager.list_integrations.return_value = []

            response = client.get("/api/v1/integration/list")
            assert response.status_code in [200, 401, 403]

    def test_get_integration_status(self, client):
        """测试获取集成状态"""
        with patch("api.integration_router.integration_manager") as mock_manager:
            mock_manager.get_status.return_value = {"status": "active"}

            response = client.get("/api/v1/integration/status/test-integration")
            assert response.status_code in [200, 401, 403, 404]

    def test_register_integration(self, client):
        """测试注册集成"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_integration = Mock()
            mock_integration.integration_id = "int-123"
            mock_integration.integration_type.value = "prometheus"
            mock_integration.name = "Prometheus监控"
            mock_integration.enabled = True
            mock_integration.status.value = "active"
            mock_integration.last_tested = None
            mock_manager.register_integration = AsyncMock(return_value=mock_integration)

            response = client.post(
                "/api/v1/integration/register",
                json={
                    "integration_type": "prometheus",
                    "name": "Prometheus监控",
                    "config": {"url": "http://localhost:9090"},
                    "enabled": True,
                },
            )
            assert response.status_code in [200, 503]

    def test_delete_integration(self, client):
        """测试删除集成"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.integrations = {"int-123": Mock()}

            response = client.delete("/api/v1/integration/int-123")
            assert response.status_code in [200, 503]

    def test_send_notification(self, client):
        """测试发送通知"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_message = Mock()
            mock_message.message_id = "msg-123"
            mock_message.channel = "slack"
            mock_message.recipient = "#alerts"
            mock_message.sent = True
            mock_message.error = None
            mock_message.timestamp = Mock()
            mock_message.timestamp.isoformat.return_value = "2026-07-03T00:00:00Z"
            mock_manager.send_notification = AsyncMock(return_value=mock_message)

            response = client.post(
                "/api/v1/integration/notification/send",
                json={
                    "channel": "slack",
                    "recipient": "#alerts",
                    "subject": "Test Alert",
                    "body": "Test message",
                    "priority": "normal",
                },
            )
            assert response.status_code in [200, 503]

    def test_get_integration_types(self, client):
        """测试获取支持的集成类型"""
        response = client.get("/api/v1/integration/types")
        assert response.status_code == 200
        data = response.json()
        assert "integration_types" in data

    @pytest.mark.skip("endpoint not found")
    def test_test_integration(self, client):
        """测试测试集成连接"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.test_connection = AsyncMock(
                return_value={"success": True, "latency_ms": 50}
            )

            response = client.post("/api/v1/integration/test/int-123")
            assert response.status_code in [200, 503]

    @pytest.mark.skip("endpoint not found")
    def test_enable_integration(self, client):
        """测试启用集成"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.enable_integration = AsyncMock(return_value=True)

            response = client.post("/api/v1/integration/enable/int-123")
            assert response.status_code in [200, 503]

    @pytest.mark.skip("endpoint not found")
    def test_disable_integration(self, client):
        """测试禁用集成"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.disable_integration = AsyncMock(return_value=True)

            response = client.post("/api/v1/integration/disable/int-123")
            assert response.status_code in [200, 503]

    @pytest.mark.skip("endpoint not found")
    def test_update_integration_config(self, client):
        """测试更新集成配置"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.update_config = AsyncMock(return_value=True)

            response = client.put(
                "/api/v1/integration/int-123/config", json={"url": "http://new-url"}
            )
            assert response.status_code in [200, 503]

    @pytest.mark.skip("async mock issue")
    def test_query_prometheus(self, client):
        """测试Prometheus查询"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.query_prometheus = AsyncMock(
                return_value={"result": [{"value": [1234567890, "42"]}]}
            )

            response = client.post(
                "/api/v1/integration/prometheus/query",
                json={"integration_id": "int-123", "query": "up", "time_range": "1h"},
            )
            assert response.status_code in [200, 503]

    @pytest.mark.skip("endpoint not found")
    def test_register_webhook(self, client):
        """测试注册Webhook"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_webhook = Mock()
            mock_webhook.webhook_id = "web-123"
            mock_webhook.source = "github"
            mock_webhook.event_type = "push"
            mock_webhook.endpoint = "http://example.com/webhook"
            mock_webhook.enabled = True
            mock_manager.register_webhook = AsyncMock(return_value=mock_webhook)

            response = client.post(
                "/api/v1/integration/webhooks/register",
                json={
                    "source": "github",
                    "event_type": "push",
                    "endpoint": "http://example.com/webhook",
                },
            )
            assert response.status_code in [200, 503]

    @pytest.mark.skip("endpoint not found")
    def test_list_webhooks(self, client):
        """测试列出Webhook"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.list_webhooks.return_value = []

            response = client.get("/api/v1/integration/webhooks")
            assert response.status_code in [200, 503]

    @pytest.mark.skip("endpoint not found")
    def test_delete_webhook(self, client):
        """测试删除Webhook"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.webhooks = {"web-123": Mock()}

            response = client.delete("/api/v1/integration/webhooks/web-123")
            assert response.status_code in [200, 503]

    def test_get_integration_not_found(self, client):
        """测试获取不存在的集成状态"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.integrations = {}

            response = client.get("/api/v1/integration/status/nonexistent")
            assert response.status_code in [200, 404, 503]

    def test_register_integration_unavailable(self, client):
        """测试集成管理器不可用时注册"""
        with patch("api.integration_router.INTEGRATION_AVAILABLE", False):
            response = client.post(
                "/api/v1/integration/register",
                json={"integration_type": "prometheus", "name": "Test", "config": {}},
            )
            assert response.status_code == 503

    def test_test_integration(self, client):
        """测试测试集成连接"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.test_integration = AsyncMock(
                return_value={"success": True, "latency_ms": 50}
            )

            response = client.post("/api/v1/integration/test/int-123")
            assert response.status_code == 200

    def test_get_notification_channels(self, client):
        """测试获取通知渠道"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.notification_channels = {
                "slack": {"type": "slack", "enabled": True},
                "email": {"type": "email", "enabled": True},
            }

            response = client.get("/api/v1/integration/notification/channels")
            assert response.status_code == 200

    def test_register_webhook(self, client):
        """测试注册Webhook"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.register_webhook = AsyncMock(return_value="web-123")

            response = client.post(
                "/api/v1/integration/webhook/register",
                json={
                    "source": "github",
                    "event_type": "push",
                    "endpoint": "http://example.com/webhook",
                },
            )
            assert response.status_code == 200

    def test_handle_webhook(self, client):
        """测试处理Webhook事件"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.handle_webhook = AsyncMock(return_value={"success": True})

            response = client.post(
                "/api/v1/integration/webhook/handle?webhook_id=web-123",
                json={"payload": {"test": "data"}},
            )
            assert response.status_code == 200

    def test_list_webhooks(self, client):
        """测试列出Webhook"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.webhooks.values.return_value = [
                {
                    "webhook_id": "web-123",
                    "source": "github",
                    "event_type": "push",
                    "endpoint": "http://example.com",
                    "enabled": True,
                    "created_at": "2026-07-03",
                }
            ]

            response = client.get("/api/v1/integration/webhooks")
            assert response.status_code == 200

    def test_query_prometheus_metrics(self, client):
        """测试Prometheus查询"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.query_prometheus_metrics = AsyncMock(
                return_value={"result": [{"value": [1234567890, "42"]}]}
            )

            response = client.post(
                "/api/v1/integration/prometheus/query",
                json={"integration_id": "int-123", "query": "up", "time_range": "1h"},
            )
            assert response.status_code == 200

    def test_trigger_jenkins_job(self, client):
        """测试触发Jenkins任务"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.trigger_jenkins_job = AsyncMock(
                return_value={"build_number": 123, "status": "queued"}
            )

            response = client.post(
                "/api/v1/integration/jenkins/trigger",
                json={"integration_id": "int-123", "job_name": "test-job"},
            )
            assert response.status_code == 200

    def test_create_jira_issue(self, client):
        """测试创建Jira问题"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.create_jira_issue = AsyncMock(
                return_value={"issue_id": "PROJ-123", "key": "PROJ-123"}
            )

            response = client.post(
                "/api/v1/integration/jira/issue",
                json={
                    "integration_id": "int-123",
                    "summary": "Test issue",
                    "description": "Test description",
                },
            )
            assert response.status_code == 200

    def test_get_integration_templates(self, client):
        """测试获取集成模板"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_type = Mock()
            mock_type.value = "prometheus"
            mock_manager.integration_templates.items.return_value = [
                ("prometheus", {"type": mock_type, "name": "Prometheus", "config_schema": {}, "default_config": {}})
            ]

            response = client.get("/api/v1/integration/templates")
            assert response.status_code == 200

    def test_get_integration_summary(self, client):
        """测试获取集成摘要"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.get_integration_summary.return_value = {
                "total_integrations": 5,
                "active": 4,
                "failed": 1,
            }

            response = client.get("/api/v1/integration/summary")
            assert response.status_code == 200

    def test_get_webhook_events(self, client):
        """测试获取Webhook事件"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_event = Mock()
            mock_event.event_id = "evt-123"
            mock_event.source = "github"
            mock_event.event_type = "push"
            mock_event.processed = True
            mock_event.retry_count = 0
            mock_event.timestamp.isoformat.return_value = "2026-07-03T10:00:00Z"
            mock_manager.webhook_events = [mock_event]

            response = client.get("/api/v1/integration/events")
            assert response.status_code == 200

    def test_list_integrations_with_filter(self, client):
        """测试列出集成（带过滤）"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
            patch("api.integration_router.IntegrationType") as mock_type,
            patch("api.integration_router.IntegrationStatus") as mock_status,
        ):
            mock_integration = Mock()
            mock_integration.integration_type = mock_type
            mock_integration.status = mock_status
            mock_integration.integration_type.value = "prometheus"
            mock_integration.status.value = "active"
            mock_integration.last_tested = None
            mock_integration.last_error = None
            mock_manager.integrations.values.return_value = [mock_integration]

            response = client.get("/api/v1/integration/list?integration_type=prometheus")
            assert response.status_code in [200, 400]

    def test_list_integrations_invalid_type(self, client):
        """测试列出集成（无效类型）"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
            patch("api.integration_router.IntegrationType") as mock_type,
        ):
            mock_type.side_effect = ValueError("Invalid type")
            mock_manager.integrations.values.return_value = []

            response = client.get("/api/v1/integration/list?integration_type=invalid")
            assert response.status_code == 400

    def test_delete_integration_not_found(self, client):
        """测试删除集成（不存在）"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.integration_manager") as mock_manager,
        ):
            mock_manager.integrations = {}

            response = client.delete("/api/v1/integration/nonexistent")
            assert response.status_code == 404

    def test_register_integration_invalid_type(self, client):
        """测试注册集成（无效类型）"""
        with (
            patch("api.integration_router.INTEGRATION_AVAILABLE", True),
            patch("api.integration_router.IntegrationType") as mock_type,
        ):
            mock_type.side_effect = ValueError("Invalid type")

            response = client.post(
                "/api/v1/integration/register",
                json={"integration_type": "invalid", "name": "Test", "config": {}},
            )
            assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
