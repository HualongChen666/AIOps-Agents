# -*- coding: utf-8 -*-
"""Unit tests for autoheal_router to improve coverage to 90%+."""

import asyncio
import sys
import types
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = [pytest.mark.api]

from fastapi import HTTPException

# Import the module
import api.autoheal_router as autoheal_router

# ---------------------------------------------------------------------------
# Test helper functions
# ---------------------------------------------------------------------------


def test_verify_internal_key_no_key_configured():
    """Test _verify_internal_key when INTERNAL_API_KEY is not configured."""
    with patch.object(autoheal_router, "INTERNAL_API_KEY", None):
        request = MagicMock()
        request.headers = {}
        # Should not raise
        autoheal_router._verify_internal_key(request)


def test_verify_internal_key_missing_header():
    """Test _verify_internal_key when X-Internal-Key header is missing."""
    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        request = MagicMock()
        request.headers = {}
        with pytest.raises(HTTPException) as exc_info:
            autoheal_router._verify_internal_key(request)
        assert exc_info.value.status_code == 403
        assert "Missing X-Internal-Key header" in exc_info.value.detail


def test_verify_internal_key_invalid_key():
    """Test _verify_internal_key with invalid key."""
    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        request = MagicMock()
        request.headers = {"X-Internal-Key": "wrong"}
        with pytest.raises(HTTPException) as exc_info:
            autoheal_router._verify_internal_key(request)
        assert exc_info.value.status_code == 403
        assert "Invalid X-Internal-Key" in exc_info.value.detail


def test_verify_internal_key_valid_key():
    """Test _verify_internal_key with valid key."""
    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        request = MagicMock()
        request.headers = {"X-Internal-Key": "secret"}
        # Should not raise
        autoheal_router._verify_internal_key(request)


def test_enrich_error_msg_empty():
    """Test _enrich_error_msg with empty string."""
    result = autoheal_router._enrich_error_msg("")
    assert result == ""


def test_enrich_error_msg_none():
    """Test _enrich_error_msg with None."""
    result = autoheal_router._enrich_error_msg(None)
    assert result is None


def test_enrich_error_msg_approved_no_script():
    """Test _enrich_error_msg with approved_no_script status."""
    result = autoheal_router._enrich_error_msg("Error: approved_no_script")
    assert "approved_no_script" in result
    assert "提示:此审批为高风险方案" in result


def test_enrich_error_msg_executed_success():
    """Test _enrich_error_msg with executed_success status."""
    result = autoheal_router._enrich_error_msg("Error: executed_success")
    assert "executed_success" in result
    assert "提示:此审批已成功执行" in result


def test_enrich_error_msg_executed_failed():
    """Test _enrich_error_msg with executed_failed status."""
    result = autoheal_router._enrich_error_msg("Error: executed_failed")
    assert "executed_failed" in result
    assert "提示:此审批已执行但失败" in result


def test_enrich_error_msg_execute_error():
    """Test _enrich_error_msg with execute_error status."""
    result = autoheal_router._enrich_error_msg("Error: execute_error")
    assert "execute_error" in result
    assert "提示:此审批执行时发生异常" in result


def test_enrich_error_msg_rejected():
    """Test _enrich_error_msg with rejected status."""
    result = autoheal_router._enrich_error_msg("Error: rejected")
    assert "rejected" in result
    assert "提示:此审批已被驳回" in result


def test_enrich_error_msg_no_match():
    """Test _enrich_error_msg with no matching status."""
    result = autoheal_router._enrich_error_msg("Some other error")
    assert result == "Some other error"


def test_find_alert_by_id_not_found():
    """Test _find_alert_by_id when alert is not found."""
    with patch("core.alert_engine.alert_history", []):
        result = autoheal_router._find_alert_by_id("A1")
        assert result is None


def test_find_alert_by_id_found():
    """Test _find_alert_by_id when alert is found."""
    with patch("core.alert_engine.alert_history", [{"id": "A1", "title": "CPU"}]):
        result = autoheal_router._find_alert_by_id("A1")
        assert result is not None
        assert result["id"] == "A1"


def test_find_alert_by_id_non_dict_item():
    """Test _find_alert_by_id with non-dict items in history."""
    with patch("core.alert_engine.alert_history", ["string", 123, {"id": "A1"}]):
        result = autoheal_router._find_alert_by_id("A1")
        assert result is not None
        assert result["id"] == "A1"


def test_collect_rich_context_for_ai_import_error():
    """Test _collect_rich_context_for_ai when import fails."""
    with patch("api.ai_router._collect_rich_context", side_effect=ImportError("No module")):
        with patch("core.collector.collect_all", return_value=None):
            result = asyncio.run(autoheal_router._collect_rich_context_for_ai())
            # When import fails, rich_context is None, snapshot may be {} or None
            assert result[0] is None


def test_collect_rich_context_for_ai_cancelled_error():
    """Test _collect_rich_context_for_ai with CancelledError."""
    with patch(
        "api.ai_router._collect_rich_context", AsyncMock(side_effect=asyncio.CancelledError())
    ):
        with patch("core.collector.collect_all", return_value=None):
            with pytest.raises(asyncio.CancelledError):
                asyncio.run(autoheal_router._collect_rich_context_for_ai())


def test_collect_rich_context_for_ai_exception():
    """Test _collect_rich_context_for_ai with general exception."""
    with patch("api.ai_router._collect_rich_context", AsyncMock(side_effect=Exception("boom"))):
        with patch("core.collector.collect_all", return_value=None):
            result = asyncio.run(autoheal_router._collect_rich_context_for_ai())
            # When exception occurs, rich_context is None, snapshot may be {} or None
            assert result[0] is None


def test_collect_rich_context_for_ai_success():
    """Test _collect_rich_context_for_ai success case."""
    with patch("api.ai_router._collect_rich_context", AsyncMock(return_value={"processes": []})):
        with patch("core.collector.collect_all", return_value={}):
            result = asyncio.run(autoheal_router._collect_rich_context_for_ai())
            assert result[0] is not None


def test_generate_runbook_cancelled_error():
    """Test _generate_runbook with CancelledError."""
    with patch(
        "api.autoheal_router.generate_repair_runbook",
        AsyncMock(side_effect=asyncio.CancelledError()),
    ):
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(autoheal_router._generate_runbook({}, None, "A1", "127.0.0.1"))


def test_generate_runbook_exception():
    """Test _generate_runbook with general exception."""
    with patch(
        "api.autoheal_router.generate_repair_runbook", AsyncMock(side_effect=Exception("boom"))
    ):
        with pytest.raises(HTTPException) as exc_info:
            asyncio.run(autoheal_router._generate_runbook({}, None, "A1", "127.0.0.1"))
        assert exc_info.value.status_code == 500
        assert "AI 方案生成失败" in exc_info.value.detail


def test_generate_runbook_success():
    """Test _generate_runbook success case."""
    with patch(
        "api.autoheal_router.generate_repair_runbook", AsyncMock(return_value={"success": True})
    ):
        result = asyncio.run(autoheal_router._generate_runbook({}, None, "A1", "127.0.0.1"))
        assert result["success"] is True


def test_validate_runbook_result_empty():
    """Test _validate_runbook_result with empty result."""
    with pytest.raises(HTTPException) as exc_info:
        autoheal_router._validate_runbook_result(None)
    assert exc_info.value.status_code == 500
    assert "Runbook 生成器返回空结果" in exc_info.value.detail


def test_validate_runbook_result_not_dict():
    """Test _validate_runbook_result with non-dict result."""
    with pytest.raises(HTTPException) as exc_info:
        autoheal_router._validate_runbook_result("string")
    assert exc_info.value.status_code == 500
    assert "Runbook 生成器返回空结果" in exc_info.value.detail


def test_validate_runbook_result_success_false():
    """Test _validate_runbook_result with success=False."""
    with pytest.raises(HTTPException) as exc_info:
        autoheal_router._validate_runbook_result({"success": False, "error": "test error"})
    assert exc_info.value.status_code == 400
    assert "test error" in exc_info.value.detail


def test_validate_runbook_result_success_false_with_guard():
    """Test _validate_runbook_result with success=False and guard_results."""
    with pytest.raises(HTTPException) as exc_info:
        autoheal_router._validate_runbook_result(
            {"success": False, "error": "test error", "guard_results": {}}
        )
    assert exc_info.value.status_code == 400
    assert "test error" in exc_info.value.detail
    assert "guard_results" in exc_info.value.detail


def test_validate_runbook_result_success():
    """Test _validate_runbook_result with success=True."""
    result = autoheal_router._validate_runbook_result({"success": True, "proposal": "restart"})
    assert result["success"] is True


# ---------------------------------------------------------------------------
# Test Pydantic models
# ---------------------------------------------------------------------------


def test_approve_request_validator_whitespace():
    """Test ApproveRequest validator with whitespace."""
    from api.autoheal_router import ApproveRequest

    with pytest.raises(ValueError) as exc_info:
        ApproveRequest(alert_id="   ")
    assert "不能为纯空白字符串" in str(exc_info.value)


def test_approve_request_validator_strip():
    """Test ApproveRequest validator strips whitespace."""
    from api.autoheal_router import ApproveRequest

    req = ApproveRequest(alert_id="  A1  ")
    assert req.alert_id == "A1"


def test_reject_request_validator_alert_id_whitespace():
    """Test RejectRequest validator with whitespace alert_id."""
    from api.autoheal_router import RejectRequest

    with pytest.raises(ValueError) as exc_info:
        RejectRequest(alert_id="   ")
    assert "不能为纯空白字符串" in str(exc_info.value)


def test_reject_request_validator_reason_whitespace():
    """Test RejectRequest validator with whitespace reason."""
    from api.autoheal_router import RejectRequest

    req = RejectRequest(alert_id="A1", reason="   ")
    assert req.reason == "用户驳回"


def test_reject_request_validator_reason_long():
    """Test RejectRequest validator truncates long reason."""
    from pydantic import ValidationError

    from api.autoheal_router import RejectRequest

    long_reason = "x" * 600
    # Pydantic will raise ValidationError for strings longer than max_length
    with pytest.raises(ValidationError):
        RejectRequest(alert_id="A1", reason=long_reason)


def test_ai_propose_request_validator_whitespace():
    """Test AIProposeRequest validator with whitespace."""
    from api.autoheal_router import AIProposeRequest

    with pytest.raises(ValueError) as exc_info:
        AIProposeRequest(alert_id="   ")
    assert "不能为纯空白字符串" in str(exc_info.value)


def test_ai_propose_request_validator_strip():
    """Test AIProposeRequest validator strips whitespace."""
    from api.autoheal_router import AIProposeRequest

    req = AIProposeRequest(alert_id="  A1  ")
    assert req.alert_id == "A1"


# ---------------------------------------------------------------------------
# Test validate_ai_propose_request
# ---------------------------------------------------------------------------


def test_validate_ai_propose_request_not_available():
    """Test _validate_ai_propose_request when runbook is not available."""
    with patch.object(autoheal_router, "is_runbook_available", False):
        with patch.object(autoheal_router, "_runbook_import_error", "Import error"):
            request = MagicMock()
            request.client = MagicMock(host="127.0.0.1")
            payload = MagicMock(alert_id="A1")

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(autoheal_router._validate_ai_propose_request(payload, request))
            assert exc_info.value.status_code == 503
            assert "AI 方案生成模块不可用" in exc_info.value.detail


def test_validate_ai_propose_request_alert_not_found():
    """Test _validate_ai_propose_request when alert is not found."""
    with patch.object(autoheal_router, "is_runbook_available", True):
        with patch("core.alert_engine.alert_history", []):
            request = MagicMock()
            request.client = MagicMock(host="127.0.0.1")
            payload = MagicMock(alert_id="MISSING")

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(autoheal_router._validate_ai_propose_request(payload, request))
            assert exc_info.value.status_code == 404
            assert "未找到告警" in exc_info.value.detail


def test_validate_ai_propose_request_success():
    """Test _validate_ai_propose_request success case."""
    with patch.object(autoheal_router, "is_runbook_available", True):
        with patch("core.alert_engine.alert_history", [{"id": "A1", "title": "CPU"}]):
            request = MagicMock()
            request.client = MagicMock(host="127.0.0.1")
            payload = MagicMock(alert_id="A1")

            alert, ip = asyncio.run(autoheal_router._validate_ai_propose_request(payload, request))
            assert alert["id"] == "A1"
            assert ip == "127.0.0.1"


def test_validate_ai_propose_request_no_client():
    """Test _validate_ai_propose_request when request.client is None."""
    with patch.object(autoheal_router, "is_runbook_available", True):
        with patch("core.alert_engine.alert_history", [{"id": "A1", "title": "CPU"}]):
            request = MagicMock()
            request.client = None
            payload = MagicMock(alert_id="A1")

            alert, ip = asyncio.run(autoheal_router._validate_ai_propose_request(payload, request))
            assert alert["id"] == "A1"
            assert ip == "unknown"


# ---------------------------------------------------------------------------
# Test execute_ai_propose_workflow
# ---------------------------------------------------------------------------


def test_execute_ai_propose_workflow_cancelled():
    """Test _execute_ai_propose_workflow with CancelledError."""
    with patch(
        "api.autoheal_router._collect_rich_context_for_ai",
        AsyncMock(side_effect=asyncio.CancelledError()),
    ):
        with pytest.raises(asyncio.CancelledError):
            asyncio.run(autoheal_router._execute_ai_propose_workflow({}, "A1", "127.0.0.1"))


def test_execute_ai_propose_workflow_success():
    """Test _execute_ai_propose_workflow success case."""
    with patch(
        "api.autoheal_router._collect_rich_context_for_ai", AsyncMock(return_value=({}, {}))
    ):
        with patch(
            "api.autoheal_router._generate_runbook", AsyncMock(return_value={"success": True})
        ):
            with patch("api.autoheal_router.get_pending_approvals", AsyncMock(return_value=[])):
                result = asyncio.run(
                    autoheal_router._execute_ai_propose_workflow({}, "A1", "127.0.0.1")
                )
                assert result["success"] is True


def test_execute_ai_propose_workflow_pending_count_error():
    """Test _execute_ai_propose_workflow when pending_count calculation fails."""
    with patch(
        "api.autoheal_router._collect_rich_context_for_ai", AsyncMock(return_value=({}, {}))
    ):
        with patch(
            "api.autoheal_router._generate_runbook", AsyncMock(return_value={"success": True})
        ):
            with patch(
                "api.autoheal_router.get_pending_approvals",
                AsyncMock(side_effect=Exception("boom")),
            ):
                result = asyncio.run(
                    autoheal_router._execute_ai_propose_workflow({}, "A1", "127.0.0.1")
                )
                assert result["success"] is True


# ---------------------------------------------------------------------------
# Test takeover endpoint edge cases
# ---------------------------------------------------------------------------


def test_takeover_empty_alert_id():
    """Test takeover with empty alert_id."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(autoheal_router.takeover("", request))
    assert exc_info.value.status_code == 422
    assert "不能为空" in exc_info.value.detail


def test_takeover_whitespace_alert_id():
    """Test takeover with whitespace alert_id."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(autoheal_router.takeover("   ", request))
    assert exc_info.value.status_code == 422
    assert "不能为空" in exc_info.value.detail


def test_takeover_non_string_alert_id():
    """Test takeover with non-string alert_id."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(autoheal_router.takeover(123, request))
    assert exc_info.value.status_code == 422
    assert "不能为空" in exc_info.value.detail


def test_takeover_no_client():
    """Test takeover when request.client is None."""
    request = MagicMock()
    request.client = None

    with patch("core.auto_heal.reject_repair", AsyncMock(return_value={"success": True})):
        result = asyncio.run(autoheal_router.takeover("A1", request))
        assert result["success"] is True
        # The message includes the operator IP which is "unknown" when client is None
        assert result["message"] == "Agent 已接管，审批已取消"


def test_takeover_reject_exception():
    """Test takeover when reject_repair raises exception."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")

    with patch("core.auto_heal.reject_repair", AsyncMock(side_effect=Exception("boom"))):
        result = asyncio.run(autoheal_router.takeover("A1", request))
        # Should still return success even if reject fails
        assert result["success"] is True


# ---------------------------------------------------------------------------
# Test approve endpoint edge cases
# ---------------------------------------------------------------------------


def test_approve_cancelled_error():
    """Test approve with CancelledError."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch(
            "gateway.services_client.approve_and_execute",
            AsyncMock(side_effect=asyncio.CancelledError()),
        ):
            with patch(
                "api.autoheal_router.async_update_approval_status_by_alert",
                AsyncMock(return_value=None),
            ):
                with patch("core.alert_engine.alert_history", [{"id": "A1"}]):
                    with pytest.raises(asyncio.CancelledError):
                        asyncio.run(autoheal_router.approve("A1", request))


def test_approve_exception():
    """Test approve with general exception."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch(
            "gateway.services_client.approve_and_execute", AsyncMock(side_effect=Exception("boom"))
        ):
            with patch(
                "api.autoheal_router.async_update_approval_status_by_alert",
                AsyncMock(return_value=None),
            ):
                with patch("core.alert_engine.alert_history", [{"id": "A1"}]):
                    result = asyncio.run(autoheal_router.approve("A1", request))
                    assert result["success"] is False


def test_approve_none_result():
    """Test approve when approve_and_execute returns None."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch("gateway.services_client.approve_and_execute", AsyncMock(return_value=None)):
            with patch(
                "api.autoheal_router.async_update_approval_status_by_alert",
                AsyncMock(return_value=None),
            ):
                with patch("core.alert_engine.alert_history", [{"id": "A1"}]):
                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(autoheal_router.approve("A1", request))
                    assert exc_info.value.status_code == 500
                    assert "修复引擎未返回结果" in exc_info.value.detail


def test_approve_alert_not_found():
    """Test approve when alert is not found (fallback to minimal alert)."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch(
            "gateway.services_client.approve_and_execute", AsyncMock(return_value={"success": True})
        ):
            with patch(
                "api.autoheal_router.async_update_approval_status_by_alert",
                AsyncMock(return_value=None),
            ):
                with patch("core.alert_engine.alert_history", []):
                    result = asyncio.run(autoheal_router.approve("A1", request))
                    assert result["success"] is True


def test_approve_no_client():
    """Test approve when request.client is None."""
    request = MagicMock()
    request.client = None
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch(
            "gateway.services_client.approve_and_execute", AsyncMock(return_value={"success": True})
        ):
            with patch(
                "api.autoheal_router.async_update_approval_status_by_alert",
                AsyncMock(return_value=None),
            ):
                with patch("core.alert_engine.alert_history", [{"id": "A1"}]):
                    result = asyncio.run(autoheal_router.approve("A1", request))
                    assert result["success"] is True


def test_approve_update_status_exception():
    """Test approve when status update fails (should continue)."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch(
            "gateway.services_client.approve_and_execute", AsyncMock(return_value={"success": True})
        ):
            with patch(
                "api.autoheal_router.async_update_approval_status_by_alert",
                AsyncMock(side_effect=Exception("boom")),
            ):
                with patch("core.alert_engine.alert_history", [{"id": "A1"}]):
                    result = asyncio.run(autoheal_router.approve("A1", request))
                    assert result["success"] is True


# ---------------------------------------------------------------------------
# Test reject endpoint edge cases
# ---------------------------------------------------------------------------


def test_reject_cancelled_error():
    """Test reject with CancelledError."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch("core.auto_heal.reject_repair", AsyncMock(side_effect=asyncio.CancelledError())):
            payload = MagicMock(alert_id="A1", reason="test")
            with pytest.raises(asyncio.CancelledError):
                asyncio.run(autoheal_router.reject(payload, request))


def test_reject_exception():
    """Test reject with general exception."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch("core.auto_heal.reject_repair", AsyncMock(side_effect=Exception("boom"))):
            payload = MagicMock(alert_id="A1", reason="test")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(autoheal_router.reject(payload, request))
            assert exc_info.value.status_code == 500


def test_reject_none_result():
    """Test reject when reject_repair returns None."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch("core.auto_heal.reject_repair", AsyncMock(return_value=None)):
            payload = MagicMock(alert_id="A1", reason="test")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(autoheal_router.reject(payload, request))
            assert exc_info.value.status_code == 500
            assert "驳回引擎未返回结果" in exc_info.value.detail


def test_reject_no_client():
    """Test reject when request.client is None."""
    request = MagicMock()
    request.client = None
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch("core.auto_heal.reject_repair", AsyncMock(return_value={"success": True})):
            with patch("api.autoheal_router.get_pending_approvals", AsyncMock(return_value=[])):
                payload = MagicMock(alert_id="A1", reason="test")
                result = asyncio.run(autoheal_router.reject(payload, request))
                assert result["success"] is True


def test_reject_pending_count_error():
    """Test reject when pending_count calculation fails."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch("core.auto_heal.reject_repair", AsyncMock(return_value={"success": True})):
            with patch(
                "api.autoheal_router.get_pending_approvals",
                AsyncMock(side_effect=Exception("boom")),
            ):
                payload = MagicMock(alert_id="A1", reason="test")
                result = asyncio.run(autoheal_router.reject(payload, request))
                assert result["success"] is True
                # pending_count should not be in result when calculation fails


def test_reject_sync_function():
    """Test reject when reject_repair is not async."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch("core.auto_heal.reject_repair", MagicMock(return_value={"success": True})):
            with patch("asyncio.iscoroutinefunction", return_value=False):
                with patch("api.autoheal_router.get_pending_approvals", MagicMock(return_value=[])):
                    payload = MagicMock(alert_id="A1", reason="test")
                    result = asyncio.run(autoheal_router.reject(payload, request))
                    assert result["success"] is True


# ---------------------------------------------------------------------------
# Test list_pending edge cases
# ---------------------------------------------------------------------------


def test_list_pending_sync_function():
    """Test list_pending when get_pending_approvals is not async."""
    request = MagicMock()
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch("core.auto_heal.get_pending_approvals", MagicMock(return_value=[{"id": "A1"}])):
            with patch("asyncio.iscoroutinefunction", return_value=False):
                with patch.object(
                    autoheal_router, "get_pending_approvals", MagicMock(return_value=[{"id": "A1"}])
                ):
                    result = asyncio.run(autoheal_router.list_pending(request))
                    assert result["total"] == 1


def test_list_pending_no_client():
    """Test list_pending when request.client is None."""
    request = MagicMock()
    request.client = None
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch.object(
            autoheal_router, "get_pending_approvals", AsyncMock(return_value=[{"id": "A1"}])
        ):
            result = asyncio.run(autoheal_router.list_pending(request))
        assert result["total"] == 1


# ---------------------------------------------------------------------------
# Test status hint map coverage
# ---------------------------------------------------------------------------


def test_status_hint_map_all_keys():
    """Test that all status hint map keys are covered."""
    from api.autoheal_router import _STATUS_HINT_MAP

    assert "approved_no_script" in _STATUS_HINT_MAP
    assert "executed_success" in _STATUS_HINT_MAP
    assert "executed_failed" in _STATUS_HINT_MAP
    assert "execute_error" in _STATUS_HINT_MAP
    assert "rejected" in _STATUS_HINT_MAP


def test_approve_business_error_with_enrichment():
    """Test approve with business error that gets enriched."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch(
            "gateway.services_client.approve_and_execute",
            AsyncMock(return_value={"success": False, "error": "executed_failed"}),
        ):
            with patch(
                "api.autoheal_router.async_update_approval_status_by_alert",
                AsyncMock(return_value=None),
            ):
                with patch("core.alert_engine.alert_history", [{"id": "A1"}]):
                    with pytest.raises(HTTPException) as exc_info:
                        asyncio.run(autoheal_router.approve("A1", request))
                    assert exc_info.value.status_code == 400
                    assert "executed_failed" in exc_info.value.detail
                    assert "提示" in exc_info.value.detail


def test_reject_business_error():
    """Test reject with business error."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch(
            "core.auto_heal.reject_repair",
            AsyncMock(return_value={"success": False, "error": "test error"}),
        ):
            payload = MagicMock(alert_id="A1", reason="test")
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(autoheal_router.reject(payload, request))
            assert exc_info.value.status_code == 400
            assert "test error" in exc_info.value.detail


def test_takeover_sync_reject():
    """Test takeover with synchronous reject_repair."""
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")

    with patch("core.auto_heal.reject_repair", MagicMock(return_value={"success": True})):
        with patch("asyncio.iscoroutinefunction", return_value=False):
            result = asyncio.run(autoheal_router.takeover("A1", request))
            assert result["success"] is True


def test_ai_propose_unavailable():
    """Test ai_propose_repair when runbook is not available."""
    with patch.object(autoheal_router, "is_runbook_available", False):
        with patch.object(autoheal_router, "_runbook_import_error", "Import error"):
            request = MagicMock()
            request.client = MagicMock(host="127.0.0.1")
            payload = MagicMock(alert_id="A1")

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(autoheal_router.ai_propose_repair(payload, request))
            assert exc_info.value.status_code == 503
            assert "AI 方案生成模块不可用" in exc_info.value.detail


def test_async_update_approval_status_by_alert_none():
    """Test when async_update_approval_status_by_alert is None."""
    # This tests the import error case at module level (lines 26-28)
    # We can't easily test the actual import error, but we can test the None case
    request = MagicMock()
    request.client = MagicMock(host="127.0.0.1")
    request.headers = {"X-Internal-Key": "secret"}

    with patch.object(autoheal_router, "INTERNAL_API_KEY", "secret"):
        with patch("api.autoheal_router.async_update_approval_status_by_alert", None):
            with patch(
                "gateway.services_client.approve_and_execute",
                AsyncMock(return_value={"success": True}),
            ):
                with patch("core.alert_engine.alert_history", [{"id": "A1"}]):
                    result = asyncio.run(autoheal_router.approve("A1", request))
                    assert result["success"] is True
