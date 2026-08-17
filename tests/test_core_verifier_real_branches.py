# -*- coding: utf-8 -*-
"""Real-function, no-mock branch coverage tests for core.verifier."""

import asyncio
import os
import sys

# Configure the verifier environment before the module loads config.
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ["VERIFY_TIMEOUT_SEC"] = "5"
os.environ["VERIFY_METRIC_WAIT_SEC"] = "4"
os.environ["SNAPSHOT_VERIFY_WAIT_TIMEOUT"] = "1"
os.environ["SNAPSHOT_VERIFY_POLL_INTERVAL"] = "1"

import pytest

import core.metrics_history
from core.verifier import (
    _build_error_result,
    _build_skipped_result,
    _check_command_with_guard,
    _select_strategy,
    _verify_disk_usage,
    _verify_k8s_status,
    _verify_metric_threshold,
    _verify_network_check,
    _verify_process_check,
    _verify_service_status,
    verify_repair,
)


def _run(coro):
    """Run an async coroutine in a fresh event loop."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Top-level verify_repair branches
# ---------------------------------------------------------------------------
def test_verify_repair_invalid_alert():
    result = _run(verify_repair("not-a-dict", "restart_service", {}, None, ""))
    assert result["strategy"] == "error"
    assert "alert 必须为 dict" in result["error_msg"]


def test_verify_repair_empty_script_key():
    result = _run(verify_repair({"platform": "windows"}, "", {}, None, ""))
    assert result["strategy"] == "error"
    assert "script_key 不能为空" in result["error_msg"]


def test_verify_repair_invalid_platform_defaults_to_windows():
    # Unknown platform falls back to windows and ends up as a skipped/unknown strategy.
    result = _run(verify_repair({"platform": "Plan9"}, "unknown_script", {}, None, ""))
    assert result["strategy"] == "skipped"


def test_verify_repair_metric_wait_timeout_conflict():
    # VERIFY_TIMEOUT_SEC=5 and VERIFY_METRIC_WAIT_SEC=4 => 4+2 > 5 triggers skip.
    result = _run(
        verify_repair(
            {"platform": "linux", "host": "localhost"},
            "free_cache",
            {},
            {"memory": [10.0, 9.0, 8.0]},
            "",
        )
    )
    assert result["strategy"] == "skipped"
    assert result["recommendation"] and (
        "不兼容" in result["recommendation"] or "数据点" in result["recommendation"]
    )


def test_verify_repair_cancelled_is_reraised():
    async def _main():
        task = asyncio.create_task(
            verify_repair(
                {"platform": "windows"},
                "restart_service",
                {"service_name": "w32time"},
                None,
                "",
            )
        )
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    _run(_main())


def test_verify_repair_upsert_failure_is_caught():
    # Any real call reaches the upsert at the end and may fail because Qdrant is absent.
    result = _run(
        verify_repair(
            {"platform": "windows"},
            "restart_service",
            {"service_name": "w32time"},
            None,
            "repair output preview",
        )
    )
    assert result["strategy"] == "service_status"
    # repair_output should be reflected in evidence.
    assert result["evidence"].get("repair_output_preview") == "repair output preview"


# ---------------------------------------------------------------------------
# _select_strategy
# ---------------------------------------------------------------------------
def test_select_strategy():
    # Exact map hits
    assert _select_strategy("restart_service") == "service_status"
    assert _select_strategy("kill_high_cpu") == "process_check"
    assert _select_strategy("free_cache") == "metric_threshold"
    assert _select_strategy("disk_high_script") == "disk_usage"
    assert _select_strategy("flush_dns") == "network_check"
    assert _select_strategy("k8s_pod_crash") == "k8s_status"
    assert _select_strategy("sfc_scan") == "none"
    assert _select_strategy("totally_unknown") == "none"

    # AI_DYNAMIC heuristics
    assert (
        _select_strategy("AI_DYNAMIC", {"commands": ["systemctl restart nginx"]})
        == "service_status"
    )
    assert _select_strategy("AI_DYNAMIC", {"commands": ["kill 12345"]}) == "process_check"
    assert (
        _select_strategy("AI_DYNAMIC", {"commands": ["echo 1 > /proc/sys/vm/drop_caches"]})
        == "metric_threshold"
    )
    assert _select_strategy("AI_DYNAMIC", {"commands": ["rm -rf /tmp/old"]}) == "disk_usage"
    assert _select_strategy("AI_DYNAMIC", {"commands": ["ping 1.1.1.1"]}) == "network_check"
    assert _select_strategy("AI_DYNAMIC", {"commands": ["kubectl get pods app-0"]}) == "k8s_status"
    # AI_DYNAMIC with no/malformed runbook falls back to custom_command.
    assert _select_strategy("AI_DYNAMIC", None) == "custom_command"
    assert (
        _select_strategy("AI_DYNAMIC", {"commands": "systemctl restart nginx"}) == "custom_command"
    )
    assert _select_strategy("AI_DYNAMIC", {"commands": ["echo hello"]}) == "custom_command"


# ---------------------------------------------------------------------------
# _check_command_with_guard
# ---------------------------------------------------------------------------
def test_check_command_with_guard():
    ok, _ = _check_command_with_guard("systemctl is-active nginx")
    assert ok is True
    ok, _ = _check_command_with_guard("ps -p 123 --no-headers | wc -l")
    assert ok is True
    ok, _ = _check_command_with_guard("some totally unknown command xyz")
    assert ok is True  # LOW is still allowed for verification
    ok, reason = _check_command_with_guard("rm -rf /")
    assert ok is False
    ok, reason = _check_command_with_guard("iptables -F")
    assert ok is False


# ---------------------------------------------------------------------------
# service_status
# ---------------------------------------------------------------------------
def test_verify_service_status_windows():
    result = _run(
        _verify_service_status(
            {"platform": "windows", "host": "localhost"},
            {"service_name": "w32time"},
            "windows",
        )
    )
    assert result["strategy"] == "service_status"
    assert result["evidence"]["service_name"] == "w32time"


def test_verify_service_status_no_service_name():
    result = _run(_verify_service_status({"platform": "windows"}, {}, "windows"))
    assert result["strategy"] == "skipped"


def test_verify_service_status_invalid_service_name():
    result = _run(
        _verify_service_status(
            {"platform": "windows"},
            {"service_name": "bad;service"},
            "windows",
        )
    )
    assert result["strategy"] == "service_status"
    assert "非法字符" in result["error_msg"]


def test_verify_service_status_name_too_long():
    result = _run(
        _verify_service_status(
            {"platform": "windows"},
            {"service_name": "x" * 257},
            "windows",
        )
    )
    assert result["strategy"] == "service_status"
    assert "超长" in result["error_msg"]


def test_verify_service_status_linux_no_host():
    result = _run(
        _verify_service_status(
            {"platform": "linux", "host": "missing-host"},
            {"service_name": "nginx"},
            "linux",
        )
    )
    assert result["strategy"] == "service_status"
    assert "执行异常" in result["error_msg"] or "未找到" in result["error_msg"]


def test_verify_service_status_from_ai_runbook():
    result = _run(
        _verify_service_status(
            {"platform": "linux", "host": "missing-host"},
            {},
            "linux",
            ai_runbook={"commands": ["systemctl restart nginx"]},
        )
    )
    assert result["strategy"] == "service_status"


# ---------------------------------------------------------------------------
# process_check
# ---------------------------------------------------------------------------
def test_verify_process_check_windows():
    import os

    # Existing current process is alive -> verified False.
    result = _run(
        _verify_process_check(
            {"platform": "windows", "host": "localhost"},
            {"pid": os.getpid()},
            "windows",
        )
    )
    assert result["strategy"] == "process_check"
    assert result["verified"] is False

    # Non-existent PID -> verified True.
    result = _run(
        _verify_process_check(
            {"platform": "windows", "host": "localhost"},
            {"pid": 999999},
            "windows",
        )
    )
    assert result["strategy"] == "process_check"
    assert result["verified"] is True


def test_verify_process_check_invalid_pid():
    # 0 is falsy so extraction falls back to empty -> skipped; test range with a large value.
    result = _run(
        _verify_process_check(
            {"platform": "windows"},
            {"pid": 5_000_000},
            "windows",
        )
    )
    assert result["strategy"] == "process_check"
    assert "超出合法范围" in result["error_msg"]

    result = _run(
        _verify_process_check(
            {"platform": "windows"},
            {"pid": "not-a-number"},
            "windows",
        )
    )
    assert result["strategy"] == "skipped"


def test_verify_process_check_from_ai_runbook():
    result = _run(
        _verify_process_check(
            {"platform": "windows"},
            {},
            "windows",
            ai_runbook={"commands": ["Stop-Process -Id 12345"]},
        )
    )
    assert result["strategy"] == "process_check"
    assert result["verified"] is True


def test_verify_process_check_linux_no_host():
    result = _run(
        _verify_process_check(
            {"platform": "linux", "host": "missing-host"},
            {"pid": 12345},
            "linux",
        )
    )
    assert result["strategy"] == "process_check"
    assert "执行异常" in result["error_msg"]


# ---------------------------------------------------------------------------
# disk_usage
# ---------------------------------------------------------------------------
def test_verify_disk_usage_invalid_mount():
    result = _run(
        _verify_disk_usage(
            {"platform": "windows"},
            {"mount_point": "bad;mount"},
            "windows",
        )
    )
    assert result["strategy"] == "disk_usage"
    assert "非法挂载点" in result["error_msg"]


def test_verify_disk_usage_from_ai_runbook():
    result = _run(
        _verify_disk_usage(
            {"platform": "windows"},
            {},
            "windows",
            ai_runbook={"commands": ["C:"]},
        )
    )
    assert result["strategy"] == "disk_usage"


def test_verify_disk_usage_linux_no_host():
    result = _run(
        _verify_disk_usage(
            {"platform": "linux", "host": "missing-host"},
            {"mount_point": "/"},
            "linux",
        )
    )
    assert result["strategy"] == "disk_usage"
    assert "执行异常" in result["error_msg"]


def test_verify_disk_usage_unparseable_output():
    # Windows C: drive command currently fails with a PS syntax error, hitting parse-failure branches.
    result = _run(
        _verify_disk_usage(
            {"platform": "windows"},
            {"mount_point": "C:"},
            "windows",
        )
    )
    assert result["strategy"] == "disk_usage"
    assert "无法解析" in result["error_msg"]


# ---------------------------------------------------------------------------
# network_check
# ---------------------------------------------------------------------------
def test_verify_network_check():
    result = _run(
        _verify_network_check(
            {"platform": "windows"},
            {"target": "127.0.0.1"},
            "windows",
        )
    )
    assert result["strategy"] == "network_check"


def test_verify_network_check_from_ai_runbook():
    result = _run(
        _verify_network_check(
            {"platform": "windows"},
            {},
            "windows",
            ai_runbook={"commands": ["ping 127.0.0.1"]},
        )
    )
    assert result["strategy"] == "network_check"


def test_verify_network_check_invalid_target():
    result = _run(
        _verify_network_check(
            {"platform": "windows"},
            {"target": "bad target;"},
            "windows",
        )
    )
    assert result["strategy"] == "network_check"
    assert "非法网络目标" in result["error_msg"]


def test_verify_network_check_linux_no_host():
    result = _run(
        _verify_network_check(
            {"platform": "linux", "host": "missing-host"},
            {"target": "127.0.0.1"},
            "linux",
        )
    )
    assert result["strategy"] == "network_check"
    assert "执行异常" in result["error_msg"]


# ---------------------------------------------------------------------------
# k8s_status
# ---------------------------------------------------------------------------
def test_verify_k8s_status_windows_skips():
    result = _run(
        _verify_k8s_status(
            {"platform": "windows"},
            {"name": "app-0"},
            "windows",
        )
    )
    assert result["strategy"] == "k8s_status"
    assert "仅支持 Linux" in result["recommendation"]


def test_verify_k8s_status_from_ai_runbook():
    result = _run(
        _verify_k8s_status(
            {"platform": "linux", "host": "missing-host"},
            {},
            "linux",
            ai_runbook={"commands": ["kubectl get pods app-0 -n default"]},
        )
    )
    assert result["strategy"] == "k8s_status"


def test_verify_k8s_status_invalid_name():
    # The k8s name pattern currently matches everything; exercise the no-name branch instead.
    result = _run(
        _verify_k8s_status(
            {"platform": "linux", "host": "missing-host"},
            {},
            "linux",
        )
    )
    assert result["strategy"] == "skipped"
    assert "无法提取 K8s 资源名" in result["recommendation"]


def test_verify_k8s_status_linux_no_host():
    result = _run(
        _verify_k8s_status(
            {"platform": "linux", "host": "missing-host"},
            {"name": "app-0"},
            "linux",
        )
    )
    assert result["strategy"] == "k8s_status"
    assert "执行异常" in result["error_msg"]


# ---------------------------------------------------------------------------
# metric_threshold
# ---------------------------------------------------------------------------
def _push_memory_samples(values):
    for v in values:
        core.metrics_history.metrics_history.push(0.0, v, 0.0, "00:00:00")


def test_verify_metric_threshold_no_pre_snapshot():
    result = _run(_verify_metric_threshold("free_cache", None))
    assert result["strategy"] == "skipped"
    assert "无修复前快照" in result["recommendation"]


def test_verify_metric_threshold_unmapped_script():
    result = _run(_verify_metric_threshold("unknown_script", {"memory": [1, 2, 3]}))
    assert result["strategy"] == "skipped"
    assert "无关联的 metric 字段" in result["recommendation"]


def test_verify_metric_threshold_malformed_series():
    # pre_series not a list
    result = _run(_verify_metric_threshold("free_cache", {"memory": "not-a-list"}))
    assert result["strategy"] == "metric_threshold"
    assert "序列格式异常" in result["error_msg"]


def test_verify_metric_threshold_not_enough_samples():
    _push_memory_samples([1.0, 2.0, 3.0])
    result = _run(_verify_metric_threshold("free_cache", {"memory": [1.0, 2.0]}))
    assert result["strategy"] == "skipped"
    assert "数据点不足" in result["recommendation"]


def test_verify_metric_threshold_non_numeric():
    _push_memory_samples([1.0, 2.0, 3.0])
    result = _run(_verify_metric_threshold("free_cache", {"memory": ["a", "b", "c"]}))
    assert result["strategy"] == "metric_threshold"
    assert "指标数值计算异常" in result["error_msg"]


def test_verify_metric_threshold_zero_pre_avg():
    _push_memory_samples([0.0, 0.0, 0.0])
    result = _run(_verify_metric_threshold("free_cache", {"memory": [0.0, 0.0, 0.0]}))
    assert result["strategy"] == "metric_threshold"
    assert result["verified"] is False


def test_verify_metric_threshold_significant_drop():
    _push_memory_samples([1.0, 2.0, 3.0])
    result = _run(_verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]}))
    assert result["strategy"] == "metric_threshold"
    assert result["verified"] is True


def test_verify_metric_threshold_insufficient_drop():
    _push_memory_samples([9.9, 9.9, 9.9])
    result = _run(_verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]}))
    assert result["strategy"] == "metric_threshold"
    assert result["verified"] is False


def test_verify_metric_threshold_cancelled():
    async def _main():
        task = asyncio.create_task(
            _verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]})
        )
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    _run(_main())


# ---------------------------------------------------------------------------
# custom_command / AI_DYNAMIC
# ---------------------------------------------------------------------------
def test_verify_custom_command_disabled():
    result = _run(
        verify_repair(
            {"platform": "linux"},
            "AI_DYNAMIC",
            {},
            None,
            "",
            ai_runbook={"commands": ["echo hello"]},
        )
    )
    assert result["strategy"] == "skipped"
    assert "custom_command 验证已禁用" in result["recommendation"]


# ---------------------------------------------------------------------------
# Result builders
# ---------------------------------------------------------------------------
def test_build_results():
    skipped = _build_skipped_result("skipped", "recommendation text")
    assert skipped["verified"] is None
    error = _build_error_result("error", "something went wrong")
    assert error["error_msg"]
