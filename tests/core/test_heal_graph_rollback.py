# -*- coding: utf-8 -*-
"""Tests for heal_graph rollback escalation, approval and snapshot integration."""

from unittest.mock import AsyncMock, patch

import pytest

from core import heal_graph


@pytest.fixture
def base_state():
    """Return a HealState pre-configured with an approved repair and failed verification."""
    return heal_graph.HealState(
        alert={"id": "alert-rollback", "platform": "linux"},
        runbook={"script_key": "restart_service", "commands": ["systemctl restart nginx"]},
        approval_status="approved",
        fix_applied=True,
        executed_commands=["systemctl restart nginx"],
        rollback_info={"rollback_commands": ["python -c \"print('ok')\""]},
        snapshot_id="snap-rollback-001",
        verification={"passed": False},
    )


@pytest.fixture
def failing_state(base_state):
    """State with a rollback command that exits non-zero."""
    base_state.rollback_info = {"rollback_commands": ['python -c "import sys; sys.exit(1)"']}
    base_state.verification = {"passed": False}
    return base_state


@pytest.fixture(autouse=True)
def _enable_execution(monkeypatch):
    """Enable real command execution for rollback tests."""
    monkeypatch.setenv("HEAL_EXECUTE_ENABLED", "true")
    monkeypatch.setenv("SNAPSHOT_ROLLBACK_APPROVAL_REQUIRED", "true")
    monkeypatch.setenv("SNAPSHOT_ROLLBACK_FAILURE_ESCALATION_ENABLED", "true")

    def _safe_analyze(cmd):
        return {
            "risk_level": heal_graph.RiskLevel.LOW,
            "risk_name": "safe",
            "reason": "test",
            "action": "allow",
        }

    monkeypatch.setattr(heal_graph, "analyze_command", _safe_analyze)


@pytest.mark.asyncio
async def test_rollback_requires_approval():
    """Rollback is blocked when repair was not approved."""
    state = heal_graph.HealState(
        alert={"id": "alert-1"},
        approval_status="pending",
        verification={"passed": False},
        rollback_info={"rollback_commands": ["echo ok"]},
    )
    with patch.object(heal_graph, "update_snapshot_status", new=AsyncMock()):
        await heal_graph.rollback(state)

    assert "not approved" in state.error
    assert state.escalated is False


@pytest.mark.asyncio
async def test_rollback_escalates_on_failure(failing_state, monkeypatch):
    """Rollback failure triggers escalation and snapshot status update."""
    notifier_mock = AsyncMock()
    monkeypatch.setattr(heal_graph, "notify_rollback_failure", notifier_mock)
    status_mock = AsyncMock()
    monkeypatch.setattr(heal_graph, "update_snapshot_status", status_mock)

    await heal_graph.rollback(failing_state)

    assert failing_state.escalated is True
    assert "failed" in failing_state.error.lower()
    assert notifier_mock.called
    call_kwargs = notifier_mock.call_args.kwargs
    assert call_kwargs["alert_id"] == "alert-rollback"
    assert call_kwargs["snapshot_id"] == "snap-rollback-001"
    assert status_mock.called


@pytest.mark.asyncio
async def test_rollback_success_updates_snapshot(base_state, monkeypatch):
    """Successful rollback sets snapshot status to success."""
    status_mock = AsyncMock()
    monkeypatch.setattr(heal_graph, "update_snapshot_status", status_mock)

    await heal_graph.rollback(base_state)

    assert base_state.error is None
    assert base_state.escalated is False
    assert base_state.fix_applied is False
    status_mock.assert_awaited_with("snap-rollback-001", "success")


@pytest.mark.asyncio
async def test_rollback_guard_blocks_blocked_command(base_state, monkeypatch):
    """Rollback commands with BLOCKED risk level are rejected."""
    base_state.rollback_info = {"rollback_commands": ["rm -rf /"]}

    def _fake_analyze(cmd):
        from core.command_guard import RiskLevel

        return {"risk_level": RiskLevel.BLOCKED, "reason": "destructive"}

    monkeypatch.setattr(heal_graph, "analyze_command", _fake_analyze)
    status_mock = AsyncMock()
    monkeypatch.setattr(heal_graph, "update_snapshot_status", status_mock)

    await heal_graph.rollback(base_state)

    assert "blocked" in base_state.error.lower()
    status_mock.assert_awaited()


@pytest.mark.asyncio
async def test_complete_cleans_up_expired_snapshots(monkeypatch):
    """complete node invokes expired snapshot cleanup."""
    cleanup_mock = AsyncMock(return_value=5)
    monkeypatch.setattr(heal_graph, "cleanup_expired_snapshots", cleanup_mock)
    status_mock = AsyncMock()
    monkeypatch.setattr(heal_graph, "update_snapshot_status", status_mock)

    state = heal_graph.HealState(
        alert={"id": "alert-complete"},
        fix_applied=True,
        verification={"passed": True},
        snapshot_id="snap-complete",
    )

    await heal_graph.complete(state)

    cleanup_mock.assert_awaited_once()
    status_mock.assert_awaited_with("snap-complete", "success")
    assert state.metrics["snapshot_id"] == "snap-complete"
