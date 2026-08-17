# -*- coding: utf-8 -*-
"""Unit tests for previously uncovered alert and notification core modules.

Covers the public APIs in ``core.alert_engine`` and ``core.notify_engine``.
The alert and notify modules do not expose the historical ``AlertEngine`` /
``NotifyEngine`` classes referenced in the task prompt, so these tests exercise
their functional equivalents: ``AutomaticAlertRouter``/``alert_engine``,
``AlertTopologyCorrelation``, ``AlertTrendPredictor``, the module-level notify
functions, and the notification formatters.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

import core.alert_engine as alert_engine
import core.notify_engine as notify_engine

pytestmark = [pytest.mark.core]


class _FakeRepo:
    """In-memory stand-in for the alert repository."""

    async def save(self, alert):
        pass

    async def get_recent(self, limit):
        return []


@pytest.fixture(autouse=True)
def _reset_alert_state(monkeypatch):
    """Keep alert-engine global caches isolated between tests."""
    alert_engine.clear_dedup_cache()
    alert_engine.clear_ssh_brute_force_cache()
    alert_engine._ws_subscribers.clear()
    monkeypatch.setattr(alert_engine, "alert_repository", _FakeRepo())
    yield
    alert_engine.clear_dedup_cache()
    alert_engine.clear_ssh_brute_force_cache()
    alert_engine._ws_subscribers.clear()


@pytest.fixture(autouse=True)
def _reset_notify_state(monkeypatch):
    """Keep notify-engine global cooldown/history state isolated."""
    notify_engine._notification_cooldowns.clear()
    notify_engine._notification_history.clear()
    monkeypatch.setattr(notify_engine, "_http_client", None)
    yield
    notify_engine._notification_cooldowns.clear()
    notify_engine._notification_history.clear()


def _stub_post_webhook(monkeypatch):
    """Stub the generic webhook sender so no real HTTP is made."""
    monkeypatch.setattr(
        notify_engine,
        "_post_webhook",
        AsyncMock(return_value={"success": True, "channel": "wecom"}),
    )


def _stub_notify_channel_funcs(monkeypatch):
    """Stub the individual channel senders used by ``send_notification``."""
    monkeypatch.setattr(
        notify_engine, "send_slack_notification", AsyncMock(return_value={"success": True})
    )
    monkeypatch.setattr(
        notify_engine, "send_teams_notification", AsyncMock(return_value={"success": True})
    )
    monkeypatch.setattr(
        notify_engine, "send_email_notification", AsyncMock(return_value={"success": True})
    )


def test_check_and_generate_alerts():
    """``check_and_generate_alerts`` produces CPU, memory and disk candidates."""
    metrics = {
        "cpu": {"usage_percent": 99},
        "memory": {"usage_percent": 92},
        "disk": [{"device": "C:", "usage_percent": 95, "used_gb": 80, "total_gb": 100}],
    }
    alerts = alert_engine.check_and_generate_alerts(metrics)
    assert len(alerts) == 3
    assert all(isinstance(a, dict) for a in alerts)
    assert any(a["metric"] == "cpu_percent" and a["level"] == "critical" for a in alerts)
    assert any(a["metric"] == "memory_percent" for a in alerts)
    assert any(a["metric"] == "disk_percent" for a in alerts)


def test_dedup_and_stats():
    """``_try_dedup`` suppresses repeated alerts and ``get_dedup_stats`` reports it."""
    alert = {
        "id": "CPU-10:00:00",
        "level": "critical",
        "metric": "cpu_percent",
    }
    assert alert_engine._try_dedup(alert) is False
    stats = alert_engine.get_dedup_stats()
    assert isinstance(stats, dict)
    assert stats["active_windows"] >= 1
    assert stats["cache_size"] >= 1

    assert alert_engine._try_dedup(alert) is True
    assert alert_engine.get_dedup_stats()["total_suppressed"] >= 1

    cleared = alert_engine.clear_dedup_cache()
    assert cleared >= 1
    assert alert_engine.get_dedup_stats()["cache_size"] == 0


def test_ssh_brute_force_and_clear():
    """``_check_ssh_brute_force`` triggers after enough failures and cache can be cleared."""
    host = "test-host-01"
    assert alert_engine._check_ssh_brute_force(host, 5) is None
    alert = alert_engine._check_ssh_brute_force(host, 25)
    assert isinstance(alert, dict)
    assert alert["level"] == "critical"
    assert alert["host"] == host
    assert alert["alert_type"] == "ssh_brute_force"
    assert alert["id"].startswith(f"SEC-SSH-{host}-")

    assert alert_engine.clear_ssh_brute_force_cache() >= 1


async def test_check_linux_security_alerts(monkeypatch):
    """``check_linux_security_alerts`` persists SSH alerts and forwards to notify."""
    notify_send = AsyncMock(return_value={"status": "ok"})
    monkeypatch.setattr(notify_engine, "send_alert_notification", notify_send)

    linux_results = [
        {
            "status": "ok",
            "name": "srv01",
            "metrics": {"ssh_failed_logins": {"value": "25"}},
        }
    ]
    alerts = await alert_engine.check_linux_security_alerts(linux_results)
    assert len(alerts) == 1
    assert alerts[0]["alert_type"] == "ssh_brute_force"
    notify_send.assert_awaited_once()


async def test_broadcast():
    """``broadcast`` sends JSON to registered WebSocket subscribers."""
    sent = []

    class FakeWS:
        async def send_text(self, msg):
            sent.append(msg)

    ws = FakeWS()
    alert_engine.register_ws(ws)
    await alert_engine.broadcast({"type": "test", "data": {"x": 1}})
    assert len(sent) == 1
    payload = json.loads(sent[0])
    assert payload["type"] == "test"

    alert_engine.unregister_ws(ws)
    # A broadcast with no subscribers should be a no-op, not raise.
    await alert_engine.broadcast({"type": "empty"})


def test_alert_topology_correlation():
    """``AlertTopologyCorrelation`` builds topology and correlates/impacts alerts."""
    tc = alert_engine.AlertTopologyCorrelation()
    topology = tc.build_topology_from_alerts(
        [
            {"source": "host1", "type": "cpu_high"},
            {"source": "host2", "type": "disk_high"},
        ]
    )
    assert "host1" in topology
    assert "host2" in topology

    # Manually set dependencies so correlate/impact have a complete graph to reason about.
    tc.topology_graph = {"host1": ["processes"], "processes": []}
    roots = tc.correlate_alerts_with_topology({"source": "host1"})
    assert "processes" in roots

    impact = tc.get_impact_analysis({"source": "processes"})
    assert isinstance(impact, dict)
    assert impact["source"] == "processes"


def test_automatic_alert_router():
    """``AutomaticAlertRouter`` routes alerts by rule and reports statistics."""
    router = alert_engine.AutomaticAlertRouter()
    router.add_route("critical_email", {"severity": "critical"}, "email", priority=10)
    router.add_route("warning_webhook", {"severity": "warning"}, "webhook", priority=5)

    critical_channels = router.route_alert({"severity": "critical", "id": "a1"})
    assert "email" in critical_channels

    warning_channels = router.route_alert({"severity": "warning", "id": "a2"})
    assert "webhook" in warning_channels

    stats = router.get_routing_stats()
    assert isinstance(stats, dict)
    assert stats["total_routes"] >= 2
    assert "channel_distribution" in stats


def test_alert_trend_predictor():
    """``AlertTrendPredictor`` stores history and produces predictions/summaries."""
    predictor = alert_engine.AlertTrendPredictor()
    for i in range(12):
        predictor.add_historical_data("cpu", 10.0 + i)

    prediction = predictor.predict_trend("cpu", prediction_horizon_hours=6)
    assert prediction is not None
    assert prediction.trend_direction in ("increasing", "decreasing", "stable")
    assert len(prediction.predicted_values) == 6

    summary = predictor.get_prediction_summary()
    assert "cpu" in summary["predictions"]
    assert summary["predictions"]["cpu"]["trend_direction"] == prediction.trend_direction


async def test_get_summary_metrics(monkeypatch):
    """``get_summary_metrics`` delegates to ``stats_engine.get_real_summary``."""
    fake_summary = {"active_alerts": 7, "critical_count": 1}
    monkeypatch.setattr(
        "core.stats_engine.get_real_summary",
        AsyncMock(return_value=fake_summary),
    )
    result = await alert_engine.get_summary_metrics()
    assert result == fake_summary


def test_format_alert_message():
    """``format_alert_message`` renders a plain-text alert summary."""
    alert = {
        "severity": "critical",
        "type": "cpu_high",
        "message": "CPU usage high",
        "host": "srv01",
        "metrics": {"cpu_percent": 95.5},
    }
    msg = notify_engine.format_alert_message(alert)
    assert "CPU usage high" in msg
    assert "Host: srv01" in msg
    assert "cpu_percent=95.5" in msg


def test_build_structured_alert_message_formats():
    """``build_structured_alert_message`` supports markdown, text and HTML."""
    alert = {
        "level": "critical",
        "title": "Disk full",
        "desc": "Disk is nearly full",
        "raw_time": "10:00:00",
        "impact": "service degraded",
        "diagnosis": "logs growing",
        "action": "rotate logs",
        "confidence": 0.95,
        "dashboard_url": "http://dash.example.com",
    }
    for fmt in ("markdown", "text", "html"):
        rendered = notify_engine.build_structured_alert_message(alert, fmt=fmt)
        assert isinstance(rendered, str)
        assert "Disk full" in rendered
        assert "rotate logs" in rendered


def test_format_for_slack_and_teams():
    """``format_for_slack``/``format_for_teams`` wrap the structured formatter."""
    alert = {"level": "high", "title": "Latency", "desc": "p95 high", "raw_time": "09:00"}
    slack = notify_engine.format_for_slack(alert)
    assert isinstance(slack, str)
    assert "Latency" in slack

    teams = notify_engine.format_for_teams(alert)
    payload = json.loads(teams)
    assert "text" in payload
    assert "Latency" in payload["text"]


def test_validate_webhook_url():
    """``_validate_webhook_url`` accepts HTTP(S) URLs and rejects invalid ones."""
    assert notify_engine._validate_webhook_url("https://example.com/hook", "wecom") is True
    assert notify_engine._validate_webhook_url("http://localhost:8080/", "feishu") is True
    assert notify_engine._validate_webhook_url("ftp://example.com", "test") is False
    assert notify_engine._validate_webhook_url("not-a-url", "test") is False
    assert notify_engine._validate_webhook_url("https://" + "x" * 3000, "test") is False


async def test_send_email_notification(monkeypatch):
    """``send_email_notification`` sends via smtplib and validates addresses."""

    class FakeSMTP:
        def __init__(self, host, port):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def sendmail(self, sender, to, msg):
            pass

    monkeypatch.setattr(notify_engine.smtplib, "SMTP", FakeSMTP)
    good = await notify_engine.send_email_notification("ops@example.com", "Subject", "body")
    assert good["success"] is True

    bad = await notify_engine.send_email_notification("invalid", "Subject", "body")
    assert bad["success"] is False
    assert "invalid" in bad["error"].lower()


async def test_send_teams_notification(monkeypatch):
    """``send_teams_notification`` posts via aiohttp when available."""
    fake_aiohttp = MagicMock()
    session = fake_aiohttp.ClientSession.return_value
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    response = MagicMock()
    response.status = 200
    session.post = AsyncMock(return_value=response)
    monkeypatch.setattr(notify_engine, "aiohttp", fake_aiohttp)

    result = await notify_engine.send_teams_notification(
        "test message", "https://example.com/teams"
    )
    assert result["success"] is True


async def test_send_notification(monkeypatch):
    """``send_notification`` routes to requested channels and validates alerts."""
    _stub_notify_channel_funcs(monkeypatch)

    alert = {"type": "test", "message": "boom", "severity": "critical"}
    result = await notify_engine.send_notification(alert, channels=["slack", "teams"])
    assert result["success"] is True
    assert result["channels_sent"] == 2

    bad_alert = {"message": "no type"}
    result = await notify_engine.send_notification(bad_alert)
    assert result["success"] is False
    assert "invalid" in result["error"].lower()


def test_channels_can_be_added_via_config():
    """New channels appear when the config contains the matching webhook/provider."""
    config = {
        "wecom_webhook": "https://example.com/wecom",
        "email_to": "ops@example.com",
    }
    channels = notify_engine._channels_for_severity("critical", config)
    assert "wecom" in channels
    assert "email" in channels


async def test_send_alert_notification_ok(monkeypatch):
    """``send_alert_notification`` succeeds over a configured webhook channel."""
    _stub_post_webhook(monkeypatch)
    monkeypatch.setattr(
        notify_engine, "send_email_notification", AsyncMock(return_value={"success": True})
    )

    cfg = {
        "enabled": True,
        "min_level": "info",
        "cooldown_seconds": "300",
        "wecom_webhook": "https://example.com/wecom",
        "dingtalk_webhook": "https://example.com/ding",
        "dingtalk_secret": "",
        "feishu_webhook": "https://example.com/feishu",
        "email_to": "",
    }
    monkeypatch.setattr(notify_engine, "NOTIFY_CONFIG", cfg)
    notify_engine._notification_cooldowns.clear()

    alert = {"id": "A1", "level": "warning", "title": "t", "desc": "d"}
    result = await notify_engine.send_alert_notification(alert)
    assert result["status"] == "ok"
    assert "wecom" in result["channels_sent"]


async def test_send_alert_notification_states(monkeypatch):
    """``send_alert_notification`` respects disabled/min-level/no-channel config."""
    _stub_post_webhook(monkeypatch)
    monkeypatch.setattr(
        notify_engine, "send_email_notification", AsyncMock(return_value={"success": True})
    )

    # disabled
    monkeypatch.setattr(
        notify_engine,
        "NOTIFY_CONFIG",
        {
            "enabled": False,
            "min_level": "info",
            "wecom_webhook": "https://example.com/wecom",
            "dingtalk_webhook": "",
            "feishu_webhook": "",
            "email_to": "",
        },
    )
    disabled = await notify_engine.send_alert_notification({"level": "critical"})
    assert disabled["status"] == "disabled"

    # below min level
    monkeypatch.setattr(
        notify_engine,
        "NOTIFY_CONFIG",
        {
            "enabled": True,
            "min_level": "critical",
            "wecom_webhook": "https://example.com/wecom",
            "dingtalk_webhook": "",
            "feishu_webhook": "",
            "email_to": "",
        },
    )
    filtered = await notify_engine.send_alert_notification({"id": "A2", "level": "warning"})
    assert filtered["status"] == "filtered"

    # no channel configured
    monkeypatch.setattr(
        notify_engine,
        "NOTIFY_CONFIG",
        {
            "enabled": True,
            "min_level": "info",
            "wecom_webhook": "",
            "dingtalk_webhook": "",
            "feishu_webhook": "",
            "email_to": "",
        },
    )
    no_channel = await notify_engine.send_alert_notification({"id": "A3", "level": "warning"})
    assert no_channel["status"] == "no_channel_configured"


async def test_notification_history_and_read_status(monkeypatch):
    """History/status/read APIs track sent notifications correctly."""
    _stub_post_webhook(monkeypatch)
    cfg = {
        "enabled": True,
        "min_level": "info",
        "cooldown_seconds": "300",
        "wecom_webhook": "https://example.com/wecom",
        "dingtalk_webhook": "",
        "feishu_webhook": "",
        "email_to": "",
    }
    monkeypatch.setattr(notify_engine, "NOTIFY_CONFIG", cfg)
    notify_engine._notification_cooldowns.clear()
    notify_engine._notification_history.clear()

    alert = {"id": "H1", "level": "warning", "title": "t", "desc": "d"}
    result = await notify_engine.send_alert_notification(alert)
    assert result["status"] == "ok"

    history = await notify_engine.get_notification_history(limit=10)
    assert len(history) >= 1

    status = notify_engine.get_notification_status(alert_id="H1")
    assert len(status) >= 1
    assert status[0]["id"] == "H1"

    marked = notify_engine.mark_notification_read("H1", "wecom")
    assert marked is True

    read_status = notify_engine.get_notification_read_status("H1", "wecom")
    assert read_status["status"] == "read"


async def test_close_http_client():
    """``close_http_client`` closes the cached httpx client when present."""
    fake_client = MagicMock()
    fake_client.is_closed = False
    fake_client.aclose = AsyncMock()
    notify_engine._http_client = fake_client
    await notify_engine.close_http_client()
    fake_client.aclose.assert_awaited_once()
    assert notify_engine._http_client is None


def test_get_slack_client():
    """``_get_slack_client`` returns None when no bot token is configured."""
    assert notify_engine._get_slack_client() is None


def test_reload_notify_config():
    """``reload_notify_config`` reloads and returns a configuration dict."""
    original = dict(notify_engine.NOTIFY_CONFIG)
    try:
        new_cfg = notify_engine.reload_notify_config()
        assert isinstance(new_cfg, dict)
        assert "enabled" in new_cfg
    finally:
        notify_engine.NOTIFY_CONFIG = original
