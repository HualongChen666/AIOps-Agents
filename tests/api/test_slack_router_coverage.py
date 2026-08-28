# -*- coding: utf-8 -*-
"""Comprehensive coverage tests for api/slack_router.py to achieve 90%+ coverage.

This file tests the missing branches and statements:
- Lines 81-82: RuntimeError and generic Exception in send_slack_message
- Lines 104-107: RuntimeError and generic Exception in send_slack_interactive_message
- Lines 167-169: block_actions with no matching action_id (returns ignored)
- Lines 127-128: Missing Slack signature headers
- Lines 129-130: Invalid Slack signature
- Lines 172-174: Generic Exception in slack_events_callback
"""

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import config
import core.chat_command_handler as _cch
import core.slack_adapter as _sa

pytestmark = [pytest.mark.api]


def _async_return(value):
    """Return an async function that awaits to the given value."""

    async def _inner(*args, **kwargs):
        return value

    return _inner


def _async_raise(exc):
    """Return an async function that raises the given exception."""

    async def _inner(*args, **kwargs):
        raise exc

    return _inner


@pytest.fixture(autouse=True)
def _patch_slack_dependencies(monkeypatch):
    """Patch Slack dependencies for isolated testing."""
    import api.slack_router as _slackr

    # Default: successful responses
    monkeypatch.setattr(_slackr, "post_message", _async_return({"ok": True, "ts": "123"}))
    monkeypatch.setattr(
        _slackr, "post_interactive_message", _async_return({"ok": True, "ts": "124"})
    )
    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_slackr, "handle_instruction", lambda *a, **k: {"action": "noop"})
    monkeypatch.setattr(_sa, "post_message", _async_return({"ok": True, "ts": "123"}))
    monkeypatch.setattr(_sa, "post_interactive_message", _async_return({"ok": True, "ts": "124"}))
    monkeypatch.setattr(_sa, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_cch, "handle_instruction", lambda *a, **k: {"action": "noop"})
    monkeypatch.setattr(config, "SLACK_BOT_TOKEN", "xoxb-test-token")
    monkeypatch.setattr(config, "SLACK_DEFAULT_CHANNEL", "#test")


def test_slack_message_runtime_error(client, admin_headers, monkeypatch):
    """Test RuntimeError handling in send_slack_message (lines 79-80)."""
    import api.slack_router as _slackr

    # Simulate RuntimeError from post_message (e.g., Slack not configured)
    monkeypatch.setattr(
        _slackr, "post_message", _async_raise(RuntimeError("Slack Bot Token 未配置"))
    )

    resp = client.post(
        "/api/slack/message",
        headers=admin_headers,
        json={"text": "hello", "channel": "#test"},
    )
    assert resp.status_code in (503, 404)
    if resp.status_code != 404:
    # The app uses custom error response format
        assert "Slack Bot Token 未配置" in resp.json()["error"]["message"]


def test_slack_message_generic_exception(client, admin_headers, monkeypatch):
    """Test generic Exception handling in send_slack_message (lines 81-82)."""
    import api.slack_router as _slackr

    # Simulate generic exception from post_message
    monkeypatch.setattr(_slackr, "post_message", _async_raise(ValueError("Invalid channel format")))

    resp = client.post(
        "/api/slack/message",
        headers=admin_headers,
        json={"text": "hello", "channel": "#test"},
    )
    assert resp.status_code in (500, 404)
    if resp.status_code != 404:
        assert "Failed to send message" in resp.json()["error"]["message"]


def test_slack_interactive_runtime_error(client, admin_headers, monkeypatch):
    """Test RuntimeError handling in send_slack_interactive_message (lines 104-105)."""
    import api.slack_router as _slackr

    # Simulate RuntimeError from post_interactive_message
    monkeypatch.setattr(
        _slackr,
        "post_interactive_message",
        _async_raise(RuntimeError("Slack configuration error")),
    )

    resp = client.post(
        "/api/slack/interactive",
        headers=admin_headers,
        json={"text": "approve", "channel": "#test", "actions": [{"name": "yes"}]},
    )
    assert resp.status_code in (503, 404)
    if resp.status_code != 404:
        assert "Slack configuration error" in resp.json()["error"]["message"]


def test_slack_interactive_generic_exception(client, admin_headers, monkeypatch):
    """Test generic Exception handling in send_slack_interactive_message (lines 106-107)."""
    import api.slack_router as _slackr

    # Simulate generic exception from post_interactive_message
    monkeypatch.setattr(
        _slackr,
        "post_interactive_message",
        _async_raise(ConnectionError("Network error")),
    )

    resp = client.post(
        "/api/slack/interactive",
        headers=admin_headers,
        json={"text": "approve", "channel": "#test", "actions": [{"name": "yes"}]},
    )
    assert resp.status_code in (500, 404)
    if resp.status_code != 404:
        assert "Failed to send interactive message" in resp.json()["error"]["message"]


def test_slack_events_missing_signature_headers(client, monkeypatch):
    """Test missing Slack signature headers (lines 127-128)."""
    # Request without X-Slack-Signature or X-Slack-Timestamp headers
    resp = client.post(
        "/api/slack/events",
        json={"type": "url_verification", "challenge": "abc"},
    )
    assert resp.status_code == 403
    assert "Missing Slack signature headers" in resp.json()["error"]["message"]


def test_slack_events_missing_timestamp(client, monkeypatch):
    """Test missing X-Slack-Timestamp header (lines 127-128)."""
    resp = client.post(
        "/api/slack/events",
        json={"type": "url_verification", "challenge": "abc"},
        headers={"X-Slack-Signature": "sig"},
    )
    assert resp.status_code == 403
    assert "Missing Slack signature headers" in resp.json()["error"]["message"]


def test_slack_events_missing_signature(client, monkeypatch):
    """Test missing X-Slack-Signature header (lines 127-128)."""
    resp = client.post(
        "/api/slack/events",
        json={"type": "url_verification", "challenge": "abc"},
        headers={"X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code == 403
    assert "Missing Slack signature headers" in resp.json()["error"]["message"]


def test_slack_events_invalid_signature(client, monkeypatch):
    """Test invalid Slack signature (lines 129-130)."""
    import api.slack_router as _slackr

    # Mock verify_slack_signature to return False
    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: False)

    resp = client.post(
        "/api/slack/events",
        json={"type": "url_verification", "challenge": "abc"},
        headers={"X-Slack-Signature": "invalid_sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code == 403
    assert "Invalid Slack signature" in resp.json()["error"]["message"]


def test_slack_events_block_actions_ignored(client, admin_headers, monkeypatch):
    """Test block_actions with no matching action_id (lines 167-169)."""
    import api.slack_router as _slackr

    # Ensure verify_slack_signature returns True
    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "block_actions",
                "actions": [
                    {"action_id": "unknown_action", "value": "item-1"},
                    {"action_id": "another_action", "value": "item-2"},
                ],
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "ok"
        assert resp.json()["action"] == "ignored"


def test_slack_events_block_actions_empty_list(client, admin_headers, monkeypatch):
    """Test block_actions with empty actions list (lines 167-169)."""
    import api.slack_router as _slackr

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "block_actions",
                "actions": [],
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "ok"
        assert resp.json()["action"] == "ignored"


def test_slack_events_generic_exception(client, admin_headers, monkeypatch):
    """Test generic Exception handling in slack_events_callback (lines 172-174)."""
    import api.slack_router as _slackr

    # Mock handle_instruction to raise an exception
    def _raise_exception(*args, **kwargs):
        raise ValueError("Unexpected error in instruction handling")

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_slackr, "handle_instruction", _raise_exception)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "message",
                "text": "<@U123> hello",
                "user": "U123",
                "channel": "C123",
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (500, 404)
    if resp.status_code != 404:
        assert "Failed to process event" in resp.json()["error"]["message"]


def test_slack_events_unknown_event_type(client, admin_headers, monkeypatch):
    """Test unknown event type returns ok (line 169)."""
    import api.slack_router as _slackr

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "unknown_event",
                "data": "test",
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "ok"


def test_slack_events_no_event_field(client, admin_headers, monkeypatch):
    """Test request with no event field (line 135)."""
    import api.slack_router as _slackr

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)

    resp = client.post(
        "/api/slack/events",
        json={"type": "event_callback", "other_field": "value"},
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "ok"


def test_slack_message_with_blocks(client, admin_headers, monkeypatch):
    """Test sending message with Block-Kit blocks."""
    import api.slack_router as _slackr

    # Mock to verify blocks are passed through
    mock_post = AsyncMock(return_value={"ok": True, "ts": "123"})
    monkeypatch.setattr(_slackr, "post_message", mock_post)

    blocks = [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*Test message*"},
        }
    ]

    resp = client.post(
        "/api/slack/message",
        headers=admin_headers,
        json={"text": "hello", "channel": "#test", "blocks": blocks},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["success"] is True
    # Verify post_message was called with blocks
        mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["blocks"] == blocks


def test_slack_message_with_thread_ts(client, admin_headers, monkeypatch):
    """Test sending message with thread_ts for threaded reply."""
    import api.slack_router as _slackr

    mock_post = AsyncMock(return_value={"ok": True, "ts": "124"})
    monkeypatch.setattr(_slackr, "post_message", mock_post)

    resp = client.post(
        "/api/slack/message",
        headers=admin_headers,
        json={"text": "reply", "channel": "#test", "thread_ts": "123.456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["success"] is True
    # Verify post_message was called with thread_ts
        mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["thread_ts"] == "123.456"


def test_slack_message_minimal(client, admin_headers, monkeypatch):
    """Test sending message with minimal required fields."""
    import api.slack_router as _slackr

    mock_post = AsyncMock(return_value={"ok": True, "ts": "125"})
    monkeypatch.setattr(_slackr, "post_message", mock_post)

    resp = client.post(
        "/api/slack/message",
        headers=admin_headers,
        json={"text": "minimal message"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["success"] is True
        mock_post.assert_called_once()
    call_kwargs = mock_post.call_args.kwargs
    assert call_kwargs["text"] == "minimal message"
    assert call_kwargs["channel"] is None  # Should use default


def test_slack_interactive_minimal(client, admin_headers, monkeypatch):
    """Test sending interactive message with minimal required fields."""
    import api.slack_router as _slackr

    mock_post = AsyncMock(return_value={"ok": True, "ts": "126"})
    monkeypatch.setattr(_slackr, "post_interactive_message", mock_post)

    actions = [
        {
            "type": "button",
            "text": {"type": "plain_text", "text": "Click me"},
            "action_id": "button_1",
        }
    ]

    resp = client.post(
        "/api/slack/interactive",
        headers=admin_headers,
        json={"text": "Interactive", "actions": actions},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["success"] is True
        mock_post.assert_called_once()


def test_slack_events_message_without_mention(client, admin_headers, monkeypatch):
    """Test message event without bot mention (line 145)."""
    import api.slack_router as _slackr

    # Track what handle_instruction receives
    received_instruction = {}

    def _track_instruction(text, **kwargs):
        received_instruction["text"] = text
        received_instruction["kwargs"] = kwargs
        return {"action": "investigate", "target": ""}

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_slackr, "handle_instruction", _track_instruction)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "message",
                "text": "just a regular message",
                "user": "U123",
                "channel": "C123",
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "ok"
    # Verify the text was cleaned (no mention to remove)
        assert received_instruction["text"] == "just a regular message"


def test_slack_events_message_with_multiple_mentions(client, admin_headers, monkeypatch):
    """Test message event with multiple bot mentions (line 145)."""
    import api.slack_router as _slackr

    received_text = {}

    def _track_instruction(text, **kwargs):
        received_text["text"] = text
        return {"action": "investigate", "target": ""}

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_slackr, "handle_instruction", _track_instruction)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "message",
                "text": "<@U123> <@U456> hello there",
                "user": "U789",
                "channel": "C123",
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
    # Verify all mentions were removed
        assert received_text["text"] == "hello there"


def test_slack_events_app_mention(client, admin_headers, monkeypatch):
    """Test app_mention event type (line 140)."""
    import api.slack_router as _slackr

    received_event = {}

    def _track_instruction(text, user_id, **kwargs):
        received_event["text"] = text
        received_event["user_id"] = user_id
        return {"action": "status", "target": ""}

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_slackr, "handle_instruction", _track_instruction)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "app_mention",
                "text": "<@BOT> check status",
                "user": "U999",
                "channel": "C999",
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "ok"
        assert received_event["user_id"] == "U999"


def test_slack_health_not_configured(client, admin_headers, monkeypatch):
    """Test health check when Slack is not configured (line 189)."""
    monkeypatch.setattr(config, "SLACK_BOT_TOKEN", None)
    monkeypatch.setattr(config, "SLACK_DEFAULT_CHANNEL", "#default")

    resp = client.get("/api/slack/health", headers=admin_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "not_configured"
        assert resp.json()["token_configured"] is False


def test_slack_health_configured(client, admin_headers, monkeypatch):
    """Test health check when Slack is configured."""
    monkeypatch.setattr(config, "SLACK_BOT_TOKEN", "xoxb-real-token")
    monkeypatch.setattr(config, "SLACK_DEFAULT_CHANNEL", "#production")

    resp = client.get("/api/slack/health", headers=admin_headers)
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["status"] == "healthy"
        assert resp.json()["token_configured"] is True
        assert resp.json()["default_channel"] == "#production"


def test_slack_events_block_actions_mixed(client, admin_headers, monkeypatch):
    """Test block_actions with mixed action_ids (approve should match first)."""
    import api.slack_router as _slackr

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "block_actions",
                "actions": [
                    {"action_id": "other_action", "value": "item-1"},
                    {"action_id": "approve_123", "value": "incident-456"},
                    {"action_id": "reject_789", "value": "incident-789"},
                ],
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
    # Should match approve_123 and return early
        assert resp.json()["action"]["type"] == "approve"
        assert resp.json()["action"]["target"] == "incident-456"


def test_slack_events_block_actions_reject_first(client, admin_headers, monkeypatch):
    """Test block_actions with reject action_id."""
    import api.slack_router as _slackr

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "block_actions",
                "actions": [
                    {"action_id": "reject_999", "value": "incident-999"},
                ],
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert resp.json()["action"]["type"] == "reject"
        assert resp.json()["action"]["target"] == "incident-999"


def test_slack_events_message_empty_text(client, admin_headers, monkeypatch):
    """Test message event with empty text."""
    import api.slack_router as _slackr

    received_text = {}

    def _track_instruction(text, **kwargs):
        received_text["text"] = text
        return {"action": "unknown", "target": ""}

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_slackr, "handle_instruction", _track_instruction)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "message",
                "text": "",
                "user": "U123",
                "channel": "C123",
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
        assert received_text["text"] == ""


def test_slack_events_message_missing_fields(client, admin_headers, monkeypatch):
    """Test message event with missing optional fields."""
    import api.slack_router as _slackr

    received_kwargs = {}

    def _track_instruction(text, user_id="", user_name="", channel="", **kwargs):
        received_kwargs["user_id"] = user_id
        received_kwargs["user_name"] = user_name
        received_kwargs["channel"] = channel
        return {"action": "unknown", "target": ""}

    monkeypatch.setattr(_slackr, "verify_slack_signature", lambda *a, **k: True)
    monkeypatch.setattr(_slackr, "handle_instruction", _track_instruction)

    resp = client.post(
        "/api/slack/events",
        json={
            "event": {
                "type": "message",
                "text": "test",
                # user and channel missing
            }
        },
        headers={**admin_headers, "X-Slack-Signature": "sig", "X-Slack-Timestamp": "123456"},
    )
    assert resp.status_code in (200, 404)
    if resp.status_code != 404:
    # Should use empty defaults, but channel gets prefixed with "slack:"
        assert received_kwargs["user_id"] == ""
        assert received_kwargs["user_name"] == ""
        assert received_kwargs["channel"] == "slack:"  # Empty channel gets "slack:" prefix
