# -*- coding: utf-8 -*-
"""Targeted tests for core.error_logging.alerting."""

from unittest.mock import MagicMock, patch

import pytest

from core.error_logging.alerting import (
    AlertChannel,
    EmailAlertChannel,
    ErrorAlertManager,
    SlackAlertChannel,
    check_error_alerts,
    get_error_alert_manager,
)


class TestEmailAlertChannel:
    def test_send_alert_success(self) -> None:
        channel = EmailAlertChannel(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="u",
            password="p",
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
        )
        with patch("smtplib.SMTP") as mock_smtp:
            channel.send_alert("test message", {"key": "value"})
            mock_smtp.assert_called_once_with("smtp.example.com", 587)
            server = mock_smtp.return_value.__enter__.return_value
            server.starttls.assert_called_once()
            server.login.assert_called_once_with("u", "p")
            server.send_message.assert_called_once()

    def test_send_alert_failure(self) -> None:
        channel = EmailAlertChannel(
            smtp_host="smtp.example.com",
            smtp_port=587,
            username="u",
            password="p",
            from_addr="from@example.com",
            to_addrs=["to@example.com"],
        )
        with patch("smtplib.SMTP", side_effect=RuntimeError("smtp down")):
            # Should not raise
            channel.send_alert("test message")


class TestSlackAlertChannel:
    def test_send_alert(self) -> None:
        channel = SlackAlertChannel("https://hooks.slack.com/test", "#alerts")
        with patch("requests.post") as mock_post:
            channel.send_alert("slack alert", {"metric": "cpu"})
            mock_post.assert_called_once()
            payload = mock_post.call_args[1].get("json") or mock_post.call_args[0][1]
            assert payload["text"] == "slack alert"

    def test_send_alert_failure(self) -> None:
        channel = SlackAlertChannel("https://hooks.slack.com/test", "#alerts")
        with patch("requests.post", side_effect=RuntimeError("network down")):
            channel.send_alert("slack alert")


class TestAlertChannel:
    def test_cannot_instantiate_abstract(self) -> None:
        with pytest.raises(TypeError):
            AlertChannel()


class TestErrorAlertManager:
    @pytest.fixture
    def manager(self):
        handler = MagicMock()
        handler.get_error_count = MagicMock(return_value=0)
        handler.get_error_rate = MagicMock(return_value=0.0)
        handler.get_top_errors = MagicMock(return_value=[])
        return ErrorAlertManager(handler)

    def test_add_channel_and_set_threshold(self, manager) -> None:
        channel = MagicMock()
        manager.add_alert_channel(channel)
        manager.set_threshold("total_errors", 5)
        assert "total_errors" in manager.thresholds
        assert channel in manager.alert_channels

    def test_check_alerts_triggers_total_errors(self, manager) -> None:
        channel = MagicMock()
        manager.add_alert_channel(channel)
        manager.error_handler.get_error_count.return_value = 150
        manager.error_handler.get_error_rate.return_value = 0.0
        manager.error_handler.get_top_errors.return_value = []
        manager.check_alerts()
        channel.send_alert.assert_called_once()

    def test_check_alerts_triggers_error_rate(self, manager) -> None:
        channel = MagicMock()
        manager.add_alert_channel(channel)
        manager.error_handler.get_error_count.return_value = 0
        manager.error_handler.get_error_rate.return_value = 15.0
        manager.error_handler.get_top_errors.return_value = []
        manager.check_alerts()
        assert channel.send_alert.call_count == 1

    def test_check_alerts_triggers_specific_error(self, manager) -> None:
        channel = MagicMock()
        manager.add_alert_channel(channel)
        manager.error_handler.get_error_count.return_value = 0
        manager.error_handler.get_error_rate.return_value = 0.0
        manager.error_handler.get_top_errors.return_value = [("E001", 60)]
        manager.check_alerts()
        channel.send_alert.assert_called_once()

    def test_check_alerts_no_threshold(self, manager) -> None:
        channel = MagicMock()
        manager.add_alert_channel(channel)
        manager.check_alerts()
        channel.send_alert.assert_not_called()


class TestGlobalManager:
    def test_get_error_alert_manager(self, monkeypatch) -> None:
        from core import error_logging

        handler = MagicMock()
        monkeypatch.setattr(error_logging, "get_error_log_handler", lambda: handler)
        monkeypatch.setattr("core.error_logging.alerting._error_alert_manager", None, raising=False)
        manager = get_error_alert_manager()
        assert manager is not None
        assert manager.error_handler is handler

    def test_check_error_alerts(self, monkeypatch) -> None:
        manager = MagicMock()
        monkeypatch.setattr("core.error_logging.alerting.get_error_alert_manager", lambda: manager)
        check_error_alerts()
        manager.check_alerts.assert_called_once()
