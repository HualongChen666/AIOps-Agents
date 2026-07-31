# -*- coding: utf-8 -*-
# tests/test_notify_engine.py
# 通知引擎单元测试
import asyncio  # noqa: F401
from datetime import datetime  # noqa: F401
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.xdist_group("notify_engine"), pytest.mark.integration]

from core.notify_engine import (
    get_notification_history,
    send_email_notification,
    send_notification,
    send_slack_notification,
    send_teams_notification,
)


class TestSlackNotification:
    """Slack 通知测试"""

    @pytest.mark.asyncio
    async def test_send_slack_notification_success(self, mock_logger):
        """测试 Slack 通知发送成功"""
        message = "Test alert: CPU usage high"
        channel = "#alerts"

        with patch("core.notify_engine.logger", mock_logger):
            # Mock Slack 客户端
            with patch("core.notify_engine._get_slack_client", AsyncMock(return_value=MagicMock())):
                mock_client = MagicMock()
                mock_client.chat_postMessage = AsyncMock(return_value={"ok": True})

                with patch("core.notify_engine._get_slack_client", return_value=mock_client):
                    result = await send_slack_notification(message, channel)

                    # 验证发送成功
                    assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_slack_notification_failure(self, mock_logger):
        """测试 Slack 通知发送失败"""
        message = "Test alert"
        channel = "#alerts"

        with patch("core.notify_engine.logger", mock_logger):
            # Mock Slack 客户端失败
            with patch(
                "core.notify_engine._get_slack_client",
                AsyncMock(side_effect=Exception("Slack API error")),
            ):
                result = await send_slack_notification(message, channel)

                # 验证发送失败
                assert result["success"] is False
                # 验证日志记录
                mock_logger.error.assert_called()

    @pytest.mark.asyncio
    async def test_send_slack_notification_rate_limit(self, mock_logger):
        """测试 Slack 通知限流"""
        message = "Test alert"
        channel = "#alerts"

        with patch("core.notify_engine.logger", mock_logger):
            # Mock Slack 限流
            mock_client = MagicMock()
            mock_client.chat_postMessage = AsyncMock(side_effect=Exception("Rate limit exceeded"))

            with patch("core.notify_engine._get_slack_client", return_value=mock_client):
                result = await send_slack_notification(message, channel)

                # 验证限流处理
                assert result["success"] is False
                assert "rate limit" in result["error"].lower()


class TestTeamsNotification:
    """Teams 通知测试"""

    @pytest.mark.asyncio
    async def test_send_teams_notification_success(self, mock_logger):
        """测试 Teams 通知发送成功"""
        message = "Test alert: Memory usage high"
        webhook_url = "https://example.com/webhook"

        with patch("core.notify_engine.logger", mock_logger):
            # Mock HTTP 客户端
            with patch(
                "aiohttp.ClientSession.post", AsyncMock(return_value=MagicMock(status=200))
            ) as mock_post:
                result = await send_teams_notification(message, webhook_url)

                # 验证发送成功
                assert result["success"] is True
                mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_teams_notification_failure(self, mock_logger):
        """测试 Teams 通知发送失败"""
        message = "Test alert"
        webhook_url = "https://example.com/webhook"

        with patch("core.notify_engine.logger", mock_logger):
            # Mock HTTP 客户端失败
            with patch(
                "aiohttp.ClientSession.post", AsyncMock(side_effect=Exception("HTTP error"))
            ):
                result = await send_teams_notification(message, webhook_url)

                # 验证发送失败
                assert result["success"] is False

    @pytest.mark.asyncio
    async def test_send_teams_notification_invalid_webhook(self, mock_logger):
        """测试无效 Webhook URL"""
        message = "Test alert"
        webhook_url = "invalid-url"

        with patch("core.notify_engine.logger", mock_logger):
            result = await send_teams_notification(message, webhook_url)

            # 验证无效 URL 处理
            assert result["success"] is False
            assert "invalid" in result["error"].lower()


class TestEmailNotification:
    """邮件通知测试"""

    @pytest.mark.asyncio
    async def test_send_email_notification_success(self, mock_logger):
        """测试邮件通知发送成功"""
        to = "admin@example.com"
        subject = "Alert: CPU usage high"
        body = "CPU usage exceeds 80%"

        with patch("core.notify_engine.logger", mock_logger):
            # Mock SMTP 客户端
            with patch("smtplib.SMTP") as mock_smtp:
                mock_smtp_instance = MagicMock()
                mock_smtp.return_value.__enter__.return_value = mock_smtp_instance
                mock_smtp_instance.sendmail = MagicMock()

                result = await send_email_notification(to, subject, body)

                # 验证发送成功
                assert result["success"] is True

    @pytest.mark.asyncio
    async def test_send_email_notification_failure(self, mock_logger):
        """测试邮件通知发送失败"""
        to = "admin@example.com"
        subject = "Alert"
        body = "Test"

        with patch("core.notify_engine.logger", mock_logger):
            # Mock SMTP 失败
            with patch("smtplib.SMTP", side_effect=Exception("SMTP error")):
                result = await send_email_notification(to, subject, body)

                # 验证发送失败
                assert result["success"] is False

    @pytest.mark.asyncio
    async def test_send_email_notification_invalid_email(self, mock_logger):
        """测试无效邮箱地址"""
        to = "invalid-email"
        subject = "Alert"
        body = "Test"

        with patch("core.notify_engine.logger", mock_logger):
            result = await send_email_notification(to, subject, body)

            # 验证无效邮箱处理
            assert result["success"] is False
            assert "invalid" in result["error"].lower()


class TestNotificationRouting:
    """通知路由测试"""

    @pytest.mark.asyncio
    async def test_send_notification_slack(self, mock_logger):
        """测试路由到 Slack"""
        alert = {
            "type": "cpu_high",
            "message": "CPU usage high",
            "severity": "warning",
        }

        with patch("core.notify_engine.logger", mock_logger):
            # Mock Slack 通知
            with patch(
                "core.notify_engine.send_slack_notification",
                AsyncMock(return_value={"success": True}),
            ) as mock_slack:
                result = await send_notification(alert, channels=["slack"])

                # 验证路由到 Slack
                assert result["success"] is True
                mock_slack.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_notification_multiple_channels(self, mock_logger):
        """测试多通道通知"""
        alert = {
            "type": "cpu_high",
            "message": "CPU usage high",
            "severity": "critical",
        }

        with patch("core.notify_engine.logger", mock_logger):
            # Mock 各通道通知
            with patch(
                "core.notify_engine.send_slack_notification",
                AsyncMock(return_value={"success": True}),
            ):
                with patch(
                    "core.notify_engine.send_teams_notification",
                    AsyncMock(return_value={"success": True}),
                ):
                    with patch(
                        "core.notify_engine.send_email_notification",
                        AsyncMock(return_value={"success": True}),
                    ):
                        result = await send_notification(
                            alert, channels=["slack", "teams", "email"]
                        )

                        # 验证多通道发送
                        assert result["success"] is True
                        assert result["channels_sent"] == 3

    @pytest.mark.asyncio
    async def test_send_notification_with_severity_routing(self, mock_logger):
        """测试基于严重级别的路由"""
        alert = {
            "type": "cpu_high",
            "message": "CPU usage high",
            "severity": "critical",
        }

        with patch("core.notify_engine.logger", mock_logger):
            # Mock 通知
            with patch(
                "core.notify_engine.send_slack_notification",
                AsyncMock(return_value={"success": True}),
            ):
                with patch(
                    "core.notify_engine.send_email_notification",
                    AsyncMock(return_value={"success": True}),
                ):
                    result = await send_notification(alert)

                    # 验证严重级别路由（critical 应该发送到所有通道）
                    assert result["success"] is True


class TestNotificationHistory:
    """通知历史测试"""

    @pytest.mark.asyncio
    async def test_get_notification_history(self, mock_logger):
        """测试获取通知历史"""
        with patch("core.notify_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.notify_engine.query_notifications",
                AsyncMock(
                    return_value=[
                        {
                            "id": "notif-001",
                            "channel": "slack",
                            "message": "Test alert",
                            "status": "sent",
                            "timestamp": "2026-06-09T10:00:00Z",
                        }
                    ]
                ),
            ):
                history = await get_notification_history(limit=10)

                # 验证历史记录
                assert len(history) > 0
                assert history[0]["channel"] == "slack"

    @pytest.mark.asyncio
    async def test_get_notification_history_with_filter(self, mock_logger):
        """测试带过滤的通知历史"""
        with patch("core.notify_engine.logger", mock_logger):
            # Mock 数据库查询
            with patch(
                "core.notify_engine.query_notifications",
                AsyncMock(
                    return_value=[
                        {
                            "id": "notif-001",
                            "channel": "slack",
                            "message": "Test alert",
                            "status": "sent",
                            "severity": "critical",
                        }
                    ]
                ),
            ):
                history = await get_notification_history(limit=10, severity="critical")

                # 验证过滤结果
                assert len(history) > 0
                assert history[0]["severity"] == "critical"


class TestNotificationFormatting:
    """通知格式化测试"""

    @pytest.mark.asyncio
    async def test_format_alert_message(self, mock_logger):
        """测试告警消息格式化"""
        alert = {
            "type": "cpu_high",
            "message": "CPU usage high",
            "host": "server-01",
            "severity": "warning",
            "metrics": {"cpu_percent": 85.5},
        }

        with patch("core.notify_engine.logger", mock_logger):
            from core.notify_engine import format_alert_message

            formatted = format_alert_message(alert)

            # 验证格式化
            assert "CPU" in formatted
            assert "server-01" in formatted
            assert "85.5" in formatted

    @pytest.mark.asyncio
    async def test_format_alert_for_slack(self, mock_logger):
        """测试 Slack 格式化"""
        alert = {
            "type": "cpu_high",
            "message": "CPU usage high",
            "severity": "warning",
        }

        with patch("core.notify_engine.logger", mock_logger):
            from core.notify_engine import format_for_slack

            formatted = format_for_slack(alert)

            # 验证 Slack 格式
            assert "⚠️" in formatted or "warning" in formatted.lower()

    @pytest.mark.asyncio
    async def test_format_alert_for_teams(self, mock_logger):
        """测试 Teams 格式化"""
        alert = {
            "type": "cpu_high",
            "message": "CPU usage high",
            "severity": "critical",
        }

        with patch("core.notify_engine.logger", mock_logger):
            from core.notify_engine import format_for_teams

            formatted = format_for_teams(alert)

            # 验证 Teams 格式（JSON）
            import json

            parsed = json.loads(formatted)
            assert "text" in parsed
            assert "CPU" in parsed["text"]


class TestNotificationRetry:
    """通知重试测试"""

    @pytest.mark.asyncio
    async def test_notification_retry_on_failure(self, mock_logger):
        """测试失败重试"""
        message = "Test alert"
        channel = "#alerts"

        with patch("core.notify_engine.logger", mock_logger):
            # Mock 前两次失败，第三次成功
            call_count = [0]

            async def mock_send(*args, **kwargs):
                call_count[0] += 1
                if call_count[0] < 3:
                    return {"success": False, "error": "Temporary error"}
                return {"success": True}

            with patch("core.notify_engine.send_slack_notification", side_effect=mock_send):
                result = await send_slack_notification(message, channel, max_retries=3)

                # 验证重试成功
                assert result["success"] is True
                assert call_count[0] == 3

    @pytest.mark.asyncio
    async def test_notification_retry_exhausted(self, mock_logger):
        """测试重试次数耗尽"""
        message = "Test alert"
        channel = "#alerts"

        with patch("core.notify_engine.logger", mock_logger):
            # Mock 持续失败
            with patch(
                "core.notify_engine.send_slack_notification",
                AsyncMock(return_value={"success": False}),
            ):
                result = await send_slack_notification(message, channel, max_retries=3)

                # 验证重试耗尽
                assert result["success"] is False


class TestNotificationErrorHandling:
    """通知错误处理测试"""

    @pytest.mark.asyncio
    async def test_send_notification_with_invalid_alert(self, mock_logger):
        """测试无效告警"""
        alert = {}

        with patch("core.notify_engine.logger", mock_logger):
            result = await send_notification(alert)

            # 验证无效告警处理
            assert result["success"] is False
            assert "invalid" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_send_notification_with_exception(self, mock_logger):
        """测试异常处理"""
        alert = {
            "type": "cpu_high",
            "message": "CPU usage high",
            "severity": "warning",
        }

        with patch("core.notify_engine.logger", mock_logger):
            # Mock 通知抛出异常
            with patch(
                "core.notify_engine.send_slack_notification",
                AsyncMock(side_effect=Exception("Unexpected error")),
            ):
                result = await send_notification(alert, channels=["slack"])

                # 验证异常被捕获
                assert result["success"] is False
                # 验证日志记录
                mock_logger.error.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
