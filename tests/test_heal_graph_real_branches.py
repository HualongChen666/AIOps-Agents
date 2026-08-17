# -*- coding: utf-8 -*-
"""Real branch-coverage tests for core.heal_graph.

These tests exercise the actual HealGraph nodes, helper functions and the
full ``run_heal`` entry point with real ``HealState`` instances, real
alert/repair data and the real underlying subsystems.  No mocks or stubs are
used.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest  # noqa: F401  # Imported for test setup

from core.db_engine import (
    AsyncSessionLocal,
    async_update_approval_status_by_alert,
    async_upsert_pending_approval,
)
from core.heal_graph import (
    HealState,
    _is_alert_resolved,
    _is_auto_approve_allowed,
    _metrics_history,
    apply_fix,
    check_sla,
    complete,
    evaluate,
    fetch_alert,
    generate_runbook,
    invoke_agent,
    rollback,
    run_heal,
)
from core.models import PendingApproval


def _memory_runbook():
    """Return a low-risk, auto-executable memory repair runbook."""
    return {
        "success": True,
        "runbook": {
            "script_key": "memory_high_script",
            "name": "High Memory Usage Repair",
            "description": "Clear memory cache",
            "commands": ["import gc", "gc.collect()", "print('done')"],
            "rollback": "",
            "risk_level": "low",
            "params": {},
        },
        "worst_risk": "low",
        "needs_approval": False,
        "auto_executable": True,
        "source": "repair_script_library",
    }


async def test_fetch_alert_empty():
    state = HealState()
    result = await fetch_alert(state)  # noqa: F841  # Variable for test verification
    assert result.error == "No alert payload provided"


async def test_check_sla_real():
    state = HealState(alert={"business_name": "critical", "title": "test"})
    result = await check_sla(state)  # noqa: F841  # Variable for test verification
    assert isinstance(result.sla_score, int)


async def test_invoke_agent_real():
    state = HealState(
        alert={
            "id": "agent-1",
            "query": "high cpu",
            "title": "cpu high",
            "platform": "windows",
        }
    )
    result = await invoke_agent(state)  # noqa: F841  # Variable for test verification
    assert result.analysis is not None
    assert result.analysis.get("query")


async def test_generate_runbook_hardware_redfish():
    state = HealState(
        alert={
            "category": "hardware",
            "title": "redfish",
            "desc": "idrac",
        }
    )
    result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
    assert result.error is None


async def test_generate_runbook_hardware_raid():
    state = HealState(
        alert={
            "category": "hardware",
            "title": "raid failure",
            "desc": "storcli error",
        }
    )
    result = await generate_runbook(state)  # noqa: F841  # Variable for test verification
    assert result.error is None


async def test_is_alert_resolved_branches():
    _metrics_history.push(10.0, 0.0, 0.0, "00:00:00")
    assert _is_alert_resolved("not a dict") is False
    assert _is_alert_resolved({"status": "resolved"}) is True
    assert _is_alert_resolved({"resolved": True}) is True
    assert (
        _is_alert_resolved(
            {
                "resolved_condition": {
                    "metric": "cpu",
                    "operator": ">",
                    "threshold": 5,
                }
            }
        )
        is True
    )
    assert (
        _is_alert_resolved(
            {
                "resolved_condition": {
                    "metric": "cpu",
                    "operator": "<",
                    "threshold": 20,
                }
            }
        )
        is True
    )
    assert (
        _is_alert_resolved(
            {
                "resolved_condition": {
                    "metric": "cpu",
                    "operator": ">=",
                    "threshold": 10,
                }
            }
        )
        is True
    )
    assert (
        _is_alert_resolved(
            {
                "resolved_condition": {
                    "metric": "cpu",
                    "operator": "<=",
                    "threshold": 10,
                }
            }
        )
        is True
    )
    assert (
        _is_alert_resolved(
            {
                "resolved_condition": {
                    "metric": "cpu",
                    "operator": "==",
                    "threshold": 10,
                }
            }
        )
        is True
    )


async def test_apply_fix_missing_alert_id():
    state = HealState(alert={}, runbook=_memory_runbook())
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "Missing alert_id" in result.error


async def test_apply_fix_no_valid_runbook():
    state = HealState(alert={"id": "a1"}, runbook="not a dict")
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "No valid runbook" in result.error


async def test_apply_fix_runbook_not_dict():
    state = HealState(
        alert={"id": "a2"},
        runbook={"success": True, "runbook": "not a dict"},
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "contains no executable commands" in result.error


async def test_apply_fix_commands_not_list():
    state = HealState(
        alert={"id": "a3"},
        runbook={"success": True, "runbook": {"commands": "not a list"}},
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "contains no executable commands" in result.error


async def test_apply_fix_invalid_confidence():
    state = HealState(
        alert={"id": "a4"},
        runbook={
            "success": True,
            "runbook": {
                "commands": ["echo 1"],
                "confidence": "bad",
            },
        },
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "not approved" in result.error


async def test_apply_fix_pending_approval_and_notify(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "false")
    state = HealState(
        alert={"id": "pending-1", "metric": "memory", "title": "memory high"},
        runbook=_memory_runbook(),
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "not approved" in result.error


async def test_apply_fix_auto_approve_and_simulate(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    state = HealState(
        alert={"id": "auto-1", "metric": "memory", "title": "memory high"},
        runbook=_memory_runbook(),
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert result.fix_applied is True
    assert result.approval_status == "approved"
    assert result.repair_result is not None


async def test_apply_fix_command_blocked(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    runbook = _memory_runbook()
    runbook["runbook"]["commands"] = ["rm -rf /"]
    state = HealState(
        alert={"id": "block-1", "metric": "memory"},
        runbook=runbook,
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "blocked" in result.error.lower()


async def test_apply_fix_command_target_mismatch(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    runbook = {
        "success": True,
        "runbook": {
            "script_key": "AI_DYNAMIC",
            "commands": ["systemctl restart nginx"],
            "risk_level": "low",
            "params": {},
        },
        "worst_risk": "low",
        "auto_executable": True,
    }
    state = HealState(
        alert={"id": "mismatch-1", "service": "mysql", "platform": "linux"},
        runbook=runbook,
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "target" in result.error.lower()


async def test_apply_fix_alert_resolved_precheck(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    state = HealState(
        alert={
            "id": "resolved-1",
            "metric": "memory",
            "status": "resolved",
        },
        runbook=_memory_runbook(),
    )
    result = await apply_fix(state)  # noqa: F841  # Variable for test verification
    assert "self-healed" in result.error.lower()
    assert result.approval_status == "cancelled"


async def test_rollback_no_command():
    state = HealState(
        alert={"id": "rb-1"},
        verification={"passed": False},
        approval_status="approved",
        snapshot_id="snap-nonexistent",
        rollback_info={"rollback_commands": []},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert result.error is None


async def test_rollback_blocked_command():
    state = HealState(
        alert={"id": "rb-2"},
        verification={"passed": False},
        approval_status="approved",
        snapshot_id="snap-nonexistent",
        rollback_info={"rollback_commands": ["rm -rf /"]},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert "blocked" in result.error.lower()


async def test_rollback_success_simulated():
    state = HealState(
        alert={"id": "rb-3", "platform": "windows"},
        verification={"passed": False},
        approval_status="approved",
        snapshot_id="snap-nonexistent",
        rollback_info={"rollback_commands": ["echo ok"]},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert result.error is None
    assert result.fix_applied is False


async def test_rollback_execution_failure(monkeypatch):
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    state = HealState(
        alert={"id": "rb-4", "platform": "windows"},
        verification={"passed": False},
        approval_status="approved",
        snapshot_id="snap-nonexistent",
        rollback_info={"rollback_commands": ["exit 1"]},
    )
    result = await rollback(state)  # noqa: F841  # Variable for test verification
    assert result.escalated is True
    assert "failed" in result.error.lower()


async def test_evaluate_skipped_verification():
    state = HealState(
        alert={"id": "ev-1", "platform": "windows"},
        fix_applied=True,
        runbook={
            "script_key": "memory_high_script",
            "runbook": {"params": {}},
        },
    )
    result = await evaluate(state)  # noqa: F841  # Variable for test verification
    assert result.verification.get("passed") is True


async def test_complete_success(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    state = HealState(
        alert={"id": "comp-1", "metric": "memory", "title": "memory high"},
        runbook=_memory_runbook(),
    )
    state = await apply_fix(state)
    assert state.fix_applied is True
    state.verification = {"passed": True}
    result = await complete(state)  # noqa: F841  # Variable for test verification
    assert result.metrics["status"] == "success"


async def test_complete_failure():
    state = HealState(
        alert={"id": "comp-2"},
        error="something went wrong",
        fix_applied=False,
    )
    result = await complete(state)  # noqa: F841  # Variable for test verification
    assert result.metrics["status"] == "failure"


async def test_run_heal_full_workflow(monkeypatch):
    monkeypatch.setenv("HEAL_AUTO_APPROVE_SAFE_LOW", "true")
    state = HealState(
        alert={
            "id": "full-1",
            "metric": "memory",
            "title": "memory high",
            "desc": "memory",
            "platform": "windows",
        }
    )
    result = await run_heal(state)  # noqa: F841  # Variable for test verification
    assert result.alert.get("trace_id")
    assert result.error is None
