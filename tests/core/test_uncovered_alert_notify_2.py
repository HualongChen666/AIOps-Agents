# -*- coding: utf-8 -*-
"""Additional unit tests for remaining uncovered alert/notify/intelligent analyzer branches."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import httpx
import pandas as pd
import pytest

import core.alert_engine as alert_engine
import core.intelligent_alert_analyzer as analyzer
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
    alert_engine.alert_history.clear()
    monkeypatch.setattr(alert_engine, "alert_repository", _FakeRepo())
    yield
    alert_engine.clear_dedup_cache()
    alert_engine.clear_ssh_brute_force_cache()
    alert_engine._ws_subscribers.clear()
    alert_engine.alert_history.clear()


@pytest.fixture(autouse=True)
def _reset_notify_state(monkeypatch):
    """Keep notify-engine global cooldown/history state isolated."""
    notify_engine._notification_cooldowns.clear()
    notify_engine._notification_history.clear()
    monkeypatch.setattr(notify_engine, "_http_client", None)
    yield
    notify_engine._notification_cooldowns.clear()
    notify_engine._notification_history.clear()


# ============================================================
# alert_engine remaining branches
# ============================================================


def test_check_and_generate_alerts_invalid_inputs():
    """``check_and_generate_alerts`` defensively handles bad inputs."""
    assert alert_engine.check_and_generate_alerts(None) == []
    assert alert_engine.check_and_generate_alerts("not-a-dict") == []
    assert alert_engine.check_and_generate_alerts({}) == []
    # non-dict sub-fields are treated as empty
    metrics = {
        "cpu": "bad",
        "memory": 123,
        "disk": "not-list",
    }
    assert alert_engine.check_and_generate_alerts(metrics) == []


def test_check_and_generate_alerts_disk_warning_and_safe_float():
    """Disk warnings are produced and ``_safe_float`` tolerates strings/None."""
    metrics = {
        "cpu": {"usage_percent": "50"},
        "memory": {"usage_percent": None},
        "disk": [
            {"device": "C:", "usage_percent": "95", "used_gb": "80", "total_gb": "100"},
            "not-a-dict",
        ],
    }
    alerts = alert_engine.check_and_generate_alerts(metrics)
    assert any(a["metric"] == "disk_percent" and a["level"] == "warning" for a in alerts)
    assert not any(a["metric"] == "cpu_percent" for a in alerts)
    assert not any(a["metric"] == "memory_percent" for a in alerts)


def test_dynamic_warn_threshold_branches(monkeypatch):
    """``_get_dynamic_warn_threshold`` returns static or dynamic values and handles errors."""
    monkeypatch.setattr(alert_engine, "DYNAMIC_THRESHOLD_CONFIG", {"enabled": True})

    # Normal dynamic branch with a threshold far from static -> returns dynamic
    fake_history = MagicMock()
    fake_history.get_dynamic_threshold = MagicMock(return_value=(60.0, {"source": "ml"}))
    monkeypatch.setattr(alert_engine, "metrics_history", fake_history)
    assert alert_engine._get_dynamic_warn_threshold("cpu", 80.0) == 60.0

    # Exception branch falls back to static value
    fake_history.get_dynamic_threshold = MagicMock(side_effect=RuntimeError("boom"))
    assert alert_engine._get_dynamic_warn_threshold("cpu", 80.0) == 80.0


async def test_check_linux_security_alerts_edge_cases():
    """``check_linux_security_alerts`` safely ignores malformed / non-ok results."""
    # Not a list
    assert await alert_engine.check_linux_security_alerts(None) == []
    # Non-ok status and bad ssh metric values
    results = [
        {"status": "error", "name": "bad-status"},
        {"status": "ok", "name": "bad-metrics", "metrics": "nope"},
        {"status": "ok", "name": "timeout", "metrics": {"ssh_failed_logins": {"value": "TIMEOUT"}}},
        {
            "status": "ok",
            "name": "error",
            "metrics": {"ssh_failed_logins": {"value": "ERROR: foo"}},
        },
        {"status": "ok", "name": "invalid", "metrics": {"ssh_failed_logins": {"value": "abc"}}},
    ]
    alerts = await alert_engine.check_linux_security_alerts(results)
    assert alerts == []


def test_ssh_brute_force_negative_increment_and_cooldown():
    """``_check_ssh_brute_force`` resets on negative increments and respects cooldown."""
    alert_engine.clear_ssh_brute_force_cache()
    host = "test-host-ssh"

    # First sample insufficient for a window
    assert alert_engine._check_ssh_brute_force(host, 0) is None

    # Build a window then rotate logs -> negative increment resets window
    alert_engine._ssh_failed_window[host] = [
        (datetime.now() - timedelta(seconds=10), 100),
        (datetime.now(), 5),
    ]
    assert alert_engine._check_ssh_brute_force(host, 5) is None

    # Trigger once
    alert_engine._ssh_failed_window[host] = [
        (datetime.now() - timedelta(seconds=10), 0),
        (datetime.now(), 30),
    ]
    alert = alert_engine._check_ssh_brute_force(host, 30)
    assert alert is not None
    assert alert["alert_type"] == "ssh_brute_force"

    # Same host in cooldown should not re-alert
    assert alert_engine._check_ssh_brute_force(host, 50) is None


def test_alert_topology_correlation_impact():
    """``AlertTopologyCorrelation.get_impact_analysis`` reports affected services."""
    tc = alert_engine.AlertTopologyCorrelation()
    topology = tc.build_topology_from_alerts(
        [
            {"source": "db", "type": "disk_high"},
            {"source": "api", "type": "cpu_high"},
        ]
    )
    assert "db" in topology and "api" in topology
    tc.topology_graph = {"db": ["api"], "api": ["db"]}
    impact = tc.get_impact_analysis({"source": "db"})
    assert "api" in impact["affected_services"]
    assert impact["source"] == "db"

    roots = tc.correlate_alerts_with_topology({"source": "db"})
    assert "api" in roots


def test_automatic_alert_router_ml_strategy():
    """``AutomaticAlertRouter`` ML strategy adds ML-predicted channels."""
    router = alert_engine.AutomaticAlertRouter()
    router.strategy = alert_engine.AlertRoutingStrategy.ML_BASED

    # Score >= 4 -> email + sms + webhook
    ml = router._ml_route_alert({"severity": "critical", "title": "outage down fail"})
    assert set(ml) == {"email", "sms", "webhook"}

    # Score >= 2 -> email + webhook
    ml = router._ml_route_alert({"severity": "warning", "title": "latency timeout"})
    assert set(ml) == {"email", "webhook"}

    # Score < 2 -> webhook only
    ml = router._ml_route_alert({"severity": "info", "title": "ok"})
    assert ml == ["webhook"]

    # Hybrid mode combines rule and ML channels
    router.add_route("crit", {"severity": "critical"}, "pager", priority=10)
    hybrid = router.route_alert({"severity": "critical", "id": "x"})
    assert "pager" in hybrid
    assert "email" in hybrid


def test_alert_trend_predictor_linear_regression():
    """``AlertTrendPredictor`` works with LINEAR_REGRESSION model."""
    predictor = alert_engine.AlertTrendPredictor(
        model=alert_engine.TrendPredictionModel.LINEAR_REGRESSION
    )
    for i in range(12):
        predictor.add_historical_data("cpu", 10.0 + i * 2)
    prediction = predictor.predict_trend("cpu", prediction_horizon_hours=6)
    assert prediction is not None
    assert prediction.trend_direction in ("increasing", "decreasing", "stable")
    assert len(prediction.predicted_values) == 6
    assert prediction.metric_name == "metric"


# ============================================================
# notify_engine remaining branches
# ============================================================


def test_email_validation_and_cooldown():
    """``_is_valid_email`` rejects malformed addresses and cooldown works."""
    assert notify_engine._is_valid_email("ops@example.com") is True
    assert notify_engine._is_valid_email("not-an-email") is False
    assert notify_engine._is_valid_email(123) is False  # type: ignore[arg-type]

    alert = {"id": "C1", "level": "warning"}
    notify_engine._mark_sent(alert, "wecom")
    assert notify_engine._is_in_cooldown(alert, "wecom", window_seconds=300) is True
    assert notify_engine._is_in_cooldown(alert, "wecom", window_seconds=0) is False


async def test_notification_query_and_read_not_found():
    """History, status, and read APIs handle missing records gracefully."""
    notify_engine._track_notification_status({"id": "N1", "level": "warning"}, "wecom", "delivered")
    history = await notify_engine.query_notifications(limit=10, severity="warning")
    assert any(r["id"] == "N1" for r in history)

    not_found = notify_engine.get_notification_read_status("missing", "wecom")
    assert not_found["status"] == "not_found"
    assert notify_engine.mark_notification_read("missing", "wecom") is False

    # get_notification_history exception fallback
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            notify_engine, "query_notifications", AsyncMock(side_effect=RuntimeError("boom"))
        )
        result = await notify_engine.get_notification_history(limit=5)
        assert result == []


def test_formatters_edge_cases():
    """Alert formatters tolerate non-dict metrics, non-dict links and auto-collect URLs."""
    msg = notify_engine.format_alert_message(
        {"severity": "high", "type": "x", "message": "m", "metrics": "plain string"}
    )
    assert "plain string" in msg

    structured = notify_engine.build_structured_alert_message(
        {
            "level": "critical",
            "title": "T",
            "raw_time": "09:00",
            "links": "should-be-ignored",
            "runbook_url": "http://runbook.example.com",
        },
        fmt="markdown",
    )
    assert "runbook_url" in structured or "runbook" in structured
    assert "http://runbook.example.com" in structured


async def test_slack_notification_with_client(monkeypatch):
    """``_send_slack_notification_once`` sends and interprets Slack responses."""
    fake_client = MagicMock()
    fake_client.chat_postMessage = AsyncMock(return_value={"ok": True, "channel": "#alerts"})
    monkeypatch.setattr(notify_engine, "_get_slack_client", lambda: fake_client)

    result = await notify_engine._send_slack_notification_once("hello", "#alerts")
    assert result["success"] is True

    # Response object with ok attribute
    fake_client.chat_postMessage = AsyncMock(return_value=MagicMock(ok=True))
    result = await notify_engine._send_slack_notification_once("hello", "#alerts")
    assert result["success"] is True

    # Rate-limit error message
    fake_client.chat_postMessage = AsyncMock(
        side_effect=Exception("rate limit exceeded"),
    )
    result = await notify_engine._send_slack_notification_once("hello", "#alerts")
    assert result["success"] is False
    assert "rate limit" in result["error"]


async def test_send_slack_notification_retry(monkeypatch):
    """``send_slack_notification`` retries until success or exhaustion."""
    once = AsyncMock(side_effect=[{"success": False}, {"success": True}])
    monkeypatch.setattr(notify_engine, "_send_slack_notification_once", once)

    result = await notify_engine.send_slack_notification("m", "#c", max_retries=2)
    assert result["success"] is True
    assert once.await_count == 2

    once.side_effect = [{"success": False}, {"success": False}]
    result = await notify_engine.send_slack_notification("m", "#c", max_retries=2)
    assert result["success"] is False


async def test_post_webhook_error_paths(monkeypatch):
    """``_post_webhook`` catches httpx HTTP, timeout, and connection errors."""
    # Use the original (non-retry-wrapped) implementation if available.
    original = getattr(notify_engine, "_post_webhook_original", notify_engine._post_webhook)
    monkeypatch.setattr(notify_engine, "_post_webhook", original)

    req = httpx.Request("POST", "https://example.com/hook")

    def make_client(exc):
        client = MagicMock()
        client.post = AsyncMock(side_effect=exc)
        return client

    monkeypatch.setattr(
        notify_engine,
        "_get_http_client",
        lambda: make_client(
            httpx.HTTPStatusError("boom", request=req, response=httpx.Response(500, request=req))
        ),
    )
    r = await notify_engine._post_webhook("https://example.com/hook", {"x": 1}, "wecom")
    assert r["success"] is False
    assert "500" in r["error"]

    monkeypatch.setattr(
        notify_engine,
        "_get_http_client",
        lambda: make_client(httpx.TimeoutException("timeout", request=req)),
    )
    r = await notify_engine._post_webhook("https://example.com/hook", {"x": 1}, "wecom")
    assert r["success"] is False
    assert "超时" in r["error"] or "timeout" in r["error"].lower()

    monkeypatch.setattr(
        notify_engine,
        "_get_http_client",
        lambda: make_client(httpx.ConnectError("conn", request=req)),
    )
    r = await notify_engine._post_webhook("https://example.com/hook", {"x": 1}, "wecom")
    assert r["success"] is False


async def test_send_wecom_dingtalk_feishu(monkeypatch):
    """``_send_wecom``, ``_send_dingtalk`` (with signature), and ``_send_feishu`` build payloads."""
    posted = AsyncMock(return_value={"success": True})
    monkeypatch.setattr(notify_engine, "_post_webhook", posted)
    monkeypatch.setattr(
        notify_engine,
        "NOTIFY_CONFIG",
        {
            "wecom_webhook": "https://wecom.example.com",
            "dingtalk_webhook": "https://ding.example.com?timestamp=old&sign=old",
            "dingtalk_secret": "sec123",
            "feishu_webhook": "https://feishu.example.com",
        },
    )

    alert = {"level": "critical", "title": "T", "summary": "S", "desc": "D", "raw_time": "09:00"}

    r = await notify_engine._send_wecom(alert)
    assert r["success"] is True
    url, payload, ch = posted.call_args[0]
    assert url == "https://wecom.example.com"
    assert payload["msgtype"] == "markdown"

    r = await notify_engine._send_dingtalk(alert)
    assert r["success"] is True
    url, payload, ch = posted.call_args[0]
    assert "timestamp" in url and "sign" in url
    assert "old" not in url  # old params replaced
    assert payload["msgtype"] == "markdown"

    r = await notify_engine._send_feishu(alert)
    assert r["success"] is True
    url, payload, ch = posted.call_args[0]
    assert url == "https://feishu.example.com"
    assert payload["msg_type"] == "text"


async def test_send_alert_notification_critical_all_channels(monkeypatch):
    """``send_alert_notification`` sends to all high-priority channels for fatal alerts."""
    monkeypatch.setattr(notify_engine, "_post_webhook", AsyncMock(return_value={"success": True}))
    monkeypatch.setattr(
        notify_engine, "send_slack_notification", AsyncMock(return_value={"success": True})
    )
    monkeypatch.setattr(
        notify_engine, "send_teams_notification", AsyncMock(return_value={"success": True})
    )
    monkeypatch.setattr(
        notify_engine, "send_email_notification", AsyncMock(return_value={"success": True})
    )
    monkeypatch.setattr(
        notify_engine, "_send_phone_notification", AsyncMock(return_value={"success": True})
    )
    monkeypatch.setattr(
        notify_engine, "_send_sms_notification", AsyncMock(return_value={"success": True})
    )
    monkeypatch.setenv("SLACK_BOT_TOKEN", "xoxb-fake")

    monkeypatch.setattr(
        notify_engine,
        "NOTIFY_CONFIG",
        {
            "enabled": True,
            "min_level": "info",
            "cooldown_seconds": "300",
            "wecom_webhook": "https://wecom.example.com",
            "dingtalk_webhook": "https://ding.example.com",
            "dingtalk_secret": "",
            "feishu_webhook": "https://feishu.example.com",
            "teams_webhook": "https://teams.example.com",
            "email_to": "ops@example.com",
            "phone_provider": "https://phone.example.com",
            "phone_to": "+123",
            "sms_provider": "https://sms.example.com",
            "sms_to": "+123",
        },
    )
    notify_engine._notification_cooldowns.clear()

    result = await notify_engine.send_alert_notification(
        {"id": "F1", "level": "fatal", "title": "boom", "desc": "bad"}
    )
    assert result["status"] == "ok"
    assert "wecom" in result["channels_sent"]
    assert "email" in result["channels_sent"]
    assert len(result["channels_sent"]) >= 6


async def test_send_alert_notification_warning_break_and_all_failed(monkeypatch):
    """``send_alert_notification`` breaks after first success for warning and reports all_failed."""
    monkeypatch.setattr(notify_engine, "_post_webhook", AsyncMock(return_value={"success": True}))
    monkeypatch.setattr(
        notify_engine, "send_email_notification", AsyncMock(return_value={"success": True})
    )
    monkeypatch.setattr(
        notify_engine,
        "NOTIFY_CONFIG",
        {
            "enabled": True,
            "min_level": "info",
            "cooldown_seconds": "300",
            "wecom_webhook": "https://wecom.example.com",
            "dingtalk_webhook": "",
            "feishu_webhook": "",
            "email_to": "ops@example.com",
        },
    )
    notify_engine._notification_cooldowns.clear()

    # warning: wecom succeeds and breaks
    result = await notify_engine.send_alert_notification(
        {"id": "W1", "level": "warning", "title": "w", "desc": "d"}
    )
    assert result["status"] == "ok"
    assert result["channels_sent"] == ["wecom"]

    # All configured channels fail
    notify_engine._post_webhook = AsyncMock(return_value={"success": False})
    notify_engine.send_email_notification = AsyncMock(return_value={"success": False})
    result = await notify_engine.send_alert_notification(
        {"id": "W2", "level": "warning", "title": "w", "desc": "d"}
    )
    assert result["status"] == "all_failed"


async def test_phone_and_sms_notifications(monkeypatch):
    """``_send_phone_notification`` and ``_send_sms_notification`` call HTTP client."""
    client = MagicMock()
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.status_code = 200
    client.post = AsyncMock(return_value=resp)
    monkeypatch.setattr(notify_engine, "_get_http_client", lambda: client)

    alert = {"id": "P1", "level": "critical", "title": "t", "summary": "s", "action": "a"}
    cfg = {"phone_provider": "https://phone.example.com", "phone_to": "+123"}
    r = await notify_engine._send_phone_notification(alert, cfg)
    assert r["success"] is True
    assert client.post.await_count == 1

    cfg = {"sms_provider": "https://sms.example.com", "sms_to": "+123"}
    r = await notify_engine._send_sms_notification(alert, cfg)
    assert r["success"] is True
    assert client.post.await_count == 2


# ============================================================
# intelligent_alert_analyzer (0% -> covered)
# ============================================================


async def test_intelligent_alert_analyzer_lifecycle():
    """``IntelligentAlertAnalyzer`` initializes and reports statistics."""
    a = analyzer.IntelligentAlertAnalyzer()
    await a.initialize()
    stats = await a.get_alert_statistics()
    assert stats["total_alerts"] == 0
    assert stats["patterns_count"] == 0
    assert stats["suppression_rules_count"] == 0
    assert stats["routing_rules_count"] == 0
    assert stats["topology_entities_count"] == 0


async def test_intelligent_alert_analyzer_aggregation():
    """``aggregate_alerts`` groups similar alerts using the rule-based fallback."""
    a = analyzer.IntelligentAlertAnalyzer()
    alerts = [
        analyzer.Alert("1", analyzer.AlertSeverity.HIGH, "disk full", "host-a", datetime.now()),
        analyzer.Alert("2", analyzer.AlertSeverity.HIGH, "disk full", "host-a", datetime.now()),
        analyzer.Alert("3", analyzer.AlertSeverity.LOW, "ok", "host-b", datetime.now()),
    ]
    aggregated = await a.aggregate_alerts(alerts)
    assert len(aggregated) == 2
    disk = next(g for g in aggregated if "disk" in g.message.lower())
    assert disk.count == 2
    single = next(g for g in aggregated if g.count == 1)
    assert single is not None
    assert await a.aggregate_alerts([]) == []


async def test_intelligent_alert_analyzer_trend_prediction(monkeypatch):
    """``predict_alert_trends`` returns None for insufficient data and a result with fake Prophet."""
    a = analyzer.IntelligentAlertAnalyzer()
    # Insufficient data
    assert await a.predict_alert_trends("cpu", []) is None
    small = [(datetime.now() - timedelta(hours=i), float(i)) for i in range(5)]
    assert await a.predict_alert_trends("cpu", small) is None

    # Fake Prophet branch
    class FakeProphet:
        def __init__(self, *args, **kwargs):
            pass

        def make_future_dataframe(self, periods):
            return pd.DataFrame({"ds": pd.date_range("2026-01-01", periods=periods, freq="h")})

        def predict(self, future):
            df = future.copy()
            df["yhat"] = 1.0
            return df

    monkeypatch.setattr(analyzer, "PROPHET_AVAILABLE", True)
    monkeypatch.setattr(analyzer, "Prophet", FakeProphet)
    data = [(datetime.now() - timedelta(hours=i), float(i)) for i in range(20)]
    prediction = await a.predict_alert_trends("cpu", data)
    assert prediction is not None
    assert isinstance(prediction, analyzer.AlertTrendPrediction)
    assert prediction.trend in ("increasing", "decreasing", "stable")
    assert len(prediction.predicted_values) == 24


async def test_intelligent_alert_analyzer_route_and_correlate():
    """``route_alert`` and ``correlate_alerts_with_topology`` use rules and topology."""
    a = analyzer.IntelligentAlertAnalyzer()
    await a.add_routing_rule({"severity": "critical", "teams": ["sre"]})
    await a.update_topology({"db": ["database"]})

    alert = analyzer.Alert(
        "r1",
        analyzer.AlertSeverity.CRITICAL,
        "db down",
        "db",
        datetime.now(),
        related_entities=["db"],
    )
    teams = await a.route_alert(alert)
    assert "sre" in teams
    assert "database-team" in teams

    correlated = await a.correlate_alerts_with_topology([alert])
    assert "db" in correlated
    assert len(correlated["db"]) == 1


async def test_intelligent_alert_analyzer_noise_reduction():
    """``reduce_alert_noise`` suppresses by rules and known noisy patterns."""
    a = analyzer.IntelligentAlertAnalyzer()
    await a.add_suppression_rule({"pattern": "ignore"})
    now = datetime.now()
    alert = analyzer.Alert("n1", analyzer.AlertSeverity.INFO, "ignore this", "host", now)
    assert await a.reduce_alert_noise([alert]) == []

    # Known noise pattern: >10 recent similar alerts
    for i in range(12):
        a.alert_patterns[a._generate_pattern_key(alert)].append(
            analyzer.Alert(f"p{i}", analyzer.AlertSeverity.INFO, "ignore this", "host", now)
        )
    noisy = analyzer.Alert("n2", analyzer.AlertSeverity.INFO, "ignore this", "host", now)
    assert await a.reduce_alert_noise([noisy]) == []


async def test_intelligent_alert_analyzer_noop_helpers():
    """Internal async helpers are safe to call."""
    a = analyzer.IntelligentAlertAnalyzer()
    await a._load_historical_patterns()
    await a._build_topology_graph()
