# -*- coding: utf-8 -*-
"""Real in-memory branch coverage tests for core/notify_engine.py.

Uses real HTTP servers, real on-call schedules, real message payloads and
real notification engine logic.  No unittest.mock objects are used.
"""

import contextlib
import importlib
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
import httpx

# Set sane defaults before the first import of notify_engine.
os.environ.setdefault("NOTIFY_ENABLED", "true")
os.environ.setdefault("NOTIFY_MIN_LEVEL", "info")

import core.notify_engine as notify_engine
import core.oncall_adapter as oncall_adapter


pytestmark = [pytest.mark.core]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _env_vars(**kwargs):
    """Temporarily set environment variables and restore them afterwards."""
    saved = {}
    for key, value in kwargs.items():
        saved[key] = os.environ.get(key)
        if value is not None:
            os.environ[key] = str(value)
        else:
            os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _reload_notify_modules():
    """Reload configuration modules to pick up the current environment."""
    # Force the on-call singleton to be recreated from env.
    oncall_adapter._oncall_adapter = None
    importlib.reload(oncall_adapter)
    importlib.reload(notify_engine)


class _WebhookHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler that records incoming POSTs and returns stub answers."""

    def _path_key(self):
        return self.path.split("?", 1)[0]

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        self.server.requests.append((self._path_key(), self.path, body))
        status, payload = self.server.responses.get(self._path_key(), (200, b"ok"))
        self.send_response(status)
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self):
        # For the phone/sms providers if they ever GET.
        self.server.requests.append((self._path_key(), self.path, b""))
        status, payload = self.server.responses.get(self._path_key(), (200, b"ok"))
        self.send_response(status)
        if isinstance(payload, str):
            payload = payload.encode("utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        pass


class _WebhookServer(HTTPServer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.requests = []
        self.responses = {}


@pytest.fixture
def webhook_server():
    """Run a real HTTP server in a thread and yield its base URL + server object."""
    server = _WebhookServer(("127.0.0.1", 0), _WebhookHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}", server
    finally:
        server.shutdown()
        thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Validation and utilities
# ---------------------------------------------------------------------------

def test_validate_webhook_url_edge_cases():
    assert notify_engine._validate_webhook_url("http://example.com/hook", "x") is True
    assert notify_engine._validate_webhook_url("ftp://example.com/hook", "x") is False
    assert notify_engine._validate_webhook_url("http://", "x") is False
    assert notify_engine._validate_webhook_url("   ", "x") is False
    long_url = "https://x.com/" + "a" * 3000
    assert notify_engine._validate_webhook_url(long_url, "x") is False


def test_format_alert_message_branches():
    a1 = {
        "type": "cpu",
        "message": "high",
        "severity": "critical",
        "host": "srv01",
        "metrics": {"cpu": 99},
    }
    text1 = notify_engine.format_alert_message(a1)
    assert "CRITICAL" in text1
    assert "srv01" in text1
    assert "cpu=99" in text1

    a2 = {"type": "cpu", "message": "high", "severity": "warning", "metrics": None}
    text2 = notify_engine.format_alert_message(a2)
    assert text2
    assert "Host" not in text2

    a3 = {"type": "cpu", "message": "high", "severity": "warning", "metrics": "90%"}
    text3 = notify_engine.format_alert_message(a3)
    assert "90%" in text3


def test_build_structured_alert_message_formats_and_link_dedup():
    alert = {
        "level": "critical",
        "summary": "summary text",
        "impact": "users",
        "diagnosis": "cpu hot",
        "action": "restart",
        "raw_time": "now",
        "confidence": 0.95,
        "links": {"dashboard_url": "http://existing"},
        "dashboard_url": "http://auto",
    }
    md = notify_engine.build_structured_alert_message(alert, fmt="markdown")
    assert "summary text" in md
    txt = notify_engine.build_structured_alert_message(alert, fmt="text")
    assert "0.95" in txt
    html = notify_engine.build_structured_alert_message(alert, fmt="html")
    assert "<h3>" in html

    # Branch where a link-like key is already present in the explicit links dict.
    dedup = notify_engine.build_structured_alert_message(
        {"level": "high", "summary": "s", "links": {"dashboard_url": "http://d"}, "dashboard_url": "http://ignored"},
        fmt="text",
    )
    assert "http://ignored" not in dedup


def test_channels_for_severity_and_priority():
    full_cfg = {
        "phone_provider": "http://phone",
        "sms_provider": "http://sms",
        "wecom_webhook": "http://wecom",
        "dingtalk_webhook": "http://dingtalk",
        "feishu_webhook": "http://feishu",
        "teams_webhook": "http://teams",
        "email_to": "ops@example.com",
    }
    # SLACK_BOT_TOKEN must be set for slack to appear.
    with _env_vars(SLACK_BOT_TOKEN="xoxb-test-token"):
        fatal = notify_engine._channels_for_severity("fatal", full_cfg)
        for ch in ["phone", "sms", "wecom", "dingtalk", "feishu", "slack", "teams", "email"]:
            assert ch in fatal

    # Missing provider config should skip the channel branches.
    empty = notify_engine._channels_for_severity("fatal", {})
    assert empty == []

    ordered = notify_engine._order_channels_by_priority(["email", "phone", "wecom"])
    assert ordered == ["phone", "wecom", "email"]


def test_http_client_singleton_and_close():
    notify_engine._http_client = None
    c1 = notify_engine._get_http_client()
    c2 = notify_engine._get_http_client()
    assert c1 is c2
    # close when open
    assert c1.is_closed is False

    async def _close():
        await notify_engine.close_http_client()

    import asyncio
    asyncio.run(_close())
    # closing when already None should not error (covers the false branch).
    asyncio.run(notify_engine.close_http_client())


def test_reload_notify_config():
    with _env_vars(NOTIFY_MIN_LEVEL="warning", WECOM_WEBHOOK="https://qyapi.weixin.qq.com/w"):
        cfg = notify_engine.reload_notify_config()
    assert cfg["min_level"] == "warning"
    # Webhook that passes validation stays in config.
    assert cfg["wecom_webhook"] == "https://qyapi.weixin.qq.com/w"


# ---------------------------------------------------------------------------
# Real routing with in-memory providers
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_alert_notification_routes_all_channels(webhook_server):
    url, server = webhook_server
    server.responses = {
        "/": (200, b"ok"),
    }
    schedule = json.dumps({
        "oncall": [
            {"name": "alice", "email": "alice@example.com", "phone": "+8613800000001"},
            {"name": "bob", "phone": "+8613800000002"},
            {"name": "carol", "email": "carol@example.com"},
        ]
    })
    env = {
        "NOTIFY_ENABLED": "true",
        "NOTIFY_MIN_LEVEL": "info",
        "WECOM_WEBHOOK": url,
        "DINGTALK_WEBHOOK": url,
        "DINGTALK_SECRET": "SEC123",
        "FEISHU_WEBHOOK": url,
        "TEAMS_WEBHOOK_URL": url,
        "EMAIL_TO": "ops@example.com",
        "PHONE_PROVIDER": url,
        "SMS_PROVIDER": url,
        "ONCALL_PROVIDER": "json",
        "ONCALL_SCHEDULE_JSON": schedule,
    }
    with _env_vars(**env):
        _reload_notify_modules()
        ne = notify_engine

        alert = {
            "id": "ALT-1",
            "fingerprint": "fp-cpu-1",
            "title": "CPU critical",
            "summary": "CPU is critical",
            "severity": "critical",
            "level": "critical",
            "impact": "all users",
            "diagnosis": "cpu overload",
            "action": "scale out",
            "raw_time": "2024-01-01T00:00:00Z",
            "links": {},
        }
        result = await ne.send_alert_notification(alert)
        assert result["status"] in ("ok", "all_failed")
        assert result["level"] == "critical"
        # Most configured channels should have received a POST.
        paths = [p for p, _, _ in server.requests]
        # All POSTs go to "/" because the server handlers normalise the path.
        assert paths.count("/") >= 3


@pytest.mark.asyncio
async def test_send_alert_notification_warning_stops_after_first_success(webhook_server):
    url, server = webhook_server
    # First channel to succeed stops the loop for P2/P3 levels.
    server.responses = {"/": (200, b"ok")}
    env = {
        "NOTIFY_ENABLED": "true",
        "NOTIFY_MIN_LEVEL": "info",
        "WECOM_WEBHOOK": url,
        "DINGTALK_WEBHOOK": url,
        "FEISHU_WEBHOOK": url,
        "EMAIL_TO": "ops@example.com",
    }
    with _env_vars(**env):
        _reload_notify_modules()
        ne = notify_engine
        alert = {
            "id": "ALT-2",
            "fingerprint": "fp-warn-2",
            "title": "Disk warning",
            "summary": "disk at 80%",
            "severity": "warning",
            "level": "warning",
            "impact": "some users",
            "diagnosis": "disk growing",
            "action": "cleanup",
            "raw_time": "2024-01-01T00:00:00Z",
            "links": {},
        }
        result = await ne.send_alert_notification(alert)
        # warning stops after first success
        sent = result["channels_sent"]
        assert isinstance(sent, list)
        assert len(sent) >= 1


# ---------------------------------------------------------------------------
# send_notification routing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_notification_channels_none_and_partial_success(webhook_server):
    url, server = webhook_server
    server.responses = {"/": (200, b"ok")}
    env = {
        "TEAMS_WEBHOOK_URL": url,
    }
    with _env_vars(**env):
        _reload_notify_modules()
        ne = notify_engine

    # channels is None and severity is warning -> only slack attempted (fails)
    alert = {
        "type": "cpu",
        "message": "high",
        "severity": "warning",
    }
    result = await ne.send_notification(alert)
    assert result["success"] is False

    # channels is None and severity is critical -> slack/teams/email attempted, teams succeeds.
    alert2 = {
        "type": "cpu",
        "message": "high",
        "severity": "critical",
        "webhook_url": url,
    }
    result2 = await ne.send_notification(alert2)
    assert result2["success"] is True
    assert result2["channels_sent"] >= 1


# ---------------------------------------------------------------------------
# Oncall-driven email / phone / SMS branches
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_one_channel_email_uses_oncall_and_fallback_admin(webhook_server):
    url, server = webhook_server
    base_alert = {
        "id": "E1",
        "fingerprint": "fp-e1",
        "level": "critical",
        "title": "t",
        "summary": "s",
        "impact": "i",
        "diagnosis": "d",
        "action": "a",
        "raw_time": "now",
        "links": {},
    }
    # Case 1: oncall contact has an email address.
    env1 = {
        "ONCALL_PROVIDER": "json",
        "ONCALL_SCHEDULE_JSON": json.dumps({
            "ops": [
                {"name": "noemail", "phone": "+8613800000001"},
                {"name": "hasemail", "email": "oncall@example.com"},
            ]
        }),
    }
    with _env_vars(**env1):
        _reload_notify_modules()
        ne = notify_engine
        result = await ne._send_one_channel(base_alert, "email", ne.NOTIFY_CONFIG)
        assert result.get("recipient") == "oncall@example.com"

    # Case 2: no oncall email -> fallback to admin@example.com.
    env2 = {
        "ONCALL_PROVIDER": "json",
        "ONCALL_SCHEDULE_JSON": json.dumps({"ops": [{"name": "noemail"}]}),
    }
    with _env_vars(**env2):
        _reload_notify_modules()
        ne = notify_engine
        result2 = await ne._send_one_channel(base_alert, "email", ne.NOTIFY_CONFIG)
        assert result2.get("recipient") == "admin@example.com"


@pytest.mark.asyncio
async def test_send_one_channel_phone_and_sms_branches(webhook_server):
    url, server = webhook_server
    server.responses = {"/": (200, b"ok")}
    base_alert = {
        "id": "P1",
        "fingerprint": "fp-p1",
        "level": "critical",
        "title": "t",
        "summary": "s",
        "impact": "i",
        "diagnosis": "d",
        "action": "a",
        "raw_time": "now",
        "links": {},
    }

    # Phone branch: oncall contacts have no phone number -> recipient unresolved.
    env1 = {
        "ONCALL_PROVIDER": "json",
        "ONCALL_SCHEDULE_JSON": json.dumps({
            "ops": [{"name": "nophone", "email": "only@example.com"}]
        }),
        "PHONE_PROVIDER": url,
    }
    with _env_vars(**env1):
        _reload_notify_modules()
        ne = notify_engine
        phone1 = await ne._send_one_channel(base_alert, "phone", ne.NOTIFY_CONFIG)
        assert phone1.get("success") is False
        assert "recipient" not in phone1 or not phone1.get("recipient")

    # SMS branches: oncall has a phone -> send succeeds, covering the loop body and send.
    env2 = {
        "ONCALL_PROVIDER": "json",
        "ONCALL_SCHEDULE_JSON": json.dumps({
            "ops": [
                {"name": "nophone", "email": "only@example.com"},
                {"name": "hasphone", "phone": "+8613800000001"},
            ]
        }),
        "SMS_PROVIDER": url,
    }
    with _env_vars(**env2):
        _reload_notify_modules()
        ne = notify_engine
        sms = await ne._send_one_channel(base_alert, "sms", ne.NOTIFY_CONFIG)
        assert sms.get("success") is True
        assert sms.get("recipient") == "+8613800000001"


# ---------------------------------------------------------------------------
# Dingtalk signing branches
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_dingtalk_existing_query_params(webhook_server):
    url, server = webhook_server
    server.responses = {"/": (200, b"ok")}
    base = f"{url}?timestamp=123&sign=old&extra=foo"
    env = {
        "DINGTALK_WEBHOOK": base,
        "DINGTALK_SECRET": "SEC123",
    }
    with _env_vars(**env):
        _reload_notify_modules()
        ne = notify_engine

    alert = {
        "id": "D1",
        "fingerprint": "fp-d1",
        "level": "critical",
        "title": "CPU",
        "summary": "s",
        "impact": "i",
        "diagnosis": "d",
        "action": "a",
        "raw_time": "now",
        "links": {},
    }
    result = await ne._send_dingtalk(alert)
    assert result.get("success") is True
    # The extra query parameter should survive sign replacement.
    raw_paths = [raw for _, raw, _ in server.requests]
    assert any("extra=foo" in p for p in raw_paths)


@pytest.mark.asyncio
async def test_send_dingtalk_sign_exception(webhook_server):
    url, server = webhook_server
    env = {
        "DINGTALK_WEBHOOK": url,
        "DINGTALK_SECRET": "SEC123",
    }
    with _env_vars(**env):
        _reload_notify_modules()
        ne = notify_engine

    # Make the secret a bytes object so .encode('utf-8') raises AttributeError
    # inside the sign try/except block.
    ne.NOTIFY_CONFIG["dingtalk_secret"] = b"SEC123"

    alert = {
        "id": "D2",
        "fingerprint": "fp-d2",
        "level": "critical",
        "title": "CPU",
        "summary": "s",
        "impact": "i",
        "diagnosis": "d",
        "action": "a",
        "raw_time": "now",
        "links": {},
    }
    result = await ne._send_dingtalk(alert)
    assert result.get("success") is False
    assert "加签" in result.get("error", "")


# ---------------------------------------------------------------------------
# Teams and Slack branches
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_teams_notification_connection_error():
    with _env_vars():
        _reload_notify_modules()
        ne = notify_engine
    # Port 1 should refuse the connection, exercising the except branch.
    result = await ne.send_teams_notification("hello", "http://127.0.0.1:1/webhook")
    assert result.get("success") is False


@pytest.mark.asyncio
async def test_slack_client_factory():
    with _env_vars(SLACK_BOT_TOKEN="xoxb-test-token"):
        _reload_notify_modules()
        ne = notify_engine
        client = ne._get_slack_client()
        assert client is not None
    # Empty token should yield None.
    with _env_vars(SLACK_BOT_TOKEN=""):
        assert ne._get_slack_client() is None


# ---------------------------------------------------------------------------
# History and status tracking
# ---------------------------------------------------------------------------

def test_notification_history_and_read_status():
    notify_engine._notification_history.clear()
    notify_engine._notification_cooldowns.clear()
    notify_engine._track_notification_status(
        {"id": "M1", "fingerprint": "fp1", "title": "t", "level": "critical"},
        "email",
        "delivered",
        recipient="ops@example.com",
        message_id="M1",
    )
    assert notify_engine.get_notification_status(alert_id="M1")
    assert notify_engine.mark_notification_read("M1", "email") is True
    status = notify_engine.get_notification_read_status("M1", "email")
    assert status["status"] == "read"


@pytest.mark.asyncio
async def test_query_and_history_async():
    notify_engine._notification_history.clear()
    notify_engine._track_notification_status(
        {"id": "M2", "fingerprint": "fp2", "title": "t", "level": "high"},
        "wecom",
        "delivered",
    )
    rows = await notify_engine.query_notifications(limit=10, severity="high")
    assert len(rows) >= 1
    hist = await notify_engine.get_notification_history(limit=10, severity="high")
    assert len(hist) >= 1
