# -*- coding: utf-8 -*-
"""Medium-ledger batch 15 (2026-09-16) — monitoring contract fixes.

Regression coverage for the endpoints/page contracts repaired in batch 15:

* FE-248 ``/linux-monitoring`` now returns the nested real system detail
  (host / OS / CPU / memory / disk / network) instead of discarding it.
* FE-269 ``/windows-monitoring`` now returns the nested detail plus real
  service enumeration, and ``/windows-monitoring/service-action`` refuses
  clearly when no Windows service manager is present.
* FE-262 ``/process-monitoring/kill`` terminates a real PID with guard rails.
* FE-252 ``/log-search/export`` returns a real, downloadable export file.
* FE-257 ``/metrics-history`` echoes ``metric`` and nests the series in ``data``.
* FE-267 ``/tracing-visualization`` exposes ``services`` and
  ``total_duration_ms`` derived from the real spans.
"""

import json
import os
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api import monitoring_advanced_router as mar
from core.db_engine import async_get_session


@pytest.fixture
def client():
    app = FastAPI()
    app.dependency_overrides[async_get_session] = lambda: None
    app.include_router(mar.router)
    return TestClient(app)


def _snapshot() -> dict:
    return {
        "timestamp": "2026-09-16T00:00:00",
        "cpu": {
            "usage_percent": 12.5,
            "core_count": 4,
            "logical_count": 8,
            "frequency_mhz": 2500.0,
            "per_core": [],
        },
        "memory": {
            "usage_percent": 40.0,
            "total_gb": 16.0,
            "used_gb": 6.0,
            "available_gb": 10.0,
            "free_gb": 10.0,
        },
        "disk": [
            {
                "device": "/dev/vda1",
                "mountpoint": "/",
                "fstype": "ext4",
                "total_gb": 100.0,
                "used_gb": 55.0,
                "free_gb": 45.0,
                "usage_percent": 55.0,
            }
        ],
        "network": {"recv_speed_mb": 1.5, "sent_speed_mb": 0.5},
        "system": {
            "hostname": "srv-a",
            "os": "Linux",
            "os_version": "Alibaba Cloud Linux",
            "os_release": "5.10.0",
            "architecture": "x86_64",
            "uptime_hours": 25.0,
        },
    }


# --------------------------------------------------------------------------
# FE-248 — linux-monitoring nested real detail
# --------------------------------------------------------------------------


class TestLinuxMonitoringDetail:
    def test_nested_detail_returned(self, client, monkeypatch):
        import config

        monkeypatch.setattr(mar, "collect_all", lambda: _snapshot())
        monkeypatch.setattr(config, "LINUX_HOSTS", {"enabled": False, "hosts": []})

        resp = client.get("/api/v1/monitoring/linux-monitoring")
        assert resp.status_code == 200, resp.text
        data = resp.json()

        # legacy flat keys preserved
        assert data["cpu_usage"] == 12.5
        assert data["disk_usage"] == 55.0
        # nested real detail
        assert data["hostname"] == "srv-a"
        assert data["kernel_version"] == "5.10.0"
        assert data["uptime"] == 90000
        assert data["cpu"]["cores"] == 4
        assert data["memory"]["total_gb"] == 16.0
        assert isinstance(data["network"]["interfaces"], list)

    def test_legacy_dict_disk_does_not_crash(self, client, monkeypatch):
        legacy = {
            "cpu": {"usage_percent": 50.0},
            "memory": {"usage_percent": 60.0},
            "disk": {"usage_percent": 70.0},
            "network": {"recv_speed_mb": 10.0, "sent_speed_mb": 5.0},
        }
        monkeypatch.setattr(mar, "collect_all", lambda: legacy)
        import config

        monkeypatch.setattr(config, "LINUX_HOSTS", {"enabled": False, "hosts": []})

        resp = client.get("/api/v1/monitoring/linux-monitoring")
        assert resp.status_code == 200, resp.text
        assert resp.json()["cpu_usage"] == 50.0


# --------------------------------------------------------------------------
# FE-269 — windows-monitoring nested detail + services
# --------------------------------------------------------------------------


class TestWindowsMonitoringDetail:
    def test_nested_detail_and_services(self, client, monkeypatch):
        monkeypatch.setattr(mar, "collect_all", lambda: _snapshot())
        monkeypatch.setattr(mar, "get_top_processes", lambda limit=10: [{"pid": 1}] * 3)
        monkeypatch.setattr(mar, "_windows_services", lambda: [
            {"name": "wuauserv", "display_name": "Windows Update", "status": "running", "start_type": "manual"}
        ])

        resp = client.get("/api/v1/monitoring/windows-monitoring")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["hostname"] == "srv-a"
        assert data["processes"] == 3
        assert data["services"][0]["name"] == "wuauserv"
        assert data["disk_partitions"][0]["drive"] == "/"

    def test_service_action_requires_windows(self, client):
        resp = client.post(
            "/api/v1/monitoring/windows-monitoring/service-action",
            json={"service_name": "wuauserv", "action": "start"},
        )
        # non-Windows host (psutil has no service manager) → explicit 503 marker
        assert resp.status_code == 503, resp.text
        assert resp.json()["detail"]["error"] == "requires-backend"


# --------------------------------------------------------------------------
# FE-262 — process termination guard rails
# --------------------------------------------------------------------------


class TestProcessKill:
    def test_refuses_self(self, client):
        resp = client.post("/api/v1/monitoring/process-monitoring/kill", json={"pid": os.getpid()})
        assert resp.status_code == 400

    def test_missing_process(self, client):
        resp = client.post("/api/v1/monitoring/process-monitoring/kill", json={"pid": 99999999})
        assert resp.status_code == 404


# --------------------------------------------------------------------------
# FE-252 — log-search export
# --------------------------------------------------------------------------


class TestLogSearchExport:
    def test_export_returns_attachment(self, client, monkeypatch):
        async def fake_collect(keyword, newest):
            return [{"TimeGenerated": "2024-01-01 00:00:00", "Source": "syslog", "Message": keyword}]

        monkeypatch.setattr(mar, "_collect_log_search", fake_collect)

        resp = client.get("/api/v1/monitoring/log-search/export?keyword=error&newest=5")
        assert resp.status_code == 200, resp.text
        assert "attachment" in resp.headers["content-disposition"]
        body = json.loads(resp.content)
        assert body["keyword"] == "error"
        assert body["total"] == 1
        assert body["logs"][0]["Message"] == "error"


# --------------------------------------------------------------------------
# FE-257 — metrics-history nested data
# --------------------------------------------------------------------------


class TestMetricsHistory:
    def test_nested_series(self, client, monkeypatch):
        fake = SimpleNamespace(
            to_dict=lambda: {
                "cpu": [10.0, 20.0],
                "memory": [30.0, 40.0],
                "net_in": [1.0, 2.0],
                "timestamps": ["00:00:00", "00:01:00"],
            }
        )
        monkeypatch.setattr(mar, "metrics_history", fake)

        resp = client.get("/api/v1/monitoring/metrics-history?metric=cpu&time_range=1h")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["metric"] == "cpu"
        assert data["data"]["cpu"] == [10.0, 20.0]
        assert data["data"]["timestamps"] == ["00:00:00", "00:01:00"]


# --------------------------------------------------------------------------
# FE-267 — tracing visualization services + duration
# --------------------------------------------------------------------------


class TestTracingVisualization:
    def test_services_and_total_duration(self, client, monkeypatch):
        spans = [
            SimpleNamespace(spanID="1", parentSpanID=None, operationName="GET /", duration=100_000_000,
                            process={"serviceName": "gateway"}),
            SimpleNamespace(spanID="2", parentSpanID="1", operationName="GET /orders", duration=40_000_000,
                            process={"serviceName": "orders"}),
        ]
        fake_trace = SimpleNamespace(spans=spans)

        class _FakeTempo:
            async def get_trace(self, trace_id):
                return fake_trace

        monkeypatch.setattr(mar, "get_tempo_client", lambda: _FakeTempo())

        resp = client.get("/api/v1/monitoring/tracing-visualization?trace_id=t-1")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert set(data["services"]) == {"gateway", "orders"}
        assert data["total_duration_ms"] == 100.0
        assert data["total_spans"] == 2
