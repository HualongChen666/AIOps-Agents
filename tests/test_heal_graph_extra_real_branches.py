# -*- coding: utf-8 -*-
"""Extra real branch-coverage tests for core.heal_graph.

Targets branch transitions still missing from the existing real-branch
suites.  Tests use real HealState/HealGraph instances and real alert/runbook
data; optional subsystem globals are set to None via pytest monkeypatch to
exercise the graceful fallback branches.
"""

from __future__ import annotations

import os  # noqa: F401  # Imported for test setup
import uuid

import pytest  # noqa: F401  # Imported for test setup

from core.heal_graph import (
    HealState,
    _allowed_targets_from_alert,
    _extract_command_target,
    _is_auto_approve_allowed,
    _metrics_history,
    apply_fix,
    complete,
    evaluate,
    rollback,
    run_heal,
)


def _low_risk_runbook(commands, source="repair_script_library"):
    """Return a low-risk auto-executable runbook for coverage tests."""
    return {
        "success": True,
        "runbook": {
            "script_key": "memory_high_script",
            "name": "Memory high repair",
            "description": "Coverage test",
            "commands": commands,
            "rollback": "",
            "risk_level": "low",
            "params": {},
            "confidence": 1.0,
        },
        "worst_risk": "low",
        "needs_approval": False,
        "auto_executable": True,
        "source": source,
    }


def _enable_auto_approve(monkeypatch):
    """Enable auto-approve including the off-hours opt-in."""
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    monkeypatch.setenv("HEAL_OFFHOURS_AUTO_APPROVE", "true")


# ---------------------------------------------------------------------------
# auto-approve helper branches
# ---------------------------------------------------------------------------


def test_auto_approve_off_hours_without_opt_in(monkeypatch):
    """Off-hours auto-approve is blocked when the opt-in is missing."""
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    monkeypatch.delenv("HEAL_OFFHOURS_AUTO_APPROVE", raising=False)
    assert _is_auto_approve_allowed() is False


# ---------------------------------------------------------------------------
# Target extraction helpers
# ---------------------------------------------------------------------------


def test_allowed_targets_from_alert_includes_value():
    targets = _allowed_targets_from_alert({"title": "CPU high", "value": 42.5})
    assert "42.5" in targets


def test_extract_command_target_remaining_patterns():
    assert _extract_command_target("sc start W32Time") == "w32time"
    assert _extract_command_target("launchctl restart com.foo.bar") == "com.foo.bar"
    assert _extract_command_target("Restart-Service -Name spooler") == "spooler"
    assert _extract_command_target("service nginx restart") == "nginx"
    assert _extract_command_target("kubectl rollout restart deployment web") == "web"


# ---------------------------------------------------------------------------
# apply_fix remaining branches
# ---------------------------------------------------------------------------


async def test_apply_fix_non_dict_inner_runbook(monkeypatch):
    """Inner runbook is not a dict -> no commands are extracted."""
    _enable_auto_approve(monkeypatch)
    state = HealState(
        alert={"id": "nd-1", "metric": "memory"},
        runbook={
            "success": True,
            "runbook": "not a dict",
            "worst_risk": "low",
            "auto_executable": True,
            "source": "AI_DYNAMIC",
        },
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "contains no executable commands" in (result.error or "")


async def test_apply_fix_bad_confidence_and_record_decision_disabled(monkeypatch):
    """Non-numeric confidence triggers the exception branch and record_decision None."""
    _enable_auto_approve(monkeypatch)
    monkeypatch.setattr("core.heal_graph.record_decision", None)
    runbook = _low_risk_runbook(["echo ok"], source="AI_DYNAMIC")
    runbook["runbook"]["confidence"] = "bad"
    state = HealState(
        alert={"id": f"conf-1-{uuid.uuid4().hex[:6]}", "metric": "memory"},
        runbook=runbook,
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert result.fix_applied is True
    assert result.decision_id is None


async def test_apply_fix_disabled_optional_deps(monkeypatch):
    """Run apply_fix with all optional persistence/notification/guard deps disabled."""
    _enable_auto_approve(monkeypatch)
    monkeypatch.setattr("core.heal_graph.save_snapshot", None)
    monkeypatch.setattr("core.heal_graph.update_snapshot_status", None)
    monkeypatch.setattr("core.heal_graph.async_get_approval_by_alert", None)
    monkeypatch.setattr("core.heal_graph.async_upsert_pending_approval", None)
    monkeypatch.setattr("core.heal_graph.record_decision", None)
    monkeypatch.setattr("core.heal_graph.analyze_command", None)
    monkeypatch.setattr("core.heal_graph.RiskLevel", None)
    monkeypatch.setattr("core.heal_graph._send_alert_notification", None)
    monkeypatch.setattr("core.heal_graph.NOTIFY_AVAILABLE", False)

    state = HealState(
        alert={
            "id": f"dep-1-{uuid.uuid4().hex[:6]}",
            "metric": "memory",
            "title": "memory high",
        },
        runbook=_low_risk_runbook(["echo test"]),
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert result.fix_applied is True
    assert result.snapshot_id is None
    assert isinstance(result.snapshot, dict)
    assert "alert" in result.snapshot
    assert result.rollback_info["snapshot"] is result.snapshot


async def test_apply_fix_alert_resolved_and_update_disabled(monkeypatch):
    """Alert resolves before execution; async_update_approval_status_by_alert is None."""
    _enable_auto_approve(monkeypatch)
    monkeypatch.setattr("core.heal_graph.async_update_approval_status_by_alert", None)
    state = HealState(
        alert={
            "id": f"resolved-1-{uuid.uuid4().hex[:6]}",
            "metric": "memory",
            "status": "resolved",
        },
        runbook=_low_risk_runbook(["echo test"]),
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "self-healed" in (result.error or "").lower()
    assert result.approval_status == "cancelled"


async def test_apply_fix_target_mismatch_guard_disabled(monkeypatch):
    """Command target not in alert context; guard disabled so validation is reached."""
    _enable_auto_approve(monkeypatch)
    monkeypatch.setattr("core.heal_graph.analyze_command", None)
    monkeypatch.setattr("core.heal_graph.RiskLevel", None)
    runbook = _low_risk_runbook(["systemctl restart nginx"], source="AI_DYNAMIC")
    state = HealState(
        alert={"id": f"mismatch-1-{uuid.uuid4().hex[:6]}", "service": "mysql"},
        runbook=runbook,
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "target" in (result.error or "").lower()


async def test_apply_fix_target_match_guard_disabled(monkeypatch):
    """Command target matches alert context and guard disabled -> fix applied."""
    _enable_auto_approve(monkeypatch)
    monkeypatch.setattr("core.heal_graph.analyze_command", None)
    monkeypatch.setattr("core.heal_graph.RiskLevel", None)
    runbook = _low_risk_runbook(["systemctl restart nginx"], source="AI_DYNAMIC")
    state = HealState(
        alert={
            "id": f"match-1-{uuid.uuid4().hex[:6]}",
            "service_name": "nginx",
            "platform": "linux",
        },
        runbook=runbook,
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert result.fix_applied is True
    assert any("nginx" in c for c in result.executed_commands)


# ---------------------------------------------------------------------------
# evaluate remaining branches
# ---------------------------------------------------------------------------


async def test_evaluate_non_dict_params_and_existing_snapshot_metrics(monkeypatch):
    """params not a dict and snapshot.metrics already a dict."""
    monkeypatch.setattr("core.heal_graph.record_outcome", None)
    _metrics_history.push(10.0, 0.0, 0.0, "00:00:00")
    state = HealState(
        alert={"id": f"ev-1-{uuid.uuid4().hex[:6]}", "platform": "windows"},
        fix_applied=True,
        runbook={
            "script_key": "memory_high_script",
            "runbook": {"params": {"inner": "val"}},
            "params": "not a dict",
        },
        snapshot={"metrics": {"cpu": [10.0]}},
        repair_result={"success": True},
    )
    result = await evaluate(state)  # noqa: F841  # Variable for test verification
    assert isinstance(result.snapshot["metrics"], dict)
    assert result.verification is not None


# ---------------------------------------------------------------------------
# rollback remaining branches
# ---------------------------------------------------------------------------


async def test_rollback_without_approval_required(monkeypatch):
    """rollback_approval_required=False bypasses approval_status check."""
    monkeypatch.setattr("core.heal_graph.SNAPSHOT_CONFIG", {"rollback_approval_required": False})
    state = HealState(
        alert={"id": f"rb-na-{uuid.uuid4().hex[:6]}"},
        verification={"passed": False},
        approval_status="pending",
        snapshot_id="snap-1",
        rollback_info={"rollback_commands": ["echo ok"]},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert result.error is None
    assert result.fix_applied is False


async def test_rollback_fallback_rollback_command(monkeypatch):
    """Legacy rollback_command field is used when rollback_commands is empty."""
    monkeypatch.setattr("core.heal_graph.update_snapshot_status", None)
    state = HealState(
        alert={"id": f"rb-fb-{uuid.uuid4().hex[:6]}"},
        verification={"passed": False},
        approval_status="approved",
        snapshot_id="snap-1",
        rollback_info={"rollback_command": "echo fallback"},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert result.error is None
    assert result.fix_applied is False


async def test_rollback_guard_disabled_and_update_disabled(monkeypatch):
    """Guard disabled and snapshot update disabled; rollback succeeds."""
    monkeypatch.setattr("core.heal_graph.analyze_command", None)
    monkeypatch.setattr("core.heal_graph.update_snapshot_status", None)
    state = HealState(
        alert={"id": f"rb-guard-{uuid.uuid4().hex[:6]}"},
        verification={"passed": False},
        approval_status="approved",
        snapshot_id="snap-1",
        rollback_info={"rollback_commands": ["echo ok"]},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert result.error is None
    assert result.fix_applied is False


async def test_rollback_blocked_and_update_disabled(monkeypatch):
    """Blocked rollback command; update_snapshot_status disabled."""
    monkeypatch.setattr("core.heal_graph.update_snapshot_status", None)
    state = HealState(
        alert={"id": f"rb-block-{uuid.uuid4().hex[:6]}"},
        verification={"passed": False},
        approval_status="approved",
        snapshot_id="snap-1",
        rollback_info={"rollback_commands": ["rm -rf /"]},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert "blocked" in (result.error or "").lower()


async def test_rollback_failure_escalation_disabled(monkeypatch):
    """Rollback command fails and escalation notification is unavailable."""
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    monkeypatch.setattr("core.heal_graph.notify_rollback_failure", None)
    monkeypatch.setattr("core.heal_graph.update_snapshot_status", None)
    state = HealState(
        alert={"id": f"rb-fail-{uuid.uuid4().hex[:6]}"},
        verification={"passed": False},
        approval_status="approved",
        snapshot_id="snap-1",
        rollback_info={"rollback_commands": ["exit 1"]},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert result.escalated is True
    assert "failed" in (result.error or "").lower()


# ---------------------------------------------------------------------------
# complete remaining branches
# ---------------------------------------------------------------------------


async def test_complete_disabled_persistence(monkeypatch):
    """complete() with snapshot/repair persistence unavailable."""
    monkeypatch.setattr("core.heal_graph.cleanup_expired_snapshots", None)
    monkeypatch.setattr("core.heal_graph.async_insert_repair_record", None)
    monkeypatch.setattr("core.heal_graph.update_snapshot_status", None)
    state = HealState(
        alert={"id": f"comp-1-{uuid.uuid4().hex[:6]}"},
        fix_applied=True,
        verification={"passed": True},
        runbook={"worst_risk": "low"},
        snapshot_id="snap-1",
        executed_commands=["echo ok"],
        repair_result={"success": True},
    )
    result = await complete(state)  # noqa: F841  # Variable for test verification
    assert result.metrics["status"] == "success"


# ---------------------------------------------------------------------------
# run_heal remaining branches
# ---------------------------------------------------------------------------


async def test_run_heal_without_trace_setter(monkeypatch):
    """run_heal with _set_trace_id unavailable still generates a trace_id."""
    _enable_auto_approve(monkeypatch)
    monkeypatch.setattr("core.heal_graph._set_trace_id", None)
    state = HealState(
        alert={
            "id": f"trace-1-{uuid.uuid4().hex[:6]}",
            "metric": "memory",
            "title": "memory high",
            "platform": "windows",
        }
    )
    result = await run_heal(state)  # noqa: F841  # Variable for test verification
    assert result.alert.get("trace_id")
