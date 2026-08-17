# -*- coding: utf-8 -*-
"""Unit tests for low-coverage core collector modules."""

import time  # noqa: F401  # Imported for test setup
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest  # noqa: F401  # Imported for test setup

import core.collector as collector
import core.linux_collector as linux_collector
from core.agent import observability_client as oc

pytestmark = [pytest.mark.core]


# ---- collector fixtures/helpers ----
class _FakePsutil:
    class NoSuchProcess(Exception):
        pass

    class AccessDenied(Exception):
        pass

    @staticmethod
    def cpu_freq():
        return SimpleNamespace(current=2400.0)

    @staticmethod
    def cpu_percent(interval=None, percpu=False):
        if percpu:
            return [10.0, 20.0]
        return 15.0

    @staticmethod
    def virtual_memory():
        return SimpleNamespace(
            total=8 * 1024**3,
            used=4 * 1024**3,
            available=4 * 1024**3,
            percent=50.0,
        )

    @staticmethod
    def swap_memory():
        return SimpleNamespace(
            total=2 * 1024**3,
            used=1 * 1024**3,
            percent=25.0,
        )

    @staticmethod
    def disk_partitions(all=False):
        return [
            SimpleNamespace(
                device="/dev/sda1",
                mountpoint="/",
                fstype="ext4",
                opts="rw",
            )
        ]

    @staticmethod
    def disk_usage(path):
        return SimpleNamespace(
            total=100 * 1024**3,
            used=50 * 1024**3,
            free=50 * 1024**3,
            percent=50.0,
        )

    @staticmethod
    def net_io_counters():
        return SimpleNamespace(
            bytes_recv=1000,
            bytes_sent=2000,
            packets_recv=10,
            packets_sent=20,
            errin=0,
            errout=0,
        )

    @staticmethod
    def boot_time():
        return 0.0

    @staticmethod
    def process_iter(attrs=None):
        return [
            _FakeProcess(1, "python", "running", "user"),
            _FakeProcess(2, "nginx", "sleeping", "user"),
        ]


class _FakeProcess:
    def __init__(self, pid, name, status, username):
        self.pid = pid
        self.info = {"pid": pid, "name": name, "status": status, "username": username}

    def cpu_percent(self):
        return 5.0 * self.pid

    def memory_percent(self):
        return 2.5 * self.pid


@pytest.fixture(autouse=True)
def _reset_collector(monkeypatch):
    collector.invalidate_collect_cache()
    monkeypatch.setattr(collector, "psutil", _FakePsutil)
    monkeypatch.setattr(collector.time, "sleep", lambda s: None)
    monkeypatch.setattr(collector, "_is_first_net_call", True)
    monkeypatch.setattr(collector, "_last_net_recv", 0)
    monkeypatch.setattr(collector, "_last_net_sent", 0)


def test_get_cpu_metrics():
    data = collector.get_cpu_metrics()
    assert isinstance(data, dict)
    assert {"usage_percent", "core_count", "logical_count", "frequency_mhz", "per_core"} <= set(
        data
    )
    assert data["usage_percent"] == 15.0
    assert data["per_core"] == [10.0, 20.0]


def test_get_memory_metrics():
    data = collector.get_memory_metrics()
    assert isinstance(data, dict)
    assert {
        "total_gb",
        "used_gb",
        "available_gb",
        "usage_percent",
        "swap_total_gb",
        "swap_used_gb",
        "swap_percent",
    } <= set(data)


def test_get_disk_metrics():
    data = collector.get_disk_metrics()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert {
        "device",
        "mountpoint",
        "fstype",
        "total_gb",
        "used_gb",
        "free_gb",
        "usage_percent",
    } <= set(data[0])


def test_get_network_metrics():
    data = collector.get_network_metrics()
    assert isinstance(data, dict)
    assert {
        "recv_speed_mb",
        "sent_speed_mb",
        "bytes_recv_total_mb",
        "bytes_sent_total_mb",
        "packets_recv",
        "packets_sent",
        "errin",
        "errout",
    } <= set(data)


def test_get_top_processes():
    procs = collector.get_top_processes(limit=5)
    assert isinstance(procs, list)
    assert len(procs) <= 5
    if procs:
        assert {"pid", "name", "cpu_percent", "memory_percent", "status", "username"} <= set(
            procs[0]
        )


def test_get_system_info():
    info = collector.get_system_info()
    assert isinstance(info, dict)
    assert {"os", "hostname", "architecture", "processor", "boot_time", "uptime_hours"} <= set(info)


def test_collect_all_and_cache():
    snapshot = collector.collect_all()
    assert isinstance(snapshot, dict)
    assert {"timestamp", "cpu", "memory", "disk", "network", "system", "top_processes"} <= set(
        snapshot
    )
    cached = collector.get_cached_snapshot()
    assert isinstance(cached, dict)
    assert "timestamp" in cached
    metrics = collector.get_collect_metrics()
    assert isinstance(metrics, dict)
    assert {
        "total_calls",
        "cache_hits",
        "cache_misses",
        "last_collect_ms",
        "avg_collect_ms",
        "timeout_count",
        "cache_hit_rate",
    } <= set(metrics)


# ---- linux_collector helpers/tests ----
def _linux_batch_output(nonce="abc"):
    prefix = f"===AIOPS{nonce}METRIC:"
    suffix = f":{nonce}===AIOPSEND==="
    lines = []
    for key in linux_collector.COLLECT_COMMANDS:
        lines.append(f"{prefix}{key}{suffix}")
        lines.append("ok")
    return "\n".join(lines)


@pytest.fixture(autouse=True)
def _reset_linux_collector(monkeypatch):
    monkeypatch.setattr(linux_collector, "_host_failure_tracker", {})
    monkeypatch.setattr(linux_collector.secrets, "token_hex", lambda n: "abc")


def test_get_available_metrics():
    metrics = linux_collector.get_available_metrics()
    assert isinstance(metrics, list)
    assert len(metrics) == len(linux_collector.COLLECT_COMMANDS)
    assert {"key", "desc"} <= set(metrics[0])


def test_get_configured_hosts(monkeypatch):
    monkeypatch.setattr(
        linux_collector,
        "LINUX_HOSTS",
        {
            "hosts": [
                {
                    "name": "web1",
                    "host": "10.0.0.1",
                    "port": 22,
                    "username": "root",
                    "key_file": "/key",
                    "role": "app",
                    "layer": 2,
                    "downstream": ["db1"],
                }
            ]
        },
    )
    hosts = linux_collector.get_configured_hosts()
    assert isinstance(hosts, list)
    assert len(hosts) == 1
    assert hosts[0]["name"] == "web1"
    assert hosts[0]["auth"] == "key"
    assert "role" in hosts[0]


@pytest.mark.asyncio
async def test_ssh_execute_validation():
    out = await linux_collector._ssh_execute(None, "cmd")
    assert out == "ERROR: invalid host_config"
    out = await linux_collector._ssh_execute({}, "")
    assert out == ""
    out = await linux_collector._ssh_execute({"host": "   ", "username": "u"}, "ls")
    assert out.startswith("ERROR")


@pytest.mark.asyncio
async def test_collect_linux_host(monkeypatch):
    monkeypatch.setattr(
        linux_collector, "_ssh_execute", AsyncMock(return_value=_linux_batch_output())
    )
    host_config = {
        "name": "h1",
        "host": "1.2.3.4",
        "username": "u",
        "password": "p",
    }
    result = await linux_collector.collect_linux_host(host_config, metrics=["cpu_usage", "memory"])  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert result["name"] == "h1"
    assert result["status"] in {"ok", "degraded"}
    assert "metrics" in result
    assert "cpu_usage" in result["metrics"] and "memory" in result["metrics"]


@pytest.mark.asyncio
async def test_collect_all_linux(monkeypatch):
    monkeypatch.setattr(
        linux_collector, "_ssh_execute", AsyncMock(return_value=_linux_batch_output())
    )
    monkeypatch.setattr(
        linux_collector,
        "LINUX_HOSTS",
        {"hosts": [{"name": "h1", "host": "1.2.3.4", "username": "u", "password": "p"}]},
    )
    results = await linux_collector.collect_all_linux(metrics=["cpu_usage", "memory"])
    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["name"] == "h1"
    assert results[0]["status"] in {"ok", "degraded"}


def test_get_host_cooldown_status():
    linux_collector._host_failure_tracker["h1"] = {
        "count": 5,
        "last_fail": time.monotonic(),
    }
    status = linux_collector.get_host_cooldown_status()
    assert isinstance(status, dict)
    assert status["total_tracked"] >= 1
    assert any(item["host"] == "h1" for item in status["stale_hosts"])


# ---- observability_client tests ----
PROM_DATA = {"status": "success", "data": {"result": [{"value": [0, "1.23"]}]}}


@pytest.fixture(autouse=True)
def _setup_observability(monkeypatch):
    monkeypatch.setattr(oc, "HTTPX_AVAILABLE", True)
    monkeypatch.setattr(oc, "httpx", SimpleNamespace())
    monkeypatch.setattr(oc, "validate_promql", lambda q: None)
    monkeypatch.setattr(oc, "validate_logql", lambda q: None)
    monkeypatch.setattr(oc, "limit_range_samples", lambda *a, **k: a[2] if len(a) >= 3 else 15)
    monkeypatch.setattr(oc, "parse_duration_to_seconds", lambda d: 15.0)
    monkeypatch.setattr(oc, "get_prometheus_url", lambda: "http://prom")
    monkeypatch.setattr(oc, "get_loki_url", lambda: "http://loki")
    monkeypatch.setattr(oc, "get_kubernetes_api_url", lambda: "http://k8s")
    monkeypatch.setattr(oc, "get_kubernetes_token", lambda: "token")
    monkeypatch.setattr(oc, "get_change_events_url", lambda: "http://events")


def test_query_prometheus(monkeypatch):
    monkeypatch.setattr(oc, "_http_get_json", lambda url, **kwargs: (PROM_DATA, None))
    result = oc.query_prometheus("up")  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert "data" in result


def test_query_prometheus_range(monkeypatch):
    monkeypatch.setattr(oc, "_http_get_json", lambda url, **kwargs: (PROM_DATA, None))
    result = oc.query_prometheus_range("up", 0.0, 100.0)  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert "data" in result


def test_query_service_metrics(monkeypatch):
    monkeypatch.setattr(oc, "_http_get_json", lambda url, **kwargs: (PROM_DATA, None))
    result = oc.query_service_metrics("my-service")  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert result.get("source") == "prometheus"
    assert result.get("available") is True
    for key in ("request_rate", "error_rate", "latency_p99", "latency_p95", "latency_p50"):
        assert key in result


def test_query_network_metrics(monkeypatch):
    monkeypatch.setattr(oc, "_http_get_json", lambda url, **kwargs: (PROM_DATA, None))
    result = oc.query_network_metrics("8.8.8.8")  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert result.get("source") == "prometheus"
    assert result.get("target") == "8.8.8.8"
    for key in (
        "dns_resolution_error_rate",
        "dns_lookup_time_ms",
        "packet_loss_percent",
        "latency_ms",
    ):
        assert key in result


def test_query_loki(monkeypatch):
    monkeypatch.setattr(oc, "_http_get_json", lambda url, **kwargs: ({"status": "success"}, None))
    result = oc.query_loki('{job="test"}')  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert "status" in result


def test_query_kubernetes_events(monkeypatch):
    k8s_data = {
        "items": [
            {
                "type": "Warning",
                "reason": "Failed",
                "message": "error",
                "involvedObject": {"name": "pod1", "kind": "Pod"},
                "metadata": {"namespace": "default"},
                "lastTimestamp": "2024-01-01T00:00:00Z",
            }
        ]
    }
    monkeypatch.setattr(oc, "_http_get_json", lambda url, **kwargs: (k8s_data, None))
    events = oc.query_kubernetes_events(namespace="default", field_selector="type=Warning")
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0]["type"] == "Warning"
    assert events[0]["namespace"] == "default"


def test_query_kubernetes_pod(monkeypatch):
    pod_data = {
        "status": {"phase": "Running", "containerStatuses": []},
        "spec": {"nodeName": "node1"},
    }
    monkeypatch.setattr(oc, "_http_get_json", lambda url, **kwargs: (pod_data, None))
    result = oc.query_kubernetes_pod("pod1", "default")  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert result.get("available") is True
    assert result.get("pod_name") == "pod1"
    assert result.get("phase") == "Running"


def test_query_change_events(monkeypatch):
    monkeypatch.setattr(
        oc, "_http_get_json", lambda url, **kwargs: ([{"id": 1, "target": "api"}], None)
    )
    events = oc.query_change_events("api", hours=1)
    assert isinstance(events, list)
    assert len(events) == 1
    assert events[0]["target"] == "api"


def test_query_kubernetes_node(monkeypatch):
    node_data = {
        "status": {
            "conditions": [{"type": "Ready", "status": "True"}],
            "allocatable": {"memory": "16Gi", "cpu": "4"},
        },
        "metadata": {"name": "node1"},
    }
    monkeypatch.setattr(oc, "_http_get_json", lambda url, **kwargs: (node_data, None))
    result = oc.query_kubernetes_node("node1")  # noqa: F841  # Variable for test verification
    assert isinstance(result, dict)
    assert result.get("available") is True
    assert result.get("node_name") == "node1"
    assert result.get("allocatable_memory") == "16Gi"
    assert result.get("allocatable_cpu") == "4"
