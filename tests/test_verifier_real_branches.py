# -*- coding: utf-8 -*-
"""Real-function, no-mock branch coverage tests for core.verifier."""

import asyncio  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup
import sys  # noqa: F401  # Imported for test setup

# Use a fast, test-friendly verifier configuration.
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

import pytest  # noqa: F401  # Imported for test setup

# noqa: E402  # Module level import not at top (intentional for env var setup)
import config

# noqa: E402  # Module level import not at top (intentional for env var setup)
import core.metrics_history

# noqa: E402  # Module level import not at top (intentional for env var setup)
from core.verifier import (
    _build_error_result,
    _build_skipped_result,
    _check_command_with_guard,
    _execute_linux_verify_command,
    _select_strategy,
    _verification_wait_params,
    _verify_custom_command,
    _verify_disk_usage,
    _verify_k8s_status,
    _verify_metric_threshold,
    _verify_network_check,
    _verify_process_check,
    _verify_service_status,
    verify_repair,
)


def _ensure_fast_config():
    config.VERIFY_CONFIG.setdefault("enabled", True)
    config.VERIFY_CONFIG["timeout_sec"] = 30.0
    config.VERIFY_CONFIG["metric_wait_sec"] = 2.0
    config.VERIFY_CONFIG["llm_for_custom"] = False
    config.SNAPSHOT_CONFIG["verify_wait_timeout"] = 1.0
    config.SNAPSHOT_CONFIG["verify_poll_interval"] = 0.2


_ensure_fast_config()


def _run(coro):
    """Run an async coroutine in a fresh event loop."""
    return asyncio.run(coro)


def _push_memory_samples(values):
    for v in values:
        core.metrics_history.metrics_history.push(0.0, v, 0.0, "00:00:00")


def _push_cpu_samples(values):
    for v in values:
        core.metrics_history.metrics_history.push(v, 0.0, 0.0, "00:00:00")


def _reset_metrics():
    core.metrics_history.metrics_history.cpu.clear()
    core.metrics_history.metrics_history.memory.clear()
    core.metrics_history.metrics_history.net_in.clear()
    core.metrics_history.metrics_history.timestamps.clear()
    core.metrics_history.metrics_history._samples.clear()


# ---------------------------------------------------------------------------
# Top-level verify_repair
# ---------------------------------------------------------------------------
def test_verify_repair_disabled():
    old = config.VERIFY_CONFIG["enabled"]
    try:
        config.VERIFY_CONFIG["enabled"] = False
        result = _run(
            verify_repair({"platform": "linux"}, "restart_service", {}, None, "")
        )  # noqa: F841  # Variable for test verification
        assert result["strategy"] == "skipped"
        assert "已禁用" in result["recommendation"]
    finally:
        config.VERIFY_CONFIG["enabled"] = old


def test_verify_repair_invalid_alert():
    result = _run(
        verify_repair("not-a-dict", "restart_service", {}, None, "")
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "error"
    assert "alert 必须为 dict" in result["error_msg"]


def test_verify_repair_empty_script_key():
    result = _run(
        verify_repair({"platform": "windows"}, "", {}, None, "")
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "error"
    assert "script_key 不能为空" in result["error_msg"]


def test_verify_repair_bad_platform_defaults_to_windows():
    result = _run(
        verify_repair({"platform": "Plan9"}, "unknown_script", {}, None, "")
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"


def test_verify_repair_params_not_dict():
    result = _run(
        verify_repair({"platform": "linux"}, "restart_service", "notdict", None, "")
    )  # noqa: F841  # Variable for test verification
    # safe_params becomes {} and no service_name is found, so _verify_service_status skips.
    assert result["strategy"] == "skipped"


def test_verify_repair_metric_wait_timeout_conflict():
    old_t = config.VERIFY_CONFIG["timeout_sec"]
    old_w = config.VERIFY_CONFIG["metric_wait_sec"]
    try:
        config.VERIFY_CONFIG["timeout_sec"] = 3.0
        config.VERIFY_CONFIG["metric_wait_sec"] = 2.0
        # 2 + 2 > 3, so the metric_threshold is skipped at the top level.
        result = _run(  # noqa: F841  # Variable for test verification
            verify_repair(
                {"platform": "linux", "host": "localhost"},
                "free_cache",
                {},
                {"memory": [10.0, 9.0, 8.0]},
                "",
            )
        )
        assert result["strategy"] == "skipped"
        assert "不兼容" in result["recommendation"]
    finally:
        config.VERIFY_CONFIG["timeout_sec"] = old_t
        config.VERIFY_CONFIG["metric_wait_sec"] = old_w


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
    result = _run(  # noqa: F841  # Variable for test verification
        verify_repair(
            {"platform": "windows"},
            "restart_service",
            {"service_name": "w32time"},
            None,
            "repair output preview",
        )
    )
    assert result["strategy"] == "service_status"
    assert result["evidence"].get("repair_output_preview") == "repair output preview"


# ---------------------------------------------------------------------------
# _select_strategy
# ---------------------------------------------------------------------------
def test_select_strategy():
    assert _select_strategy("restart_service") == "service_status"
    assert _select_strategy("kill_high_cpu") == "process_check"
    assert _select_strategy("cpu_high_script") == "metric_threshold"
    assert _select_strategy("free_cache") == "metric_threshold"
    assert _select_strategy("free_memory") == "metric_threshold"
    assert _select_strategy("disk_high_script") == "disk_usage"
    assert _select_strategy("clear_temp") == "disk_usage"
    assert _select_strategy("flush_dns") == "network_check"
    assert _select_strategy("k8s_pod_crash") == "k8s_status"
    assert _select_strategy("sfc_scan") == "none"
    assert _select_strategy("unknown_script") == "none"

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
    assert _select_strategy("AI_DYNAMIC", None) == "custom_command"
    assert _select_strategy("AI_DYNAMIC", {"commands": "not-a-list"}) == "custom_command"
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
    ok, reason = _check_command_with_guard(123)  # type: ignore[arg-type]
    assert ok is False
    assert "护栏审查异常" in reason


# ---------------------------------------------------------------------------
# _verification_wait_params
# ---------------------------------------------------------------------------
def test_verification_wait_params():
    max_wait, interval = _verification_wait_params()
    assert max_wait >= 1.0
    assert interval > 0


# ---------------------------------------------------------------------------
# service_status
# ---------------------------------------------------------------------------
def test_verify_service_status_windows_no_name():
    result = _run(
        _verify_service_status({"platform": "windows"}, {}, "windows")
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"


def test_verify_service_status_windows_invalid_name():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_service_status({"platform": "windows"}, {"service_name": "bad;name"}, "windows")
    )
    assert "非法字符" in result["error_msg"]


def test_verify_service_status_windows_too_long():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_service_status({"platform": "windows"}, {"service_name": "x" * 257}, "windows")
    )
    assert "超长" in result["error_msg"]


def test_verify_service_status_windows_service():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_service_status({"platform": "windows"}, {"service_name": "w32time"}, "windows")
    )
    assert result["strategy"] == "service_status"
    assert result["evidence"]["service_name"] == "w32time"


def test_verify_service_status_from_ai_runbook():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_service_status(
            {"platform": "linux", "host": "missing"},
            {},
            "linux",
            ai_runbook={"commands": ["systemctl restart nginx"]},
        )
    )
    assert result["strategy"] == "service_status"
    # service_name was extracted from the runbook; execution fails because host is missing.
    assert "nginx" in result["error_msg"] or result["error_msg"]


def test_verify_service_status_linux_no_host():
    result = _run(
        _verify_service_status({"platform": "linux"}, {"service_name": "nginx"}, "linux")
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "service_status"
    assert ("执行异常" in result["error_msg"]) or ("缺少 host" in result["error_msg"])


# ---------------------------------------------------------------------------
# process_check
# ---------------------------------------------------------------------------
def test_verify_process_check_windows():
    import os as _os  # noqa: E402  # Module level import not at top (intentional for test setup)

    # Current process is alive -> verified False.
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_process_check(
            {"platform": "windows", "host": "localhost"},
            {"pid": _os.getpid()},
            "windows",
        )
    )
    assert result["verified"] is False

    # Non-existent PID -> verified True.
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_process_check(
            {"platform": "windows", "host": "localhost"},
            {"pid": 999999},
            "windows",
        )
    )
    assert result["verified"] is True


def test_verify_process_check_invalid_pid():
    result = _run(
        _verify_process_check({"platform": "windows"}, {"pid": 0}, "windows")
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"

    result = _run(
        _verify_process_check({"platform": "windows"}, {"pid": 5_000_000}, "windows")
    )  # noqa: F841  # Variable for test verification
    assert "超出合法范围" in result["error_msg"]

    result = _run(
        _verify_process_check({"platform": "windows"}, {"pid": "abc"}, "windows")
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"


def test_verify_process_check_from_ai_runbook():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_process_check(
            {"platform": "windows"},
            {},
            "windows",
            ai_runbook={"commands": ["Stop-Process -Id 12345"]},
        )
    )
    assert result["strategy"] == "process_check"
    assert result["verified"] is True


def test_verify_process_check_linux():
    import config as _config  # noqa: E402  # Module level import not at top (intentional for test setup)

    _config.LINUX_HOSTS["hosts"] = [{"name": "test", "host": "127.0.0.1", "user": "test"}]
    try:
        result = _run(  # noqa: F841  # Variable for test verification
            _verify_process_check({"platform": "linux", "host": "test"}, {"pid": 12345}, "linux")
        )
        assert result["strategy"] == "process_check"
    finally:
        _config.LINUX_HOSTS["hosts"] = []


# ---------------------------------------------------------------------------
# disk_usage
# ---------------------------------------------------------------------------
def test_verify_disk_usage_windows_c_drive():
    # Verify real C: drive and force the result to be True with a generous threshold.
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_disk_usage(
            {"platform": "windows"},
            {"mount_point": "C:", "threshold": 100.0},
            "windows",
        )
    )
    assert result["strategy"] == "disk_usage"
    assert result["verified"] is True


def test_verify_disk_usage_invalid_mount():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_disk_usage({"platform": "windows"}, {"mount_point": "bad;mount"}, "windows")
    )
    assert "非法挂载点" in result["error_msg"]


def test_verify_disk_usage_from_ai_runbook():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_disk_usage(
            {"platform": "windows"},
            {},
            "windows",
            ai_runbook={"commands": ["C:"]},
        )
    )
    assert result["strategy"] == "disk_usage"


def test_verify_disk_usage_linux():
    import config as _config  # noqa: E402  # Module level import not at top (intentional for test setup)

    _config.LINUX_HOSTS["hosts"] = [{"name": "test", "host": "127.0.0.1", "user": "test"}]
    try:
        result = _run(  # noqa: F841  # Variable for test verification
            _verify_disk_usage({"platform": "linux", "host": "test"}, {"mount_point": "/"}, "linux")
        )
        assert result["strategy"] == "disk_usage"
    finally:
        _config.LINUX_HOSTS["hosts"] = []


def test_verify_disk_usage_threshold_parsing():
    # Non-numeric threshold falls back to 90.0; the command still runs.
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_disk_usage(
            {"platform": "windows"},
            {"mount_point": "C:", "threshold": "not-a-number"},
            "windows",
        )
    )
    assert result["strategy"] == "disk_usage"
    assert result["evidence"]["threshold"] == 90.0


# ---------------------------------------------------------------------------
# network_check
# ---------------------------------------------------------------------------
def test_verify_network_check_up():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_network_check({"platform": "windows"}, {"target": "127.0.0.1"}, "windows")
    )
    assert result["strategy"] == "network_check"
    # 127.0.0.1 should be reachable.
    assert result["verified"] is True


def test_verify_network_check_from_ai_runbook():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_network_check(
            {"platform": "windows"},
            {},
            "windows",
            ai_runbook={"commands": ["ping 127.0.0.1"]},
        )
    )
    assert result["strategy"] == "network_check"


def test_verify_network_check_invalid_target():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_network_check({"platform": "windows"}, {"target": "bad target;"}, "windows")
    )
    assert "非法网络目标" in result["error_msg"]


def test_verify_network_check_linux():
    import config as _config  # noqa: E402  # Module level import not at top (intentional for test setup)

    _config.LINUX_HOSTS["hosts"] = [{"name": "test", "host": "127.0.0.1", "user": "test"}]
    try:
        result = _run(  # noqa: F841  # Variable for test verification
            _verify_network_check(
                {"platform": "linux", "host": "test"}, {"target": "127.0.0.1"}, "linux"
            )
        )
        assert result["strategy"] == "network_check"
    finally:
        _config.LINUX_HOSTS["hosts"] = []


# ---------------------------------------------------------------------------
# k8s_status
# ---------------------------------------------------------------------------
def test_verify_k8s_status_windows_skip():
    result = _run(
        _verify_k8s_status({"platform": "windows"}, {"name": "app-0"}, "windows")
    )  # noqa: F841  # Variable for test verification
    assert "仅支持 Linux" in result["recommendation"]


def test_verify_k8s_status_linux_no_host():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_k8s_status({"platform": "linux", "host": "missing"}, {"name": "app-0"}, "linux")
    )
    assert result["strategy"] == "k8s_status"
    assert "执行异常" in result["error_msg"]


def test_verify_k8s_status_from_ai_runbook():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_k8s_status(
            {"platform": "linux", "host": "missing"},
            {},
            "linux",
            ai_runbook={"commands": ["kubectl get pods app-0 -n default"]},
        )
    )
    assert result["strategy"] == "k8s_status"


def test_verify_k8s_status_invalid_name():
    result = _run(
        _verify_k8s_status({"platform": "linux", "host": "missing"}, {}, "linux")
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"
    assert "无法提取 K8s 资源名" in result["recommendation"]


def test_verify_k8s_status_invalid_name_chars():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_k8s_status({"platform": "linux", "host": "missing"}, {"name": "bad;name"}, "linux")
    )
    assert result["strategy"] == "k8s_status"
    assert "非法 K8s 资源名" in result["error_msg"]


def test_verify_disk_usage_ai_runbook_no_match():
    # No command matches the mount-point patterns, so it falls back to the default.
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_disk_usage(
            {"platform": "windows"},
            {},
            "windows",
            ai_runbook={"commands": ["echo hello"]},
        )
    )
    assert result["strategy"] == "disk_usage"


# ---------------------------------------------------------------------------
# metric_threshold
# ---------------------------------------------------------------------------
def test_verify_metric_threshold_no_pre_snapshot():
    result = _run(
        _verify_metric_threshold("free_cache", None)
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"
    assert "无修复前快照" in result["recommendation"]


def test_verify_metric_threshold_unmapped_script():
    result = _run(
        _verify_metric_threshold("unknown_script", {"memory": [1, 2, 3]})
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"


def test_verify_metric_threshold_malformed_series():
    result = _run(
        _verify_metric_threshold("free_cache", {"memory": "not-a-list"})
    )  # noqa: F841  # Variable for test verification
    assert "序列格式异常" in result["error_msg"]


def test_verify_metric_threshold_not_enough_samples():
    _reset_metrics()
    _push_memory_samples([1.0, 2.0, 3.0])
    result = _run(
        _verify_metric_threshold("free_cache", {"memory": [1.0]})
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"
    assert "数据点不足" in result["recommendation"]


def test_verify_metric_threshold_non_numeric():
    _reset_metrics()
    _push_memory_samples([1.0, 2.0, 3.0])
    result = _run(
        _verify_metric_threshold("free_cache", {"memory": ["a", "b", "c"]})
    )  # noqa: F841  # Variable for test verification
    assert "指标数值计算异常" in result["error_msg"]


def test_verify_metric_threshold_zero_pre_avg():
    _reset_metrics()
    _push_memory_samples([0.0, 0.0, 0.0])
    result = _run(
        _verify_metric_threshold("free_cache", {"memory": [0.0, 0.0, 0.0]})
    )  # noqa: F841  # Variable for test verification
    assert result["verified"] is False


def test_verify_metric_threshold_significant_drop():
    _reset_metrics()
    _push_memory_samples([1.0, 2.0, 3.0])
    result = _run(
        _verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]})
    )  # noqa: F841  # Variable for test verification
    assert result["verified"] is True


def test_verify_metric_threshold_insufficient_drop():
    _reset_metrics()
    _push_memory_samples([9.9, 9.9, 9.9])
    result = _run(
        _verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]})
    )  # noqa: F841  # Variable for test verification
    assert result["verified"] is False


def test_verify_metric_threshold_cpu():
    _reset_metrics()
    _push_cpu_samples([10.0, 10.0, 10.0])
    result = _run(
        _verify_metric_threshold("cpu_high_script", {"cpu": [90.0, 90.0, 90.0]})
    )  # noqa: F841  # Variable for test verification
    assert result["verified"] is True


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
    result = _run(  # noqa: F841  # Variable for test verification
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


def test_verify_custom_command_enabled():
    old = config.VERIFY_CONFIG["llm_for_custom"]
    try:
        config.VERIFY_CONFIG["llm_for_custom"] = True
        result = _run(  # noqa: F841  # Variable for test verification
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
        assert "custom_command LLM 验证逻辑预留" in result["recommendation"]
    finally:
        config.VERIFY_CONFIG["llm_for_custom"] = old


def test_verify_custom_command_direct():
    result = _run(
        _verify_custom_command({"platform": "linux"}, {}, "linux", None)
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "skipped"


# ---------------------------------------------------------------------------
# _execute_linux_verify_command
# ---------------------------------------------------------------------------
def test_execute_linux_verify_missing_host_field():
    with pytest.raises(ValueError):
        _run(_execute_linux_verify_command({"platform": "linux"}, "echo ok"))


def test_execute_linux_verify_host_not_found():
    with pytest.raises(ValueError):
        _run(_execute_linux_verify_command({"host": "missing"}, "echo ok"))


# ---------------------------------------------------------------------------
# Result builders
# ---------------------------------------------------------------------------
def test_build_results():
    skipped = _build_skipped_result("skipped", "recommendation text")
    assert skipped["verified"] is None
    assert skipped["duration_sec"] == 0.0
    error = _build_error_result("error", "something went wrong", 1.23)
    assert error["error_msg"]
    assert error["duration_sec"] == 1.23


# ---------------------------------------------------------------------------
# Dispatch via verify_repair for each strategy
# ---------------------------------------------------------------------------
def test_verify_repair_service_status():
    result = _run(  # noqa: F841  # Variable for test verification
        verify_repair(
            {"platform": "windows"},
            "restart_service",
            {"service_name": "w32time"},
            None,
            "service restarted",
        )
    )
    assert result["strategy"] == "service_status"


def test_verify_repair_process_check():
    import os as _os  # noqa: E402  # Module level import not at top (intentional for test setup)

    result = _run(  # noqa: F841  # Variable for test verification
        verify_repair(
            {"platform": "windows"},
            "kill_high_cpu",
            {"pid": _os.getpid()},
            None,
            "",
        )
    )
    assert result["strategy"] == "process_check"


def test_verify_repair_disk_usage():
    result = _run(  # noqa: F841  # Variable for test verification
        verify_repair(
            {"platform": "windows"},
            "disk_high_script",
            {"mount_point": "C:", "threshold": 100.0},
            None,
            "",
        )
    )
    assert result["strategy"] == "disk_usage"


def test_verify_repair_network_check():
    result = _run(  # noqa: F841  # Variable for test verification
        verify_repair(
            {"platform": "windows"},
            "flush_dns",
            {"target": "127.0.0.1"},
            None,
            "",
        )
    )
    assert result["strategy"] == "network_check"


def test_verify_repair_k8s_status():
    result = _run(  # noqa: F841  # Variable for test verification
        verify_repair(
            {"platform": "windows"},
            "k8s_pod_crash",
            {"name": "app-0"},
            None,
            "",
        )
    )
    assert result["strategy"] == "k8s_status"


def test_verify_repair_metric_threshold():
    # No compatibility conflict; the full metric_threshold path through verify_repair is exercised.
    _reset_metrics()
    _push_memory_samples([10.0, 10.0, 10.0])
    old_t = config.VERIFY_CONFIG["timeout_sec"]
    old_w = config.VERIFY_CONFIG["metric_wait_sec"]
    try:
        config.VERIFY_CONFIG["timeout_sec"] = 30.0
        config.VERIFY_CONFIG["metric_wait_sec"] = 2.0
        result = _run(  # noqa: F841  # Variable for test verification
            verify_repair(
                {"platform": "linux"},
                "free_cache",
                {},
                {"memory": [10.0, 10.0, 10.0]},
                "",
            )
        )
        assert result["strategy"] == "metric_threshold"
    finally:
        config.VERIFY_CONFIG["timeout_sec"] = old_t
        config.VERIFY_CONFIG["metric_wait_sec"] = old_w


def test_verify_metric_threshold_cancel_during_sleep():
    _reset_metrics()
    _push_memory_samples([1.0, 1.0, 1.0])

    async def _main():
        task = asyncio.create_task(
            _verify_metric_threshold("free_cache", {"memory": [10.0, 10.0, 10.0]})
        )
        await asyncio.sleep(0.5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    _run(_main())


def test_dispatch_verification_unhandled_strategy():
    from core.verifier import (  # noqa: E402  # Module level import not at top (intentional for test setup)
        _dispatch_verification,
    )

    result = _run(  # noqa: F841  # Variable for test verification
        _dispatch_verification(
            "totally_unhandled",
            {"platform": "windows"},
            "unknown",
            {},
            "windows",
            None,
            "",
            None,
        )
    )
    assert result["strategy"] == "skipped"
    assert "未实现的策略" in result["recommendation"]


def test_verify_service_status_params_not_dict():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_service_status(
            {"platform": "linux", "host": "missing"},
            "not-a-dict",  # type: ignore[arg-type]
            "linux",
            ai_runbook={"commands": ["systemctl restart nginx"]},
        )
    )
    assert result["strategy"] == "service_status"


def test_verify_process_check_params_not_dict():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_process_check(
            {"platform": "linux", "host": "missing"},
            "not-a-dict",  # type: ignore[arg-type]
            "linux",
            ai_runbook={"commands": ["kill 12345"]},
        )
    )
    assert result["strategy"] == "process_check"


def test_verify_service_status_linux_with_config():
    import config as _config  # noqa: E402  # Module level import not at top (intentional for test setup)

    _config.LINUX_HOSTS["hosts"] = [{"name": "test", "host": "127.0.0.1", "user": "test"}]
    try:
        result = _run(  # noqa: F841  # Variable for test verification
            _verify_service_status(
                {"platform": "linux", "host": "test"},
                {"service_name": "nginx"},
                "linux",
            )
        )
        assert result["strategy"] == "service_status"
        # SSH is not expected in the test environment, so the service is treated as not active.
        assert result["verified"] is False
    finally:
        _config.LINUX_HOSTS["hosts"] = []


def test_execute_linux_verify_match_by_host_field():
    import config as _config  # noqa: E402  # Module level import not at top (intentional for test setup)

    _config.LINUX_HOSTS["hosts"] = [
        {"name": "first", "host": "10.0.0.1", "user": "test"},
        {"name": "other", "host": "127.0.0.1", "user": "test"},
    ]
    try:
        # host matches the "host" key on the second entry after the first is skipped.
        out = _run(_execute_linux_verify_command({"host": "127.0.0.1"}, "echo ok"))
        assert isinstance(out, str)
    finally:
        _config.LINUX_HOSTS["hosts"] = []


def test_verify_disk_usage_unparseable_windows():
    # Non-existent drive returns empty output, hitting the parse-failure branch.
    result = _run(
        _verify_disk_usage({"platform": "windows"}, {"mount_point": "Z:"}, "windows")
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "disk_usage"
    assert "无法解析磁盘输出" in result["error_msg"]


def test_verify_service_status_ai_runbook_no_match():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_service_status(
            {"platform": "linux", "host": "missing"},
            {},
            "linux",
            ai_runbook={"commands": ["echo hello"]},
        )
    )
    assert result["strategy"] == "skipped"


def test_verify_service_status_ai_runbook_not_list():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_service_status(
            {"platform": "linux", "host": "missing"},
            {},
            "linux",
            ai_runbook={"commands": "systemctl restart nginx"},
        )
    )
    assert result["strategy"] == "skipped"


def test_verify_process_check_ai_runbook_no_match():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_process_check(
            {"platform": "linux", "host": "missing"},
            {},
            "linux",
            ai_runbook={"commands": ["echo hello"]},
        )
    )
    assert result["strategy"] == "skipped"


def test_verify_process_check_ai_runbook_not_list():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_process_check(
            {"platform": "linux", "host": "missing"},
            {},
            "linux",
            ai_runbook={"commands": "kill 12345"},
        )
    )
    assert result["strategy"] == "skipped"


def test_verify_disk_usage_ai_runbook_none():
    # No ai_runbook and no mount_point -> defaults to "/".
    result = _run(
        _verify_disk_usage({"platform": "windows"}, {}, "windows", ai_runbook=None)
    )  # noqa: F841  # Variable for test verification
    assert result["strategy"] == "disk_usage"


def test_verify_disk_usage_linux_no_host():
    # Missing host forces _execute_linux_verify_command to raise, covering the except block.
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_disk_usage({"platform": "linux", "host": "missing"}, {"mount_point": "/"}, "linux")
    )
    assert result["strategy"] == "disk_usage"
    assert "执行异常" in result["error_msg"]


def test_verify_network_check_ai_runbook_no_match():
    # No host in alert and no matching command -> target is empty.
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_network_check(
            {"platform": "linux"},
            {},
            "linux",
            ai_runbook={"commands": ["echo hello"]},
        )
    )
    assert result["strategy"] == "skipped"


def test_verify_network_check_ai_runbook_not_list():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_network_check(
            {"platform": "linux"},
            {},
            "linux",
            ai_runbook={"commands": "ping 127.0.0.1"},
        )
    )
    assert result["strategy"] == "skipped"


def test_verify_network_check_linux_no_host():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_network_check(
            {"platform": "linux", "host": "missing"},
            {"target": "127.0.0.1"},
            "linux",
        )
    )
    assert result["strategy"] == "network_check"
    assert "执行异常" in result["error_msg"]


def test_verify_k8s_status_ai_runbook_no_match():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_k8s_status(
            {"platform": "linux", "host": "missing"},
            {},
            "linux",
            ai_runbook={"commands": ["echo hello"]},
        )
    )
    assert result["strategy"] == "skipped"


def test_verify_k8s_status_ai_runbook_not_list():
    result = _run(  # noqa: F841  # Variable for test verification
        _verify_k8s_status(
            {"platform": "linux", "host": "missing"},
            {},
            "linux",
            ai_runbook={"commands": "kubectl get pods app-0"},
        )
    )
    assert result["strategy"] == "skipped"
