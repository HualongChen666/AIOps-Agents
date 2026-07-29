# -*- coding: utf-8 -*-
"""Notify Router Tests
告警通知路由API基础测试
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.notify_router import (
    get_notify_config,
    notify_health,
    reload_config,
    send_manual_notify,
    send_test_notify,
)

# Mock problematic imports before importing router
sys.modules["core.authentication"] = MagicMock()
sys.modules["core.notify_engine"] = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/notify", tags=["告警通知"])
    test_router.add_api_route("/config", get_notify_config, methods=["GET"])
    test_router.add_api_route("/test", send_test_notify, methods=["POST"])
    test_router.add_api_route("/send", send_manual_notify, methods=["POST"])
    test_router.add_api_route("/reload", reload_config, methods=["POST"])
    test_router.add_api_route("/health", notify_health, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestNotifyRouter:
    """测试告警通知路由"""

    def test_get_notify_config(self, client):
        """测试获取通知渠道配置状态"""
        with patch("api.notify_router._safe_get_notify_config") as mock_config:
            mock_config.return_value = {
                "enabled": True,
                "min_level": "critical",
                "wecom_webhook": "http://test",
                "dingtalk_webhook": "http://test",
                "feishu_webhook": "http://test",
                "email_webhook": "http://test",
            }
            response = client.get("/api/notify/config")
            assert response.status_code == 200
            data = response.json()
            assert "enabled" in data

    def test_send_test_notify(self, client):
        """测试发送测试通知"""
        with patch("api.notify_router._safe_get_notify_config") as mock_config:
            mock_config.return_value = {"enabled": True}
            with patch("api.notify_router.send_alert_notification") as mock_send:

                async def mock_send_func(alert):
                    return {"wecom": True, "dingtalk": True}

                mock_send.side_effect = mock_send_func
                response = client.post(
                    "/api/notify/test",
                    json={"level": "critical", "title": "Test", "desc": "Test message"},
                )
                assert response.status_code == 200

    def test_send_test_notify_disabled(self, client):
        """测试通知引擎未启用时的测试通知"""
        with patch("api.notify_router._safe_get_notify_config") as mock_config:
            mock_config.return_value = {"enabled": False}
            response = client.post(
                "/api/notify/test",
                json={"level": "critical", "title": "Test", "desc": "Test message"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "skipped"

    def test_send_manual_notify(self, client):
        """测试手动推送告警通知"""
        with patch("api.notify_router.send_alert_notification") as mock_send:

            async def mock_send_func(alert):
                return {"wecom": True, "dingtalk": True}

            mock_send.side_effect = mock_send_func
            response = client.post(
                "/api/notify/send",
                json={"level": "critical", "title": "Test Alert", "desc": "Test description"},
            )
            assert response.status_code == 200

    def test_send_manual_notify_missing_fields(self, client):
        """测试缺少必填字段的手动推送"""
        response = client.post("/api/notify/send", json={"level": "critical"})
        assert response.status_code == 422

    def test_reload_config(self, client):
        """测试热重载通知配置"""
        with patch("api.notify_router.reload_notify_config") as mock_reload:
            mock_reload.return_value = {
                "enabled": True,
                "min_level": "critical",
                "wecom_webhook": "http://test",
            }
            response = client.post("/api/notify/reload")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ok"

    def test_notify_health(self, client):
        """测试通知模块健康检查"""
        with patch("api.notify_router._safe_get_notify_config") as mock_config:
            mock_config.return_value = {"enabled": True, "wecom_webhook": "http://test"}
            response = client.get("/api/notify/health")
            assert response.status_code == 200
            data = response.json()
            assert "module_loaded" in data

    def test_get_notify_config_error(self, client):
        """测试获取通知配置异常"""
        with patch("api.notify_router._safe_get_notify_config") as mock_config:
            mock_config.side_effect = RuntimeError("config error")
            response = client.get("/api/notify/config")
            assert response.status_code == 500

    def test_send_test_notify_error(self, client):
        """测试发送测试通知异常"""
        with patch("api.notify_router._safe_get_notify_config") as mock_config:
            mock_config.return_value = {"enabled": True}
            with patch("api.notify_router.send_alert_notification") as mock_send:

                async def fail(*args, **kwargs):
                    raise RuntimeError("send error")

                mock_send.side_effect = fail
                response = client.post(
                    "/api/notify/test",
                    json={"level": "critical", "title": "Test", "desc": "Test message"},
                )
                assert response.status_code == 500

    def test_send_manual_notify_invalid_level(self, client):
        """测试手动推送非法 level"""
        response = client.post(
            "/api/notify/send",
            json={"level": "unknown", "title": "Test", "desc": "desc"},
        )
        assert response.status_code == 422

    def test_send_manual_notify_adds_raw_time(self, client):
        """测试缺失 raw_time 自动补充"""
        with patch("api.notify_router.send_alert_notification") as mock_send:

            async def ok(alert):
                return {"ok": True}

            mock_send.side_effect = ok
            response = client.post(
                "/api/notify/send",
                json={"level": "critical", "title": "Test", "desc": "desc"},
            )
            assert response.status_code == 200

    def test_send_manual_notify_error(self, client):
        """测试手动推送异常"""
        with patch("api.notify_router.send_alert_notification") as mock_send:

            async def fail(*args, **kwargs):
                raise RuntimeError("send error")

            mock_send.side_effect = fail
            response = client.post(
                "/api/notify/send",
                json={"level": "critical", "title": "Test", "desc": "desc"},
            )
            assert response.status_code == 500

    def test_reload_config_error(self, client):
        """测试热重载配置异常"""
        with patch("api.notify_router.reload_notify_config") as mock_reload:
            mock_reload.side_effect = RuntimeError("reload error")
            response = client.post("/api/notify/reload")
            assert response.status_code == 500

    def test_notify_health_error(self, client):
        """测试通知健康检查异常"""
        with patch("api.notify_router._safe_get_notify_config") as mock_config:
            mock_config.side_effect = RuntimeError("health error")
            response = client.get("/api/notify/health")
            assert response.status_code == 200
            assert response.json()["module_loaded"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
