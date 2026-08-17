# -*- coding: utf-8 -*-
"""Targeted real branch-coverage tests for core.heal_graph.

These tests exercise branches not already covered by
``test_heal_graph_real_branches.py`` using real HealState instances, real
alert/runbook data and the real underlying subsystems.  No unit-test mocks are
used; only pytest's ``monkeypatch`` fixture for environment/configuration
changes.
"""

from __future__ import annotations

import os  # noqa: F401  # Imported for test setup
import uuid
from datetime import datetime, timedelta, timezone

import pytest  # noqa: F401  # Imported for test setup

from core.db_engine import AsyncSessionLocal
from core.heal_graph import (
    HealState,
    _allowed_targets_from_alert,
    _extract_command_target,
    _is_alert_resolved,
    _is_approval_expired,
    _is_auto_approve_allowed,
    _is_hardware_alert,
    _metrics_history,
    _pre_execution_check,
    _tokenize_alert_text,
    apply_fix,
    complete,
    evaluate,
    generate_runbook,
    rollback,
    run_heal,
)
from core.models import PendingApproval


def _low_risk_runbook(commands, rollback=""):
    """Return a minimal, auto-executable low-risk runbook."""
    return {
        "success": True,
        "runbook": {
            "script_key": "AI_DYNAMIC",
            "name": "Targeted repair",
            "description": "Coverage test runbook",
            "commands": commands,
            "rollback": rollback,
            "risk_level": "low",
            "params": {},
            "confidence": 1.0,
        },
        "worst_risk": "low",
        "needs_approval": False,
        "auto_executable": True,
        "source": "AI_DYNAMIC",
    }


# ---------------------------------------------------------------------------
# Helper-function branches
# ---------------------------------------------------------------------------


def test_is_hardware_alert_non_dict():
    assert _is_hardware_alert("not a dict") is False
    assert _is_hardware_alert({"category": "hardware"}) is True


def test_tokenize_and_extract_targets():
    alert = {
        "title": "MySQL service down",
        "service_name": "mysql",
    }
    targets = _allowed_targets_from_alert(alert)
    assert "mysql" in targets
    # no 'value' field -> covers the ``value is not None`` false branch
    alert_no_value = {"title": "redis down"}
    targets_no_value = _allowed_targets_from_alert(alert_no_value)
    assert "redis" in targets_no_value

    assert _tokenize_alert_text(None) == []
    assert _tokenize_alert_text("") == []

    assert _extract_command_target("systemctl restart nginx") == "nginx"
    # pattern 1 fails, pattern 2 matches -> covers the continue branch
    assert _extract_command_target("net stop MySQL") == "mysql"
    assert _extract_command_target("echo test") is None


def test_is_alert_resolved_fallthrough_branches():
    _metrics_history.push(10.0, 0.0, 0.0, "00:00:00")
    # metric not present in history -> ``values and threshold is not None`` false
    assert (
        _is_alert_resolved(
            {
                "resolved_condition": {
                    "metric": "nonexistent",
                    "operator": ">",
                    "threshold": 5,
                }
            }
        )
        is False
    )
    # unsupported operator falls through all comparisons
    assert (
        _is_alert_resolved(
            {
                "resolved_condition": {
                    "metric": "cpu",
                    "operator": "!=",
                    "threshold": 10,
                }
            }
        )
        is False
    )
    # threshold is None
    assert (
        _is_alert_resolved(
            {
                "resolved_condition": {
                    "metric": "cpu",
                    "operator": ">",
                    "threshold": None,
                }
            }
        )
        is False
    )


def test_is_approval_expired_branches():
    assert _is_approval_expired(None) is False
    assert _is_approval_expired({}) is False
    assert _is_approval_expired({"approved_at": None}) is False
    assert _is_approval_expired({"approved_at": "not-a-timestamp"}) is True
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    assert _is_approval_expired({"approved_at": old}) is True
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    assert _is_approval_expired({"approved_at": future}) is False


def test_pre_execution_check_expired():
    old = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    can, reason = _pre_execution_check({"id": "a1"}, {"approved_at": old})
    assert can is False
    assert "approval expired" in reason


def test_auto_approve_env_branches(monkeypatch):
    monkeypatch.delenv("HEAL_AUTO_APPROVE_SAFE_LOW", raising=False)
    assert _is_auto_approve_allowed() is False

    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    monkeypatch.setenv("HEAL_OFFHOURS_AUTO_APPROVE", "true")
    assert _is_auto_approve_allowed() is True


# ---------------------------------------------------------------------------
# generate_runbook fallback branches
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "alert,expected_key",
    [
        ({"category": "hardware", "metric": "ipmi"}, "ipmi_power_cycle"),
        ({"category": "hardware", "metric": "smart"}, "smart_test"),
        ({"category": "hardware", "metric": "cordon"}, "k8s_drain"),
        ({"category": "hardware", "metric": "node"}, "k8s_drain"),
        ({"metric": "disk", "title": "disk"}, "disk_high_script"),
        ({"metric": "service", "title": "service"}, "service_restart_script"),
        ({"metric": "cpu", "title": "cpu"}, "cpu_high_script"),
    ],
)
async def test_generate_runbook_fallback_keys(alert, expected_key):
    state = HealState(alert=alert)
    result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
    assert result.error is None
    if isinstance(result.runbook, dict) and result.runbook.get("success"):
        assert result.runbook.get("script_key") == expected_key


async def test_generate_runbook_default_hardware():
    # category hardware but no specific keyword -> falls through to ipmi
    state = HealState(alert={"category": "hardware"})
    result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
    assert result.error is None


# ---------------------------------------------------------------------------
# apply_fix branches
# ---------------------------------------------------------------------------


async def test_apply_fix_low_confidence(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    runbook = _low_risk_runbook(["echo test"])
    runbook["runbook"]["confidence"] = 0.1
    state = HealState(
        alert={"id": "conf-1", "metric": "memory", "title": "memory high"},
        runbook=runbook,
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "not approved" in result.error.lower()


async def test_apply_fix_approval_expired(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    alert_id = f"expired-{uuid.uuid4().hex[:8]}"
    async with AsyncSessionLocal() as session:
        approval = PendingApproval(
            id=f"approval-{alert_id}",
            alert_id=alert_id,
            alert_json="{}",
            rule_name="test",
            script_key="test",
            proposal="{}",
            risk_level="low",
            status="approved",
            approved_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        session.add(approval)
        await session.commit()

    state = HealState(
        alert={"id": alert_id, "metric": "memory", "title": "memory high"},
        runbook=_low_risk_runbook(["echo test"]),
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "expired" in result.error.lower()
    assert result.approval_status == "expired"


async def test_apply_fix_rollback_plan_and_in_memory_snapshot(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    state = HealState(
        alert={"id": "rollback-1", "metric": "memory", "title": "memory high"},
        runbook=_low_risk_runbook(["echo test"], rollback="echo rollback"),
        snapshot="not a dict",
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert result.fix_applied is True
    assert isinstance(result.snapshot, dict)
    assert result.rollback_info.get("rollback_commands") == ["echo rollback"]


async def test_apply_fix_hardware_simulation(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    monkeypatch.setenv("HARDWARE_EXECUTE_ENABLED", "false")
    state = HealState(
        alert={
            "id": "hw-1",
            "metric": "ipmi",
            "category": "hardware",
            "platform": "windows",
        },
        runbook=_low_risk_runbook(["echo hw"]),
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert result.fix_applied is True
    for r in result.repair_result.get("results", []):
        assert r.get("simulated") is True


async def test_apply_fix_real_execution_success_and_complete(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    state = HealState(
        alert={"id": "exec-ok-1", "metric": "memory", "title": "memory high"},
        runbook=_low_risk_runbook(["echo test"]),
    )
    state = await apply_fix(state)
    assert state.fix_applied is True
    state = await evaluate(state)
    assert state.verification is not None
    state = await complete(state)
    assert state.metrics.get("status") == "success"


async def test_apply_fix_real_execution_failure_and_complete(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    state = HealState(
        alert={"id": "exec-fail-1", "metric": "memory", "title": "memory high"},
        runbook=_low_risk_runbook(["exit 1"]),
    )
    state = await apply_fix(state)
    assert state.error is not None
    assert state.fix_applied is False
    state = await complete(state)
    assert state.metrics.get("status") == "failure"


# ---------------------------------------------------------------------------
# evaluate branches
# ---------------------------------------------------------------------------


async def test_evaluate_fix_not_applied():
    state = HealState(fix_applied=False)
    result = await evaluate(state)  # noqa: F841  # Variable for test verification
    assert result.verification is None


async def test_evaluate_string_runbook():
    state = HealState(fix_applied=True, runbook="plain text runbook")
    result = await evaluate(state)  # noqa: F841  # Variable for test verification
    assert result.verification.get("passed") is True


async def test_evaluate_params_and_snapshot_normalization(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    state = HealState(
        alert={"id": "ev-params-1", "metric": "memory", "platform": "windows"},
        fix_applied=True,
        runbook={
            "script_key": "memory_high_script",
            "runbook": {
                "script_key": "memory_high_script",
                "params": {"inner": "value"},
            },
            "params": {"outer": "value"},
        },
        snapshot="bad",
    )
    result = await evaluate(state)  # noqa: F841  # Variable for test verification
    assert isinstance(result.snapshot, dict)
    assert result.verification is not None


# ---------------------------------------------------------------------------
# rollback branches
# ---------------------------------------------------------------------------


async def test_rollback_not_approved():
    state = HealState(
        alert={"id": "rb-nap-1"},
        verification={"passed": False},
        approval_status="pending",
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert "not approved" in (result.error or "").lower()


async def test_rollback_no_rollback_command():
    state = HealState(
        alert={"id": "rb-none-1"},
        verification={"passed": False},
        approval_status="approved",
        rollback_info={"rollback_command": "无需回滚"},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert result.error is None


async def _apply_and_rollback(monkeypatch, alert_id, platform, rollback_commands):
    """Helper to create an approved, executed state and then roll it back."""
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    state = HealState(
        alert={"id": alert_id, "metric": "memory", "platform": platform},
        runbook=_low_risk_runbook(["echo test"]),
    )
    state = await apply_fix(state)
    assert state.fix_applied is True
    state.verification = {"passed": False}
    state.rollback_info = {
        "snapshot_id": state.snapshot_id,
        "rollback_commands": rollback_commands,
        "snapshot": state.snapshot,
    }
    return await rollback(state)


async def test_rollback_real_success_windows(monkeypatch):
    result = await _apply_and_rollback(  # noqa: F841  # Variable for test verification
        monkeypatch,
        f"rb-win-{uuid.uuid4().hex[:8]}",
        "windows",
        ["echo rollback"],
    )
    assert result.error is None
    assert result.fix_applied is False


async def test_rollback_real_success_linux(monkeypatch):
    result = await _apply_and_rollback(  # noqa: F841  # Variable for test verification
        monkeypatch,
        f"rb-lin-{uuid.uuid4().hex[:8]}",
        "linux",
        ["echo rollback"],
    )
    assert result.error is None
    assert result.fix_applied is False


async def test_rollback_real_failure_escalation(monkeypatch):
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    state = HealState(
        alert={"id": f"rb-esc-{uuid.uuid4().hex[:8]}", "metric": "memory"},
        verification={"passed": False},
        approval_status="approved",
        snapshot_id="snap-nonexistent",
        rollback_info={"rollback_commands": ["exit 1"]},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert result.escalated is True
    assert "failed" in (result.error or "").lower()


# ---------------------------------------------------------------------------
# complete branches
# ---------------------------------------------------------------------------


async def test_complete_approval_pending():
    state = HealState(alert={"id": "comp-pending-1"})
    result = await complete(state)  # noqa: F841  # Variable for test verification
    assert result.metrics.get("status") == "approval_pending"


# ---------------------------------------------------------------------------
# run_heal entry point
# ---------------------------------------------------------------------------


async def test_run_heal_no_alert():
    state = HealState(alert=None)
    result = await run_heal(state)  # noqa: F841  # Variable for test verification
    assert result.error is not None


async def test_run_heal_with_existing_trace_id():
    state = HealState(alert={"id": "trace-1", "trace_id": "existing-trace"})
    result = await run_heal(state)  # noqa: F841  # Variable for test verification
    assert result.alert.get("trace_id") == "existing-trace"


async def test_run_heal_full_workflow(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    state = HealState(
        alert={
            "id": f"full-target-{uuid.uuid4().hex[:8]}",
            "metric": "memory",
            "title": "memory high",
            "desc": "memory",
            "platform": "windows",
        }
    )
    result = await run_heal(state)  # noqa: F841  # Variable for test verification
    assert result.error is None
    assert result.alert.get("trace_id")
