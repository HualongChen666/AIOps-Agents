# -*- coding: utf-8 -*-
"""Real end-to-end tests for batch E uncovered API routers."""

import asyncio
import json

import pytest

pytestmark = [pytest.mark.api]


@pytest.fixture(autouse=True)
def _patch_user_lookup(monkeypatch):
    """Avoid remote asyncpg/Redis user-service dependencies during token validation."""
    import core.authentication as auth
    from core.authentication import UserInDB

    async def fake_get_user(username):
        return UserInDB(
            id=1,
            username="admin",
            role="admin",
            disabled=False,
            hashed_password="",
            mfa_enabled=False,
        )

    def fake_get_user_by_username(username):
        return {
            "id": 1,
            "username": "admin",
            "role": "admin",
            "is_active": True,
            "disabled": False,
        }

    async def fake_is_token_revoked(*args, **kwargs):
        return False

    monkeypatch.setattr(auth, "get_user", fake_get_user)
    monkeypatch.setattr(auth, "get_user_by_username", fake_get_user_by_username)
    monkeypatch.setattr(auth, "is_token_revoked", fake_is_token_revoked)


# ---------------------------------------------------------------------------
# Audit router
# ---------------------------------------------------------------------------
def test_audit_router_endpoints(client, approval_headers, monkeypatch):
    """Exercise CSV/Excel export and report/list endpoints for audit."""
    import api.audit_router as ar

    sample_log = {
        "timestamp": "2026-07-01T12:00:00",
        "event": "LOGIN",
        "risk_level": "low",
        "result": "allowed",
        "detail": "password=secret123",
    }

    monkeypatch.setattr(ar, "get_audit_log", lambda limit=None: [sample_log])

    resp = client.get("/api/v1/audit/export?fmt=csv&limit=10", headers=approval_headers)
    assert resp.status_code == 200
    assert "audit_export_csv.csv" in resp.headers.get("content-disposition", "")
    body = resp.content.decode("utf-8")
    assert "event" in body

    # Excel export falls back to a 500 when openpyxl is not installed; still covers the branch.
    resp = client.get("/api/v1/audit/export?fmt=excel&limit=10", headers=approval_headers)
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        assert "audit_export_excel.xlsx" in resp.headers.get("content-disposition", "")
    else:
        assert "openpyxl" in resp.json()["detail"]

    resp = client.get("/api/v1/audit/report?limit=10", headers=approval_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert "risk_distribution" in data
    assert "result_distribution" in data

    resp = client.get("/api/v1/audit/?limit=10", headers=approval_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert any(item.get("event") == "LOGIN" for item in resp.json())


# ---------------------------------------------------------------------------
# WebSocket router
# ---------------------------------------------------------------------------
def _read_websocket_message(ws):
    """Read a JSON message from a websocket."""
    data = ws.receive_json()
    assert isinstance(data, dict)
    return data


def test_websocket_router_realtime(client):
    """Connect to the realtime WebSocket and broadcast a message."""
    with client.websocket_connect("/ws/realtime") as ws:
        ws.send_text(json.dumps({"hello": "world"}))
        msg = _read_websocket_message(ws)
        assert isinstance(msg, dict)


def test_websocket_router_alerts(client):
    """Connect to alerts WebSocket and send valid/invalid JSON payloads."""
    with client.websocket_connect("/ws/alerts") as ws:
        ws.send_text(json.dumps({"alert": "cpu"}))
        data = ws.receive_json()
        assert data.get("type") == "ack"
        assert data.get("received", {}).get("alert") == "cpu"

        ws.send_text("not-json")
        data = ws.receive_json()
        assert data.get("type") == "ack"
        assert data.get("received", {}).get("raw") == "not-json"


def test_websocket_router_metrics(client, monkeypatch):
    """Connect to the metrics WebSocket and receive one metrics push."""
    import core.collector as col

    monkeypatch.setattr(col, "collect_all", lambda: {"cpu": 10})

    with client.websocket_connect("/ws/metrics") as ws:
        data = ws.receive_json()
        assert data.get("type") == "metrics"
        assert "data" in data


# ---------------------------------------------------------------------------
# Service discovery router
# ---------------------------------------------------------------------------
def test_service_discovery_router_endpoints(client, admin_headers, monkeypatch):
    """Register, discover, deregister and query service instances."""
    import core.service_discovery_manager as sdm

    class FakeInstance:
        instance_id = "i-001"
        service_name = "orders"
        host = "10.0.0.1"
        port = 8080
        status = type("S", (), {"value": "healthy"})()
        weight = 1

    class FakeManager:
        def get_service_summary(self):
            return {"services": {"orders": 1}}

        def register_service(self, **kwargs):
            return FakeInstance()

        def deregister_service(self, service_name, instance_id):
            return True

        def discover_service(self, service_name):
            return [FakeInstance()]

        def get_service_instance(self, service_name, strategy):
            return FakeInstance()

        def get_service_details(self, service_name):
            return {"service_name": service_name, "instances": 1}

    monkeypatch.setattr(sdm, "get_service_discovery_manager", lambda: FakeManager())

    resp = client.get("/api/service-discovery/status", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    resp = client.post(
        "/api/service-discovery/register",
        headers=admin_headers,
        params={
            "service_name": "orders",
            "instance_id": "i-001",
            "host": "10.0.0.1",
            "port": 8080,
            "weight": 1,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["instance_id"] == "i-001"

    resp = client.delete(
        "/api/service-discovery/deregister",
        headers=admin_headers,
        params={"service_name": "orders", "instance_id": "i-001"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["success"] is True

    resp = client.get("/api/service-discovery/discover/orders", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["count"] == 1

    resp = client.get(
        "/api/service-discovery/get-instance/orders?strategy=round_robin",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["host"] == "10.0.0.1"

    resp = client.get("/api/service-discovery/details/orders", headers=admin_headers)
    assert resp.status_code == 200
    assert "instances" in resp.json()["data"]


# ---------------------------------------------------------------------------
# Unified repair router
# ---------------------------------------------------------------------------
def test_unified_repair_router_endpoints(client, admin_headers, monkeypatch):
    """List scripts, run a repair and fetch history."""
    import api.unified_repair_router as urr
    import core.platform_strategies as ps

    class FakeStrategy:
        @staticmethod
        def get_scripts():
            return [{"key": "restart", "name": "Restart Service"}]

        @staticmethod
        def requires_host_name():
            return False

        async def execute_repair(self, script_key, host_name, params):
            return {"success": True, "output": f"ran {script_key}", "exit_code": 0}

        def get_history(self, limit):
            return [{"script": "restart", "success": True}]

    fake = FakeStrategy()
    monkeypatch.setattr(urr, "get_platform_strategy", lambda platform: fake)
    monkeypatch.setattr(ps, "get_all_platform_strategies", lambda: {"windows": fake, "linux": fake})

    resp = client.get("/api/v1/repairs/scripts", headers=admin_headers)
    assert resp.status_code == 200
    assert "scripts" in resp.json()

    resp = client.get("/api/v1/repairs/scripts?platform=windows", headers=admin_headers)
    assert resp.status_code == 200
    assert any(s["key"] == "restart" for s in resp.json()["scripts"])

    resp = client.post(
        "/api/v1/repairs/execute",
        headers=admin_headers,
        json={"platform": "windows", "script_key": "restart", "host_name": "win", "params": {}},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = client.get("/api/v1/repairs/history?platform=windows&limit=5", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1

    resp = client.get("/api/v1/repairs/history", headers=admin_headers)
    assert resp.status_code == 200
    assert "records" in resp.json()


# ---------------------------------------------------------------------------
# Chaos router
# ---------------------------------------------------------------------------
def test_chaos_router_endpoints(client, admin_headers, monkeypatch):
    """Enable, run an experiment and check history/templates for chaos."""
    import api.chaos_router as cr

    class FakeResult:
        status = type("S", (), {"value": "completed"})()
        success = True
        duration_seconds = 1.2
        metrics = {"affected_services": 1}

    class FakeEngine:
        _enabled = False

        def is_enabled(self):
            return self._enabled

        def get_experiment_stats(self):
            return {"total": 0}

        def enable(self):
            self._enabled = True

        def disable(self):
            self._enabled = False

        async def run_experiment(self, experiment, parameters):
            return FakeResult()

        def get_experiment_history(self, limit):
            return []

    engine = FakeEngine()
    monkeypatch.setattr(cr, "chaos_engine", engine)

    resp = client.get("/api/v1/chaos/status", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = client.post("/api/v1/chaos/enable", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["enabled"] is True

    resp = client.post("/api/v1/chaos/disable", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["enabled"] is False

    resp = client.post(
        "/api/v1/chaos/experiment/latency_injection",
        headers=admin_headers,
        json={"target": "svc"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["data"]["experiment"] == "latency_injection"

    resp = client.post(
        "/api/v1/chaos/experiment/unknown_type",
        headers=admin_headers,
        json={},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False

    resp = client.get("/api/v1/chaos/experiments?limit=5", headers=admin_headers)
    assert resp.status_code == 200
    assert "total" in resp.json()["data"]

    resp = client.get("/api/v1/chaos/templates", headers=admin_headers)
    assert resp.status_code == 200
    assert any(t["id"] == "latency_injection" for t in resp.json()["data"]["templates"])


# ---------------------------------------------------------------------------
# Plugin development router
# ---------------------------------------------------------------------------
def test_plugin_development_router_endpoints(client, admin_headers, monkeypatch):
    """Status, templates, generate package/code/config for plugin SDK."""
    import core.plugin_development_sdk as pds

    class FakeSDK:
        def get_sdk_summary(self):
            return {"version": "1.0.0"}

        def get_available_templates(self):
            return ["collector", "analyzer"]

        def create_plugin_package(self, **kwargs):
            return {
                "plugin_name": kwargs.get("plugin_name"),
                "version": kwargs.get("version"),
                "template_type": kwargs.get("template_type"),
            }

        def generate_plugin_code(self, **kwargs):
            return "class CollectorPlugin:\n    pass\n"

        def generate_plugin_config(self, template_type, custom_config=None):
            return {"type": template_type, "custom": custom_config or {}}

    monkeypatch.setattr(pds, "get_plugin_sdk", lambda: FakeSDK())

    resp = client.get("/api/plugin-sdk/status", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["version"] == "1.0.0"

    resp = client.get("/api/plugin-sdk/templates", headers=admin_headers)
    assert resp.status_code == 200
    assert "collector" in resp.json()["data"]["templates"]

    resp = client.post(
        "/api/plugin-sdk/generate",
        headers=admin_headers,
        params={
            "template_type": "collector",
            "plugin_name": "MyCollector",
            "class_name": "MyCollector",
            "version": "1.0.0",
            "author": "tester",
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["plugin_name"] == "MyCollector"
    assert data["plugin_id"] == "mycollector_1_0_0"

    resp = client.get(
        "/api/plugin-sdk/generate/code",
        headers=admin_headers,
        params={
            "template_type": "collector",
            "plugin_name": "MyCollector",
            "class_name": "MyCollector",
            "version": "1.0.0",
            "author": "tester",
        },
    )
    assert resp.status_code == 200
    assert "line_count" in resp.json()["data"]

    resp = client.get(
        "/api/plugin-sdk/generate/config",
        headers=admin_headers,
        params={"template_type": "collector"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["type"] == "collector"


# ---------------------------------------------------------------------------
# Plugin marketplace router
# ---------------------------------------------------------------------------
def test_plugin_marketplace_router_endpoints(client, admin_headers, monkeypatch):
    """Publish, approve, reject, review, list and download plugins."""
    import core.plugin_marketplace_manager as pmm

    class FakeQuality:
        def __init__(self, value):
            self.value = value

    class FakeStatus:
        def __init__(self, value):
            self.value = value

    class FakeManager:
        def __init__(self):
            self._plugins = {}
            self._reviews = {}

        def get_marketplace_summary(self):
            return {"total": len(self._plugins)}

        def publish_plugin(self, **kwargs):
            self._plugins[kwargs["plugin_id"]] = kwargs
            return True

        def approve_plugin(self, plugin_id, reviewer):
            return plugin_id in self._plugins

        def reject_plugin(self, plugin_id, reason):
            return plugin_id in self._plugins

        def download_plugin(self, plugin_id):
            return self._plugins.get(plugin_id)

        def get_plugin_listings(self, quality, review_status):
            return list(self._plugins.values())

        def add_review(self, plugin_id, reviewer, rating, comment):
            self._reviews[plugin_id] = {"rating": rating, "comment": comment}
            return True

    manager = FakeManager()
    monkeypatch.setattr(pmm, "get_marketplace_manager", lambda: manager)
    monkeypatch.setattr(pmm, "PluginQuality", FakeQuality)
    monkeypatch.setattr(pmm, "PluginReviewStatus", FakeStatus)

    resp = client.get("/api/plugin-marketplace/status", headers=admin_headers)
    assert resp.status_code == 200
    assert "total" in resp.json()["data"]

    resp = client.post(
        "/api/plugin-marketplace/publish",
        headers=admin_headers,
        params={
            "plugin_id": "p-001",
            "plugin_name": "Test Plugin",
            "version": "1.0.0",
            "description": "desc",
            "author": "tester",
            "plugin_code": "code",
            "quality": "community",
        },
        json={"plugin_config": {"key": "value"}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["published"] is True

    resp = client.post(
        "/api/plugin-marketplace/plugin/p-001/approve",
        headers=admin_headers,
        params={"reviewer": "alice"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["approved"] is True

    resp = client.post(
        "/api/plugin-marketplace/plugin/p-001/reject",
        headers=admin_headers,
        params={"reason": "bad"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["rejected"] is True

    resp = client.post(
        "/api/plugin-marketplace/plugin/p-001/download",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["plugin_id"] == "p-001"

    resp = client.get("/api/plugin-marketplace/listings", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["count"] >= 1

    resp = client.post(
        "/api/plugin-marketplace/plugin/p-001/review",
        headers=admin_headers,
        params={"reviewer": "alice", "rating": 5, "comment": "great"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["review_added"] is True


# ---------------------------------------------------------------------------
# Realtime router
# ---------------------------------------------------------------------------
def test_realtime_router_status(client, admin_headers, monkeypatch):
    """Fetch realtime connection status."""
    import api.realtime_router as rr

    class FakeManager:
        rooms = {"realtime": [1, 2]}
        active_connections = [1, 2, 3]

    monkeypatch.setattr(rr, "websocket_manager", FakeManager())

    resp = client.get("/api/v1/realtime/status", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["connections"] == 3
    assert data["rooms"]["realtime"] == 2


def test_realtime_router_websocket(client):
    """Connect to the unified realtime WebSocket."""
    with client.websocket_connect("/api/v1/realtime/ws") as ws:
        ws.send_text(json.dumps({"msg": "ping"}))
        data = _read_websocket_message(ws)
        assert isinstance(data, dict)


@pytest.mark.skip(reason="SSE infinite stream not reliably testable with TestClient")
def test_realtime_router_sse(client, admin_headers):
    """Read a single SSE heartbeat event."""
    with client.stream("GET", "/api/v1/realtime/events", timeout=2.0, headers=admin_headers) as resp:
        assert resp.status_code == 200
        chunk = next(resp.iter_text())
        assert "heartbeat" in chunk


# ---------------------------------------------------------------------------
# Windows repair router
# ---------------------------------------------------------------------------
def test_windows_repair_router_endpoints(client, admin_headers, monkeypatch):
    """List scripts, execute repair and fetch history for Windows."""
    import api.windows_repair_router as wrr

    monkeypatch.setattr(wrr, "find_windows_host_config", lambda host: {"name": host, "ip": "1.1.1.1"})

    async def fake_execute(key, params):
        return {"success": True, "output": "ok", "exit_code": 0}

    monkeypatch.setattr(wrr, "execute_windows_repair", fake_execute)
    monkeypatch.setattr(
        wrr,
        "get_windows_repair_history",
        lambda limit: [{"host": "win", "script": "restart", "success": True}],
    )

    resp = client.get("/api/v1/platforms/windows/repair/scripts", headers=admin_headers)
    assert resp.status_code == 200
    assert "restart_service" in resp.json()["scripts"]

    resp = client.post(
        "/api/v1/platforms/windows/repair/execute",
        headers=admin_headers,
        json={"host_name": "win", "script_key": "restart_service", "params": {"service_name": "Spooler"}},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = client.get(
        "/api/v1/platforms/windows/repair/history?limit=5&host_name=win",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# Metrics router
# ---------------------------------------------------------------------------
def test_metrics_router_endpoints(client, admin_headers, monkeypatch):
    """Hit dashboard, snapshot, history, predictions, processes, summary and KPI."""
    import api.metrics_router as mr
    import core.stats_engine as se

    snapshot = {
        "cpu": {"usage_percent": 10.0, "cores": 4},
        "memory": {"usage_percent": 20.0, "total_gb": 16},
        "disk": {"usage_percent": 30.0, "total_gb": 500},
    }

    async def fake_summary():
        return {"total_alerts": 1, "heal_rate": 90, "mttd_min": 10, "rca_accuracy": 95}

    monkeypatch.setattr(mr, "collect_all", lambda: snapshot)
    monkeypatch.setattr(mr, "get_top_processes", lambda limit: [{"pid": 1, "name": "python", "cpu_percent": 5.0}])
    monkeypatch.setattr(mr, "get_real_summary", fake_summary)
    monkeypatch.setattr(mr.metrics_history, "to_dict", lambda: {"cpu": [10.0, 11.0], "memory": [20.0, 21.0], "net_in": [1.0, 2.0]})

    resp = client.get("/api/v1/metrics/", headers=admin_headers)
    assert resp.status_code == 200
    assert "metrics" in resp.json()

    resp = client.get("/api/v1/metrics/snapshot", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["cpu"]["usage_percent"] == 10.0

    resp = client.get("/api/v1/metrics/history", headers=admin_headers)
    assert resp.status_code == 200
    assert "_meta" in resp.json()

    resp = client.get("/api/v1/metrics/predictions", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)

    resp = client.get("/api/v1/metrics/processes?limit=5", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["processes"][0]["name"] == "python"

    resp = client.get("/api/v1/metrics/summary", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total_alerts"] == 1

    resp = client.delete("/api/v1/metrics/cache", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["snapshot_cleared"] is True

    resp = client.get("/api/v1/metrics/agent/feedback-accuracy", headers=admin_headers)
    assert resp.status_code == 200
    assert "total" in resp.json()

    resp = client.get("/api/v1/metrics/agent/decision-accuracy", headers=admin_headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/metrics/kpi/config", headers=admin_headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/metrics/kpi/values", headers=admin_headers)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# SLO router
# ---------------------------------------------------------------------------
def test_slo_router_endpoints(client, admin_headers, monkeypatch):
    """Create, list, get, update, delete SLO and generate/list reports."""
    import api.slo_router as sr

    _slos = {}
    _reports = []
    _id = 0

    class FakeRule:
        def __init__(self, **kw):
            nonlocal _id
            _id += 1
            self.id = f"slo-{_id}"
            for k, v in kw.items():
                setattr(self, k, v)
            self.aggregation = kw.get("aggregation", "good_ratio")

    def create_slo(**kw):
        rule = FakeRule(**kw)
        _slos[rule.id] = rule
        return rule

    def list_slos():
        return list(_slos.values())

    def get_slo(slo_id):
        return _slos.get(slo_id)

    def update_slo(slo_id, **kw):
        rule = _slos.get(slo_id)
        if not rule:
            return None
        for k, v in kw.items():
            setattr(rule, k, v)
        return rule

    def delete_slo(slo_id):
        return _slos.pop(slo_id, None) is not None

    def evaluate_slo(rule, points):
        return {"current": 0.99, "error_budget_remaining_percent": 0.95, "burn_rate": 0.1, "status": "ok"}

    def format_window(window):
        return str(window)

    def parse_window(window):
        return 1

    def generate_sla_report(period):
        _reports.append({"id": "r-1", "period": period})
        return _reports

    def save_sla_reports(reports):
        return ["r-1"]

    def list_sla_reports(period=None):
        return _reports

    def get_sla_report(report_id):
        return next((r for r in _reports if r.get("id") == report_id), None)

    def delete_sla_report(report_id):
        before = len(_reports)
        _reports[:] = [r for r in _reports if r.get("id") != report_id]
        return len(_reports) < before

    monkeypatch.setattr(sr, "create_slo", create_slo)
    monkeypatch.setattr(sr, "list_slos", list_slos)
    monkeypatch.setattr(sr, "get_slo", get_slo)
    monkeypatch.setattr(sr, "update_slo", update_slo)
    monkeypatch.setattr(sr, "delete_slo", delete_slo)
    monkeypatch.setattr(sr, "evaluate_slo", evaluate_slo)
    monkeypatch.setattr(sr, "format_window", format_window)
    monkeypatch.setattr(sr, "parse_window", parse_window)
    monkeypatch.setattr(sr, "generate_sla_report", generate_sla_report)
    monkeypatch.setattr(sr, "save_sla_reports", save_sla_reports)
    monkeypatch.setattr(sr, "list_sla_reports", list_sla_reports)
    monkeypatch.setattr(sr, "get_sla_report", get_sla_report)
    monkeypatch.setattr(sr, "delete_sla_report", delete_sla_report)

    resp = client.get("/api/v1/slo/", headers=admin_headers)
    assert resp.status_code == 200
    assert "slos" in resp.json()

    resp = client.post(
        "/api/v1/slo/",
        headers=admin_headers,
        json={
            "name": "availability",
            "service": "api",
            "metric": "availability",
            "target": 99.9,
            "window": "30d",
            "alert_threshold": 95.0,
            "aggregation": "good_ratio",
        },
    )
    assert resp.status_code == 200
    slo_id = resp.json()["id"]
    assert resp.json()["target"] == 99.9

    resp = client.get(f"/api/v1/slo/{slo_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == slo_id

    resp = client.put(
        f"/api/v1/slo/{slo_id}",
        headers=admin_headers,
        json={"target": 99.99},
    )
    assert resp.status_code == 200
    assert resp.json()["target"] == 99.99

    resp = client.post("/api/v1/slo/reports?period=7d", headers=admin_headers, json={})
    assert resp.status_code == 200
    assert "reports" in resp.json()

    resp = client.get("/api/v1/slo/reports", headers=admin_headers)
    assert resp.status_code == 200
    assert "reports" in resp.json()

    report_id = resp.json()["reports"][0]["id"]
    resp = client.get(f"/api/v1/slo/reports/{report_id}", headers=admin_headers)
    assert resp.status_code == 200

    resp = client.delete(f"/api/v1/slo/reports/{report_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    resp = client.delete(f"/api/v1/slo/{slo_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


# ---------------------------------------------------------------------------
# gRPC service router
# ---------------------------------------------------------------------------
def test_grpc_service_router_endpoints(client, admin_headers, monkeypatch):
    """Create, export proto/python and status for gRPC services."""
    import core.grpc_service_manager as gsm

    class FakeService:
        def __init__(self, name, package, status_value="active"):
            self.service_name = name
            self.package_name = package
            self.status = type("S", (), {"value": status_value})()
            self.proto_content = f"syntax = 'proto3'; service {name} {{}}"
            self.python_content = f"class {name}Servicer: pass"

    class FakeManager:
        def __init__(self):
            self.services = {}

        def get_service_summary(self):
            return {"total": len(self.services)}

        def create_service(self, **kw):
            svc = FakeService(kw["service_name"], kw["package_name"])
            self.services[kw["service_name"]] = svc
            return svc

        def create_monitoring_service(self):
            return self.create_service(service_name="MonitoringService", package_name="monitoring")

        def create_alert_service(self):
            return self.create_service(service_name="AlertService", package_name="alert")

        def create_repair_service(self):
            return self.create_service(service_name="RepairService", package_name="repair")

    manager = FakeManager()
    monkeypatch.setattr(gsm, "get_grpc_service_manager", lambda: manager)

    resp = client.get("/api/grpc-services/status", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["total"] == 0

    resp = client.post(
        "/api/grpc-services/create",
        headers=admin_headers,
        params={"service_name": "UserService", "package_name": "user"},
        json={
            "methods": [
                {
                    "method_name": "GetUser",
                    "request_type": "UserRequest",
                    "response_type": "UserResponse",
                    "streaming_type": "unary",
                    "description": "get user",
                }
            ],
            "messages": {},
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["service_name"] == "UserService"
    assert data["method_count"] == 1

    resp = client.post("/api/grpc-services/create/monitoring", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["service_name"] == "MonitoringService"

    resp = client.post("/api/grpc-services/create/alert", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["service_name"] == "AlertService"

    resp = client.post("/api/grpc-services/create/repair", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["service_name"] == "RepairService"

    resp = client.get("/api/grpc-services/export/proto/UserService", headers=admin_headers)
    assert resp.status_code == 200
    assert "proto_content" in resp.json()["data"]

    resp = client.get("/api/grpc-services/export/python/UserService", headers=admin_headers)
    assert resp.status_code == 200
    assert "python_content" in resp.json()["data"]


# ---------------------------------------------------------------------------
# AI feedback router
# ---------------------------------------------------------------------------
def test_ai_feedback_router_endpoints(client, admin_headers):
    """Submit, get stats and list recent AI feedback."""
    resp = client.post(
        "/api/ai/feedback/submit",
        headers=admin_headers,
        json={
            "feedback_type": "positive",
            "analysis_text": "analysis",
            "query_text": "query",
            "platform": "windows",
            "stage_name": "rca",
            "comment": "good",
            "rich_context": True,
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "feedback_id" in data
    assert data["stats"]["total"] >= 1

    resp = client.get("/api/ai/feedback/stats?today_only=false", headers=admin_headers)
    assert resp.status_code == 200
    assert "accuracy" in resp.json()

    resp = client.get("/api/ai/feedback/recent?limit=5", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# Alert webhook router
# ---------------------------------------------------------------------------
def test_alert_webhook_router_endpoints(client, monkeypatch):
    """Receive alerts from supported providers and Prometheus."""
    import api.alert_webhook_router as awr
    import core.alert_providers as ap

    class FakeProvider:
        def normalize(self, payload):
            return [{
                "id": "a-1",
                "host": "host-1",
                "severity": "critical",
                "status": "firing",
                "trace_id": "t-1",
            }]

    monkeypatch.setattr(ap, "get_alert_provider", lambda name: FakeProvider())
    monkeypatch.setattr(ap, "list_alert_providers", lambda: ["prometheus"])

    async def fake_try_auto_heal(alert):
        return {"alert_id": alert.get("id"), "status": "healed"}

    monkeypatch.setattr(awr, "try_auto_heal", fake_try_auto_heal)
    monkeypatch.setattr(awr, "record_audit", lambda **kwargs: None)

    payload = {"alerts": [{"labels": {"alertname": "HighCPU"}}]}

    resp = client.post("/api/v1/alerts/webhook/prometheus", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "prometheus"
    assert data["received"] == 1
    assert any(r["status"] == "processed" for r in data["results"])

    resp = client.post("/api/v1/alerts/webhook/unknown", json=payload)
    assert resp.status_code == 404

    resp = client.post("/api/v1/alerts/prometheus", json=payload)
    assert resp.status_code == 200
    assert resp.json()["source"] == "prometheus"


# ---------------------------------------------------------------------------
# Additional error-path coverage for routers below 80%
# ---------------------------------------------------------------------------


def test_audit_router_error_paths(client, admin_headers, approval_headers, monkeypatch):
    """Cover internal-key and empty-data branches."""
    import api.audit_router as ar

    monkeypatch.setattr(ar, "get_audit_log", lambda limit=None: [])

    # Missing / invalid X-Internal-Key (must be authenticated first)
    resp = client.get("/api/v1/audit/export?fmt=csv&limit=10", headers=admin_headers)
    assert resp.status_code == 403

    bad_headers = {**admin_headers, "X-Internal-Key": "wrong"}
    resp = client.get(
        "/api/v1/audit/export?fmt=csv&limit=10",
        headers=bad_headers,
    )
    assert resp.status_code == 403

    # Empty data still returns a file for CSV and Excel
    resp = client.get("/api/v1/audit/export?fmt=csv&limit=10", headers=approval_headers)
    assert resp.status_code == 200

    resp = client.get("/api/v1/audit/export?fmt=excel&limit=10", headers=approval_headers)
    assert resp.status_code in (200, 500)

    resp = client.get("/api/v1/audit/report?limit=10", headers=approval_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 0


def test_websocket_router_metrics_exception(client, monkeypatch):
    """Cover the metrics WebSocket exception handler."""
    import core.collector as col

    def bad_collect():
        raise RuntimeError("boom")

    monkeypatch.setattr(col, "collect_all", bad_collect)

    # If collect_all raises, the server task crashes and the connection closes.
    with client.websocket_connect("/ws/metrics") as ws:
        pass


def test_unified_repair_router_error_paths(client, admin_headers, monkeypatch):
    """Cover all error/status branches in unified repair."""
    import api.unified_repair_router as urr
    import core.platform_strategies as ps

    class FakeStrategy:
        @staticmethod
        def get_scripts():
            return [{"key": "restart", "name": "Restart"}]

        @staticmethod
        def requires_host_name():
            return True

        async def execute_repair(self, script_key, host_name, params):
            if script_key == "none":
                return None
            if script_key == "badtype":
                return "not a dict"
            if script_key == "blocked":
                return {"success": False, "blocked": True, "error": "blocked", "safe_alternative": "safe"}
            if script_key == "unknown":
                return {"success": False, "error": "未知修复脚本 missing"}
            if script_key == "paramerr":
                return {"success": False, "error": "pid 必须为整数"}
            if script_key == "boom":
                raise RuntimeError("boom")
            return {"success": True, "output": "ok", "exit_code": 0}

        def get_history(self, limit):
            return []

    fake = FakeStrategy()
    monkeypatch.setattr(urr, "get_platform_strategy", lambda platform: fake)
    monkeypatch.setattr(ps, "get_all_platform_strategies", lambda: {"windows": fake})

    # Invalid platform in list (FastAPI literal validation)
    resp = client.get("/api/v1/repairs/scripts?platform=unknown", headers=admin_headers)
    assert resp.status_code == 422

    # Host name required
    resp = client.post(
        "/api/v1/repairs/execute",
        headers=admin_headers,
        json={"platform": "windows", "script_key": "restart", "host_name": "", "params": {}},
    )
    assert resp.status_code == 422

    # Invalid platform in execute (FastAPI literal validation)
    resp = client.post(
        "/api/v1/repairs/execute",
        headers=admin_headers,
        json={"platform": "unknown", "script_key": "restart", "host_name": "h", "params": {}},
    )
    assert resp.status_code == 422

    for key, expected in [
        ("none", 500),
        ("badtype", 500),
        ("blocked", 403),
        ("unknown", 404),
        ("paramerr", 422),
        ("boom", 500),
    ]:
        resp = client.post(
            "/api/v1/repairs/execute",
            headers=admin_headers,
            json={"platform": "windows", "script_key": key, "host_name": "h", "params": {}},
        )
        assert resp.status_code == expected, f"{key} returned {resp.status_code}"

    # Invalid platform in history (FastAPI literal validation)
    resp = client.get("/api/v1/repairs/history?platform=unknown&limit=5", headers=admin_headers)
    assert resp.status_code == 422


def test_service_discovery_router_error_paths(client, admin_headers, monkeypatch):
    """Cover exception branches in service discovery endpoints."""
    import core.service_discovery_manager as sdm

    class RaisingManager:
        def __getattr__(self, name):
            raise RuntimeError("boom")

    monkeypatch.setattr(sdm, "get_service_discovery_manager", lambda: RaisingManager())

    params_for = {
        "/api/service-discovery/register": {"service_name": "s", "instance_id": "i", "host": "h", "port": 1},
        "/api/service-discovery/deregister": {"service_name": "s", "instance_id": "i"},
    }

    for path, method in [
        ("/api/service-discovery/status", "GET"),
        ("/api/service-discovery/register", "POST"),
        ("/api/service-discovery/deregister", "DELETE"),
        ("/api/service-discovery/discover/orders", "GET"),
        ("/api/service-discovery/get-instance/orders", "GET"),
        ("/api/service-discovery/details/orders", "GET"),
    ]:
        resp = client.request(method, path, headers=admin_headers, params=params_for.get(path, {}))
        assert resp.status_code == 500, f"{path} {method}"


def test_chaos_router_error_paths(client, admin_headers, monkeypatch):
    """Cover exception branches in chaos endpoints."""
    import api.chaos_router as cr

    class BadEngine:
        def is_enabled(self):
            raise RuntimeError("boom")

        def get_experiment_stats(self):
            raise RuntimeError("boom")

        def enable(self):
            raise RuntimeError("boom")

        def disable(self):
            raise RuntimeError("boom")

        async def run_experiment(self, experiment, parameters):
            raise RuntimeError("boom")

        def get_experiment_history(self, limit):
            raise RuntimeError("boom")

    monkeypatch.setattr(cr, "chaos_engine", BadEngine())

    resp = client.get("/api/v1/chaos/status", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is False

    resp = client.post("/api/v1/chaos/enable", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is False

    resp = client.post("/api/v1/chaos/disable", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is False

    resp = client.post(
        "/api/v1/chaos/experiment/latency_injection",
        headers=admin_headers,
        json={},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is False

    resp = client.get("/api/v1/chaos/experiments?limit=5", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["success"] is False

    # templates function only catches a generic exception that is not triggered here


def test_plugin_development_router_error_paths(client, admin_headers, monkeypatch):
    """Cover exception branches in plugin SDK endpoints."""
    import core.plugin_development_sdk as pds

    class BadSDK:
        def __getattr__(self, name):
            raise RuntimeError("boom")

    monkeypatch.setattr(pds, "get_plugin_sdk", lambda: BadSDK())

    for path, method in [
        ("/api/plugin-sdk/status", "GET"),
        ("/api/plugin-sdk/templates", "GET"),
    ]:
        resp = client.request(method, path, headers=admin_headers)
        assert resp.status_code == 500, f"{path}"

    resp = client.post(
        "/api/plugin-sdk/generate",
        headers=admin_headers,
        params={"template_type": "x", "plugin_name": "x", "class_name": "X"},
    )
    assert resp.status_code == 500

    resp = client.get(
        "/api/plugin-sdk/generate/code",
        headers=admin_headers,
        params={"template_type": "x", "plugin_name": "x", "class_name": "X"},
    )
    assert resp.status_code == 500

    resp = client.get(
        "/api/plugin-sdk/generate/config",
        headers=admin_headers,
        params={"template_type": "x"},
    )
    assert resp.status_code == 500


def test_plugin_marketplace_router_error_paths(client, admin_headers, monkeypatch):
    """Cover exception branches in plugin marketplace endpoints."""
    import core.plugin_marketplace_manager as pmm

    class BadManager:
        def __getattr__(self, name):
            raise RuntimeError("boom")

    monkeypatch.setattr(pmm, "get_marketplace_manager", lambda: BadManager())
    monkeypatch.setattr(pmm, "PluginQuality", lambda v: type("Q", (), {"value": v})())
    monkeypatch.setattr(pmm, "PluginReviewStatus", lambda v: type("S", (), {"value": v})())

    for path, method in [
        ("/api/plugin-marketplace/status", "GET"),
        ("/api/plugin-marketplace/plugin/p-1/approve", "POST"),
        ("/api/plugin-marketplace/plugin/p-1/reject", "POST"),
        ("/api/plugin-marketplace/listings", "GET"),
        ("/api/plugin-marketplace/plugin/p-1/review", "POST"),
    ]:
        params = {"reviewer": "a"} if "approve" in path else {"reason": "x"} if "reject" in path else {"reviewer": "a", "rating": 5, "comment": "x"}
        resp = client.request(
            method,
            path,
            headers=admin_headers,
            params=params if "status" not in path else None,
        )
        assert resp.status_code == 500, f"{path}"

    # download missing path and exception
    resp = client.post("/api/plugin-marketplace/plugin/p-1/download", headers=admin_headers)
    assert resp.status_code == 500


def test_realtime_router_error_paths(client, admin_headers, monkeypatch):
    """Cover realtime websocket and SSE branches."""
    import api.realtime_router as rr
    from core.websocket_manager import ConnectionManager

    # realtime websocket invalid JSON
    with client.websocket_connect("/api/v1/realtime/ws") as ws:
        ws.send_text("not-json")
        data = ws.receive_json()
        assert data["data"]["raw"] == "not-json"

    # realtime websocket exception handling
    class BadManager(ConnectionManager):
        async def broadcast(self, message, channel):
            raise RuntimeError("boom")

    monkeypatch.setattr(rr, "websocket_manager", BadManager())
    with client.websocket_connect("/api/v1/realtime/ws") as ws:
        ws.send_text(json.dumps({"x": 1}))
        # the server should close the connection; just ensure no crash


def test_windows_repair_router_error_paths(client, admin_headers, monkeypatch):
    """Cover missing host and repair result error branches."""
    import api.windows_repair_router as wrr

    monkeypatch.setattr(wrr, "find_windows_host_config", lambda host: None)

    resp = client.post(
        "/api/v1/platforms/windows/repair/execute",
        headers=admin_headers,
        json={"host_name": "unknown", "script_key": "restart_service", "params": {}},
    )
    assert resp.status_code == 404

    def make_execute(result):
        async def fake_execute(script_key, params):
            return result
        return fake_execute

    for key, result, expected in [
        ("badtype", "string", 500),
        ("blocked", {"success": False, "error": "blocked"}, 500),
        ("unknown_script", {"success": False, "error": "未知的 windows 修复脚本 missing"}, 404),
        ("paramerr", {"success": False, "error": "pid 必须为整数"}, 422),
    ]:
        monkeypatch.setattr(wrr, "find_windows_host_config", lambda host, _ok=True: {"name": host, "ip": "1.1.1.1"})

        if result == "string":
            monkeypatch.setattr(
                wrr, "execute_windows_repair", make_execute("not a dict")
            )
        else:
            monkeypatch.setattr(wrr, "execute_windows_repair", make_execute(result))

        resp = client.post(
            "/api/v1/platforms/windows/repair/execute",
            headers=admin_headers,
            json={"host_name": "win", "script_key": key, "params": {}},
        )
        assert resp.status_code == expected, f"{key} -> {resp.status_code}"

    # history exception
    async def bad_history(limit):
        raise RuntimeError("boom")

    monkeypatch.setattr(wrr, "get_windows_repair_history", bad_history)
    resp = client.get("/api/v1/platforms/windows/repair/history?limit=5", headers=admin_headers)
    assert resp.status_code == 500


def test_metrics_router_extra_paths(client, admin_headers, monkeypatch):
    """Cover predictions slope branches and error paths."""
    import api.metrics_router as mr

    monkeypatch.setattr(
        mr.metrics_history,
        "to_dict",
        lambda: {
            "cpu": [1.0, 2.0, 3.0, 4.0, 5.0],
            "memory": [5.0, 4.0, 3.0, 2.0, 1.0],
            "net_in": [1.0, 1.0],
        },
    )

    resp = client.get("/api/v1/metrics/predictions", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert any(p["priority"] == "high" for p in data)
    assert any(p["priority"] == "low" for p in data)

    # processes exception
    def bad_top(limit):
        raise RuntimeError("boom")

    monkeypatch.setattr(mr, "get_top_processes", bad_top)
    resp = client.get("/api/v1/metrics/processes?limit=5", headers=admin_headers)
    assert resp.status_code == 500

    # KPI config CRUD
    resp = client.post("/api/v1/metrics/kpi/config", headers=admin_headers, json={"id": "x"})
    assert resp.status_code == 200

    resp = client.put("/api/v1/metrics/kpi/config/x", headers=admin_headers, json={"visible": True})
    assert resp.status_code == 404

    resp = client.delete("/api/v1/metrics/kpi/config/x", headers=admin_headers)
    assert resp.status_code == 404


def test_slo_router_error_paths(client, admin_headers, monkeypatch):
    """Cover SLO update/delete errors and SLA report errors."""
    import api.slo_router as sr

    # Create an SLO via patched engine (re-use from existing test by patching is enough here)
    _slos = {}
    _id = 0

    class FakeRule:
        def __init__(self, **kw):
            nonlocal _id
            _id += 1
            self.id = f"slo-{_id}"
            for k, v in kw.items():
                setattr(self, k, v)
            self.aggregation = kw.get("aggregation", "good_ratio")

    def create(**kw):
        rule = FakeRule(**kw)
        _slos[rule.id] = rule
        return rule

    monkeypatch.setattr(sr, "create_slo", create)
    monkeypatch.setattr(sr, "list_slos", lambda: list(_slos.values()))
    monkeypatch.setattr(sr, "get_slo", lambda sid: _slos.get(sid))
    monkeypatch.setattr(sr, "delete_slo", lambda sid: _slos.pop(sid, None) is not None)
    monkeypatch.setattr(sr, "update_slo", lambda sid, **kw: None)
    monkeypatch.setattr(sr, "evaluate_slo", lambda rule, points: {"current": 0.9, "error_budget_remaining_percent": 0.9, "burn_rate": 0.1, "status": "ok"})
    monkeypatch.setattr(sr, "format_window", lambda w: str(w))
    def fake_parse_window(w):
        if w == "bad":
            raise ValueError("bad")
        return 1

    monkeypatch.setattr(sr, "parse_window", fake_parse_window)
    monkeypatch.setattr(sr, "generate_sla_report", lambda period: [])
    monkeypatch.setattr(sr, "save_sla_reports", lambda reports: [])
    monkeypatch.setattr(sr, "list_sla_reports", lambda period=None: [])
    monkeypatch.setattr(sr, "get_sla_report", lambda rid: None)
    monkeypatch.setattr(sr, "delete_sla_report", lambda rid: False)

    # update/delete non-existent SLO
    resp = client.put("/api/v1/slo/missing", headers=admin_headers, json={"target": 99.9})
    assert resp.status_code == 404

    resp = client.delete("/api/v1/slo/missing", headers=admin_headers)
    assert resp.status_code == 404

    # parse window error on create
    resp = client.post(
        "/api/v1/slo/",
        headers=admin_headers,
        json={
            "name": "x",
            "service": "api",
            "metric": "m",
            "target": 99.9,
            "window": "bad",
        },
    )
    assert resp.status_code == 400


def test_grpc_service_router_error_paths(client, admin_headers, monkeypatch):
    """Cover exception branches in gRPC endpoints."""
    import core.grpc_service_manager as gsm

    class BadManager:
        def __getattr__(self, name):
            raise RuntimeError("boom")

    monkeypatch.setattr(gsm, "get_grpc_service_manager", lambda: BadManager())

    for path, method in [
        ("/api/grpc-services/status", "GET"),
        ("/api/grpc-services/create", "POST"),
        ("/api/grpc-services/create/monitoring", "POST"),
        ("/api/grpc-services/create/alert", "POST"),
        ("/api/grpc-services/create/repair", "POST"),
    ]:
        resp = client.request(
            method,
            path,
            headers=admin_headers,
            params={"service_name": "X", "package_name": "x"} if "create" in path and method == "POST" and path.endswith("/create") else {},
            json={"methods": [], "messages": {}} if path.endswith("/create") else None,
        )
        assert resp.status_code == 500, f"{path}"

    # export missing service
    class EmptyManager:
        services = {}

    monkeypatch.setattr(gsm, "get_grpc_service_manager", lambda: EmptyManager())
    resp = client.get("/api/grpc-services/export/proto/Missing", headers=admin_headers)
    assert resp.status_code == 404

    resp = client.get("/api/grpc-services/export/python/Missing", headers=admin_headers)
    assert resp.status_code == 404


def test_alert_webhook_router_error_paths(client, monkeypatch):
    """Cover branches for skipped alerts, processing errors and audit exceptions."""
    import api.alert_webhook_router as awr
    import core.alert_providers as ap

    class FakeProvider:
        def normalize(self, payload):
            if isinstance(payload, dict):
                return payload.get("alerts", [])
            return []

    monkeypatch.setattr(ap, "get_alert_provider", lambda name: FakeProvider())
    monkeypatch.setattr(ap, "list_alert_providers", lambda: ["prometheus"])

    async def failing_auto_heal(alert):
        raise RuntimeError("heal failed")

    monkeypatch.setattr(awr, "try_auto_heal", failing_auto_heal)

    audit_calls = []

    def bad_record_audit(**kwargs):
        audit_calls.append(1)
        if len(audit_calls) > 1:
            raise RuntimeError("audit failed")

    monkeypatch.setattr(awr, "record_audit", bad_record_audit)

    # auto-heal unavailable path
    monkeypatch.setattr(awr, "AUTO_HEAL_AVAILABLE", False)
    resp = client.post("/api/v1/alerts/webhook/prometheus", json={"alerts": []})
    assert resp.status_code == 503
    monkeypatch.setattr(awr, "AUTO_HEAL_AVAILABLE", True)

    # skipped (non-firing) alert branch
    resp = client.post(
        "/api/v1/alerts/webhook/prometheus",
        json={"alerts": [{"id": "a-1", "status": "resolved"}]},
    )
    assert resp.status_code == 200
    assert resp.json()["results"][0]["status"] == "skipped"

    # firing alert that triggers both try_auto_heal and audit exceptions
    resp = client.post(
        "/api/v1/alerts/webhook/prometheus",
        json={"alerts": [{"id": "a-2", "status": "firing", "severity": "critical", "host": "h"}]},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert results[0]["status"] == "error"
