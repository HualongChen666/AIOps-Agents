# -*- coding: utf-8 -*-
"""Core tests for core/notify_engine helpers.

These complement the root tests/test_notify_engine.py by exercising the
webhook, formatting and configuration helpers that are not imported by the
router-only code paths.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest


@pytest.fixture(autouse=True)
def _reset_http_client(monkeypatch):
    """Ensure the module-level HTTP client is reset for each test."""
    import core.notify_engine as ne

    monkeypatch.setattr(ne, "_http_client", None)


class TestValidateWebhookUrl:
    """Test the private _validate_webhook_url helper."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=abc", True),
            ("http://localhost:8000/webhook", True),
            ("", False),
            ("   ", False),
            (None, False),
            ("ftp://malicious.com", False),
            ("https://" + "x" * 3000, False),
        ],
    )
    def test_validate_webhook_url(self, url, expected):
        from core.notify_engine import _validate_webhook_url

        assert _validate_webhook_url(url, "test") is expected


class TestIsValidEmail:
    """Test the private _is_valid_email helper."""

    @pytest.mark.parametrize(
        "email,expected",
        [
            ("admin@example.com", True),
            ("a.b@c.d", True),
            ("not-an-email", False),
            ("", False),
            (None, False),
        ],
    )
    def test_is_valid_email(self, email, expected):
        from core.notify_engine import _is_valid_email

        assert _is_valid_email(email) is expected


class TestFormatAlertMessage:
    """Test alert message formatting helpers."""

    def test_format_alert_message_with_dict_metrics(self):
        from core.notify_engine import format_alert_message

        alert = {
            "severity": "critical",
            "type": "cpu_high",
            "message": "CPU usage high",
            "host": "server-01",
            "metrics": {"cpu": 95, "mem": 80},
        }
        result = format_alert_message(alert)
        assert "CPU usage high" in result
        assert "server-01" in result
        assert "cpu=95" in result
        assert "mem=80" in result

    def test_format_alert_message_with_non_dict_metrics(self):
        from core.notify_engine import format_alert_message

        alert = {
            "severity": "warning",
            "message": "disk full",
            "metrics": ["disk1", "disk2"],
        }
        result = format_alert_message(alert)
        assert "disk full" in result
        assert "['disk1', 'disk2']" in result

    def test_format_for_slack(self):
        from core.notify_engine import format_for_slack

        alert = {"type": "cpu", "message": "high", "severity": "critical"}
        result = format_for_slack(alert)
        assert "cpu" in result
        assert "high" in result

    def test_format_for_teams(self):
        from core.notify_engine import format_for_teams

        alert = {"type": "cpu", "message": "high", "severity": "warning"}
        result = format_for_teams(alert)
        data = json.loads(result)
        assert "WARNING" in data["text"]
        assert "high" in data["text"]


class TestNotifyConfig:
    """Test notify config loading and reload."""

    def test_load_notify_config_disabled(self, monkeypatch):
        from core.notify_engine import _load_notify_config

        monkeypatch.setenv("NOTIFY_ENABLED", "false")
        monkeypatch.setenv("WECOM_WEBHOOK", "")
        cfg = _load_notify_config()
        assert cfg["enabled"] is False
        assert cfg["min_level"] == "critical"

    def test_load_notify_config_invalid_url_ignored(self, monkeypatch):
        from core.notify_engine import _load_notify_config

        monkeypatch.setenv("NOTIFY_ENABLED", "true")
        monkeypatch.setenv("WECOM_WEBHOOK", "not-a-url")
        cfg = _load_notify_config()
        assert cfg["enabled"] is True
        assert cfg["wecom_webhook"] == ""

    @pytest.mark.asyncio
    async def test_reload_notify_config(self, monkeypatch):
        from core.notify_engine import reload_notify_config

        monkeypatch.setenv("NOTIFY_ENABLED", "true")
        monkeypatch.setenv("WECOM_WEBHOOK", "https://qyapi.weixin.qq.com/send")
        cfg = reload_notify_config()
        assert cfg["enabled"] is True


class TestPostWebhook:
    """Test the shared _post_webhook helper."""

    @pytest.mark.asyncio
    async def test_post_webhook_success(self):
        from core.notify_engine import _post_webhook

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "ok"
        mock_response.json.return_value = {"errcode": 0, "errmsg": "ok"}

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        import core.notify_engine as ne

        mock_client.is_closed = False
        ne._http_client = mock_client

        result = await _post_webhook("https://example.com", {"k": "v"}, "test")
        assert result["success"] is True

    @pytest.mark.asyncio
    async def test_post_webhook_failure_status(self):
        from core.notify_engine import _post_webhook

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "error"
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error",
            request=MagicMock(),
            response=mock_response,
        )

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=mock_response)

        import core.notify_engine as ne

        mock_client.is_closed = False
        ne._http_client = mock_client

        result = await _post_webhook("https://example.com", {"k": "v"}, "test")
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_post_webhook_exception(self):
        from core.notify_engine import _post_webhook

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=Exception("network error"))

        import core.notify_engine as ne

        mock_client.is_closed = False
        ne._http_client = mock_client

        result = await _post_webhook("https://example.com", {"k": "v"}, "test")
        assert result["success"] is False
        assert "network error" in result["error"]


class TestGetHttpClient:
    """Test the lazy HTTP client singleton."""

    def test_get_http_client_returns_client(self):
        from core.notify_engine import _get_http_client

        client = _get_http_client()
        assert client is not None

    def test_get_http_client_uses_existing(self):
        from core.notify_engine import _get_http_client

        client1 = _get_http_client()
        client2 = _get_http_client()
        assert client1 is client2


class TestSendWecom:
    """Test wecom webhook path."""

    @pytest.mark.asyncio
    async def test_send_wecom(self, monkeypatch):
        from core.notify_engine import _send_wecom

        async def fake_post(url, payload, channel):
            return {"success": True, "url": url, "channel": channel}

        monkeypatch.setattr("core.notify_engine._post_webhook", fake_post)
        monkeypatch.setattr(
            "core.notify_engine.NOTIFY_CONFIG", {"wecom_webhook": "https://wecom.example.com"}
        )

        alert = {
            "level": "critical",
            "title": "title",
            "desc": "desc",
            "raw_time": "2024-01-01",
        }
        result = await _send_wecom(alert)
        assert result["success"] is True
        assert result["channel"] == "企业微信"


class TestSendDingtalk:
    """Test dingtalk webhook path with and without secret."""

    @pytest.mark.asyncio
    async def test_send_dingtalk_with_secret(self, monkeypatch):
        from core.notify_engine import _send_dingtalk

        posted = {}

        async def fake_post(url, payload, channel):
            posted["url"] = url
            posted["channel"] = channel
            return {"success": True}

        monkeypatch.setattr("core.notify_engine._post_webhook", fake_post)
        monkeypatch.setattr(
            "core.notify_engine.NOTIFY_CONFIG",
            {
                "dingtalk_webhook": "https://oapi.dingtalk.com/robot/send",
                "dingtalk_secret": "SECRET",
            },
        )

        alert = {
            "level": "warning",
            "title": "title",
            "desc": "desc",
            "raw_time": "2024-01-01",
        }
        result = await _send_dingtalk(alert)
        assert result["success"] is True
        assert "timestamp" in posted["url"]
        assert "sign" in posted["url"]
        assert posted["channel"] == "钉钉"

    @pytest.mark.asyncio
    async def test_send_dingtalk_without_secret(self, monkeypatch):
        from core.notify_engine import _send_dingtalk

        async def fake_post(url, payload, channel):
            return {"success": True, "url": url}

        monkeypatch.setattr("core.notify_engine._post_webhook", fake_post)
        monkeypatch.setattr(
            "core.notify_engine.NOTIFY_CONFIG",
            {"dingtalk_webhook": "https://oapi.dingtalk.com/robot/send", "dingtalk_secret": ""},
        )

        alert = {
            "level": "info",
            "title": "title",
            "desc": "desc",
            "raw_time": "2024-01-01",
        }
        result = await _send_dingtalk(alert)
        assert result["success"] is True


class TestSendFeishu:
    """Test feishu webhook path."""

    @pytest.mark.asyncio
    async def test_send_feishu(self, monkeypatch):
        from core.notify_engine import _send_feishu

        async def fake_post(url, payload, channel):
            return {"success": True, "channel": channel}

        monkeypatch.setattr("core.notify_engine._post_webhook", fake_post)
        monkeypatch.setattr(
            "core.notify_engine.NOTIFY_CONFIG",
            {"feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"},
        )

        alert = {
            "level": "critical",
            "title": "title",
            "desc": "desc",
            "raw_time": "2024-01-01",
        }
        result = await _send_feishu(alert)
        assert result["success"] is True
        assert result["channel"] == "飞书"


class TestEmailNotification:
    """Test email notification path."""

    @pytest.mark.asyncio
    async def test_send_email_notification_success(self, monkeypatch):
        from core.notify_engine import send_email_notification

        smtp_mock = MagicMock()
        smtp_instance = smtp_mock.return_value.__enter__.return_value
        smtp_instance.sendmail = MagicMock()

        monkeypatch.setattr("smtplib.SMTP", smtp_mock)

        result = await send_email_notification("admin@example.com", "subject", "body")
        assert result["success"] is True
        smtp_instance.sendmail.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_notification_invalid_address(self):
        from core.notify_engine import send_email_notification

        result = await send_email_notification("not-an-email", "subject", "body")
        assert result["success"] is False
        assert "invalid email" in result["error"].lower()


class TestSendNotification:
    """Test the send_notification dispatcher."""

    @pytest.mark.asyncio
    async def test_send_notification_invalid_alert(self):
        from core.notify_engine import send_notification

        result = await send_notification({})
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_send_notification_critical_routes_multiple(self, monkeypatch):
        from core.notify_engine import send_notification

        calls = []

        async def fake_slack(message, channel="#alerts"):
            calls.append("slack")
            return {"success": True}

        async def fake_teams(message, webhook_url):
            calls.append("teams")
            return {"success": True}

        async def fake_email(to, subject, body):
            calls.append("email")
            return {"success": True}

        monkeypatch.setattr("core.notify_engine.send_slack_notification", fake_slack)
        monkeypatch.setattr("core.notify_engine.send_teams_notification", fake_teams)
        monkeypatch.setattr("core.notify_engine.send_email_notification", fake_email)

        alert = {
            "type": "cpu",
            "message": "high",
            "severity": "critical",
            "webhook_url": "https://teams.example.com",
        }
        result = await send_notification(alert)
        assert result["success"] is True
        assert "slack" in calls
        assert "teams" in calls
        assert "email" in calls

    @pytest.mark.asyncio
    async def test_send_notification_unsupported_channel(self, monkeypatch):
        from core.notify_engine import send_notification

        async def _fake_slack(*a, **kw):
            return {"success": True}

        monkeypatch.setattr(
            "core.notify_engine.send_slack_notification",
            _fake_slack,
        )

        alert = {"type": "cpu", "message": "high", "severity": "info"}
        result = await send_notification(alert, channels=["slack", "pagerduty"])
        assert result["success"] is True


class TestSendAlertNotification:
    """Test the main send_alert_notification entrypoint."""

    @pytest.mark.asyncio
    async def test_send_alert_notification_disabled(self, monkeypatch):
        from core.notify_engine import send_alert_notification

        monkeypatch.setattr("core.notify_engine.NOTIFY_CONFIG", {"enabled": False})

        result = await send_alert_notification({"level": "critical"})
        assert result["status"] == "disabled"

    @pytest.mark.asyncio
    async def test_send_alert_notification_invalid(self):
        from core.notify_engine import send_alert_notification

        result = await send_alert_notification("not-a-dict")
        assert result["status"] == "invalid_alert"

    @pytest.mark.asyncio
    async def test_send_alert_notification_filtered(self, monkeypatch):
        from core.notify_engine import send_alert_notification

        monkeypatch.setattr(
            "core.notify_engine.NOTIFY_CONFIG", {"enabled": True, "min_level": "critical"}
        )

        result = await send_alert_notification({"level": "info"})
        assert result["status"] == "filtered"

    @pytest.mark.asyncio
    async def test_send_alert_notification_no_channel(self, monkeypatch):
        from core.notify_engine import send_alert_notification

        monkeypatch.setattr(
            "core.notify_engine.NOTIFY_CONFIG",
            {"enabled": True, "min_level": "info", "wecom_webhook": ""},
        )

        result = await send_alert_notification({"level": "critical", "title": "t", "desc": "d"})
        assert result["status"] == "no_channel_configured"

    @pytest.mark.asyncio
    async def test_send_alert_notification_success(self, monkeypatch):
        from core.notify_engine import send_alert_notification

        async def fake_wecom(alert):
            return {"success": True, "channel": "wecom"}

        monkeypatch.setattr("core.notify_engine._send_wecom", fake_wecom)
        monkeypatch.setattr(
            "core.notify_engine.NOTIFY_CONFIG",
            {"enabled": True, "min_level": "info", "wecom_webhook": "https://wecom.example.com"},
        )

        result = await send_alert_notification(
            {"level": "critical", "title": "t", "desc": "d", "raw_time": "now"}
        )
        assert "wecom" in result


class TestNotificationHistory:
    """Test notification history helpers."""

    @pytest.mark.asyncio
    async def test_get_notification_history(self):
        from core.notify_engine import get_notification_history

        result = await get_notification_history(limit=10, severity="critical")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_query_notifications(self):
        from core.notify_engine import query_notifications

        result = await query_notifications(limit=5)
        assert result == []


class TestCloseHttpClient:
    """Test close_http_client helper."""

    @pytest.mark.asyncio
    async def test_close_http_client(self):
        import core.notify_engine as ne

        mock_client = MagicMock()
        mock_client.is_closed = False
        mock_client.aclose = AsyncMock()
        ne._http_client = mock_client

        await ne.close_http_client()
        mock_client.aclose.assert_awaited_once()
