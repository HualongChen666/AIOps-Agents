# -*- coding: utf-8 -*-
"""Coverage for remaining verifier functions/branches."""

import asyncio
from unittest.mock import AsyncMock

import pytest

import core.verifier as verifier
from core.command_guard import RiskLevel

pytestmark = [pytest.mark.core]


@pytest.fixture
def guard_ok(monkeypatch):
    monkeypatch.setattr(verifier, "_check_command_with_guard", lambda cmd: (True, ""))


@pytest.fixture
def upsert_nop(monkeypatch):
    monkeypatch.setattr(verifier, "upsert_verify_record", lambda *a, **k: None)


@pytest.fixture
def short_wait(monkeypatch):
    monkeypatch.setattr(verifier, "_verification_wait_params", lambda: (0.15, 0.01))


@pytest.fixture
def verify_config(monkeypatch):
    monkeypatch.setattr(
        verifier,
        "VERIFY_CONFIG",
        {"enabled": True, "timeout_sec": 60.0, "metric_wait_sec": 1.0, "llm_for_custom": False},
    )


async def async_noop(*args, **kwargs):
    return None


def test_verification_wait_params(monkeypatch):
    monkeypatch.setattr(
        verifier, "SNAPSHOT_CONFIG", {"verify_wait_timeout": 20.0, "verify_poll_interval": 2.0}
    )
    monkeypatch.setattr(verifier, "VERIFY_CONFIG", {"timeout_sec": 30.0})
    assert verifier._verification_wait_timeout() == 20.0
    assert verifier._verification_poll_interval() == 2.0
    assert verifier._verification_wait_params() == (20.0, 2.0)


async def test_execute_linux_verify_command(monkeypatch):
    monkeypatch.setattr(verifier, "LINUX_HOSTS", {"hosts": [{"name": "host1", "host": "10.0.0.1"}]})
    monkeypatch.setattr("core.linux_collector._ssh_execute", AsyncMock(return_value="linux output"))
    out = await verifier._execute_linux_verify_command({"host": "host1"}, "ls")
    assert out == "linux output"

    with pytest.raises(ValueError, match="host"):
        await verifier._execute_linux_verify_command({}, "ls")

    with pytest.raises(ValueError, match="未找到"):
        await verifier._execute_linux_verify_command({"host": "missing"}, "ls")


async def test_execute_windows_verify_command(monkeypatch):
    monkeypatch.setattr("core.repair_engine._run_powershell", lambda cmd: {"output": "Running"})
    out = await verifier._execute_windows_verify_command("Get-Service x")
    assert out == "Running"


async def test_verify_service_status_linux_active(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier, "_execute_linux_verify_command", AsyncMock(return_value="active\n")
    )
    result = await verifier._verify_service_status(
        {"platform": "linux"}, {"service_name": "nginx"}, "linux"
    )
    assert result["verified"] is True
    assert result["strategy"] == "service_status"
    assert "nginx" in result["recommendation"]
    assert "command" in result["evidence"]


async def test_verify_service_status_windows_running(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier, "_execute_windows_verify_command", AsyncMock(return_value="Running\n")
    )
    result = await verifier._verify_service_status(
        {"platform": "windows"},
        {},
        "windows",
        ai_runbook={"commands": ["Restart-Service -Name 'w3svc'"]},
    )
    assert result["verified"] is True
    assert result["evidence"]["service_name"] == "w3svc"


async def test_verify_service_status_transient(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier, "_execute_linux_verify_command", AsyncMock(return_value="activating\n")
    )
    result = await verifier._verify_service_status(
        {"platform": "linux"}, {"service_name": "nginx"}, "linux"
    )
    assert result["verified"] is None
    assert "中间态" in result["recommendation"]


async def test_verify_service_status_invalid_name(guard_ok, short_wait):
    result = await verifier._verify_service_status(
        {"platform": "linux"}, {"service_name": "bad;name"}, "linux"
    )
    assert result["strategy"] == "service_status"
    assert "非法" in result["error_msg"]


async def test_verify_service_status_missing_name():
    result = await verifier._verify_service_status({"platform": "linux"}, {}, "linux")
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_service_status_execute_exception(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(side_effect=RuntimeError("ssh failed")),
    )
    result = await verifier._verify_service_status(
        {"platform": "linux"}, {"service_name": "nginx"}, "linux"
    )
    assert result["strategy"] == "service_status"
    assert "RuntimeError" in result["error_msg"]


async def test_verify_process_check_linux_killed(guard_ok, monkeypatch):
    monkeypatch.setattr(verifier, "_execute_linux_verify_command", AsyncMock(return_value="0"))
    result = await verifier._verify_process_check({"platform": "linux"}, {"pid": "12345"}, "linux")
    assert result["verified"] is True
    assert result["evidence"]["pid"] == 12345


async def test_verify_process_check_linux_alive(guard_ok, monkeypatch):
    monkeypatch.setattr(verifier, "_execute_linux_verify_command", AsyncMock(return_value="1"))
    result = await verifier._verify_process_check({"platform": "linux"}, {"pid": "12345"}, "linux")
    assert result["verified"] is False


async def test_verify_process_check_windows_dead(guard_ok, monkeypatch):
    monkeypatch.setattr(verifier, "_execute_windows_verify_command", AsyncMock(return_value="DEAD"))
    result = await verifier._verify_process_check(
        {"platform": "windows"}, {}, "windows", ai_runbook={"commands": ["Stop-Process -Id 9999"]}
    )
    assert result["verified"] is True
    assert result["evidence"]["pid"] == 9999


async def test_verify_process_check_windows_alive(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier, "_execute_windows_verify_command", AsyncMock(return_value="ALIVE")
    )
    result = await verifier._verify_process_check({"platform": "windows"}, {"pid": "42"}, "windows")
    assert result["verified"] is False


async def test_verify_process_check_invalid_pid():
    result = await verifier._verify_process_check({"platform": "linux"}, {"pid": "abc"}, "linux")
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_process_check_pid_out_of_range(guard_ok):
    result = await verifier._verify_process_check(
        {"platform": "linux"}, {"pid": "5000000"}, "linux"
    )
    assert result["strategy"] == "process_check"
    assert "超出合法范围" in result["error_msg"]


async def test_verify_metric_threshold_success(monkeypatch):
    monkeypatch.setattr(verifier, "VERIFY_CONFIG", {"metric_wait_sec": 0.05})
    monkeypatch.setattr("asyncio.sleep", async_noop)
    monkeypatch.setattr(
        "core.metrics_history.metrics_history",
        type("M", (), {"to_dict": lambda self: {"memory": [4.0, 4.0, 4.0]}})(),
    )
    result = await verifier._verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]})
    assert result["verified"] is True
    assert result["strategy"] == "metric_threshold"
    assert result["evidence"]["delta_percent"] == 60.0


async def test_verify_metric_threshold_insufficient_samples(monkeypatch):
    monkeypatch.setattr(verifier, "VERIFY_CONFIG", {"metric_wait_sec": 0.05})
    monkeypatch.setattr("asyncio.sleep", async_noop)
    monkeypatch.setattr(
        "core.metrics_history.metrics_history",
        type("M", (), {"to_dict": lambda self: {"memory": [10.0]}})(),
    )
    result = await verifier._verify_metric_threshold("free_cache", {"memory": [10.0]})
    assert result["verified"] is None
    assert "数据点不足" in result["recommendation"]


async def test_verify_metric_threshold_no_snapshot():
    result = await verifier._verify_metric_threshold("free_cache", None)
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_disk_usage_linux(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(
            return_value=(
                "Filesystem     1K-blocks    Used Available Use% Mounted on\n"
                "/dev/sda1       100000   50000     50000  50% /"
            )
        ),
    )
    result = await verifier._verify_disk_usage({"platform": "linux"}, {"mount_point": "/"}, "linux")
    assert result["verified"] is True
    assert result["evidence"]["usage_percent"] == 50.0


async def test_verify_disk_usage_linux_high(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(
            return_value=(
                "Filesystem     1K-blocks    Used Available Use% Mounted on\n"
                "/dev/sda1       100000   95000      5000  95% /"
            )
        ),
    )
    result = await verifier._verify_disk_usage(
        {"platform": "linux"}, {"mount_point": "/", "threshold": 90.0}, "linux"
    )
    assert result["verified"] is False


async def test_verify_disk_usage_windows(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier, "_execute_windows_verify_command", AsyncMock(return_value="C 100000 1000")
    )
    result = await verifier._verify_disk_usage(
        {"platform": "windows"}, {"mount_point": "C:\\"}, "windows"
    )
    assert result["verified"] is False
    assert result["evidence"]["usage_percent"] == 99.0


async def test_verify_disk_usage_invalid_mount(guard_ok):
    result = await verifier._verify_disk_usage(
        {"platform": "linux"}, {"mount_point": ";bad"}, "linux"
    )
    assert result["strategy"] == "disk_usage"
    assert "非法挂载点" in result["error_msg"]


async def test_verify_disk_usage_mount_from_runbook(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(
            return_value=(
                "Filesystem     1K-blocks    Used Available Use% Mounted on\n"
                "/dev/sda1 100 50 50 50% /tmp"
            )
        ),
    )
    result = await verifier._verify_disk_usage(
        {"platform": "linux"}, {}, "linux", ai_runbook={"commands": ["rm -rf /tmp"]}
    )
    assert result["evidence"]["mount_point"] == "/tmp"


async def test_verify_network_check_linux_success(guard_ok, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(return_value="1 packets received, 0% packet loss"),
    )
    result = await verifier._verify_network_check(
        {"platform": "linux"}, {"target": "8.8.8.8"}, "linux"
    )
    assert result["verified"] is True
    assert result["evidence"]["target"] == "8.8.8.8"


async def test_verify_network_check_windows_up(guard_ok, monkeypatch):
    monkeypatch.setattr(verifier, "_execute_windows_verify_command", AsyncMock(return_value="UP"))
    result = await verifier._verify_network_check(
        {"platform": "windows"}, {"target": "myhost"}, "windows"
    )
    assert result["verified"] is True


async def test_verify_network_check_missing_target():
    result = await verifier._verify_network_check({"platform": "linux"}, {}, "linux")
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_network_check_invalid_target(guard_ok):
    result = await verifier._verify_network_check(
        {"platform": "linux"}, {"target": "bad;target"}, "linux"
    )
    assert "非法网络目标" in result["error_msg"]


async def test_verify_network_check_target_from_runbook(guard_ok, monkeypatch):
    monkeypatch.setattr(verifier, "_execute_linux_verify_command", AsyncMock(return_value="ok"))
    result = await verifier._verify_network_check(
        {"platform": "linux"},
        {},
        "linux",
        ai_runbook={"commands": ["ping '8.8.8.8'"]},
    )
    assert result["evidence"]["target"] == "8.8.8.8"


async def test_verify_k8s_status_running_and_ready(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier,
        "_execute_linux_verify_command",
        AsyncMock(
            return_value=(
                '{"status": {"phase": "Running", '
                '"conditions": [{"type": "Ready", "status": "True"}]}}'
            )
        ),
    )
    result = await verifier._verify_k8s_status(
        {"platform": "linux"}, {"resource": "pod", "name": "web-0"}, "linux"
    )
    assert result["verified"] is True
    assert result["evidence"]["phase"] == "running"


async def test_verify_k8s_status_plain_text(guard_ok, short_wait, monkeypatch):
    monkeypatch.setattr(
        verifier, "_execute_linux_verify_command", AsyncMock(return_value="running")
    )
    result = await verifier._verify_k8s_status({"platform": "linux"}, {"name": "web-0"}, "linux")
    assert result["verified"] is True


async def test_verify_k8s_status_windows_skipped():
    result = await verifier._verify_k8s_status(
        {"platform": "windows"}, {"name": "web-0"}, "windows"
    )
    assert result["verified"] is None
    assert result["strategy"] == "k8s_status"
    assert "仅支持 Linux" in result["recommendation"]


async def test_verify_k8s_status_missing_name():
    result = await verifier._verify_k8s_status({"platform": "linux"}, {}, "linux")
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_custom_command_disabled():
    monkeypatch = pytest.MonkeyPatch()
    # kept explicit to avoid scope issues; default VERIFY_CONFIG has llm_for_custom=False
    result = await verifier._verify_custom_command({}, {}, "linux")
    assert result["verified"] is None
    assert result["strategy"] == "skipped"


async def test_verify_custom_command_enabled_still_skipped(monkeypatch):
    monkeypatch.setattr(verifier, "VERIFY_CONFIG", {"llm_for_custom": True})
    result = await verifier._verify_custom_command({}, {}, "linux")
    assert result["verified"] is None
    assert "LLM 验证逻辑预留" in result["recommendation"]


def test_check_command_with_guard_levels(monkeypatch):
    monkeypatch.setattr(
        "core.command_guard.analyze_command",
        lambda cmd: {"risk_level": RiskLevel.LOW, "reason": ""},
    )
    ok, reason = verifier._check_command_with_guard("df -h")
    assert ok is True

    monkeypatch.setattr(
        "core.command_guard.analyze_command",
        lambda cmd: {"risk_level": RiskLevel.MEDIUM, "reason": ""},
    )
    ok, reason = verifier._check_command_with_guard("some command")
    assert ok is False
    assert "中等风险" in reason

    monkeypatch.setattr(
        "core.command_guard.analyze_command",
        lambda cmd: {"risk_level": RiskLevel.BLOCKED, "reason": "blocked"},
    )
    ok, reason = verifier._check_command_with_guard("rm -rf /")
    assert ok is False
    assert "blocked" in reason


def test_check_command_with_guard_exception(monkeypatch):
    monkeypatch.setattr(
        "core.command_guard.analyze_command",
        lambda cmd: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    ok, reason = verifier._check_command_with_guard("ls")
    assert ok is False
    assert "RuntimeError" in reason


async def test_verify_repair_service_status_end_to_end(
    verify_config, upsert_nop, guard_ok, monkeypatch
):
    monkeypatch.setattr(
        verifier, "_execute_linux_verify_command", AsyncMock(return_value="active\n")
    )
    result = await verifier.verify_repair(
        {"platform": "linux"},
        "restart_service",
        {"service_name": "nginx"},
        None,
        "repair output text",
        repair_id=7,
    )
    assert result["verified"] is True
    assert result["strategy"] == "service_status"
    assert result["evidence"]["repair_output_preview"] == "repair output text"
    assert result["confidence"] == 0.95
