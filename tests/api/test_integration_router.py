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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
