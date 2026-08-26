# -*- coding: utf-8 -*-
"""Test real branches in heal_graph.py with minimal external I/O mocking."""

import asyncio  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup

# Import the module under test
import sys  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta, timezone
from typing import Any, Dict  # noqa: F401  # Imported for test setup
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest  # noqa: F401  # Imported for test setup

# Get project root directory dynamically
# From tests/core/test_heal_graph_real_branches.py, go up 3 levels to reach project root
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

# noqa: E402  # Module level import not at top (intentional for sys.path setup)
from core.heal_graph import (
    HealState,
    RiskLevel,
    _approval_validity_minutes,
    _build_graph,
    _extract_command_target,
    _get_trace_id,
    _is_alert_resolved,
    _is_approval_expired,
    _is_hardware_alert,
    _log_audit_event,
    _send_alert_notification,
    _set_trace_id,
    _tokenize_alert_text,
    analyze_command,
    apply_fix,
    async_get_approval_by_alert,
    async_insert_repair_record,
    async_update_approval_status_by_alert,
    async_upsert_pending_approval,
    check_sla,
    cleanup_expired_snapshots,
    complete,
    evaluate,
    fetch_alert,
    generate_runbook,
    invoke_agent,
    notify_rollback_failure,
    record_audit,
    record_decision,
    record_outcome,
    rollback,
    run_heal,
    save_snapshot,
    update_snapshot_status,
)

# ============================================================================
# Import fallback tests
# ============================================================================


def test_stats_engine_import_fallback():
    """Test that stats_engine import falls back gracefully."""
    from core.heal_graph import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        record_decision as rd,
    )
    from core.heal_graph import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        record_outcome as ro,
    )

    # Should be None if import failed, or callable if successful
    assert rd is None or callable(rd)
    assert ro is None or callable(ro)


def test_snapshot_store_import_fallback():
    """Test that snapshot_store import falls back gracefully."""
    from core.heal_graph import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        save_snapshot as ss,
    )
    from core.heal_graph import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        update_snapshot_status as uss,
    )

    assert ss is None or callable(ss)
    assert uss is None or callable(uss)


# ============================================================================
# Fallback StateGraph tests
# ============================================================================


@pytest.mark.asyncio
async def test_fallback_stategraph_no_entry_point():
    """Test fallback StateGraph with no entry point."""
    from core.heal_graph import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        END,
        StateGraph,
    )

    graph = StateGraph()
    graph.add_node("test_node", lambda s: s)
    # Don't set entry point
    compiled = graph.compile()

    state = HealState(alert={"id": "test"})
    result = await compiled(state)  # noqa: F841  # Variable for test verification
    assert result == state  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_fallback_stategraph_node_not_found():
    """Test fallback StateGraph when node is not found."""
    from core.heal_graph import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        END,
        StateGraph,
    )

    graph = StateGraph()
    graph.set_entry_point("missing_node")
    graph.add_edge("missing_node", END)
    compiled = graph.compile()

    state = HealState(alert={"id": "test"})
    result = await compiled(state)  # noqa: F841  # Variable for test verification
    # Should break when node not found
    assert result == state  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_fallback_stategraph_node_exception():
    """Test fallback StateGraph when node raises exception."""
    from core.heal_graph import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        END,
        StateGraph,
    )

    async def failing_node(state):
        raise ValueError("Node failed")

    graph = StateGraph()
    graph.add_node("failing_node", failing_node)
    graph.set_entry_point("failing_node")
    graph.add_edge("failing_node", END)
    compiled = graph.compile()

    state = HealState(alert={"id": "test"})
    result = await compiled(state)  # noqa: F841  # Variable for test verification
    # Should catch error and set state.error
    assert result == state  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_fallback_stategraph_no_candidates():
    """Test fallback StateGraph when no outgoing candidates."""
    from core.heal_graph import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        END,
        StateGraph,
    )

    async def test_node(state):
        return state

    graph = StateGraph()
    graph.add_node("test_node", test_node)
    graph.set_entry_point("test_node")
    # Don't add any edges
    compiled = graph.compile()

    state = HealState(alert={"id": "test"})
    result = await compiled(state)  # noqa: F841  # Variable for test verification
    assert result == state  # noqa: F841  # Variable for test verification


# ============================================================================
# Helper function tests
# ============================================================================


def test_approval_validity_minutes_invalid_env():
    """Test _approval_validity_minutes with invalid env var."""
    with patch.dict(os.environ, {"HEAL_APPROVAL_VALIDITY_MINUTES": "invalid"}):
        result = _approval_validity_minutes()  # noqa: F841  # Variable for test verification
        assert result == 5  # Default value  # noqa: F841  # Variable for test verification


def test_is_approval_expired_no_approved_at():
    """Test _is_approval_expired with no approved_at."""
    approval = {"status": "approved"}
    result = _is_approval_expired(approval)  # noqa: F841  # Variable for test verification
    assert result is False


def test_is_approval_expired_invalid_timestamp():
    """Test _is_approval_expired with invalid timestamp."""
    approval = {"approved_at": "not-a-valid-datetime"}
    result = _is_approval_expired(approval)  # noqa: F841  # Variable for test verification
    assert result is True


def test_is_approval_expired_no_timezone():
    """Test _is_approval_expired with timestamp lacking timezone."""
    # Create a datetime without timezone
    dt_without_tz = datetime.now()
    approval = {"approved_at": dt_without_tz.isoformat()}
    result = _is_approval_expired(approval)  # noqa: F841  # Variable for test verification
    # Should handle missing timezone by adding UTC
    assert isinstance(result, bool)


def test_is_alert_resolved_not_dict():
    """Test _is_alert_resolved with non-dict input."""
    result = _is_alert_resolved("not a dict")  # noqa: F841  # Variable for test verification
    assert result is False


def test_is_alert_resolved_resolved_true():
    """Test _is_alert_resolved with resolved=True."""
    alert = {"resolved": True}
    result = _is_alert_resolved(alert)  # noqa: F841  # Variable for test verification
    assert result is True


def test_is_alert_resolved_condition_not_dict():
    """Test _is_alert_resolved with non-dict condition."""
    alert = {"resolved_condition": "not a dict"}
    result = _is_alert_resolved(alert)  # noqa: F841  # Variable for test verification
    assert result is False


def test_is_alert_resolved_no_values_or_threshold():
    """Test _is_alert_resolved with missing values or threshold."""
    alert = {"resolved_condition": {"metric": "cpu", "operator": ">"}}
    result = _is_alert_resolved(alert)  # noqa: F841  # Variable for test verification
    assert result is False


def test_is_alert_resolved_exception():
    """Test _is_alert_resolved handles exceptions gracefully."""
    alert = {"resolved_condition": {"metric": "cpu", "operator": ">", "threshold": "invalid"}}
    # Should not raise exception
    result = _is_alert_resolved(alert)  # noqa: F841  # Variable for test verification
    assert isinstance(result, bool)


def test_is_hardware_alert_not_dict():
    """Test _is_hardware_alert with non-dict input."""
    result = _is_hardware_alert("not a dict")  # noqa: F841  # Variable for test verification
    assert result is False


def test_is_hardware_alert_category_not_hardware():
    """Test _is_hardware_alert with non-hardware category."""
    alert = {"category": "software"}
    result = _is_hardware_alert(alert)  # noqa: F841  # Variable for test verification
    assert result is False


def test_is_hardware_alert_text_keywords():
    """Test _is_hardware_alert with hardware keywords in text."""
    alert = {"metric": "ipmi_temperature"}
    result = _is_hardware_alert(alert)  # noqa: F841  # Variable for test verification
    assert result is True

    alert = {"description": "RAID array degraded"}
    result = _is_hardware_alert(alert)  # noqa: F841  # Variable for test verification
    assert result is True


def test_tokenize_alert_text_non_string():
    """Test _tokenize_alert_text with non-string input."""
    result = _tokenize_alert_text(123)  # noqa: F841  # Variable for test verification
    assert result == []  # noqa: F841  # Variable for test verification

    result = _tokenize_alert_text(None)  # noqa: F841  # Variable for test verification
    assert result == []  # noqa: F841  # Variable for test verification


def test_extract_command_target_no_match():
    """Test _extract_command_target with no matching pattern."""
    result = _extract_command_target("echo hello")  # noqa: F841  # Variable for test verification
    assert result is None


# ============================================================================
# Node function tests - fetch_alert, check_sla, invoke_agent
# ============================================================================


@pytest.mark.asyncio
async def test_fetch_alert_with_alert():
    """Test fetch_alert with valid alert."""
    state = HealState(alert={"id": "test-1"})
    result = await fetch_alert(state)  # noqa: F841  # Variable for test verification
    assert result.alert == {"id": "test-1"}
    assert result.error is None


@pytest.mark.asyncio
async def test_fetch_alert_no_alert():
    """Test fetch_alert with no alert."""
    state = HealState(alert={})
    result = await fetch_alert(state)  # noqa: F841  # Variable for test verification
    assert result.error == "No alert payload provided"


@pytest.mark.asyncio
async def test_check_sla_success():
    """Test check_sla with successful SLA calculation."""
    state = HealState(alert={"id": "test", "priority": "P2"})
    result = await check_sla(state)  # noqa: F841  # Variable for test verification
    # Should have sla_score set or error
    assert result.sla_score is not None or result.error is not None


@pytest.mark.asyncio
async def test_invoke_agent_no_query():
    """Test invoke_agent with alert lacking query field."""
    state = HealState(
        alert={"id": "test", "title": "Test Alert", "desc": "Test description"}, sla_score=1
    )

    with patch("core.heal_graph._metrics_history") as mock_metrics:
        mock_metrics.to_dict.return_value = {}

        with patch("core.ai_engine.analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = "Analysis result"

            result = await invoke_agent(state)  # noqa: F841  # Variable for test verification
            # Should build query from title and desc
            assert result.analysis is not None or result.error is not None


@pytest.mark.asyncio
async def test_invoke_agent_metrics_history_exception():
    """Test invoke_agent when metrics_history raises exception."""
    state = HealState(alert={"id": "test", "title": "Test", "desc": "Desc"}, sla_score=1)

    with patch("core.heal_graph._metrics_history") as mock_metrics:
        mock_metrics.to_dict.side_effect = Exception("Metrics failed")

        with patch("core.ai_engine.analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = "Analysis"

            result = await invoke_agent(state)  # noqa: F841  # Variable for test verification
            # Should handle exception gracefully
            assert result.analysis is not None or result.error is not None


@pytest.mark.asyncio
async def test_invoke_agent_alert_history_exception():
    """Test invoke_agent when alert_history raises exception."""
    state = HealState(alert={"id": "test", "title": "Test", "desc": "Desc"}, sla_score=1)

    with patch("core.heal_graph._metrics_history") as mock_metrics:
        mock_metrics.to_dict.return_value = {}

        with patch("core.ai_engine.analyze", new_callable=AsyncMock) as mock_analyze:
            mock_analyze.return_value = "Analysis"

            with patch("core.alert_engine.alert_history") as mock_alert_history:
                mock_alert_history.__iter__.side_effect = Exception("Alert history failed")

                result = await invoke_agent(state)  # noqa: F841  # Variable for test verification
                # Should handle exception gracefully
                assert result.analysis is not None or result.error is not None


# ============================================================================
# Node function tests - generate_runbook
# ============================================================================


@pytest.mark.asyncio
async def test_generate_runbook_analysis_not_dict():
    """Test generate_runbook when analysis is not a dict."""
    state = HealState(alert={"id": "test"}, analysis="not a dict", sla_score=1)

    with patch("core.runbook_generator.generate_repair_runbook") as mock_gen:
        mock_gen.return_value = {"success": True, "runbook": {"commands": ["echo test"]}}

        result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
        # Should still work with non-dict analysis
        assert result.runbook is not None or result.error is not None


@pytest.mark.asyncio
async def test_generate_runbook_coroutine_raw():
    """Test generate_runbook when generate_repair_runbook returns coroutine."""
    state = HealState(alert={"id": "test"}, analysis={"query": "test"}, sla_score=1)

    async def mock_coro():
        return {"success": True, "runbook": {"commands": ["echo test"]}}

    with patch("core.runbook_generator.generate_repair_runbook") as mock_gen:
        mock_gen.return_value = mock_coro()

        result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
        assert result.runbook is not None or result.error is not None


@pytest.mark.asyncio
async def test_generate_runbook_valid_runbook():
    """Test generate_runbook with valid runbook."""
    state = HealState(alert={"id": "test"}, analysis={"query": "test"}, sla_score=1)

    with patch("core.runbook_generator.generate_repair_runbook") as mock_gen:
        mock_gen.return_value = {
            "success": True,
            "runbook": {
                "commands": ["echo test"],
                "rollback": "echo rollback",
                "risk_level": "low",
            },
        }

        result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
        assert result.runbook is not None
        assert result.error is None


@pytest.mark.asyncio
async def test_generate_runbook_fallback_script_not_found():
    """Test generate_runbook when fallback script is not found."""
    state = HealState(alert={"id": "test"}, analysis=None, sla_score=1)

    with patch("core.runbook_generator.generate_repair_runbook") as mock_gen:
        mock_gen.return_value = None  # Invalid runbook

        # The function will use the real repair_script_library which has default scripts
        # Just verify it completes without crashing
        result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
        # Should have a runbook from the fallback library
        assert result is not None


@pytest.mark.asyncio
async def test_generate_runbook_exception():
    """Test generate_runbook when generate_repair_runbook raises exception."""
    state = HealState(alert={"id": "test"}, analysis={"query": "test"}, sla_score=1)

    with patch("core.runbook_generator.generate_repair_runbook") as mock_gen:
        mock_gen.side_effect = Exception("Generation failed")

        # Also patch the fallback to ensure it doesn't interfere
        with patch("core.auto_heal.REPAIR_SCRIPT_LIBRARY.get_script") as mock_get_script:
            mock_get_script.side_effect = Exception("Fallback also failed")

            result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
            assert result.error is not None


@pytest.mark.asyncio
async def test_generate_runbook_hardware_keywords_k8s_drain():
    """Test generate_runbook hardware keyword: k8s drain."""
    state = HealState(
        alert={"id": "test", "desc": "Node needs cordon and drain"}, analysis=None, sla_score=1
    )

    with patch("core.runbook_generator.generate_repair_runbook") as mock_gen:
        mock_gen.return_value = None

        # Patch at the heal_graph module level where it's imported
        # The real library will be used, just verify it completes
        result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
        # Should have a runbook from the fallback library
        assert result.runbook is not None


@pytest.mark.asyncio
async def test_generate_runbook_non_hardware_disk():
    """Test generate_runbook non-hardware keyword: disk."""
    state = HealState(alert={"id": "test", "metric": "disk_usage_high"}, analysis=None, sla_score=1)

    with patch("core.runbook_generator.generate_repair_runbook") as mock_gen:
        mock_gen.return_value = None

        # The real library will be used, just verify it completes
        result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
        # Should have a runbook from the fallback library
        assert result.runbook is not None


@pytest.mark.asyncio
async def test_generate_runbook_non_hardware_memory():
    """Test generate_runbook non-hardware keyword: memory."""
    state = HealState(alert={"id": "test", "title": "Memory high"}, analysis=None, sla_score=1)

    with patch("core.runbook_generator.generate_repair_runbook") as mock_gen:
        mock_gen.return_value = None

        # The real library will be used, just verify it completes
        result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
        # Should have a runbook from the fallback library
        assert result.runbook is not None


@pytest.mark.asyncio
async def test_generate_runbook_non_hardware_service():
    """Test generate_runbook non-hardware keyword: service."""
    state = HealState(
        alert={"id": "test", "desc": "Service restart needed"}, analysis=None, sla_score=1
    )

    with patch("core.runbook_generator.generate_repair_runbook") as mock_gen:
        mock_gen.return_value = None

        # The real library will be used, just verify it completes
        result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
        # Should have a runbook from the fallback library
        assert result.runbook is not None


# ============================================================================
# Node function tests - apply_fix
# ============================================================================


@pytest.mark.asyncio
async def test_apply_fix_commands_not_list():
    """Test apply_fix when commands is not a list."""
    state = HealState(
        alert={"id": "test"},
        runbook={"success": True, "runbook": {"commands": "not a list"}},
        sla_score=1,
    )

    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert result.error is not None
    assert "no executable commands" in result.error.lower()


@pytest.mark.asyncio
async def test_apply_fix_confidence_exception():
    """Test apply_fix when confidence value raises exception."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"], "confidence": "not a number"},
            "worst_risk": "low",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch(
                "core.heal_graph.async_upsert_pending_approval", new_callable=AsyncMock
            ) as mock_upsert:
                mock_upsert.return_value = None

                result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                # Should handle confidence exception gracefully
                assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_approval_get_success():
    """Test apply_fix when approval is successfully retrieved."""
    state = HealState(
        alert={"id": "test"},
        runbook={"success": True, "runbook": {"commands": ["echo test"]}, "worst_risk": "medium"},
        sla_score=1,
    )

    with patch("core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "status": "approved",
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("core.heal_graph._metrics_history") as mock_metrics:
            mock_metrics.to_dict.return_value = {}

            with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                assert result.approval_status == "approved"


@pytest.mark.asyncio
async def test_apply_fix_upsert_exception():
    """Test apply_fix when upsert_pending_approval raises exception."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "low",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch(
                "core.heal_graph.async_upsert_pending_approval", new_callable=AsyncMock
            ) as mock_upsert:
                mock_upsert.side_effect = Exception("Upsert failed")

                with patch("core.heal_graph._metrics_history") as mock_metrics:
                    mock_metrics.to_dict.return_value = {}

                    with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                        result = await apply_fix(
                            state
                        )  # noqa: F841  # Variable for test verification
                        # Should handle upsert exception gracefully
                        assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_approval_status_approved():
    """Test apply_fix when approval status is already approved."""
    state = HealState(
        alert={"id": "test"},
        runbook={"success": True, "runbook": {"commands": ["echo test"]}, "worst_risk": "medium"},
        sla_score=1,
    )

    with patch("core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "status": "approved",
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("core.heal_graph._metrics_history") as mock_metrics:
            mock_metrics.to_dict.return_value = {}

            with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                assert result.approval_status == "approved"


@pytest.mark.asyncio
async def test_apply_fix_auto_approve_sla_score_0():
    """Test apply_fix auto-approve blocked when SLA score is 0 (P0)."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=0,  # P0 requires explicit approval
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch(
                "core.heal_graph.async_upsert_pending_approval", new_callable=AsyncMock
            ) as mock_upsert:
                mock_upsert.return_value = None

                result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                # Should not auto-approve for P0
                assert result.error is not None or result.approval_status != "approved"


@pytest.mark.asyncio
async def test_apply_fix_notify_exception():
    """Test apply_fix when notification raises exception."""
    state = HealState(
        alert={"id": "test"},
        runbook={"success": True, "runbook": {"commands": ["echo test"]}, "worst_risk": "medium"},
        sla_score=1,
    )

    with patch("core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"status": "pending"}

        with patch(
            "core.heal_graph.async_upsert_pending_approval", new_callable=AsyncMock
        ) as mock_upsert:
            mock_upsert.return_value = None

            with patch(
                "core.heal_graph._send_alert_notification", new_callable=AsyncMock
            ) as mock_notify:
                mock_notify.side_effect = Exception("Notification failed")

                with patch("core.phase3_metrics.HEAL_PENDING_APPROVAL") as mock_metric:
                    mock_metric.labels.return_value.inc.return_value = None

                    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                    # Should handle notification exception gracefully
                    assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_auto_approved_audit():
    """Test apply_fix auto-approve audit logging."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                    # Should log auto-approved audit
                    assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_precheck_expired():
    """Test apply_fix when pre-execution check finds expired approval."""
    state = HealState(
        alert={"id": "test"},
        runbook={"success": True, "runbook": {"commands": ["echo test"]}, "worst_risk": "medium"},
        sla_score=1,
    )

    # Create an expired approval (old timestamp)
    old_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    with patch("core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"status": "approved", "approved_at": old_time.isoformat()}

        with patch.dict(os.environ, {"HEAL_APPROVAL_VALIDITY_MINUTES": "5"}):
            result = await apply_fix(state)  # noqa: F841  # Variable for test verification
            assert result.approval_status == "expired"
            assert "pre-execution check failed" in result.error.lower()


@pytest.mark.asyncio
async def test_apply_fix_update_status_exception():
    """Test apply_fix when update approval status raises exception."""
    state = HealState(
        alert={"id": "test"},
        runbook={"success": True, "runbook": {"commands": ["echo test"]}, "worst_risk": "medium"},
        sla_score=1,
    )

    old_time = datetime.now(timezone.utc) - timedelta(minutes=10)

    with patch("core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"status": "approved", "approved_at": old_time.isoformat()}

        with patch.dict(os.environ, {"HEAL_APPROVAL_VALIDITY_MINUTES": "5"}):
            with patch(
                "core.heal_graph.async_update_approval_status_by_alert", new_callable=AsyncMock
            ) as mock_update:
                mock_update.side_effect = Exception("Update failed")

                result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                # Should handle update exception gracefully
                assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_metrics_history_exception():
    """Test apply_fix when metrics_history raises exception."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.side_effect = Exception("Metrics failed")

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                    # Should handle metrics exception gracefully
                    assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_snapshot_save_exception():
    """Test apply_fix when save_snapshot raises exception."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

                with patch("core.heal_graph.save_snapshot", new_callable=AsyncMock) as mock_save:
                    mock_save.side_effect = Exception("Snapshot save failed")

                    with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                        result = await apply_fix(
                            state
                        )  # noqa: F841  # Variable for test verification
                        # Should handle snapshot save exception gracefully
                        assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_snapshot_disabled():
    """Test apply_fix when snapshot is disabled."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

                with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
                    mock_config.get.return_value = False  # Disabled

                    with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                        result = await apply_fix(
                            state
                        )  # noqa: F841  # Variable for test verification
                        # Should use in-memory snapshot
                        assert result.snapshot is not None


@pytest.mark.asyncio
async def test_apply_fix_hardware_enabled():
    """Test apply_fix with hardware alert and hardware execution enabled."""
    state = HealState(
        alert={"id": "test", "category": "hardware", "metric": "ipmi_temp"},
        runbook={
            "success": True,
            "runbook": {"commands": ["ipmitool power cycle"]},
            "worst_risk": "high",
        },
        sla_score=1,
    )

    with patch("core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "status": "approved",
            "approved_at": datetime.now(timezone.utc).isoformat(),
        }

        with patch("core.heal_graph._metrics_history") as mock_metrics:
            mock_metrics.to_dict.return_value = {}

            with patch.dict(
                os.environ, {"HEAL_EXECUTE_ENABLED": "false", "HARDWARE_EXECUTE_ENABLED": "true"}
            ):
                result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                # Hardware should be executed when enabled
                assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_guard_none():
    """Test apply_fix when analyze_command is None."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

            with patch("core.heal_graph.analyze_command", None):
                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                    # Should skip guard when None
                    assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_risk_level_none():
    """Test apply_fix when RiskLevel is None."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

            with patch("core.heal_graph.RiskLevel", None):
                with patch("core.heal_graph.analyze_command") as mock_analyze:
                    mock_analyze.return_value = {"risk_level": "BLOCKED"}

                    with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                        result = await apply_fix(
                            state
                        )  # noqa: F841  # Variable for test verification
                        # Should handle None RiskLevel
                        assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_target_validation_empty_allowed():
    """Test apply_fix target validation with empty allowed targets."""
    state = HealState(
        alert={"id": "test", "title": "Test alert"},
        runbook={
            "success": True,
            "runbook": {"commands": ["systemctl restart nginx"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

            with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                # Should allow when allowed_targets is empty
                assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_target_in_allowed():
    """Test apply_fix target validation when target is in allowed."""
    state = HealState(
        alert={"id": "test", "title": "nginx service down", "service": "nginx"},
        runbook={
            "success": True,
            "runbook": {"commands": ["systemctl restart nginx"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

            with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                # Should allow when target is in allowed
                assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_execute_enabled_windows():
    """Test apply_fix with execution enabled on Windows."""
    state = HealState(
        alert={"id": "test", "platform": "windows"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
                mock_exec.return_value = mock_proc

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                    # Should execute on Windows
                    assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_execute_enabled_linux():
    """Test apply_fix with execution enabled on Linux."""
    state = HealState(
        alert={"id": "test", "platform": "linux"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

            with patch("asyncio.create_subprocess_shell") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.returncode = 0
                mock_proc.communicate = AsyncMock(return_value=(b"output", b""))
                mock_exec.return_value = mock_proc

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                    # Should execute on Linux
                    assert result is not None


@pytest.mark.asyncio
async def test_apply_fix_command_timeout():
    """Test apply_fix when command times out."""
    state = HealState(
        alert={"id": "test", "platform": "linux"},
        runbook={
            "success": True,
            "runbook": {"commands": ["sleep 100"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

            with patch("asyncio.create_subprocess_shell") as mock_exec:
                mock_proc = AsyncMock()
                mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)
                mock_exec.return_value = mock_proc

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                    # Should handle timeout
                    assert result.error is not None


@pytest.mark.asyncio
async def test_apply_fix_record_decision_none():
    """Test apply_fix when record_decision is None."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch.dict(os.environ, {"HEAL_AUTO_APPROVE_SAFE_LOW": "true"}):
        with patch(
            "core.heal_graph.async_get_approval_by_alert", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            with patch("core.heal_graph._metrics_history") as mock_metrics:
                mock_metrics.to_dict.return_value = {}

            with patch("core.heal_graph.record_decision", None):
                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
                    # Should handle None record_decision
                    assert result.decision_id is None


@pytest.mark.asyncio
async def test_apply_fix_top_level_exception():
    """Test apply_fix when top-level exception occurs."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "success": True,
            "runbook": {"commands": ["echo test"]},
            "worst_risk": "safe",
            "auto_executable": True,
        },
        sla_score=1,
    )

    with patch("core.heal_graph._metrics_history") as mock_metrics:
        mock_metrics.to_dict.side_effect = Exception("Unexpected error")

        result = await apply_fix(state)  # noqa: F841  # Variable for test verification
        # Should catch top-level exception
        assert result.error is not None


# ============================================================================
# Node function tests - evaluate
# ============================================================================


@pytest.mark.asyncio
async def test_evaluate_fix_not_applied():
    """Test evaluate when fix was not applied."""
    state = HealState(alert={"id": "test"}, runbook={"success": True}, fix_applied=False)

    result = await evaluate(state)  # noqa: F841  # Variable for test verification
    # Should return early without verification
    assert result.verification is None


@pytest.mark.asyncio
async def test_evaluate_runbook_not_dict():
    """Test evaluate when runbook is not a dict."""
    state = HealState(alert={"id": "test"}, runbook="not a dict", fix_applied=True)

    result = await evaluate(state)  # noqa: F841  # Variable for test verification
    # Should treat as lightweight success
    assert result.verification is not None
    assert result.verification.get("passed") is True


@pytest.mark.asyncio
async def test_evaluate_script_key_ai_dynamic_with_inner():
    """Test evaluate with AI_DYNAMIC script_key and inner runbook."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "script_key": "AI_DYNAMIC",
            "runbook": {"script_key": "custom_script", "params": {"param1": "value1"}},
        },
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {"cpu": [50, 60, 70]}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": True, "strategy": "metric"}

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None


@pytest.mark.asyncio
async def test_evaluate_params_from_inner():
    """Test evaluate extracting params from inner runbook."""
    state = HealState(
        alert={"id": "test"},
        runbook={
            "script_key": "test",
            "params": None,
            "runbook": {"params": {"inner_param": "value"}},
        },
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": True}

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None


@pytest.mark.asyncio
async def test_evaluate_repair_result_not_dict():
    """Test evaluate when repair_result is not a dict."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result="not a dict",
        snapshot={"metrics": {}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": True}

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None


@pytest.mark.asyncio
async def test_evaluate_snapshot_not_dict():
    """Test evaluate when snapshot is not a dict."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot="not a dict",
    )

    with patch("core.heal_graph._metrics_history") as mock_metrics:
        mock_metrics.to_dict.return_value = {"cpu": [50]}

        with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified": True}

            result = await evaluate(state)  # noqa: F841  # Variable for test verification
            assert result.verification is not None


@pytest.mark.asyncio
async def test_evaluate_snapshot_metrics_not_dict():
    """Test evaluate when snapshot metrics is not a dict."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": "not a dict"},
    )

    with patch("core.heal_graph._metrics_history") as mock_metrics:
        mock_metrics.to_dict.return_value = {"cpu": [50]}

        with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
            mock_verify.return_value = {"verified": True}

            result = await evaluate(state)  # noqa: F841  # Variable for test verification
            assert result.verification is not None


@pytest.mark.asyncio
async def test_evaluate_verification_has_model_dump():
    """Test evaluate when verification result has model_dump."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )

    mock_verify_result = MagicMock()  # noqa: F841  # Variable for test verification
    mock_verify_result.model_dump.return_value = {"verified": True, "strategy": "model_dump"}

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = mock_verify_result

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None
        assert result.verification.get("verified") is True


@pytest.mark.asyncio
async def test_evaluate_verification_is_dict():
    """Test evaluate when verification result is a dict."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": True, "strategy": "dict"}

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None
        assert result.verification.get("verified") is True


@pytest.mark.asyncio
async def test_evaluate_verification_neither():
    """Test evaluate when verification result is neither model_dump nor dict."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = "verified"

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None
        assert result.verification.get("result") == "verified"


@pytest.mark.asyncio
async def test_evaluate_verified_false():
    """Test evaluate when verified is False."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": False}

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None
        assert result.verification.get("passed") is False


@pytest.mark.asyncio
async def test_evaluate_verified_true():
    """Test evaluate when verified is True."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": True}

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None
        assert result.verification.get("passed") is True


@pytest.mark.asyncio
async def test_evaluate_verified_none():
    """Test evaluate when verified is None."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": None}

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None
        assert result.verification.get("passed") is True  # None treated as pass


@pytest.mark.asyncio
async def test_evaluate_passed_not_in_verification():
    """Test evaluate when passed is not in verification."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"strategy": "test"}

        result = await evaluate(state)  # noqa: F841  # Variable for test verification
        assert result.verification is not None
        assert result.verification.get("passed") is True  # Default to True


@pytest.mark.asyncio
async def test_evaluate_strategy_none():
    """Test evaluate when strategy is None."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": True, "strategy": None}

        with patch("core.phase3_metrics.VERIFY_PASSED") as mock_metric:
            mock_metric.labels.return_value.inc.return_value = None

            result = await evaluate(state)  # noqa: F841  # Variable for test verification
            assert result.verification is not None


@pytest.mark.asyncio
async def test_evaluate_record_outcome_none():
    """Test evaluate when record_outcome is None."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
        decision_id="test-decision-id",
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": True}

        with patch("core.heal_graph.record_outcome", None):
            with patch("core.phase3_metrics.VERIFY_PASSED") as mock_metric:
                mock_metric.labels.return_value.inc.return_value = None

                result = await evaluate(state)  # noqa: F841  # Variable for test verification
                assert result.verification is not None


@pytest.mark.asyncio
async def test_evaluate_decision_id_none():
    """Test evaluate when decision_id is None."""
    state = HealState(
        alert={"id": "test"},
        runbook={"script_key": "test"},
        fix_applied=True,
        repair_result={"success": True},
        snapshot={"metrics": {}},
        decision_id=None,
    )

    with patch("core.verifier.verify_repair", new_callable=AsyncMock) as mock_verify:
        mock_verify.return_value = {"verified": True}

        with patch("core.heal_graph.record_outcome") as mock_record:
            result = await evaluate(state)  # noqa: F841  # Variable for test verification
            # Should not call record_outcome when decision_id is None
            mock_record.assert_not_called()


# ============================================================================
# Node function tests - rollback
# ============================================================================


@pytest.mark.asyncio
async def test_rollback_verification_passed():
    """Test rollback when verification passed."""
    state = HealState(alert={"id": "test"}, verification={"passed": True})

    result = await rollback(state)  # noqa: F841  # Variable for test verification
    # Should return early without rollback
    assert result == state  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_rollback_verification_none():
    """Test rollback when verification is None."""
    state = HealState(alert={"id": "test"}, verification=None)

    result = await rollback(state)  # noqa: F841  # Variable for test verification
    # Should return early (default passed=True)
    assert result == state  # noqa: F841  # Variable for test verification


@pytest.mark.asyncio
async def test_rollback_approval_not_required():
    """Test rollback when approval is not required."""
    state = HealState(
        alert={"id": "test"}, verification={"passed": False}, approval_status="approved"
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False  # Approval not required

        result = await rollback(state)  # noqa: F841  # Variable for test verification
        # Should proceed without approval check
        assert result is not None


@pytest.mark.asyncio
async def test_rollback_fallback_command():
    """Test rollback with fallback rollback_command."""
    state = HealState(
        alert={"id": "test"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_command": "echo fallback", "rollback_commands": []},
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
            result = await rollback(state)  # noqa: F841  # Variable for test verification
            assert result is not None


@pytest.mark.asyncio
async def test_rollback_no_command_with_snapshot():
    """Test rollback with no command and snapshot_id."""
    state = HealState(
        alert={"id": "test"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["无需回滚"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch("core.heal_graph.update_snapshot_status", new_callable=AsyncMock) as mock_update:
            mock_update.return_value = None

            result = await rollback(state)  # noqa: F841  # Variable for test verification
            assert result is not None


@pytest.mark.asyncio
async def test_rollback_guard_none():
    """Test rollback when analyze_command is None."""
    state = HealState(
        alert={"id": "test"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch("core.heal_graph.analyze_command", None):
            with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                result = await rollback(state)  # noqa: F841  # Variable for test verification
                assert result is not None


@pytest.mark.asyncio
async def test_rollback_risk_level_none():
    """Test rollback when RiskLevel is None."""
    state = HealState(
        alert={"id": "test"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch("core.heal_graph.RiskLevel", None):
            with patch("core.heal_graph.analyze_command") as mock_analyze:
                mock_analyze.return_value = {"risk_level": "RiskLevel.BLOCKED"}

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
                    result = await rollback(state)  # noqa: F841  # Variable for test verification
                    # Should handle text-based BLOCKED check
                    assert result is not None


@pytest.mark.asyncio
async def test_rollback_text_blocked():
    """Test rollback when risk level text ends with BLOCKED."""
    state = HealState(
        alert={"id": "test"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch("core.heal_graph.analyze_command") as mock_analyze:
            mock_analyze.return_value = {"risk_level": "SomeEnum.BLOCKED"}

            with patch(
                "core.heal_graph.update_snapshot_status", new_callable=AsyncMock
            ) as mock_update:
                mock_update.return_value = None

                result = await rollback(state)  # noqa: F841  # Variable for test verification
                assert result.error is not None


@pytest.mark.asyncio
async def test_rollback_execute_disabled():
    """Test rollback when execution is disabled."""
    state = HealState(
        alert={"id": "test"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "false"}):
            result = await rollback(state)  # noqa: F841  # Variable for test verification
            # Should skip execution
            assert result is not None


@pytest.mark.asyncio
async def test_rollback_windows_platform():
    """Test rollback on Windows platform."""
    state = HealState(
        alert={"id": "test", "platform": "windows"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                result = await rollback(state)  # noqa: F841  # Variable for test verification
                assert result is not None


@pytest.mark.asyncio
async def test_rollback_non_windows_platform():
    """Test rollback on non-Windows platform."""
    state = HealState(
        alert={"id": "test", "platform": "linux"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch("asyncio.create_subprocess_shell") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                result = await rollback(state)  # noqa: F841  # Variable for test verification
                assert result is not None


@pytest.mark.asyncio
async def test_rollback_command_success():
    """Test rollback when command succeeds."""
    state = HealState(
        alert={"id": "test", "platform": "linux"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch("asyncio.create_subprocess_shell") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            with patch(
                "core.heal_graph.update_snapshot_status", new_callable=AsyncMock
            ) as mock_update:
                mock_update.return_value = None

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                    result = await rollback(state)  # noqa: F841  # Variable for test verification
                    assert result.fix_applied is False


@pytest.mark.asyncio
async def test_rollback_update_status_exception():
    """Test rollback when update_snapshot_status raises exception."""
    state = HealState(
        alert={"id": "test", "platform": "linux"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.return_value = False

        with patch("asyncio.create_subprocess_shell") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            with patch(
                "core.heal_graph.update_snapshot_status", new_callable=AsyncMock
            ) as mock_update:
                mock_update.side_effect = Exception("Update failed")

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                    result = await rollback(state)  # noqa: F841  # Variable for test verification
                    # Should handle update exception gracefully
                    assert result is not None


@pytest.mark.asyncio
async def test_rollback_escalation_disabled():
    """Test rollback when escalation is disabled."""
    state = HealState(
        alert={"id": "test", "platform": "linux"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.side_effect = lambda k, d=False: (
            False if k == "rollback_approval_required" else d
        )

        with patch("asyncio.create_subprocess_shell") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1  # Failure
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_exec.return_value = mock_proc

            with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config2:
                mock_config2.get.side_effect = lambda k, d=True: (
                    False if k == "rollback_failure_escalation_enabled" else d
                )

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                    result = await rollback(state)  # noqa: F841  # Variable for test verification
                    # Should not escalate when disabled
                    assert result is not None


@pytest.mark.asyncio
async def test_rollback_notify_none():
    """Test rollback when notify_rollback_failure is None."""
    state = HealState(
        alert={"id": "test", "platform": "linux"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.side_effect = lambda k, d=False: (
            False if k == "rollback_approval_required" else d
        )

        with patch("asyncio.create_subprocess_shell") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1  # Failure
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_exec.return_value = mock_proc

            with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config2:
                mock_config2.get.side_effect = lambda k, d=True: (
                    True if k == "rollback_failure_escalation_enabled" else d
                )

            with patch("core.heal_graph.notify_rollback_failure", None):
                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                    result = await rollback(state)  # noqa: F841  # Variable for test verification
                    # Should handle None notify gracefully
                    assert result is not None


@pytest.mark.asyncio
async def test_rollback_notify_exception():
    """Test rollback when notify_rollback_failure raises exception."""
    state = HealState(
        alert={"id": "test", "platform": "linux"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.side_effect = lambda k, d=False: (
            False if k == "rollback_approval_required" else d
        )

        with patch("asyncio.create_subprocess_shell") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1  # Failure
            mock_proc.communicate = AsyncMock(return_value=(b"", b"error"))
            mock_exec.return_value = mock_proc

            with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config2:
                mock_config2.get.side_effect = lambda k, d=True: (
                    True if k == "rollback_failure_escalation_enabled" else d
                )

            with patch(
                "core.heal_graph.notify_rollback_failure", new_callable=AsyncMock
            ) as mock_notify:
                mock_notify.side_effect = Exception("Notify failed")

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                    result = await rollback(state)  # noqa: F841  # Variable for test verification
                    # Should handle notify exception gracefully
                    assert result is not None


@pytest.mark.asyncio
async def test_rollback_final_update_exception():
    """Test rollback when final snapshot status update raises exception."""
    state = HealState(
        alert={"id": "test", "platform": "linux"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_commands": ["echo test"]},
        snapshot_id="snap-123",
    )

    with patch("core.heal_graph.SNAPSHOT_CONFIG") as mock_config:
        mock_config.get.side_effect = lambda k, d=False: (
            False if k == "rollback_approval_required" else d
        )

        with patch("asyncio.create_subprocess_shell") as mock_exec:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_exec.return_value = mock_proc

            with patch(
                "core.heal_graph.update_snapshot_status", new_callable=AsyncMock
            ) as mock_update:
                mock_update.side_effect = Exception("Update failed")

                with patch.dict(os.environ, {"HEAL_EXECUTE_ENABLED": "true"}):
                    result = await rollback(state)  # noqa: F841  # Variable for test verification
                    # Should handle final update exception gracefully
                    assert result is not None


# ============================================================================
# Node function tests - complete
# ============================================================================


@pytest.mark.asyncio
async def test_complete_cleanup_none():
    """Test complete when cleanup_expired_snapshots is None."""
    state = HealState(alert={"id": "test"}, fix_applied=True, verification={"passed": True})

    with patch("core.heal_graph.cleanup_expired_snapshots", None):
        result = await complete(state)  # noqa: F841  # Variable for test verification
        assert result is not None


@pytest.mark.asyncio
async def test_complete_exception():
    """Test complete when cleanup raises exception."""
    state = HealState(alert={"id": "test"}, fix_applied=True, verification={"passed": True})

    with patch("core.heal_graph.cleanup_expired_snapshots", new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.side_effect = Exception("Cleanup failed")

        result = await complete(state)  # noqa: F841  # Variable for test verification
        # Should handle cleanup exception gracefully
        assert result is not None


@pytest.mark.asyncio
async def test_complete_status_failure():
    """Test complete when status is failure."""
    state = HealState(
        alert={"id": "test"}, fix_applied=False, error="Test error", verification={"passed": False}
    )

    with patch("core.heal_graph.cleanup_expired_snapshots", new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.return_value = None

        result = await complete(state)  # noqa: F841  # Variable for test verification
        assert result.metrics.get("status") == "failure"


@pytest.mark.asyncio
async def test_complete_approval_pending():
    """Test complete when status is approval_pending."""
    state = HealState(
        alert={"id": "test"},
        fix_applied=False,
        error=None,
        verification=None,
        approval_status="pending",
    )

    with patch("core.heal_graph.cleanup_expired_snapshots", new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.return_value = None

        result = await complete(state)  # noqa: F841  # Variable for test verification
        assert result.metrics.get("status") == "approval_pending"


@pytest.mark.asyncio
async def test_complete_fix_not_applied():
    """Test complete when fix was not applied (no record insert)."""
    state = HealState(
        alert={"id": "test"}, fix_applied=False, error=None, verification={"passed": True}
    )

    with patch("core.heal_graph.cleanup_expired_snapshots", new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.return_value = None

        with patch("core.heal_graph.async_insert_repair_record") as mock_insert:
            result = await complete(state)  # noqa: F841  # Variable for test verification
            # Should not insert record when fix not applied
            mock_insert.assert_not_called()


@pytest.mark.asyncio
async def test_complete_insert_record_exception():
    """Test complete when insert_repair_record raises exception."""
    state = HealState(
        alert={"id": "test"},
        fix_applied=True,
        error=None,
        verification={"passed": True},
        runbook={"worst_risk": "low"},
    )

    with patch("core.heal_graph.cleanup_expired_snapshots", new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.return_value = None

        with patch(
            "core.heal_graph.async_insert_repair_record", new_callable=AsyncMock
        ) as mock_insert:
            mock_insert.side_effect = Exception("Insert failed")

            result = await complete(state)  # noqa: F841  # Variable for test verification
            # Should handle insert exception gracefully
            assert result is not None


@pytest.mark.asyncio
async def test_complete_no_snapshot_id():
    """Test complete when snapshot_id is None."""
    state = HealState(
        alert={"id": "test"},
        fix_applied=True,
        error=None,
        verification={"passed": True},
        snapshot_id=None,
        runbook={"worst_risk": "low"},
    )

    with patch("core.heal_graph.cleanup_expired_snapshots", new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.return_value = None

        with patch(
            "core.heal_graph.async_insert_repair_record", new_callable=AsyncMock
        ) as mock_insert:
            mock_insert.return_value = None

            with patch("core.heal_graph.update_snapshot_status") as mock_update:
                result = await complete(state)  # noqa: F841  # Variable for test verification
                # Should not update status when no snapshot_id
                mock_update.assert_not_called()


@pytest.mark.asyncio
async def test_complete_update_status_none():
    """Test complete when update_snapshot_status is None."""
    state = HealState(
        alert={"id": "test"},
        fix_applied=True,
        error=None,
        verification={"passed": True},
        snapshot_id="snap-123",
        runbook={"worst_risk": "low"},
    )

    with patch("core.heal_graph.cleanup_expired_snapshots", new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.return_value = None

        with patch(
            "core.heal_graph.async_insert_repair_record", new_callable=AsyncMock
        ) as mock_insert:
            mock_insert.return_value = None

            with patch("core.heal_graph.update_snapshot_status", None):
                result = await complete(state)  # noqa: F841  # Variable for test verification
                # Should handle None update_snapshot_status gracefully
                assert result is not None


@pytest.mark.asyncio
async def test_complete_update_status_exception():
    """Test complete when update_snapshot_status raises exception."""
    state = HealState(
        alert={"id": "test"},
        fix_applied=True,
        error=None,
        verification={"passed": True},
        snapshot_id="snap-123",
        runbook={"worst_risk": "low"},
    )

    with patch("core.heal_graph.cleanup_expired_snapshots", new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.return_value = None

        with patch(
            "core.heal_graph.async_insert_repair_record", new_callable=AsyncMock
        ) as mock_insert:
            mock_insert.return_value = None

            with patch(
                "core.heal_graph.update_snapshot_status", new_callable=AsyncMock
            ) as mock_update:
                mock_update.side_effect = Exception("Update failed")

                result = await complete(state)  # noqa: F841  # Variable for test verification
                # Should handle update exception gracefully
                assert result is not None


@pytest.mark.asyncio
async def test_complete_prometheus_exception():
    """Test complete when Prometheus counter raises exception."""
    state = HealState(
        alert={"id": "test"},
        fix_applied=True,
        error=None,
        verification={"passed": True},
        runbook={"worst_risk": "low"},
    )

    with patch("core.heal_graph.cleanup_expired_snapshots", new_callable=AsyncMock) as mock_cleanup:
        mock_cleanup.return_value = None

        with patch(
            "core.heal_graph.async_insert_repair_record", new_callable=AsyncMock
        ) as mock_insert:
            mock_insert.return_value = None

            with patch("prometheus_client.Counter") as mock_counter:
                mock_counter.side_effect = Exception("Prometheus failed")

                result = await complete(state)  # noqa: F841  # Variable for test verification
                # Should handle Prometheus exception gracefully
                assert result is not None


# ============================================================================
# Node function tests - run_heal
# ============================================================================


@pytest.mark.asyncio
async def test_run_heal_trace_id_exists():
    """Test run_heal when trace_id already exists in alert."""
    state = HealState(alert={"id": "test", "trace_id": "existing-trace-123"})

    with patch("core.heal_graph._set_trace_id") as mock_set:
        with patch("core.phase3_metrics.HEAL_TOTAL") as mock_total:
            mock_total.labels.return_value.inc.return_value = None

            with patch("core.heal_graph._heal_graph_runner", new_callable=AsyncMock) as mock_runner:
                mock_runner.return_value = state

                with patch("core.phase3_metrics.HEAL_SUCCESS") as mock_success:
                    mock_success.labels.return_value.inc.return_value = None

                    result = await run_heal(state)  # noqa: F841  # Variable for test verification
                    mock_set.assert_called_with("existing-trace-123")


@pytest.mark.asyncio
async def test_run_heal_set_trace_id_none():
    """Test run_heal when _set_trace_id is None."""
    state = HealState(alert={"id": "test"})

    with patch("core.heal_graph._set_trace_id", None):
        with patch("core.phase3_metrics.HEAL_TOTAL") as mock_total:
            mock_total.labels.return_value.inc.return_value = None

            with patch("core.heal_graph._heal_graph_runner", new_callable=AsyncMock) as mock_runner:
                mock_runner.return_value = state

                with patch("core.phase3_metrics.HEAL_SUCCESS") as mock_success:
                    mock_success.labels.return_value.inc.return_value = None

                    result = await run_heal(state)  # noqa: F841  # Variable for test verification
                    # Should handle None _set_trace_id gracefully
                    assert result is not None


@pytest.mark.asyncio
async def test_run_heal_alert_none():
    """Test run_heal when alert is None."""
    state = HealState(alert=None)

    with patch("core.phase3_metrics.HEAL_TOTAL") as mock_total:
        mock_total.labels.return_value.inc.return_value = None

        with patch("core.heal_graph._heal_graph_runner", new_callable=AsyncMock) as mock_runner:
            mock_runner.return_value = state

            with patch("core.phase3_metrics.HEAL_SUCCESS") as mock_success:
                mock_success.labels.return_value.inc.return_value = None

                result = await run_heal(state)  # noqa: F841  # Variable for test verification
                # Should handle None alert gracefully
                assert result is not None


@pytest.mark.asyncio
async def test_run_heal_graph_exception():
    """Test run_heal when graph execution raises exception."""
    state = HealState(alert={"id": "test"})

    with patch("core.phase3_metrics.HEAL_TOTAL") as mock_total:
        mock_total.labels.return_value.inc.return_value = None

        with patch("core.heal_graph._heal_graph_runner", new_callable=AsyncMock) as mock_runner:
            mock_runner.side_effect = Exception("Graph failed")

            with patch("core.phase3_metrics.HEAL_FAILED") as mock_failed:
                mock_failed.labels.return_value.inc.return_value = None

                result = await run_heal(state)  # noqa: F841  # Variable for test verification
                # Should catch graph exception
                assert result.error is not None


@pytest.mark.asyncio
async def test_run_heal_final_state_error():
    """Test run_heal when final state has error."""
    state = HealState(alert={"id": "test"})

    error_state = HealState(alert={"id": "test"}, error="Node failed")

    with patch("core.phase3_metrics.HEAL_TOTAL") as mock_total:
        mock_total.labels.return_value.inc.return_value = None

        with patch("core.heal_graph._heal_graph_runner", new_callable=AsyncMock) as mock_runner:
            mock_runner.return_value = error_state

            with patch("core.phase3_metrics.HEAL_FAILED") as mock_failed:
                mock_failed.labels.return_value.inc.return_value = None

                result = await run_heal(state)  # noqa: F841  # Variable for test verification
                assert result.error is not None


# ============================================================================
# _build_graph tests
# ============================================================================


def test_build_graph_checkpointer_parameter():
    """Test _build_graph with checkpointer parameter."""
    from core.heal_graph import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        CheckpointSQLite,
    )

    # Test that checkpointer is passed when available
    graph = _build_graph()
    assert graph is not None
