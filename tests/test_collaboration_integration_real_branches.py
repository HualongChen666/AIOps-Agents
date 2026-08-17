# -*- coding: utf-8 -*-
"""Real branch-coverage tests for core/integration/l7/collaboration_integration.py.

These tests use a real ``CollaborationIntegration`` instance, real in-memory
configuration, and a real local HTTP server.  No mocks or internal
monkeypatching of httpx are used.
"""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import socket
import threading
import time  # noqa: F401  # Imported for test setup
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest  # noqa: F401  # Imported for test setup

from core.integration.l7.collaboration_integration import (
    CollaborationIntegration,
    get_collaboration_integration,
    init_collaboration_integration,
)


class _CollabHandler(BaseHTTPRequestHandler):
    """Tiny real HTTP server that returns Slack/Teams shaped responses."""

    def log_message(self, fmt, *args):  # noqa: D401
        pass

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)

    def _send_json(self, body, status=200):
        payload = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self):  # noqa: N802
        self._read_body()
        if self.path == "/slack/success":
            self._send_json({"ok": True, "ts": "1500000000.000000"})
        elif self.path == "/slack/authfail":
            self._send_json({"ok": False, "error": "invalid_auth"})
        elif self.path == "/slack/error":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"server error")
        elif self.path == "/teams/success":
            self._send_json({"ok": True})
        elif self.path == "/teams/error":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"server error")
        else:
            self.send_response(404)
            self.end_headers()


@pytest.fixture(scope="module")
def collab_server():
    """Yield a real local HTTP server URL for the test module."""
    server = HTTPServer(("127.0.0.1", 0), _CollabHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    for _ in range(50):
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except OSError:
            time.sleep(0.01)
    yield f"http://127.0.0.1:{port}"
    server.shutdown()
    server.server_close()


def test_init_unconfigured():
    collab = CollaborationIntegration()
    assert collab._is_initialized is False
    status = collab.get_status()
    assert status["initialized"] is False
    assert status["slack"]["enabled"] is False
    assert status["teams"]["enabled"] is False


def test_init_slack_only():
    collab = CollaborationIntegration({"slack": {"enabled": True, "channel": "#alerts"}})
    assert collab._is_initialized is True
    assert collab.slack_enabled is True
    assert collab.teams_enabled is False


def test_init_teams_only():
    collab = CollaborationIntegration(
        {"teams": {"enabled": True, "webhook": "http://example.com", "channel": "General"}}
    )
    assert collab._is_initialized is True
    assert collab.slack_enabled is False
    assert collab.teams_enabled is True


def test_send_slack_notification_disabled():
    async def _run():
        collab = CollaborationIntegration()
        result = await collab.send_slack_notification("hello")  # noqa: F841  # Variable for test verification
        assert result == {"error": "Slack not enabled"}  # noqa: F841  # Variable for test verification

    asyncio.run(_run())


def test_send_slack_approval_request_disabled():
    async def _run():
        collab = CollaborationIntegration()
        result = await collab.send_slack_approval_request("title", "desc")  # noqa: F841  # Variable for test verification
        assert result == {"error": "Slack not enabled"}  # noqa: F841  # Variable for test verification

    asyncio.run(_run())


def test_send_teams_notification_disabled():
    async def _run():
        collab = CollaborationIntegration()
        result = await collab.send_teams_notification("hello")  # noqa: F841  # Variable for test verification
        assert result == {"error": "Teams not enabled"}  # noqa: F841  # Variable for test verification

    asyncio.run(_run())


def test_send_teams_approval_card_disabled():
    async def _run():
        collab = CollaborationIntegration()
        result = await collab.send_teams_approval_card("title", "desc")  # noqa: F841  # Variable for test verification
        assert result == {"error": "Teams not enabled"}  # noqa: F841  # Variable for test verification

    asyncio.run(_run())


def test_slack_notification_success_and_channel_override(collab_server):
    async def _run():
        url = f"{collab_server}/slack/success"
        collab = CollaborationIntegration(
            {
                "slack": {
                    "enabled": True,
                    "bot_token": "xoxb-test",
                    "channel": "#alerts",
                    "api_url": url,
                }
            }
        )
        # channel override branch and attachments truthy branch
        result = await collab.send_slack_notification(  # noqa: F841  # Variable for test verification
            "hello",
            channel="#override",
            attachments=[{"text": "note"}],
        )
        assert result["success"] is True
        assert result["channel"] == "#override"
        assert "ts" in result

        # default channel branch and attachments falsy branch
        result2 = await collab.send_slack_notification("hello2")
        assert result2["success"] is True
        assert result2["channel"] == "#alerts"

    asyncio.run(_run())


def test_slack_notification_auth_failure(collab_server):
    async def _run():
        url = f"{collab_server}/slack/authfail"
        collab = CollaborationIntegration(
            {
                "slack": {
                    "enabled": True,
                    "bot_token": "xoxb-bad",
                    "channel": "#alerts",
                    "api_url": url,
                }
            }
        )
        result = await collab.send_slack_notification("boom")  # noqa: F841  # Variable for test verification
        assert "error" in result
        assert "invalid_auth" in result["error"]

    asyncio.run(_run())


def test_slack_notification_server_error(collab_server):
    async def _run():
        url = f"{collab_server}/slack/error"
        collab = CollaborationIntegration(
            {
                "slack": {
                    "enabled": True,
                    "bot_token": "xoxb-test",
                    "channel": "#alerts",
                    "api_url": url,
                }
            }
        )
        result = await collab.send_slack_notification("boom")  # noqa: F841  # Variable for test verification
        assert "error" in result

    asyncio.run(_run())


def test_slack_approval_request_with_actions(collab_server):
    async def _run():
        url = f"{collab_server}/slack/success"
        collab = CollaborationIntegration(
            {
                "slack": {
                    "enabled": True,
                    "bot_token": "xoxb-test",
                    "channel": "#approvals",
                    "api_url": url,
                }
            }
        )
        actions = [
            {"text": "Approve", "value": "approve"},
            {"text": "Reject", "value": "reject"},
        ]
        result = await collab.send_slack_approval_request("title", "desc", actions)  # noqa: F841  # Variable for test verification
        assert result["success"] is True
        assert result["channel"] == "#approvals"

    asyncio.run(_run())


def test_slack_approval_request_no_actions(collab_server):
    async def _run():
        url = f"{collab_server}/slack/success"
        collab = CollaborationIntegration(
            {
                "slack": {
                    "enabled": True,
                    "bot_token": "xoxb-test",
                    "channel": "#approvals",
                    "api_url": url,
                }
            }
        )
        result = await collab.send_slack_approval_request("title", "desc", None)  # noqa: F841  # Variable for test verification
        assert result["success"] is True

    asyncio.run(_run())


def test_slack_approval_request_auth_failure(collab_server):
    async def _run():
        url = f"{collab_server}/slack/authfail"
        collab = CollaborationIntegration(
            {
                "slack": {
                    "enabled": True,
                    "bot_token": "xoxb-bad",
                    "channel": "#approvals",
                    "api_url": url,
                }
            }
        )
        result = await collab.send_slack_approval_request("title", "desc")  # noqa: F841  # Variable for test verification
        assert "error" in result
        assert "invalid_auth" in result["error"]

    asyncio.run(_run())


def test_slack_approval_request_server_error(collab_server):
    async def _run():
        url = f"{collab_server}/slack/error"
        collab = CollaborationIntegration(
            {
                "slack": {
                    "enabled": True,
                    "bot_token": "xoxb-test",
                    "channel": "#approvals",
                    "api_url": url,
                }
            }
        )
        result = await collab.send_slack_approval_request("title", "desc")  # noqa: F841  # Variable for test verification
        assert "error" in result

    asyncio.run(_run())


def test_teams_notification_success(collab_server):
    async def _run():
        url = f"{collab_server}/teams/success"
        collab = CollaborationIntegration(
            {"teams": {"enabled": True, "webhook": url, "channel": "General"}}
        )
        result = await collab.send_teams_notification("body", title="title", color="FF0000")  # noqa: F841  # Variable for test verification
        assert result["success"] is True

    asyncio.run(_run())


def test_teams_notification_no_title(collab_server):
    async def _run():
        url = f"{collab_server}/teams/success"
        collab = CollaborationIntegration(
            {"teams": {"enabled": True, "webhook": url, "channel": "General"}}
        )
        result = await collab.send_teams_notification("body")  # noqa: F841  # Variable for test verification
        assert result["success"] is True

    asyncio.run(_run())


def test_teams_notification_connection_error():
    async def _run():
        collab = CollaborationIntegration(
            {
                "teams": {
                    "enabled": True,
                    "webhook": "http://127.0.0.1:1/teams",
                    "channel": "General",
                }
            }
        )
        result = await collab.send_teams_notification("body")  # noqa: F841  # Variable for test verification
        assert "error" in result

    asyncio.run(_run())


def test_teams_approval_card_with_description(collab_server):
    async def _run():
        url = f"{collab_server}/teams/success"
        collab = CollaborationIntegration(
            {"teams": {"enabled": True, "webhook": url, "channel": "General"}}
        )
        actions = [{"text": "Approve", "value": "approve"}]
        result = await collab.send_teams_approval_card("title", "desc", actions)  # noqa: F841  # Variable for test verification
        assert result["success"] is True

    asyncio.run(_run())


def test_teams_approval_card_no_description(collab_server):
    async def _run():
        url = f"{collab_server}/teams/success"
        collab = CollaborationIntegration(
            {"teams": {"enabled": True, "webhook": url, "channel": "General"}}
        )
        actions = [{"text": "Approve", "value": "approve"}]
        result = await collab.send_teams_approval_card("title", "", actions)  # noqa: F841  # Variable for test verification
        assert result["success"] is True

    asyncio.run(_run())


def test_teams_approval_card_server_error(collab_server):
    async def _run():
        url = f"{collab_server}/teams/error"
        collab = CollaborationIntegration(
            {"teams": {"enabled": True, "webhook": url, "channel": "General"}}
        )
        result = await collab.send_teams_approval_card(  # noqa: F841  # Variable for test verification
            "title", "desc", [{"text": "Approve", "value": "approve"}]
        )
        assert "error" in result

    asyncio.run(_run())


def test_alert_and_approval_routing(collab_server):
    async def _run():
        slack_url = f"{collab_server}/slack/success"
        teams_url = f"{collab_server}/teams/success"
        both = {
            "slack": {
                "enabled": True,
                "bot_token": "xoxb-test",
                "channel": "#alerts",
                "api_url": slack_url,
            },
            "teams": {"enabled": True, "webhook": teams_url, "channel": "General"},
        }
        collab = CollaborationIntegration(both)

        # default platforms (covers the ``or`` default and both provider branches)
        alert = await collab.notify_alert("A-1", {"severity": "high", "description": "oops"})
        assert "slack" in alert
        assert "teams" in alert

        # slack-only platform branch
        alert = await collab.notify_alert("A-1", {"severity": "high"}, platforms=["slack"])
        assert "slack" in alert and "teams" not in alert

        # teams-only platform branch
        alert = await collab.notify_alert("A-1", {"severity": "high"}, platforms=["teams"])
        assert "teams" in alert and "slack" not in alert

        # request approval default platforms
        approval = await collab.request_approval("R-1", {"description": "fix"})
        assert "slack" in approval
        assert "teams" in approval

        # request approval slack-only
        approval = await collab.request_approval("R-1", {"description": "fix"}, platforms=["slack"])
        assert "slack" in approval and "teams" not in approval

        # unconfigured fallback: no providers enabled -> empty results
        none = CollaborationIntegration({})
        assert await none.notify_alert("A-1", {}) == {}
        assert await none.request_approval("R-1", {}) == {}

    asyncio.run(_run())


def test_global_singleton_lifecycle():
    inst = init_collaboration_integration({"slack": {"enabled": True, "channel": "#alerts"}})
    assert isinstance(inst, CollaborationIntegration)
    assert get_collaboration_integration() is inst
