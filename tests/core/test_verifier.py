# -*- coding: utf-8 -*-
"""Tests for core/verifier.py."""

from unittest.mock import AsyncMock

import pytest

import core.verifier as verifier


def _ok_result():
    return verifier.VerifyResult(
        verified=True,
        strategy="service_status",
        confidence=0.95,
        evidence={},
        duration_sec=0.0,
        error_msg="",
        recommendation="ok",
    )


@pytest.fixture
def patch_upsert(monkeypatch):
    monkeypatch.setattr(verifier, "upsert_verify_record", lambda *a, **k: None)


@pytest.fixture
def enabled_config(monkeypatch):
    monkeypatch.setattr(
        verifier,
        "VERIFY_CONFIG",
        {"enabled": True, "timeout_sec": 10.0, "metric_wait_sec": 2.0},
    )


async def test_verify_repair_disabled(patch_upsert, monkeypatch):
    monkeypatch.setattr(verifier, "VERIFY_CONFIG", {"enabled": False})
    result = await verifier.verify_repair({}, "restart_service", {}, None, "")
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_repair_invalid_alert(enabled_config, patch_upsert):
    result = await verifier.verify_repair("bad", "restart_service", {}, None, "")
    assert result["strategy"] == "error"
    assert "dict" in result["error_msg"]


async def test_verify_repair_empty_script_key(enabled_config, patch_upsert):
    result = await verifier.verify_repair({"platform": "linux"}, "", {}, None, "")
    assert result["strategy"] == "error"


async def test_verify_repair_unknown_script(enabled_config, patch_upsert):
    result = await verifier.verify_repair({"platform": "linux"}, "unknown", {}, None, "")
    assert result["verified"] is None
    assert "skipped" in result["strategy"]


async def test_verify_repair_metric_wait_conflict(enabled_config, patch_upsert, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "VERIFY_CONFIG",
        {"enabled": True, "timeout_sec": 3.0, "metric_wait_sec": 5.0},
    )
    result = await verifier.verify_repair({"platform": "linux"}, "free_cache", {}, None, "")
    assert result["strategy"] == "skipped"
    assert "metric_wait_sec" in result["recommendation"]


async def test_verify_repair_success(enabled_config, patch_upsert, monkeypatch):
    dispatch = AsyncMock(return_value=_ok_result())
    monkeypatch.setattr(verifier, "_dispatch_verification", dispatch)

    result = await verifier.verify_repair(
        {"platform": "linux"},
        "restart_service",
        {"service_name": "nginx"},
        None,
        "repair output here",
        repair_id=42,
    )
    assert result["verified"] is True
    assert result["strategy"] == "service_status"
    assert result["evidence"]["repair_output_preview"] == "repair output here"
    assert dispatch.called


async def test_verify_repair_dispatch_exception(enabled_config, patch_upsert, monkeypatch):
    monkeypatch.setattr(
        verifier, "_dispatch_verification", AsyncMock(side_effect=RuntimeError("boom"))
    )
    result = await verifier.verify_repair(
        {"platform": "linux"}, "restart_service", {}, None, ""
    )
    assert result["strategy"] == "error"
    assert "RuntimeError" in result["error_msg"]


def test_select_strategy():
    assert verifier._select_strategy("restart_service") == "service_status"
    assert verifier._select_strategy("kill_high_cpu") == "process_check"
    assert verifier._select_strategy("free_cache") == "metric_threshold"
    assert verifier._select_strategy("disk_high_script") == "disk_usage"
    assert verifier._select_strategy("flush_dns") == "network_check"
    assert verifier._select_strategy("k8s_pod_crash") == "k8s_status"
    assert verifier._select_strategy("sfc_scan") == "none"
    assert verifier._select_strategy("unknown") == "none"


def test_select_strategy_ai_dynamic():
    assert (
        verifier._select_strategy(
            "AI_DYNAMIC", ai_runbook={"commands": ["systemctl restart nginx"]}
        )
        == "service_status"
    )
    assert (
        verifier._select_strategy(
            "AI_DYNAMIC", ai_runbook={"commands": ["kill 12345"]}
        )
        == "process_check"
    )
    assert (
        verifier._select_strategy(
            "AI_DYNAMIC", ai_runbook={"commands": ["df /tmp"]}
        )
        == "disk_usage"
    )
    assert (
        verifier._select_strategy(
            "AI_DYNAMIC", ai_runbook={"commands": ["ping 8.8.8.8"]}
        )
        == "network_check"
    )
    assert (
        verifier._select_strategy(
            "AI_DYNAMIC", ai_runbook={"commands": ["kubectl get pods"]}
        )
        == "k8s_status"
    )
    assert verifier._select_strategy("AI_DYNAMIC") == "custom_command"


def test_check_command_with_guard(monkeypatch):
    from core.command_guard import RiskLevel

    def fake_analyze(cmd):
        if "rm" in cmd:
            return {"risk_level": RiskLevel.HIGH, "reason": "dangerous"}
        return {"risk_level": RiskLevel.SAFE, "reason": ""}

    monkeypatch.setattr("core.command_guard.analyze_command", fake_analyze)

    ok, reason = verifier._check_command_with_guard("ls -la /var/log")
    assert ok is True

    ok, reason = verifier._check_command_with_guard("rm -rf / --no-preserve-root")
    assert ok is False
    assert "dangerous" in reason


def test_build_results():
    skipped = verifier._build_skipped_result("none", "skip it")
    assert skipped["verified"] is None
    assert skipped["strategy"] == "none"

    error = verifier._build_error_result("error", "boom", duration_sec=1.0)
    assert error["verified"] is None
    assert error["error_msg"] == "boom"
    assert error["duration_sec"] == 1.0
