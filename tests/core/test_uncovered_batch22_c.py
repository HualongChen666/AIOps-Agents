# -*- coding: utf-8 -*-
"""Targeted coverage tests for core/performance_tuning.py, core/linux_collector.py,
core/integration_manager.py, core/error_handling_logging.py, and
core/monitoring_system_integrator.py.
"""

import asyncio
import hashlib
import hmac
import importlib
import json
import os
import sys
import time
import types
from unittest.mock import AsyncMock, MagicMock

import pytest

pytestmark = [pytest.mark.core]

import core.integration_manager as im
import core.linux_collector as lc
import core.performance_tuning as pt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _ssh_proc(stdout: bytes, stderr: bytes = b"", returncode: int = 0):
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = MagicMock()
    proc.wait = AsyncMock()
    return proc


# ---------------------------------------------------------------------------
# core/performance_tuning.py
# ---------------------------------------------------------------------------
def test_system_limits():
    result = pt.apply_system_limits()
    assert "max_open_files" in result
    if sys.platform == "win32":
        assert "Skipped on Windows" in result["max_open_files"]


def test_python_optimizations():
    result = pt.apply_python_optimizations()
    assert "gc_threshold" in result
    assert "asyncio_threads" in result


def test_uvicorn_config():
    config = pt.get_uvicorn_config()
    assert config["workers"] == pt.PERFORMANCE_TUNING_CONFIG["uvicorn_workers"]
    assert config["log_level"] == "info"


def test_environment_tuning(monkeypatch):
    monkeypatch.setattr(pt.os, "environ", {})
    result = pt.apply_environment_tuning()
    assert result["python_optimize"] == "Set to 2"
    assert result["python_unbuffered"] == "Set to 1"
    assert result["dont_write_bytecode"] == "Set to 1"
    assert result["timezone"] == "Set to UTC"


def test_python_optimizations_failure(monkeypatch):
    monkeypatch.setattr("gc.set_threshold", MagicMock(side_effect=Exception("boom")))
    result = pt.apply_python_optimizations()
    assert "error" in result


def test_get_performance_recommendations(monkeypatch):
    vm = types.SimpleNamespace(total=16 * 1024**3)
    fake_psutil = MagicMock()
    fake_psutil.cpu_count = MagicMock(return_value=8)
    fake_psutil.virtual_memory = MagicMock(return_value=vm)
    fake_platform = MagicMock()
    fake_platform.system = MagicMock(return_value="Linux")
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
    monkeypatch.setitem(sys.modules, "platform", fake_platform)

    result = pt.get_performance_recommendations()
    assert result["system_info"]["cpu_count"] == 8
    recs = [r["area"] for r in result["recommendations"]]
    assert "worker_processes" in recs
    assert "connection_pool" in recs
    assert "system_limits" in recs


def test_get_performance_recommendations_low_resources(monkeypatch):
    vm = types.SimpleNamespace(total=4 * 1024**3)
    fake_psutil = MagicMock()
    fake_psutil.cpu_count = MagicMock(return_value=2)
    fake_psutil.virtual_memory = MagicMock(return_value=vm)
    fake_platform = MagicMock()
    fake_platform.system = MagicMock(return_value="Windows")
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
    monkeypatch.setitem(sys.modules, "platform", fake_platform)

    result = pt.get_performance_recommendations()
    assert result["recommendations"] == []


def test_monitor_performance_metrics(monkeypatch):
    vm = types.SimpleNamespace(total=8 * 1024**3, available=4 * 1024**3, percent=50.0)
    disk = types.SimpleNamespace(
        total=100 * 1024**3, used=50 * 1024**3, free=50 * 1024**3, percent=50.0
    )
    net = types.SimpleNamespace(bytes_sent=1000, bytes_recv=2000, packets_sent=10, packets_recv=20)
    fake_psutil = MagicMock()
    fake_psutil.cpu_percent = MagicMock(return_value=12.34)
    fake_psutil.cpu_count = MagicMock(return_value=4)
    fake_psutil.virtual_memory = MagicMock(return_value=vm)
    fake_psutil.disk_usage = MagicMock(return_value=disk)
    fake_psutil.net_io_counters = MagicMock(return_value=net)
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    metrics = pt.monitor_performance_metrics()
    assert metrics["cpu"]["usage_percent"] == "12.34"
    assert "memory" in metrics
    assert "disk" in metrics
    assert "network" in metrics


def test_monitor_performance_metrics_failure(monkeypatch):
    fake_psutil = MagicMock()
    fake_psutil.cpu_percent = MagicMock(side_effect=Exception("boom"))
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)

    result = pt.monitor_performance_metrics()
    assert "error" in result
    assert "timestamp" in result


def test_apply_comprehensive_tuning(monkeypatch):
    vm = types.SimpleNamespace(total=16 * 1024**3, available=8 * 1024**3, percent=50.0)
    disk = types.SimpleNamespace(
        total=100 * 1024**3, used=50 * 1024**3, free=50 * 1024**3, percent=50.0
    )
    net = types.SimpleNamespace(bytes_sent=1000, bytes_recv=2000, packets_sent=10, packets_recv=20)
    fake_psutil = MagicMock()
    fake_psutil.cpu_percent = MagicMock(return_value=5.0)
    fake_psutil.cpu_count = MagicMock(return_value=8)
    fake_psutil.virtual_memory = MagicMock(return_value=vm)
    fake_psutil.disk_usage = MagicMock(return_value=disk)
    fake_psutil.net_io_counters = MagicMock(return_value=net)
    fake_platform = MagicMock()
    fake_platform.system = MagicMock(return_value="Linux")
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
    monkeypatch.setitem(sys.modules, "platform", fake_platform)
    monkeypatch.setattr(pt.os, "environ", {})

    result = pt.apply_comprehensive_tuning()
    assert "timestamp" in result
    assert "steps" in result
    assert "system_limits" in result["steps"]
    assert "python_optimizations" in result["steps"]
    assert "environment_tuning" in result["steps"]
    assert "uvicorn_config" in result["steps"]
    assert "recommendations" in result["steps"]


def test_system_limits_non_windows(monkeypatch):
    fake_resource = MagicMock()
    fake_resource.RLIMIT_NOFILE = 0
    fake_resource.RLIMIT_AS = 1
    fake_resource.getrlimit = MagicMock(side_effect=[(1024, 4096), (1024**3, -1)])
    fake_resource.setrlimit = MagicMock()
    monkeypatch.setitem(sys.modules, "resource", fake_resource)
    monkeypatch.setattr(pt, "resource", fake_resource, raising=False)
    monkeypatch.setattr(pt.sys, "platform", "linux")
    result = pt.apply_system_limits()
    assert "max_open_files" in result
    assert "memory_limit_mb" in result


def test_python_optimizations_asyncio_failure(monkeypatch):
    monkeypatch.setattr(pt.asyncio, "get_event_loop", MagicMock(side_effect=Exception("no loop")))
    result = pt.apply_python_optimizations()
    assert "error" not in result
    assert "Failed to set" in result["asyncio_threads"]


def test_environment_tuning_failure(monkeypatch):
    fake_env = MagicMock()
    fake_env.__setitem__ = MagicMock(side_effect=Exception("read-only"))
    fake_os = types.SimpleNamespace(environ=fake_env)
    monkeypatch.setattr(pt, "os", fake_os)
    result = pt.apply_environment_tuning()
    assert "error" in result


def test_get_performance_recommendations_medium_cpu(monkeypatch):
    vm = types.SimpleNamespace(total=8 * 1024**3)
    fake_psutil = MagicMock()
    fake_psutil.cpu_count = MagicMock(return_value=4)
    fake_psutil.virtual_memory = MagicMock(return_value=vm)
    fake_platform = MagicMock()
    fake_platform.system = MagicMock(return_value="Linux")
    monkeypatch.setitem(sys.modules, "psutil", fake_psutil)
    monkeypatch.setitem(sys.modules, "platform", fake_platform)
    result = pt.get_performance_recommendations()
    recs = [r["area"] for r in result["recommendations"]]
    assert "worker_processes" in recs
    assert "connection_pool" not in recs


# ---------------------------------------------------------------------------
# core/linux_collector.py
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_linux_collector_state():
    lc._host_failure_tracker.clear()
    with lc._last_collect_cache_lock:
        lc._last_collect_cache.clear()
    with lc._host_semaphores_lock:
        lc._host_semaphores.clear()
    yield


def test_get_last_snapshot_and_available_metrics():
    assert lc.get_last_snapshot() == {}
    metrics = lc.get_available_metrics()
    assert isinstance(metrics, list)
    assert all("key" in m and "desc" in m for m in metrics)


def test_get_configured_hosts(monkeypatch):
    monkeypatch.setattr(
        lc,
        "LINUX_HOSTS",
        {
            "hosts": [
                {
                    "name": "h1",
                    "host": "10.0.0.1",
                    "port": 2222,
                    "username": "u",
                    "key_file": "/key",
                    "role": "web",
                    "layer": 2,
                    "downstream": ["db"],
                }
            ]
        },
    )
    hosts = lc.get_configured_hosts()
    assert hosts[0]["name"] == "h1"
    assert hosts[0]["port"] == 2222
    assert hosts[0]["auth"] == "key"
    assert hosts[0]["role"] == "web"


def test_get_host_semaphore():
    sem1 = lc._get_host_semaphore("h1")
    sem2 = lc._get_host_semaphore("h1")
    assert sem1 is sem2
    assert isinstance(sem1, asyncio.Semaphore)


def test_host_failure_tracker_and_cooldown(monkeypatch):
    monkeypatch.setattr(lc, "_HOST_MAX_FAILURES", 1)
    monkeypatch.setattr(lc, "_HOST_COOLDOWN_SEC", 300)
    host = "h1"
    assert lc._is_host_in_cooldown(host) is False
    lc._record_host_failure(host)
    assert lc._is_host_in_cooldown(host) is True
    status = lc.get_host_cooldown_status()
    assert status["total_tracked"] == 1
    assert any(item["host"] == host for item in status["stale_hosts"])
    lc._record_host_success(host)
    assert lc._is_host_in_cooldown(host) is False


def test_cooldown_expiry_and_time_reversal(monkeypatch):
    monkeypatch.setattr(lc, "_HOST_MAX_FAILURES", 1)
    monkeypatch.setattr(lc, "_HOST_COOLDOWN_SEC", 10)
    host = "h1"
    now = time.monotonic()
    lc._host_failure_tracker[host] = {"count": 1, "last_fail": now - 20}
    assert lc._is_host_in_cooldown(host) is False

    lc._host_failure_tracker[host] = {"count": 1, "last_fail": now + 20}
    assert lc._is_host_in_cooldown(host) is False


@pytest.mark.asyncio
async def test_ssh_execute_invalid_inputs():
    assert await lc._ssh_execute("bad", "cmd") == "ERROR: invalid host_config"
    assert await lc._ssh_execute({"host": "1.2.3.4", "username": "u"}, "") == ""
    assert (await lc._ssh_execute({"host": "  ", "username": "u"}, "cmd")).startswith(
        "ERROR: host field missing"
    )
    assert (await lc._ssh_execute({"host": "1.2.3.4"}, "cmd")).startswith(
        "ERROR: username field missing"
    )


@pytest.mark.asyncio
async def test_ssh_execute_key_auth(monkeypatch):
    monkeypatch.setattr(
        lc.asyncio, "create_subprocess_exec", AsyncMock(return_value=_ssh_proc(b"ok"))
    )
    result = await lc._ssh_execute(
        {"host": "1.2.3.4", "username": "u", "key_file": "/key"}, "hostname"
    )
    assert result == "ok"


@pytest.mark.asyncio
async def test_ssh_execute_timeout(monkeypatch):
    proc = _ssh_proc(b"ok")
    monkeypatch.setattr(lc.asyncio, "create_subprocess_exec", AsyncMock(return_value=proc))
    monkeypatch.setattr(lc.asyncio, "wait_for", AsyncMock(side_effect=asyncio.TimeoutError()))
    result = await lc._ssh_execute(
        {"host": "1.2.3.4", "username": "u", "key_file": "/key"}, "hostname"
    )
    assert result == "TIMEOUT"
    assert proc.kill.called


@pytest.mark.asyncio
async def test_ssh_execute_file_not_found_key(monkeypatch):
    monkeypatch.setattr(
        lc.asyncio,
        "create_subprocess_exec",
        AsyncMock(side_effect=FileNotFoundError("no ssh")),
    )
    result = await lc._ssh_execute(
        {"host": "1.2.3.4", "username": "u", "key_file": "/key"}, "hostname"
    )
    assert result == "SSH_NOT_FOUND"


@pytest.mark.asyncio
async def test_ssh_execute_file_not_found_password(monkeypatch):
    monkeypatch.setattr(
        lc.asyncio,
        "create_subprocess_exec",
        AsyncMock(side_effect=FileNotFoundError("no sshpass")),
    )
    result = await lc._ssh_execute(
        {"host": "1.2.3.4", "username": "u", "password": "p"}, "hostname"
    )
    assert result == "SSHPASS_NOT_FOUND"


@pytest.mark.asyncio
async def test_ssh_execute_generic_exception(monkeypatch):
    monkeypatch.setattr(
        lc.asyncio,
        "create_subprocess_exec",
        AsyncMock(side_effect=Exception("boom")),
    )
    result = await lc._ssh_execute(
        {"host": "1.2.3.4", "username": "u", "key_file": "/key"}, "hostname"
    )
    assert result.startswith("ERROR:")
    assert "boom" in result


def test_parse_structured_metrics():
    result = {
        "metrics": {
            "cpu_usage": {"value": "45.5"},
            "memory": {"value": "8192 4096 2048 50.0"},
            "load_avg": {"value": "1.0 2.0 3.0 4"},
            "swap": {"value": "2048 0 0.0"},
        }
    }
    lc._parse_structured_metrics(result)
    assert result["metrics"]["cpu_usage"]["parsed"]["usage_percent"] == 45.5
    assert result["metrics"]["memory"]["parsed"]["used_mb"] == 4096
    assert result["metrics"]["load_avg"]["parsed"]["load_1min"] == 1.0
    assert result["metrics"]["swap"]["parsed"]["usage_percent"] == 0.0


def test_parse_structured_metrics_invalid_and_empty():
    result = {
        "metrics": {
            "cpu_usage": {"value": ""},
            "memory": {"value": "bad"},
            "swap": {"value": "1"},
        }
    }
    lc._parse_structured_metrics(result)
    assert "parsed" not in result["metrics"]["cpu_usage"]
    assert "parsed" not in result["metrics"]["memory"]
    assert "parsed" not in result["metrics"]["swap"]


@pytest.mark.asyncio
async def test_collect_linux_host_success(monkeypatch):
    monkeypatch.setattr(lc.secrets, "token_hex", lambda n: "a" * 32)
    monkeypatch.setattr(lc, "_SSH_BATCH_SIZE", 100)
    sep_prefix = f"===AIOPS{'a' * 32}METRIC:"
    sep_suffix = f":{'a' * 32}===AIOPSEND==="
    raw = (
        f"{sep_prefix}hostname{sep_suffix}\nmyhost\n"
        f"{sep_prefix}os_version{sep_suffix}\nUbuntu 20.04"
    )
    monkeypatch.setattr(
        lc.asyncio, "create_subprocess_exec", AsyncMock(return_value=_ssh_proc(raw.encode()))
    )
    result = await lc.collect_linux_host(
        {"name": "h1", "host": "10.0.0.1", "username": "u", "key_file": "/key"},
        metrics=["hostname", "os_version"],
    )
    assert result["status"] == "ok"
    assert result["metrics"]["hostname"]["value"] == "myhost"
    assert result["metrics"]["os_version"]["value"] == "Ubuntu 20.04"


@pytest.mark.asyncio
async def test_collect_linux_host_missing_config():
    result = await lc.collect_linux_host("not-a-dict")
    assert result["status"] == "error"

    result = await lc.collect_linux_host({"name": "h1"})
    assert result["status"] == "error"

    result = await lc.collect_linux_host({"name": "h1", "host": "10.0.0.1", "username": "u"})
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_collect_linux_host_degraded(monkeypatch):
    monkeypatch.setattr(lc.secrets, "token_hex", lambda n: "a" * 32)
    monkeypatch.setattr(lc, "_SSH_BATCH_SIZE", 100)
    sep_prefix = f"===AIOPS{'a' * 32}METRIC:"
    sep_suffix = f":{'a' * 32}===AIOPSEND==="
    raw = (
        f"{sep_prefix}hostname{sep_suffix}\nmyhost\n"
        f"{sep_prefix}cpu_usage{sep_suffix}\nTIMEOUT\n"
        f"{sep_prefix}memory{sep_suffix}\nERROR: boom"
    )
    monkeypatch.setattr(
        lc.asyncio, "create_subprocess_exec", AsyncMock(return_value=_ssh_proc(raw.encode()))
    )
    result = await lc.collect_linux_host(
        {"name": "h1", "host": "10.0.0.1", "username": "u", "key_file": "/key"},
        metrics=["hostname", "cpu_usage", "memory"],
    )
    assert result["status"] == "degraded"


@pytest.mark.asyncio
async def test_collect_linux_host_error_and_cooldown(monkeypatch):
    monkeypatch.setattr(lc, "_HOST_MAX_FAILURES", 1)
    monkeypatch.setattr(lc, "_HOST_COOLDOWN_SEC", 300)
    monkeypatch.setattr(
        lc.asyncio,
        "create_subprocess_exec",
        AsyncMock(return_value=_ssh_proc(b"TIMEOUT")),
    )
    host_cfg = {"name": "h1", "host": "10.0.0.1", "username": "u", "key_file": "/key"}
    result = await lc.collect_linux_host(host_cfg, metrics=["hostname"])
    assert result["status"] == "error"
    assert lc._is_host_in_cooldown("h1") is True

    cached = {"name": "h1", "status": "ok"}
    with lc._last_collect_cache_lock:
        lc._last_collect_cache["h1"] = cached
    result = await lc.collect_linux_host(host_cfg, metrics=["hostname"])
    assert result["status"] == "cached_stale"
    assert "stale_reason" in result
    assert "stale_at" in result


@pytest.mark.asyncio
async def test_collect_all_linux(monkeypatch):
    monkeypatch.setattr(lc.secrets, "token_hex", lambda n: "a" * 32)
    monkeypatch.setattr(lc, "_SSH_BATCH_SIZE", 100)
    monkeypatch.setattr(
        lc,
        "LINUX_HOSTS",
        {
            "hosts": [
                {"name": "h1", "host": "10.0.0.1", "username": "u", "key_file": "/key"},
                {"name": "h2", "host": "10.0.0.2", "username": "u", "key_file": "/key"},
            ]
        },
    )
    sep_prefix = f"===AIOPS{'a' * 32}METRIC:"
    sep_suffix = f":{'a' * 32}===AIOPSEND==="
    raw = f"{sep_prefix}hostname{sep_suffix}\nhost"
    monkeypatch.setattr(
        lc.asyncio, "create_subprocess_exec", AsyncMock(return_value=_ssh_proc(raw.encode()))
    )
    results = await lc.collect_all_linux(metrics=["hostname"])
    assert len(results) == 2
    assert results[0]["status"] == "ok"
    assert lc.get_last_snapshot()


@pytest.mark.asyncio
async def test_collect_all_linux_exception(monkeypatch):
    monkeypatch.setattr(
        lc,
        "collect_linux_host",
        AsyncMock(side_effect=[Exception("boom"), {"name": "h2"}]),
    )
    monkeypatch.setattr(
        lc,
        "LINUX_HOSTS",
        {
            "hosts": [
                {"name": "h1", "host": "10.0.0.1"},
                {"name": "h2", "host": "10.0.0.2"},
            ]
        },
    )
    results = await lc.collect_all_linux()
    assert results[0]["status"] == "error"
    assert results[1]["name"] == "h2"


# ---------------------------------------------------------------------------
# core/integration_manager.py
# ---------------------------------------------------------------------------
@pytest.fixture
def im_mod(monkeypatch):
    response = MagicMock()
    response.status_code = 200
    response.json = MagicMock(return_value={"status": "success", "data": {}})
    response.text = "ok"
    response.raise_for_status = MagicMock()

    client = AsyncMock()
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    client.aclose = AsyncMock()

    def _AsyncClient(*args, **kwargs):
        return client

    monkeypatch.setattr(im.httpx, "AsyncClient", _AsyncClient)

    cw = MagicMock()
    cw.get_metric_data = MagicMock(
        return_value={"MetricDataResults": [{"Timestamps": [], "Values": []}]}
    )
    fake_boto3 = MagicMock()
    fake_boto3.client = MagicMock(return_value=cw)
    monkeypatch.setattr(im, "boto3", fake_boto3, raising=False)
    monkeypatch.setattr(im, "BOTO3_AVAILABLE", True)

    async def _pass(coro, *args, **kwargs):
        return await coro

    monkeypatch.setattr(im, "with_query_timeout", _pass)
    return im


@pytest.mark.asyncio
async def test_register_and_test_prometheus(im_mod):
    mgr = im_mod.IntegrationManager()
    integration = await mgr.register_integration(
        im_mod.IntegrationType.MONITORING,
        "prometheus",
        {"url": "http://prom"},
    )
    assert integration.status == im_mod.IntegrationStatus.ACTIVE
    assert mgr.integrations[integration.integration_id] is integration

    result = await mgr.test_integration("missing-id")
    assert result["success"] is False


@pytest.mark.asyncio
async def test_register_integration_invalid_config(im_mod):
    mgr = im_mod.IntegrationManager()
    with pytest.raises(ValueError):
        await mgr.register_integration(
            im_mod.IntegrationType.MONITORING,
            "prometheus",
            {"url": 123},
        )


def test_validate_config(im_mod):
    mgr = im_mod.IntegrationManager()
    ok = mgr._validate_config({"url": "x"}, {"url": {"type": "string", "required": True}})
    assert ok["valid"] is True
    bad = mgr._validate_config({}, {"url": {"type": "string", "required": True}})
    assert bad["valid"] is False
    bad_type = mgr._validate_config({"url": 1}, {"url": {"type": "string", "required": True}})
    assert bad_type["valid"] is False


@pytest.mark.asyncio
async def test_notification_lifecycle(im_mod):
    mgr = im_mod.IntegrationManager(
        config={
            "notification_channels": {
                "slack": {
                    "type": "webhook",
                    "config": {"url": "http://slack"},
                    "enabled": True,
                },
                "disabled": {
                    "type": "webhook",
                    "config": {"url": "http://disabled"},
                    "enabled": False,
                },
                "email": {"type": "email", "config": {}, "enabled": True},
            }
        }
    )
    await mgr.register_integration(
        im_mod.IntegrationType.NOTIFICATION,
        "slack",
        {"webhook_url": "http://slack"},
    )

    msg = await mgr.send_notification("slack", "#alerts", "s", "b")
    assert msg.sent is True

    missing = await mgr.send_notification("missing", "r", "s", "b")
    assert missing.error is not None

    disabled = await mgr.send_notification("disabled", "r", "s", "b")
    assert "disabled" in disabled.error

    unsupported = await mgr.send_notification("email", "r", "s", "b")
    assert "Unsupported channel type" in unsupported.error


@pytest.mark.asyncio
async def test_webhook_lifecycle(im_mod):
    mgr = im_mod.IntegrationManager()
    webhook_id = await mgr.register_webhook(
        "alertmanager", "alert", "http://endpoint", secret="s3cret"
    )
    payload = {"event": "alert"}
    raw = json.dumps(payload, sort_keys=True)
    expected = hmac.new("s3cret".encode(), raw.encode(), hashlib.sha256).hexdigest()

    result = await mgr.handle_webhook(webhook_id, payload, signature=expected)
    assert result["success"] is True

    bad = await mgr.handle_webhook(webhook_id, payload, signature="wrong")
    assert bad["success"] is False

    missing = await mgr.handle_webhook("unknown", payload)
    assert missing["success"] is False

    deployment_id = await mgr.register_webhook("cicd", "deployment", "http://cicd")
    await mgr.handle_webhook(deployment_id, {"id": 1})

    incident_id = await mgr.register_webhook("pd", "incident", "http://pd")
    await mgr.handle_webhook(incident_id, {"id": 1})


@pytest.mark.asyncio
async def test_query_prometheus_metrics(im_mod):
    mgr = im_mod.IntegrationManager()
    integration = await mgr.register_integration(
        im_mod.IntegrationType.MONITORING,
        "prometheus",
        {"url": "http://prom"},
    )
    result = await mgr.query_prometheus_metrics(integration.integration_id, "up", "1h")
    assert "error" not in result

    assert (
        "Integration not found"
        in (await mgr.query_prometheus_metrics("missing", "up", "1h"))["error"]
    )

    aws = await mgr.register_integration(
        im_mod.IntegrationType.CLOUD,
        "aws",
        {"access_key_id": "a", "secret_access_key": "s", "region": "r"},
    )
    assert (
        "Not a Prometheus integration"
        in (await mgr.query_prometheus_metrics(aws.integration_id, "up", "1h"))["error"]
    )

    bad = await mgr.query_prometheus_metrics(integration.integration_id, "up", "bad")
    assert "Invalid time_range" in bad["error"]


@pytest.mark.asyncio
async def test_query_prometheus_http_unavailable(im_mod, monkeypatch):
    monkeypatch.setattr(im_mod, "HTTP_AVAILABLE", False)
    mgr = im_mod.IntegrationManager()
    integration = await mgr.register_integration(
        im_mod.IntegrationType.MONITORING,
        "prometheus",
        {"url": "http://prom"},
    )
    result = await mgr.query_prometheus_metrics(integration.integration_id, "up", "1h")
    assert result["error"] == "HTTP client not available"


@pytest.mark.asyncio
async def test_query_cloudwatch_metrics(im_mod):
    mgr = im_mod.IntegrationManager()
    integration = await mgr.register_integration(
        im_mod.IntegrationType.CLOUD,
        "cloudwatch",
        {
            "region": "us-east-1",
            "aws_access_key_id": "a",
            "aws_secret_access_key": "s",
        },
    )
    result = await mgr.query_cloudwatch_metrics(integration.integration_id, "CPUUtilization", "1h")
    assert "error" not in result
    assert result["metric_name"] == "CPUUtilization"

    bad = await mgr.query_cloudwatch_metrics(integration.integration_id, "CPUUtilization", "bad")
    assert "Invalid time_range" in bad["error"]

    aws = await mgr.register_integration(
        im_mod.IntegrationType.CLOUD,
        "aws",
        {"access_key_id": "a", "secret_access_key": "s", "region": "r"},
    )
    assert (
        "Not a CloudWatch integration"
        in (await mgr.query_cloudwatch_metrics(aws.integration_id, "CPUUtilization", "1h"))["error"]
    )


@pytest.mark.asyncio
async def test_query_pagerduty_incidents(im_mod):
    mgr = im_mod.IntegrationManager()
    pd = await mgr.register_integration(
        im_mod.IntegrationType.ITSM,
        "pagerduty",
        {"api_key": "k"},
    )
    result = await mgr.query_pagerduty_incidents(pd.integration_id, "service", "1h")
    assert "error" not in result

    fail_response = MagicMock()
    fail_response.status_code = 500
    fail_response.text = "boom"
    mgr.http_client.get = AsyncMock(return_value=fail_response)
    fail = await mgr.query_pagerduty_incidents(pd.integration_id, "service", "1h")
    assert "500" in fail["error"]


@pytest.mark.asyncio
async def test_trigger_jenkins_and_create_jira(im_mod):
    mgr = im_mod.IntegrationManager()
    jenkins = await mgr.register_integration(
        im_mod.IntegrationType.CICD,
        "jenkins",
        {"url": "http://j", "username": "u", "api_token": "t"},
    )
    result = await mgr.trigger_jenkins_job(jenkins.integration_id, "deploy")
    assert result["success"] is True

    jira = await mgr.register_integration(
        im_mod.IntegrationType.ITSM,
        "jira",
        {"url": "http://jira", "username": "u", "api_token": "t"},
    )
    issue = await mgr.create_jira_issue(jira.integration_id, "s", "d")
    assert issue["success"] is True
    assert issue["issue_key"].startswith("AIO-")


def test_integration_summary(im_mod):
    mgr = im_mod.IntegrationManager()
    summary = mgr.get_integration_summary()
    assert "total_integrations" in summary
    assert "webhooks_registered" in summary


# ---------------------------------------------------------------------------
# core/error_handling_logging.py
# ---------------------------------------------------------------------------
@pytest.fixture
def ehl_mod(monkeypatch):
    import core.error_handling_logging as ehl

    fake_logger = MagicMock()
    fake_logger.opt = MagicMock(return_value=fake_logger)
    monkeypatch.setattr("loguru.logger", fake_logger)
    importlib.reload(ehl)
    monkeypatch.setattr(ehl, "loguru_logger", fake_logger)
    return ehl


@pytest.mark.asyncio
async def test_aiops_exception_and_subclasses(ehl_mod):
    exc = ehl_mod.AIOpsException(
        "msg",
        category=ehl_mod.ErrorCategory.NETWORK,
        severity=ehl_mod.ErrorSeverity.CRITICAL,
        context={"x": 1},
    )
    d = exc.to_dict()
    assert d["error_message"] == "msg"
    assert d["category"] == "network"
    assert d["severity"] == "critical"

    assert isinstance(ehl_mod.NetworkException("x"), ehl_mod.AIOpsException)
    assert isinstance(ehl_mod.DatabaseException("x"), ehl_mod.AIOpsException)
    assert isinstance(ehl_mod.AuthenticationException("x"), ehl_mod.AIOpsException)
    assert isinstance(ehl_mod.ValidationException("x"), ehl_mod.AIOpsException)


@pytest.mark.asyncio
async def test_error_handler_lifecycle(ehl_mod, monkeypatch):
    handler = ehl_mod.ErrorHandler()
    await handler.initialize()

    record = await handler.handle_exception(
        ehl_mod.AIOpsException("boom", severity=ehl_mod.ErrorSeverity.CRITICAL)
    )
    assert record.id in handler.error_index

    fetched = await handler.get_error_record(record.id)
    assert fetched is record

    stats = await handler.get_error_statistics()
    assert stats["total_errors"] >= 1

    custom = MagicMock()
    handler.register_error_handler(ValueError, custom)
    assert ValueError in handler.error_handlers


@pytest.mark.asyncio
async def test_error_handler_specific_handlers(ehl_mod):
    handler = ehl_mod.ErrorHandler()
    record = ehl_mod.ErrorRecord(
        id="r1",
        error_type="NetworkException",
        error_message="x",
        category=ehl_mod.ErrorCategory.NETWORK,
        severity=ehl_mod.ErrorSeverity.ERROR,
        timestamp=ehl_mod.datetime.now(),
        stack_trace="",
        context={},
    )
    await handler._handle_network_exception(record)
    await handler._handle_database_exception(record)
    await handler._handle_authentication_exception(record)
    await handler._handle_validation_exception(record)
    await handler._handle_aiops_exception(record)


@pytest.mark.asyncio
async def test_retry_async(ehl_mod, monkeypatch):
    monkeypatch.setattr(ehl_mod.asyncio, "sleep", AsyncMock())
    handler = ehl_mod.ErrorHandler()
    await handler.initialize()

    calls = []

    @handler.with_retry("default")
    async def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise ValueError("retry")
        return "ok"

    assert await flaky() == "ok"
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_retry_async_unhandled_exception(ehl_mod, monkeypatch):
    monkeypatch.setattr(ehl_mod.asyncio, "sleep", AsyncMock())
    handler = ehl_mod.ErrorHandler()
    await handler.initialize()
    handler.register_retry_policy(
        "no_value",
        ehl_mod.RetryPolicy(max_attempts=3, retry_on=[ValueError]),
    )

    @handler.with_retry("no_value")
    async def fail_key():
        raise KeyError("nope")

    with pytest.raises(KeyError):
        await fail_key()


def test_retry_sync(ehl_mod, monkeypatch):
    monkeypatch.setattr(ehl_mod.time, "sleep", MagicMock())
    handler = ehl_mod.ErrorHandler()
    handler.retry_policies["default"] = ehl_mod.RetryPolicy(
        max_attempts=3, initial_delay=0.01, max_delay=0.02
    )

    calls = []

    @handler.with_retry("default")
    def flaky():
        calls.append(1)
        if len(calls) < 2:
            raise RuntimeError("retry")
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 2


def test_retry_sync_unhandled_exception(ehl_mod, monkeypatch):
    monkeypatch.setattr(ehl_mod.time, "sleep", MagicMock())
    handler = ehl_mod.ErrorHandler()
    handler.retry_policies["default"] = ehl_mod.RetryPolicy(max_attempts=3, retry_on=[KeyError])

    @handler.with_retry("default")
    def fail_value():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        fail_value()


@pytest.mark.asyncio
async def test_structured_logger(ehl_mod):
    logger = ehl_mod.StructuredLogger()
    logger.info("hello")
    logger.debug("d")
    logger.warning("w")
    logger.error("e")
    logger.critical("c")

    entries = await logger.get_log_entries(level="INFO")
    assert len(entries) >= 1
    assert entries[0].message == "hello"

    limited = await logger.get_log_entries(limit=2)
    assert len(limited) == 2

    stats = await logger.get_log_statistics()
    assert stats["total_entries"] >= 1


@pytest.mark.asyncio
async def test_error_handling_and_logging_wrapper(ehl_mod):
    ehal = ehl_mod.ErrorHandlingAndLogging()
    await ehal.initialize()
    record = await ehal.handle_exception(ehl_mod.ValidationException("bad"))
    assert record.error_type == "ValidationException"
    ehal.info("hello")
    stats = await ehal.get_statistics()
    assert "error_statistics" in stats
    assert "log_statistics" in stats


# ---------------------------------------------------------------------------
# core/monitoring_system_integrator.py
# ---------------------------------------------------------------------------
@pytest.fixture
def msi_mod(monkeypatch):
    mi = importlib.import_module("core.monitoring_infrastructure")
    fake = MagicMock()
    fake.metrics_collector = MagicMock()
    fake.metrics_collector.increment_counter = MagicMock()
    fake.get_monitoring_status = MagicMock(return_value={"status": "ok"})
    monkeypatch.setattr(mi, "get_monitoring_infrastructure", lambda: fake)
    msi = importlib.import_module("core.monitoring_system_integrator")
    importlib.reload(msi)
    return msi


def test_monitoring_alert_lifecycle(msi_mod):
    integrator = msi_mod.MonitoringSystemIntegrator()
    alert = msi_mod.UnifiedAlert(
        alert_id="a1",
        alert_name="High CPU",
        severity=msi_mod.AlertSeverity.WARNING,
        status=msi_mod.AlertStatus.ACTIVE,
        message="CPU > 80%",
    )
    integrator.create_alert(alert)
    assert integrator.get_alert_by_id("a1") is alert
    assert len(integrator.get_active_alerts()) == 1

    integrator.acknowledge_alert("a1", "alice")
    assert alert.status == msi_mod.AlertStatus.ACKNOWLEDGED
    assert alert.annotations["acknowledged_by"] == "alice"

    integrator.resolve_alert("a1")
    assert alert.status == msi_mod.AlertStatus.RESOLVED
    assert alert.ends_at is not None
    assert len(integrator.get_active_alerts()) == 0


def test_evaluate_alert_rules(msi_mod):
    integrator = msi_mod.MonitoringSystemIntegrator()
    integrator.evaluate_alert_rules({"system_cpu_percent": 85.0})
    active = integrator.get_active_alerts()
    assert any(a.alert_id == "high_cpu_usage" for a in active)

    integrator.evaluate_alert_rules({"system_cpu_percent": 50.0})
    assert len(integrator.get_active_alerts()) == len(active)


def test_dashboard_lifecycle(msi_mod):
    integrator = msi_mod.MonitoringSystemIntegrator()
    dash = integrator.get_dashboard("system_overview")
    assert dash is not None
    assert len(integrator.get_all_dashboards()) >= 2

    new = msi_mod.DashboardConfig(
        dashboard_id="custom",
        dashboard_name="Custom",
        panels=[{"id": "x", "title": "X", "type": "graph", "targets": ["x"]}],
    )
    integrator.create_dashboard(new)
    assert integrator.get_dashboard("custom") is new


def test_monitoring_summary(msi_mod):
    integrator = msi_mod.MonitoringSystemIntegrator()
    summary = integrator.get_monitoring_summary()
    assert "total_alerts" in summary
    assert "total_dashboards" in summary
    assert "total_alert_rules" in summary
    assert summary["monitoring_status"]["status"] == "ok"
