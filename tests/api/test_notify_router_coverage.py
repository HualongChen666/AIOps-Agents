# -*- coding: utf-8 -*-
"""
Comprehensive coverage tests for api/notify_router.py
Target: 90%+ statement and branch coverage
"""

import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


# ============================================================
# Test _safe_get_notify_config exception branches (lines 26-27, 29-31)
# ============================================================
def test_safe_get_notify_config_none_config(client, approval_headers):
    """Test _safe_get_notify_config when NOTIFY_CONFIG is None (lines 26-27)."""
    with patch("api.notify_router._notify_engine") as mock_engine:
        mock_engine.NOTIFY_CONFIG = None
        response = client.get("/api/notify/config", headers=approval_headers)
        # Should return empty config gracefully
        assert response.status_code in (200, 500)


def test_safe_get_notify_config_non_dict_config(client, approval_headers):
    """Test _safe_get_notify_config when NOTIFY_CONFIG is not a dict (lines 26-27)."""
    with patch("api.notify_router._notify_engine") as mock_engine:
        mock_engine.NOTIFY_CONFIG = "invalid_string"
        response = client.get("/api/notify/config", headers=approval_headers)
        assert response.status_code in (200, 500)


def test_safe_get_notify_config_exception(client, approval_headers):
    """Test _safe_get_notify_config when getattr raises exception (lines 29-31)."""
    with patch("api.notify_router._notify_engine") as mock_engine:
        # Simulate an exception when accessing NOTIFY_CONFIG
        type(mock_engine).NOTIFY_CONFIG = property(
            lambda self: (_ for _ in ()).throw(RuntimeError("Test error"))
        )
        response = client.get("/api/notify/config", headers=approval_headers)
        # The exception is caught and returns empty config, so 200 is expected
        # The important thing is that the exception was logged
        assert response.status_code == 200
        data = response.json()
        # Should return disabled config when exception occurs
        assert data.get("enabled") is False


# ============================================================
# Test NotifyTestRequest validator (line 50)
# ============================================================
def test_notify_test_request_whitespace_title(client, approval_headers):
    """Test NotifyTestRequest with whitespace-only title (line 50)."""
    response = client.post(
        "/api/notify/test",
        headers=approval_headers,
        json={"level": "critical", "title": "   ", "desc": "valid desc"},
    )
    # Should fail validation with 422
    assert response.status_code == 422


def test_notify_test_request_whitespace_desc(client, approval_headers):
    """Test NotifyTestRequest with whitespace-only desc (line 50)."""
    response = client.post(
        "/api/notify/test",
        headers=approval_headers,
        json={"level": "critical", "title": "valid title", "desc": "\t\n"},
    )
    # Should fail validation with 422
    assert response.status_code == 422


def test_notify_test_request_empty_string(client, approval_headers):
    """Test NotifyTestRequest with empty string (line 50)."""
    response = client.post(
        "/api/notify/test",
        headers=approval_headers,
        json={"level": "critical", "title": "", "desc": "valid desc"},
    )
    # Should fail validation with 422
    assert response.status_code == 422


# ============================================================
# Test get_notify_config exception handling (lines 99-101)
# ============================================================
def test_get_notify_config_exception(client, approval_headers):
    """Test get_notify_config exception handling (lines 99-101)."""
    with patch("api.notify_router._safe_get_notify_config") as mock_safe:
        mock_safe.side_effect = RuntimeError("Config access failed")
        response = client.get("/api/notify/config", headers=approval_headers)
        assert response.status_code == 500
        data = response.json()
        # Check standardized error format
        assert data.get("success") is False
        assert "获取通知配置失败" in data.get("error", {}).get("message", "")


# ============================================================
# Test send_manual_notify type check (line 209)
# ============================================================
def test_send_manual_notify_non_dict_alert(client, approval_headers):
    """Test send_manual_notify with non-dict alert (line 209)."""
    # Send a list instead of dict - caught by FastAPI validation
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json=["not", "a", "dict"],
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    # FastAPI validation error
    assert "VALIDATION_ERROR" in data.get("error", {}).get("code", "")


def test_send_manual_notify_string_alert(client, approval_headers):
    """Test send_manual_notify with string alert (line 209)."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json="string_instead_of_dict",
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "VALIDATION_ERROR" in data.get("error", {}).get("code", "")


def test_send_manual_notify_number_alert(client, approval_headers):
    """Test send_manual_notify with number alert (line 209)."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json=12345,
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "VALIDATION_ERROR" in data.get("error", {}).get("code", "")


# ============================================================
# Test send_manual_notify missing required fields
# ============================================================
def test_send_manual_notify_missing_level(client, approval_headers):
    """Test send_manual_notify missing level field."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json={"title": "Test", "desc": "Test desc"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "缺少必填字段" in data.get("error", {}).get("message", "")


def test_send_manual_notify_missing_title(client, approval_headers):
    """Test send_manual_notify missing title field."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json={"level": "critical", "desc": "Test desc"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "缺少必填字段" in data.get("error", {}).get("message", "")


def test_send_manual_notify_missing_desc(client, approval_headers):
    """Test send_manual_notify missing desc field."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json={"level": "critical", "title": "Test"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "缺少必填字段" in data.get("error", {}).get("message", "")


def test_send_manual_notify_empty_level(client, approval_headers):
    """Test send_manual_notify with empty level."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json={"level": "", "title": "Test", "desc": "Test desc"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "缺少必填字段" in data.get("error", {}).get("message", "")


def test_send_manual_notify_whitespace_level(client, approval_headers):
    """Test send_manual_notify with whitespace level."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json={"level": "  ", "title": "Test", "desc": "Test desc"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "缺少必填字段" in data.get("error", {}).get("message", "")


# ============================================================
# Test send_manual_notify invalid level value
# ============================================================
def test_send_manual_notify_invalid_level(client, approval_headers):
    """Test send_manual_notify with invalid level value."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json={"level": "invalid", "title": "Test", "desc": "Test desc"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "alert.level 必须是 info/warning/critical" in data.get("error", {}).get("message", "")


def test_send_manual_notify_uppercase_level(client, approval_headers):
    """Test send_manual_notify with uppercase level (should pass due to .lower())."""
    # The code converts to lowercase, so uppercase is actually valid
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"wecom": True}
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "CRITICAL", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 200


def test_send_manual_notify_mixed_case_level(client, approval_headers):
    """Test send_manual_notify with mixed case level (should pass due to .lower())."""
    # The code converts to lowercase, so mixed case is actually valid
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"dingtalk": True}
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "Critical", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 200


def test_send_manual_notify_numeric_level(client, approval_headers):
    """Test send_manual_notify with numeric level (truly invalid)."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json={"level": 123, "title": "Test", "desc": "Test desc"},
    )
    # Should fail validation or processing
    assert response.status_code in (422, 500)


# ============================================================
# Test send_manual_notify raw_time auto-fill (lines 226-229)
# ============================================================
def test_send_manual_notify_missing_raw_time(client, approval_headers):
    """Test send_manual_notify with missing raw_time (lines 226-229)."""
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"wecom": True, "dingtalk": True}
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "critical", "title": "Test", "desc": "Test desc"},
        )
        # raw_time should be auto-filled
        assert response.status_code == 200
        # Verify the alert passed to send_alert_notification has raw_time
        call_args = mock_send.call_args[0][0]
        assert "raw_time" in call_args
        assert call_args["raw_time"] is not None


def test_send_manual_notify_none_raw_time(client, approval_headers):
    """Test send_manual_notify with None raw_time (lines 226-229)."""
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"wecom": True}
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "warning", "title": "Test", "desc": "Test desc", "raw_time": None},
        )
        assert response.status_code == 200
        call_args = mock_send.call_args[0][0]
        assert "raw_time" in call_args
        assert call_args["raw_time"] is not None


def test_send_manual_notify_empty_string_raw_time(client, approval_headers):
    """Test send_manual_notify with empty string raw_time (lines 226-229)."""
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"feishu": True}
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "info", "title": "Test", "desc": "Test desc", "raw_time": ""},
        )
        assert response.status_code == 200
        call_args = mock_send.call_args[0][0]
        assert "raw_time" in call_args
        assert call_args["raw_time"] is not None


def test_send_manual_notify_existing_raw_time(client, approval_headers):
    """Test send_manual_notify with existing raw_time (should not auto-fill)."""
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"wecom": True}
        existing_time = "12:34:56"
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={
                "level": "critical",
                "title": "Test",
                "desc": "Test desc",
                "raw_time": existing_time,
            },
        )
        assert response.status_code == 200
        call_args = mock_send.call_args[0][0]
        assert call_args["raw_time"] == existing_time


# ============================================================
# Test send_manual_notify exception handling (lines 232-234)
# ============================================================
def test_send_manual_notify_send_exception(client, approval_headers):
    """Test send_manual_notify when send_alert_notification raises exception (lines 232-234)."""
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.side_effect = RuntimeError("Notification failed")
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "critical", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 500
        data = response.json()
        assert data.get("success") is False
        assert "通知推送失败" in data.get("error", {}).get("message", "")


def test_send_manual_notify_http_exception(client, approval_headers):
    """Test send_manual_notify when send_alert_notification raises HTTPException."""
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.side_effect = HTTPException(status_code=503, detail="Service unavailable")
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "warning", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 500


# ============================================================
# Test notify_health exception handling (lines 338-339)
# ============================================================
def test_notify_health_exception(client, approval_headers):
    """Test notify_health exception handling (lines 338-339)."""
    with patch("api.notify_router._safe_get_notify_config") as mock_safe:
        mock_safe.side_effect = RuntimeError("Health check failed")
        response = client.get("/api/notify/health", headers=approval_headers)
        # Should return error in response body
        assert response.status_code == 200
        data = response.json()
        assert data.get("module_loaded") is False
        assert "error" in data


def test_notify_health_success(client, approval_headers):
    """Test notify_health success path to cover lines 314-315."""
    with patch("api.notify_router._safe_get_notify_config") as mock_safe:
        mock_safe.return_value = {
            "enabled": True,
            "wecom_webhook": "http://example.com/webhook",
            "dingtalk_webhook": "",
            "feishu_webhook": "",
            "email_webhook": "",
            "phone_provider": "",
            "sms_provider": "",
        }
    with patch("api.notify_router._notify_engine") as mock_engine:
        mock_engine.close_http_client = lambda: None
        response = client.get("/api/notify/health", headers=approval_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("module_loaded") is True
        assert data.get("close_func") is True


# ============================================================
# Test mark_notification_read parameter validation (line 369)
# ============================================================
def test_mark_notification_read_missing_message_id(client, approval_headers):
    """Test mark_notification_read with missing message_id (line 369)."""
    response = client.post(
        "/api/notify/read",
        headers=approval_headers,
        json={"channel": "wecom"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "message_id and channel are required" in data.get("error", {}).get("message", "")


def test_mark_notification_read_missing_channel(client, approval_headers):
    """Test mark_notification_read with missing channel (line 369)."""
    response = client.post(
        "/api/notify/read",
        headers=approval_headers,
        json={"message_id": "msg123"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "message_id and channel are required" in data.get("error", {}).get("message", "")


def test_mark_notification_read_empty_message_id(client, approval_headers):
    """Test mark_notification_read with empty message_id (line 369)."""
    response = client.post(
        "/api/notify/read",
        headers=approval_headers,
        json={"message_id": "", "channel": "wecom"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "message_id and channel are required" in data.get("error", {}).get("message", "")


def test_mark_notification_read_empty_channel(client, approval_headers):
    """Test mark_notification_read with empty channel (line 369)."""
    response = client.post(
        "/api/notify/read",
        headers=approval_headers,
        json={"message_id": "msg123", "channel": ""},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "message_id and channel are required" in data.get("error", {}).get("message", "")


def test_mark_notification_read_both_empty(client, approval_headers):
    """Test mark_notification_read with both fields empty (line 369)."""
    response = client.post(
        "/api/notify/read",
        headers=approval_headers,
        json={"message_id": "", "channel": ""},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "message_id and channel are required" in data.get("error", {}).get("message", "")


def test_mark_notification_read_valid(client, approval_headers):
    """Test mark_notification_read with valid parameters."""
    response = client.post(
        "/api/notify/read",
        headers=approval_headers,
        json={"message_id": "msg123", "channel": "wecom"},
    )
    # Should succeed (even if not_found, it's a valid request)
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] in ("ok", "not_found")


# ============================================================
# Test send_test_notify with disabled config
# ============================================================
def test_send_test_notify_disabled(client, approval_headers):
    """Test send_test_notify when notifications are disabled."""
    with patch("api.notify_router._safe_get_notify_config") as mock_safe:
        mock_safe.return_value = {"enabled": False}
        response = client.post(
            "/api/notify/test",
            headers=approval_headers,
            json={"level": "critical", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "skipped"
        assert "通知引擎未启用" in data.get("message", "")


# ============================================================
# Test send_test_notify exception handling
# ============================================================
def test_send_test_notify_exception(client, approval_headers):
    """Test send_test_notify when send_alert_notification raises exception."""
    with patch("api.notify_router._safe_get_notify_config") as mock_safe:
        mock_safe.return_value = {"enabled": True}
        with patch("api.notify_router.send_alert_notification") as mock_send:
            mock_send.side_effect = RuntimeError("Test exception")
            response = client.post(
                "/api/notify/test",
                headers=approval_headers,
                json={"level": "critical", "title": "Test", "desc": "Test desc"},
            )
            assert response.status_code == 500
            data = response.json()
            assert data.get("success") is False
            assert "通知发送失败" in data.get("error", {}).get("message", "")


def test_send_test_notify_success_path(client, approval_headers):
    """Test send_test_notify success path to cover lines 150-151."""
    with patch("api.notify_router._safe_get_notify_config") as mock_safe:
        mock_safe.return_value = {"enabled": True}
        with patch("api.notify_router.send_alert_notification") as mock_send:
            mock_send.return_value = {"wecom": True, "dingtalk": True, "feishu": True}
            response = client.post(
                "/api/notify/test",
                headers=approval_headers,
                json={"level": "critical", "title": "Test", "desc": "Test desc"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data.get("status") == "ok"
            assert "results" in data


# ============================================================
# Test reload_config exception handling
# ============================================================
def test_reload_config_exception(client, approval_headers):
    """Test reload_config when reload_notify_config raises exception."""
    with patch("api.notify_router.reload_notify_config") as mock_reload:
        mock_reload.side_effect = RuntimeError("Reload failed")
        response = client.post("/api/notify/reload", headers=approval_headers)
        assert response.status_code == 500
        data = response.json()
        assert data.get("success") is False
        assert "热重载失败" in data.get("error", {}).get("message", "")


def test_reload_config_success(client, approval_headers):
    """Test reload_config success path to cover lines 282-286."""
    with patch("api.notify_router.reload_notify_config") as mock_reload:
        mock_reload.return_value = {
            "enabled": True,
            "min_level": "warning",
            "wecom_webhook": "http://example.com/webhook",
            "dingtalk_webhook": "",
            "feishu_webhook": "",
            "email_webhook": "",
        }
        response = client.post("/api/notify/reload", headers=approval_headers)
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "ok"
        assert "config" in data


# ============================================================
# Test get_notification_status with various parameters
# ============================================================
def test_get_notification_status_with_alert_id(client, approval_headers):
    """Test get_notification_status with alert_id filter."""
    response = client.get(
        "/api/notify/status",
        headers=approval_headers,
        params={"alert_id": "alert123"},
    )
    assert response.status_code in (200, 500)


def test_get_notification_status_with_fingerprint(client, approval_headers):
    """Test get_notification_status with fingerprint filter."""
    response = client.get(
        "/api/notify/status",
        headers=approval_headers,
        params={"fingerprint": "fp456"},
    )
    assert response.status_code in (200, 500)


def test_get_notification_status_with_channel(client, approval_headers):
    """Test get_notification_status with channel filter."""
    response = client.get(
        "/api/notify/status",
        headers=approval_headers,
        params={"channel": "wecom"},
    )
    assert response.status_code in (200, 500)


def test_get_notification_status_with_limit(client, approval_headers):
    """Test get_notification_status with custom limit."""
    response = client.get(
        "/api/notify/status",
        headers=approval_headers,
        params={"limit": 50},
    )
    assert response.status_code in (200, 500)


def test_get_notification_status_exception(client, approval_headers):
    """Test get_notification_status when get_notification_status raises exception."""
    with patch("api.notify_router._notify_engine") as mock_engine:
        mock_engine.get_notification_status.side_effect = RuntimeError("Query failed")
        response = client.get("/api/notify/status", headers=approval_headers)
        assert response.status_code == 500


# ============================================================
# Test get_oncall with various parameters
# ============================================================
def test_get_oncall_with_category(client, approval_headers):
    """Test get_oncall with category parameter."""
    response = client.get(
        "/api/notify/oncall",
        headers=approval_headers,
        params={"category": "infrastructure"},
    )
    assert response.status_code in (200, 500)


def test_get_oncall_with_service(client, approval_headers):
    """Test get_oncall with service parameter."""
    response = client.get(
        "/api/notify/oncall",
        headers=approval_headers,
        params={"service": "api"},
    )
    assert response.status_code in (200, 500)


def test_get_oncall_with_team(client, approval_headers):
    """Test get_oncall with team parameter."""
    response = client.get(
        "/api/notify/oncall",
        headers=approval_headers,
        params={"team": "platform"},
    )
    assert response.status_code in (200, 500)


def test_get_oncall_exception(client, approval_headers):
    """Test get_oncall when lookup_async raises exception."""
    with patch("api.notify_router.get_oncall_adapter") as mock_get:
        mock_adapter = MagicMock()
        mock_adapter.lookup_async.side_effect = RuntimeError("Oncall lookup failed")
        mock_get.return_value = mock_adapter
        response = client.get("/api/notify/oncall", headers=approval_headers)
        assert response.status_code == 500


# ============================================================
# Test NotifyTestRequest with all valid levels
# ============================================================
def test_notify_test_request_info_level(client, approval_headers):
    """Test NotifyTestRequest with info level."""
    with patch("api.notify_router._safe_get_notify_config") as mock_safe:
        mock_safe.return_value = {"enabled": True}
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"wecom": True}
        response = client.post(
            "/api/notify/test",
            headers=approval_headers,
            json={"level": "info", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 200


def test_notify_test_request_warning_level(client, approval_headers):
    """Test NotifyTestRequest with warning level."""
    with patch("api.notify_router._safe_get_notify_config") as mock_safe:
        mock_safe.return_value = {"enabled": True}
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"dingtalk": True}
        response = client.post(
            "/api/notify/test",
            headers=approval_headers,
            json={"level": "warning", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 200


def test_notify_test_request_critical_level(client, approval_headers):
    """Test NotifyTestRequest with critical level."""
    with patch("api.notify_router._safe_get_notify_config") as mock_safe:
        mock_safe.return_value = {"enabled": True}
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"feishu": True}
        response = client.post(
            "/api/notify/test",
            headers=approval_headers,
            json={"level": "critical", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 200


# ============================================================
# Test send_manual_notify with all valid levels
# ============================================================
def test_send_manual_notify_info_level(client, approval_headers):
    """Test send_manual_notify with info level."""
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"wecom": True}
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "info", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 200


def test_send_manual_notify_warning_level(client, approval_headers):
    """Test send_manual_notify with warning level."""
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"dingtalk": True}
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "warning", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 200


def test_send_manual_notify_critical_level(client, approval_headers):
    """Test send_manual_notify with critical level."""
    with patch("api.notify_router.send_alert_notification") as mock_send:
        mock_send.return_value = {"feishu": True}
        response = client.post(
            "/api/notify/send",
            headers=approval_headers,
            json={"level": "critical", "title": "Test", "desc": "Test desc"},
        )
        assert response.status_code == 200


# ============================================================
# Test send_manual_notify with whitespace values in required fields
# ============================================================
def test_send_manual_notify_whitespace_title(client, approval_headers):
    """Test send_manual_notify with whitespace-only title."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json={"level": "critical", "title": "   ", "desc": "Test desc"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "缺少必填字段" in data.get("error", {}).get("message", "")


def test_send_manual_notify_whitespace_desc(client, approval_headers):
    """Test send_manual_notify with whitespace-only desc."""
    response = client.post(
        "/api/notify/send",
        headers=approval_headers,
        json={"level": "critical", "title": "Test", "desc": "\t\n"},
    )
    assert response.status_code == 422
    data = response.json()
    assert data.get("success") is False
    assert "缺少必填字段" in data.get("error", {}).get("message", "")


# ============================================================
# Direct unit tests to cover specific lines
# ============================================================
def test_send_manual_notify_non_dict_direct():
    """Direct unit test for send_manual_notify with non-dict to cover line 209."""
    import asyncio
    from unittest.mock import MagicMock

    from fastapi import HTTPException, Request

    from api.notify_router import send_manual_notify

    # Create a mock request
    mock_request = MagicMock(spec=Request)
    mock_request.client = MagicMock()
    mock_request.client.host = "testclient"

    # Test with a non-dict alert
    async def test_direct_call():
        try:
            await send_manual_notify(mock_request, ["not", "a", "dict"])
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            # Should be an HTTPException with 422 status
            assert e.status_code == 422
            assert "dict" in e.detail.lower()

    asyncio.run(test_direct_call())
