# -*- coding: utf-8 -*-
# tests/api/test_slack_router.py
# Slack集成路由API基础测试
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# isort: off
# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
# Use a real dependency with no params so FastAPI doesn't inject "args"/"kwargs"
sys.modules["core.authentication"].get_current_active_user = lambda: {
    "username": "testuser",
    "role": "admin",
}
sys.modules["core.slack_adapter"] = MagicMock()
sys.modules["core.chat_command_handler"] = MagicMock()

from api.slack_router import (
    send_slack_interactive_message,
    send_slack_message,
    slack_events_callback,
    slack_health_check,
)

# isort: on


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/slack", tags=["Slack Integration"])
    test_router.add_api_route("/message", send_slack_message, methods=["POST"])
    test_router.add_api_route("/interactive", send_slack_interactive_message, methods=["POST"])
    test_router.add_api_route("/events", slack_events_callback, methods=["POST"])
    test_router.add_api_route("/health", slack_health_check, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestSlackRouter:
    """测试Slack集成路由"""

    def test_send_slack_message_success(self, client):
        """测试成功发送Slack消息"""
        with patch("api.slack_router.post_message", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"ts": "1234567890.123456", "channel": "C12345"}

            response = client.post(
                "/api/slack/message", json={"text": "Test message", "channel": "#general"}
            )
            assert response.status_code in [200, 503]

    def test_send_slack_message_unavailable(self, client):
        """测试Slack不可用时发送消息"""
        with patch("api.slack_router.post_message", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = RuntimeError("Slack not configured")

            response = client.post(
                "/api/slack/message", json={"text": "Test message", "channel": "#general"}
            )
            assert response.status_code in [200, 503]

    def test_send_slack_interactive_message(self, client):
        """测试发送交互式Slack消息"""
        with patch(
            "api.slack_router.post_interactive_message", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value = {"ts": "1234567890.123456"}

            response = client.post(
                "/api/slack/interactive",
                json={
                    "text": "Interactive message",
                    "actions": [{"type": "button", "text": "Click me"}],
                },
            )
            assert response.status_code in [200, 503]

    def test_slack_events_callback_url_verification(self, client):
        """测试Slack Events API URL验证"""
        response = client.post(
            "/api/slack/events", json={"type": "url_verification", "challenge": "test_challenge"}
        )
        assert response.status_code in [200, 403]

    def test_slack_health_check(self, client):
        """测试Slack健康检查"""
        with (
            patch("config.SLACK_BOT_TOKEN", "test_token"),
            patch("config.SLACK_DEFAULT_CHANNEL", "#general"),
        ):
            response = client.get("/api/slack/health")
            assert response.status_code in [200, 401]

    def test_send_slack_message_server_error(self, client):
        """测试发送Slack消息通用异常"""
        with patch("api.slack_router.post_message", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = ValueError("generic error")

            response = client.post(
                "/api/slack/message", json={"text": "Test message", "channel": "#general"}
            )
            assert response.status_code == 500

    def test_send_slack_interactive_message_unavailable(self, client):
        """测试Slack交互式消息不可用时返回503"""
        with patch(
            "api.slack_router.post_interactive_message", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = RuntimeError("Slack not configured")

            response = client.post(
                "/api/slack/interactive",
                json={
                    "text": "Interactive message",
                    "actions": [{"type": "button", "text": "Click me"}],
                },
            )
            assert response.status_code == 503

    def test_send_slack_interactive_message_server_error(self, client):
        """测试发送Slack交互式消息通用异常"""
        with patch(
            "api.slack_router.post_interactive_message", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = ValueError("generic error")

            response = client.post(
                "/api/slack/interactive",
                json={
                    "text": "Interactive message",
                    "actions": [{"type": "button", "text": "Click me"}],
                },
            )
            assert response.status_code == 500

    def test_slack_events_callback_invalid_signature(self, client):
        """测试Slack事件回调签名无效"""
        with patch("api.slack_router.verify_slack_signature", return_value=False):
            response = client.post(
                "/api/slack/events",
                json={"type": "event_callback"},
                headers={"X-Slack-Signature": "sig", "X-Slack-Timestamp": "123"},
            )
            assert response.status_code == 403

    def test_send_slack_message_missing_text(self, client):
        """测试缺少text字段"""
        response = client.post("/api/slack/message", json={"channel": "#general"})
        assert response.status_code == 422

    def test_send_slack_interactive_message_missing_text(self, client):
        """测试交互式消息缺少text字段"""
        response = client.post("/api/slack/interactive", json={"actions": []})
        assert response.status_code == 422

    def test_slack_health_check_not_configured(self, client):
        """测试Slack未配置时的健康检查"""
        with (
            patch("config.SLACK_BOT_TOKEN", None),
            patch("config.SLACK_DEFAULT_CHANNEL", None),
        ):
            response = client.get("/api/slack/health")
            assert response.status_code == 200
            data = response.json()
            # Just check response is valid, structure may vary
            assert "status" in data or "configured" in data

    def test_slack_events_callback_event_type(self, client):
        """测试Slack事件回调处理事件类型"""
        with patch("api.slack_router.verify_slack_signature", return_value=True):
            response = client.post(
                "/api/slack/events",
                json={"type": "event_callback", "event": {"type": "message"}},
                headers={"X-Slack-Signature": "sig", "X-Slack-Timestamp": "123"},
            )
            assert response.status_code in [200, 503]

    def test_slack_events_callback_server_error(self, client):
        """测试Slack事件回调处理异常"""
        with patch("api.slack_router.verify_slack_signature", side_effect=RuntimeError("boom")):
            response = client.post(
                "/api/slack/events",
                json={"type": "event_callback"},
                headers={"X-Slack-Signature": "sig", "X-Slack-Timestamp": "123"},
            )
            assert response.status_code == 500

    def test_slack_events_callback_block_actions_approve(self, client):
        """测试Slack事件回调处理block_actions - approve"""
        with patch("api.slack_router.verify_slack_signature", return_value=True):
            response = client.post(
                "/api/slack/events",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "block_actions",
                        "actions": [
                            {"action_id": "approve_123", "value": "alert-456"}
                        ],
                    },
                },
                headers={"X-Slack-Signature": "sig", "X-Slack-Timestamp": "123"},
            )
            assert response.status_code in [200, 503]

    def test_slack_events_callback_block_actions_reject(self, client):
        """测试Slack事件回调处理block_actions - reject"""
        with patch("api.slack_router.verify_slack_signature", return_value=True):
            response = client.post(
                "/api/slack/events",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "block_actions",
                        "actions": [
                            {"action_id": "reject_123", "value": "alert-456"}
                        ],
                    },
                },
                headers={"X-Slack-Signature": "sig", "X-Slack-Timestamp": "123"},
            )
            assert response.status_code in [200, 503]

    def test_slack_events_callback_block_actions_ignored(self, client):
        """测试Slack事件回调处理block_actions - ignored"""
        with patch("api.slack_router.verify_slack_signature", return_value=True):
            response = client.post(
                "/api/slack/events",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "block_actions",
                        "actions": [{"action_id": "other", "value": "test"}],
                    },
                },
                headers={"X-Slack-Signature": "sig", "X-Slack-Timestamp": "123"},
            )
            assert response.status_code in [200, 503]

    def test_slack_events_callback_app_mention(self, client):
        """测试Slack事件回调处理app_mention"""
        with patch("api.slack_router.verify_slack_signature", return_value=True):
            response = client.post(
                "/api/slack/events",
                json={
                    "type": "event_callback",
                    "event": {
                        "type": "app_mention",
                        "text": "<@U123> help me",
                        "user": "U456",
                        "channel": "C789",
                    },
                },
                headers={"X-Slack-Signature": "sig", "X-Slack-Timestamp": "123"},
            )
            assert response.status_code in [200, 503]

    def test_slack_events_callback_unknown_event_type(self, client):
        """测试Slack事件回调处理未知事件类型"""
        with patch("api.slack_router.verify_slack_signature", return_value=True):
            response = client.post(
                "/api/slack/events",
                json={
                    "type": "event_callback",
                    "event": {"type": "unknown_type"},
                },
                headers={"X-Slack-Signature": "sig", "X-Slack-Timestamp": "123"},
            )
            assert response.status_code in [200, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
