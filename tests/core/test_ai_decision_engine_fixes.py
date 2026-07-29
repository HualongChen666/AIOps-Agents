# -*- coding: utf-8 -*-
"""Focused regression tests for P0-P2 AI Decision Engine repairs."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest


class TestRiskLevelUnified:
    """P0-4: RiskLevel enum values must be string-based and identical everywhere."""

    def test_risk_level_values_across_modules(self):
        from core.agent.executor import RiskLevel as ExecRiskLevel
        from core.auto_heal import RiskLevel as AutoRiskLevel
        from core.command_guard import RiskLevel as CmdRiskLevel

        for name in ("SAFE", "LOW", "MEDIUM", "HIGH", "BLOCKED"):
            assert (
                getattr(CmdRiskLevel, name).value
                == getattr(AutoRiskLevel, name).value
                == getattr(ExecRiskLevel, name).value
            )
        assert CmdRiskLevel.BLOCKED.value == "blocked"


class TestVerifierP1P2Strategies:
    """P1-2: disk/network/k8s verification strategies."""

    @pytest.mark.asyncio
    async def test_select_strategy_disk_network_k8s(self):
        from core.verifier import _select_strategy

        assert _select_strategy("disk_high_script", {}) == "disk_usage"
        assert _select_strategy("flush_dns", {}) == "network_check"
        assert _select_strategy("k8s_pod_crash", {}) == "k8s_status"

    @pytest.mark.asyncio
    async def test_verify_disk_usage_linux(self):
        from core.verifier import _verify_disk_usage

        df_output = (
            "Filesystem     1K-blocks     Used Available Use% Mounted on\n"
            "/dev/sda1       10000000  7000000   3000000  70% /"
        )
        with patch(
            "core.verifier._execute_linux_verify_command",
            new_callable=AsyncMock,
            return_value=df_output,
        ):
            result = await _verify_disk_usage(
                alert={"host": "localhost"},
                params={"mount_point": "/"},
                platform="linux",
            )
        assert result["verified"] is True
        assert result["strategy"] == "disk_usage"
        assert result["evidence"]["usage_percent"] == 70.0
        assert result["recommendation"].startswith("磁盘使用率")

    @pytest.mark.asyncio
    async def test_verify_network_check_linux(self):
        from core.verifier import _verify_network_check

        ping_output = "PING google.com (142.250.80.46): 56 data bytes\n64 bytes from ... icmp_seq=0 ttl=117 time=15.2 ms\n--- google.com ping statistics ---\n1 packets transmitted, 1 received, 0% packet loss"  # noqa: E501
        with patch(
            "core.verifier._execute_linux_verify_command",
            new_callable=AsyncMock,
            return_value=ping_output,
        ):
            result = await _verify_network_check(
                alert={"host": "localhost"},
                params={"target": "google.com"},
                platform="linux",
            )
        assert result["verified"] is True
        assert result["strategy"] == "network_check"
        assert "google.com" in result["recommendation"]

    @pytest.mark.asyncio
    async def test_verify_k8s_status_running(self):
        from core.verifier import _verify_k8s_status

        with patch(
            "core.verifier._execute_linux_verify_command",
            new_callable=AsyncMock,
            return_value="Running",
        ):
            result = await _verify_k8s_status(
                alert={"host": "localhost"},
                params={"resource": "pod", "name": "web-0", "namespace": "default"},
                platform="linux",
            )
        assert result["verified"] is True
        assert result["strategy"] == "k8s_status"
        assert result["evidence"]["phase"] == "running"


class TestAutoHealEscalationAndLock:
    """P1-3 + P1-4: failure escalation, maintenance window, per-resource lock."""

    @pytest.mark.asyncio
    async def test_try_auto_heal_maintenance_window(self, monkeypatch):
        from core import auto_heal

        monkeypatch.setenv("HEAL_MAINTENANCE_MODE", "true")
        result = await auto_heal.try_auto_heal({"id": "a1", "host": "h1"})
        assert result["maintenance"] is True
        assert "Auto-heal disabled" in result["error"]

    @pytest.mark.asyncio
    async def test_try_auto_heal_escalation_after_failures(self, monkeypatch):
        from core import auto_heal
        from core.heal_graph import HealState

        monkeypatch.setattr(auto_heal, "_HEAL_FAILURE_TRACKER", {})
        monkeypatch.setattr(auto_heal, "_FAILURE_ESCALATION_THRESHOLD", 2)

        async def fake_run_heal(state: HealState):
            state.fix_applied = False
            state.error = "command failed"
            state.verification = {}
            state.approval_status = "approved"
            return state

        with patch("core.heal_graph.run_heal", side_effect=fake_run_heal):
            # first failure
            r1 = await auto_heal.try_auto_heal({"id": "a1", "host": "h1"})
            assert r1["healed"] is False
            assert "escalated" not in r1

            # second failure triggers escalation
            r2 = await auto_heal.try_auto_heal({"id": "a1", "host": "h1"})
            assert r2.get("escalated") is True
            assert "manual intervention" in r2["error"]

    @pytest.mark.asyncio
    async def test_try_auto_heal_per_resource_lock(self):
        from core import auto_heal

        key = auto_heal._get_resource_key({"id": "a1"})
        lock = await auto_heal._acquire_heal_lock(key)
        assert isinstance(lock, asyncio.Lock)
        assert auto_heal._HEAL_LOCKS[key] is lock


class TestHealGraphFallbackAndMetrics:
    """P2-2 + P2-3: RepairScriptLibrary fallback and completion metrics."""

    @pytest.mark.asyncio
    async def test_generate_runbook_repair_script_library_fallback(self, monkeypatch):
        from core import heal_graph

        state = heal_graph.HealState(
            alert={"id": "a1", "title": "cpu high", "metric": "cpu"},
        )
        import core.runbook_generator as rg

        monkeypatch.setattr(
            rg,
            "generate_repair_runbook",
            lambda alert, ctx: {"success": False},
        )
        await heal_graph.generate_runbook(state)
        assert state.runbook is not None
        assert state.runbook.get("source") == "repair_script_library"
        assert state.runbook.get("script_key") == "cpu_high_script"

    @pytest.mark.asyncio
    async def test_complete_populates_metrics(self):
        from core import heal_graph

        state = heal_graph.HealState(
            alert={"id": "a1"},
            fix_applied=True,
            verification={"passed": True, "strategy": "service_status"},
            executed_commands=["systemctl restart nginx"],
        )
        await heal_graph.complete(state)
        assert state.metrics["status"] == "success"
        assert state.metrics["commands_executed"] == 1
        assert state.metrics["verification_strategy"] == "service_status"
