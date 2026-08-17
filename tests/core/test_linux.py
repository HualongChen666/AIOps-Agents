# -*- coding: utf-8 -*-
"""Tests for core/linux_collector.py and core/linux_repair.py helpers."""

import pytest  # noqa: F401  # Imported for test setup

from core import linux_collector, linux_repair


def test_get_last_snapshot():
    linux_collector._last_collect_cache = {}
    assert linux_collector.get_last_snapshot() == {}


def test_host_cooldown():
    host = "test-host"
    assert linux_collector._is_host_in_cooldown(host) is False
    for _ in range(linux_collector._HOST_MAX_FAILURES):
        linux_collector._record_host_failure(host)
    assert linux_collector._is_host_in_cooldown(host) is True
    status = linux_collector.get_host_cooldown_status()
    assert status["total_tracked"] >= 1
    assert any(item["host"] == host for item in status["stale_hosts"])
    linux_collector._record_host_success(host)
    assert linux_collector._is_host_in_cooldown(host) is False


def test_get_available_metrics_and_hosts():
    metrics = linux_collector.get_available_metrics()
    assert isinstance(metrics, list)
    assert all("key" in m and "desc" in m for m in metrics)
    hosts = linux_collector.get_configured_hosts()
    assert isinstance(hosts, list)


def test_sanitize_param():
    assert linux_repair._sanitize_param("service_name", "nginx.service") == "nginx.service"
    assert linux_repair._sanitize_param("pid", "12345") == "12345"
    with pytest.raises(ValueError):
        linux_repair._sanitize_param("service_name", "../../etc/passwd")


def test_validate_and_prepare_script():
    script = linux_repair._validate_script_key("restart_service")
    assert script is not None
    assert script["params"] == ["service_name"]
    safe, err = linux_repair._prepare_safe_params({"service_name": "nginx"}, script)
    assert err is None
    assert safe["service_name"] == "nginx"


def test_render_command():
    script = linux_repair._validate_script_key("restart_service")
    safe = {"service_name": "nginx"}
    cmd = linux_repair._render_command(script, safe)
    assert "systemctl restart nginx" in cmd


def test_normalize_ssh_output_and_success():
    assert linux_repair._normalize_ssh_output(None) == ""
    assert linux_repair._normalize_ssh_output(b"hello") == "hello"
    assert linux_repair._is_execution_success("ok") is True
    assert linux_repair._is_execution_success("TIMEOUT") is False
    assert linux_repair._is_execution_success("ERROR: failed") is False


def test_repair_scripts():
    scripts = linux_repair.get_linux_repair_scripts()
    assert "restart_service" in scripts
    history = linux_repair.get_linux_repair_history(limit=10)
    assert isinstance(history, list)
    cleared = linux_repair.clear_linux_repair_history()
    assert cleared == 0
