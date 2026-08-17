# -*- coding: utf-8 -*-
"""Real business-logic coverage tests for batch B API routers."""

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import config
from core.authentication import User as AuthUser
from core.command_guard import RiskLevel

pytestmark = [pytest.mark.api]


def _headers(admin_headers):
    """Admin headers with the internal API key used by approval/guard endpoints."""
    return {**admin_headers, "X-Internal-Key": getattr(config, "INTERNAL_API_KEY", "")}


# -----------------------------------------------------------------------------
# k8s_router
# -----------------------------------------------------------------------------
def test_k8s_router(client, admin_headers, monkeypatch):
    monkeypatch.setattr("api.k8s_router.collect_all_k8s", lambda: [{"pod": "pod-1"}])
    monkeypatch.setattr("api.k8s_router.get_k8s_collect_history", lambda limit: [{"ts": "now"}])
    monkeypatch.setattr(
        "api.k8s_router.execute_repair_sync",
        lambda host, script, args: {"success": True, "output": "ok", "exit_code": 0},
    )
    monkeypatch.setattr("api.k8s_router.get_k8s_repair_history", lambda limit: [{"id": 1}])

    async def fake_repair_all(script, args):
        return [{"cluster": "c1", "success": True}]

    monkeypatch.setattr("api.k8s_router.repair_all_k8s", fake_repair_all)

    base = "/api/v1/platforms/kubernetes"

    r = client.get(f"{base}/metrics", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == [{"pod": "pod-1"}]

    r = client.get(f"{base}/history?limit=5", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == [{"ts": "now"}]

    r = client.post(
        f"{base}/repair",
        headers=admin_headers,
        json={"host": "h1", "script_name": "fix.sh", "args": {}},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = client.post(
        f"{base}/repair/all",
        headers=admin_headers,
        json={"host": "h1", "script_name": "fix.sh", "args": {}},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.get(f"{base}/repair/history?limit=3", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == [{"id": 1}]


# -----------------------------------------------------------------------------
# service_mesh_router
# -----------------------------------------------------------------------------
def test_service_mesh_router(client, admin_headers, monkeypatch):
    class FakeConfig:
        mesh_id = "m1"
        control_plane_config = {}
        auto_injection_enabled = True
        service_name = "svc"
        routing_rules = []
        mtls_enabled = True
        authentication_policies = []

    class FakeManager:
        def generate_service_mesh_summary(self):
            return {"status": "ok"}

        def generate_istio_control_plane_config(self, **kwargs):
            return FakeConfig()

        def generate_auto_injection_config(self, **kwargs):
            return {"namespace": "default"}

        def generate_virtual_service_config(self, **kwargs):
            return FakeConfig()

        def generate_mtls_config(self, **kwargs):
            return FakeConfig()

    monkeypatch.setattr("core.service_mesh_manager.get_service_mesh_manager", FakeManager)

    base = "/api/service-mesh"

    r = client.get(f"{base}/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r = client.post(
        f"{base}/istio/control-plane?mesh_id=m1&namespace=istio-system&profile=default",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["mesh_id"] == "m1"

    r = client.post(
        f"{base}/istio/auto-injection?namespace=default&enabled=true",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r = client.post(
        f"{base}/istio/virtual-service?service_name=svc&namespace=default",
        headers=admin_headers,
        json={"weight": 80},
    )
    assert r.status_code == 200
    assert r.json()["data"]["service_name"] == "svc"

    r = client.post(
        f"{base}/istio/mtls?mesh_id=m1&namespace=istio-system&strict_mode=true",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["mtls_enabled"] is True


# -----------------------------------------------------------------------------
# sse_router
# -----------------------------------------------------------------------------
def test_sse_router(client, admin_headers, monkeypatch):
    class FakeHistory:
        def __len__(self):
            return 0

        def __iter__(self):
            return iter([{"id": "a1", "msg": "m"}])

    monkeypatch.setattr("api.sse_router.alert_history", FakeHistory())

    async def finite_sleep(*args, **kwargs):
        raise asyncio.CancelledError("finish sse stream")

    monkeypatch.setattr("api.sse_router.asyncio.sleep", finite_sleep)

    r = client.get("/api/v1/sse/events", headers=admin_headers)
    assert r.status_code == 200
    assert "event: alert" in r.text


# -----------------------------------------------------------------------------
# rag_router
# -----------------------------------------------------------------------------
def test_rag_router(client, admin_headers, monkeypatch):
    monkeypatch.setattr("api.rag_router.search_similar", lambda q, top_k: [{"id": 1}])
    monkeypatch.setattr("api.rag_router.upsert_record", lambda *args, **kwargs: None)
    monkeypatch.setattr("api.rag_router.upsert_records", lambda *args, **kwargs: None)

    r = client.post("/api/v1/rag/search", headers=admin_headers, json={"query": "cpu", "top_k": 3})
    assert r.status_code == 200
    assert r.json() == [{"id": 1}]

    r = client.post(
        "/api/v1/rag/ingest",
        headers=admin_headers,
        json={"text": "hello", "id": 1, "payload": {"a": 1}},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

    r = client.post(
        "/api/v1/rag/ingest/batch",
        headers=admin_headers,
        json={"items": [{"text": "a"}, {"text": "b"}]},
    )
    assert r.status_code == 200
    assert r.json()["count"] == 2


# -----------------------------------------------------------------------------
# plugin_router
# -----------------------------------------------------------------------------
def test_plugin_router(client, admin_headers, monkeypatch):
    # The auth stack requires Redis/Postgres; stub the user lookup for this router.
    async def fake_get_user(username):
        return AuthUser(username="admin", role="admin", disabled=False)

    async def fake_is_revoked(token):
        return False

    monkeypatch.setattr("core.authentication.get_user", fake_get_user)
    monkeypatch.setattr("core.authentication.is_token_revoked", fake_is_revoked)

    class FakePlugin:
        def collect(self):
            return {"value": 42}

    monkeypatch.setattr("api.plugin_router.list_plugins", lambda: ["demo"])
    monkeypatch.setattr("api.plugin_router.get_plugin", lambda name: FakePlugin())

    r = client.get("/api/plugins/", headers=admin_headers)
    assert r.status_code == 200
    assert r.json() == ["demo"]

    r = client.post("/api/plugins/demo/run", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["plugin"] == "demo"
    assert r.json()["result"]["value"] == 42


# -----------------------------------------------------------------------------
# api_performance_router
# -----------------------------------------------------------------------------
def test_api_performance_router(client, admin_headers, monkeypatch):
    class OptStrategy:
        value = "cache"

    class OptPriority:
        value = "high"

    class FakeOptimizer:
        def get_performance_summary(self):
            return {"avg_response_time": 120}

        def analyze_response_times(self):
            return {"p95": 200}

        def identify_slow_apis(self):
            return [SimpleNamespace(endpoint="/x", avg_response_time=300, call_count=5)]

        def generate_optimizations(self):
            return [
                SimpleNamespace(
                    optimization_id="o1",
                    endpoint="/x",
                    strategy=OptStrategy(),
                    priority=OptPriority(),
                    expected_improvement=0.3,
                    description="d",
                )
            ]

        def setup_response_cache(self, endpoint, ttl):
            return None

        def invalidate_cache(self, endpoint):
            return None

        def record_api_call(self, **kwargs):
            return None

        def setup_rate_limit(self, endpoint, rpm, burst):
            return None

        def get_throughput_metrics(self):
            return {"rps": 10}

        def monitor_resource_usage(self):
            return {"cpu": 0.5}

        def setup_resource_limits(self, *args, **kwargs):
            return None

        def check_resource_limits(self):
            return {"ok": True}

    monkeypatch.setattr(
        "core.api_performance_optimizer.get_api_performance_optimizer",
        lambda: FakeOptimizer(),
    )

    base = "/api/api-performance"

    r = client.get(f"{base}/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["avg_response_time"] == 120

    r = client.get(f"{base}/response-times", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["p95"] == 200

    r = client.get(f"{base}/slow-apis?limit=5", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_slow_apis"] == 1

    r = client.post(f"{base}/optimize", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_optimizations"] == 1

    r = client.post(
        f"{base}/cache/setup?endpoint=/x&ttl_seconds=120",
        headers=admin_headers,
    )
    assert r.status_code == 200

    r = client.delete(f"{base}/cache?endpoint=/x", headers=admin_headers)
    assert r.status_code == 200

    r = client.post(
        f"{base}/record?endpoint=/x&method=GET&response_time_ms=100&status_code=200&cache_hit=false",
        headers=admin_headers,
    )
    assert r.status_code == 200

    r = client.post(
        f"{base}/rate-limit/setup?endpoint=/x&requests_per_minute=100&burst_size=10",
        headers=admin_headers,
    )
    assert r.status_code == 200

    r = client.get(f"{base}/throughput", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["rps"] == 10

    r = client.get(f"{base}/resources", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["cpu"] == 0.5

    r = client.post(
        f"{base}/resource-limits/setup?max_memory_mb=1024&max_cpu_percent=80&max_connections=100",
        headers=admin_headers,
    )
    assert r.status_code == 200

    r = client.get(f"{base}/resource-limits/check", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["ok"] is True


# -----------------------------------------------------------------------------
# doc_generator_router
# -----------------------------------------------------------------------------
def test_doc_generator_router(client, admin_headers, monkeypatch):
    now = datetime.now(timezone.utc)
    doc = SimpleNamespace(
        doc_id="d1",
        title="t",
        generator_type=SimpleNamespace(value="markdown"),
        generated_at=now,
        content="# doc",
    )

    class FakeGenerator:
        def get_generator_summary(self):
            return {"available": True}

        def get_available_templates(self):
            return ["api-doc"]

        def generate_document(self, *args, **kwargs):
            return doc

        def get_generated_document(self, doc_id):
            return doc

        def save_generated_document(self, doc_id, path):
            return True

        def list_generated_documents(self):
            return [{"doc_id": "d1"}]

    monkeypatch.setattr(
        "core.documentation_generator.get_documentation_generator",
        lambda: FakeGenerator(),
    )

    base = "/api/doc-generator"

    r = client.get(f"{base}/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["available"] is True

    r = client.get(f"{base}/templates", headers=admin_headers)
    assert r.status_code == 200
    assert "api-doc" in r.json()["data"]["templates"]

    r = client.post(
        f"{base}/document/generate?doc_id=d1&title=t&template_name=api-doc&generator_type=markdown",
        headers=admin_headers,
        json={"vars": {"x": 1}},
    )
    assert r.status_code == 200
    assert r.json()["data"]["doc_id"] == "d1"

    r = client.get(f"{base}/document/d1", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["content"] == "# doc"

    r = client.post(
        f"{base}/document/d1/save?output_path=/tmp/d1.md",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["data"]["saved"] is True

    r = client.get(f"{base}/documents", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["count"] == 1


# -----------------------------------------------------------------------------
# database_optimization_router
# -----------------------------------------------------------------------------
def test_database_optimization_router(client, admin_headers, monkeypatch):
    class FakeManager:
        def get_optimization_status(self):
            return {"enabled": True}

        def run_comprehensive_optimization(self):
            return {"optimized": 5}

        def analyze_slow_queries(self):
            return {"total": 1}

        def optimize_connection_pool(self):
            return {"pools": 2}

        def setup_query_cache(self, cache_ttl_seconds):
            return {"ttl": cache_ttl_seconds}

        def record_query_execution(self, **kwargs):
            return None

    monkeypatch.setattr(
        "core.database_optimization_manager.get_database_optimization_manager",
        lambda: FakeManager(),
    )

    base = "/api/database-optimization"

    r = client.get(f"{base}/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["enabled"] is True

    r = client.post(f"{base}/optimize", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["optimized"] == 5

    r = client.get(f"{base}/slow-queries?limit=5", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["total"] == 1

    r = client.post(f"{base}/connection-pool/optimize", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["pools"] == 2

    r = client.post(f"{base}/cache/setup?ttl_seconds=120", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["ttl"] == 120

    r = client.post(
        f"{base}/query/record?query_text=SELECT+*&duration_ms=100&database=db&table_name=t",
        headers=admin_headers,
    )
    assert r.status_code == 200

    r = client.get(f"{base}/metrics", headers=admin_headers)
    assert r.status_code == 200
    assert "optimization_status" in r.json()["data"]


# -----------------------------------------------------------------------------
# collaboration_router
# -----------------------------------------------------------------------------
def test_collaboration_router(client, admin_headers, monkeypatch):
    now = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(
        "api.collaboration_router.engine_list_workspaces",
        lambda alert_id, status: [{"id": "ws1"}],
    )
    monkeypatch.setattr(
        "api.collaboration_router.engine_get_workspace",
        lambda ws_id: {"id": ws_id, "name": "n"},
    )
    monkeypatch.setattr(
        "api.collaboration_router.engine_create_workspace",
        lambda **kwargs: {"workspace_id": "ws1", "created_at": now},
    )
    monkeypatch.setattr(
        "api.collaboration_router.engine_post_message",
        lambda ws, user, content: {"message_id": "m1"},
    )
    monkeypatch.setattr(
        "api.collaboration_router.engine_add_task",
        lambda ws, title, assignee: {"task_id": "t1"},
    )
    monkeypatch.setattr(
        "api.collaboration_router.engine_assign_task",
        lambda ws, task, assignee, status: {"task_id": task, "status": status},
    )
    monkeypatch.setattr(
        "api.collaboration_router.engine_resolve_workspace",
        lambda ws: {"resolved": True},
    )
    monkeypatch.setattr(
        "api.collaboration_router.engine_get_active_context",
        lambda: {"alerts": [], "repairs": []},
    )

    base = "/api/v1/collaboration"

    r = client.get(f"{base}/workspaces", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["workspaces"][0]["id"] == "ws1"

    r = client.get(f"{base}/workspaces/ws1", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["id"] == "ws1"

    r = client.post(
        f"{base}/workspaces",
        headers=admin_headers,
        json={"name": "incident", "assignees": ["admin"]},
    )
    assert r.status_code == 201
    assert r.json()["workspace_id"] == "ws1"

    r = client.post(
        f"{base}/workspaces/ws1/messages",
        headers=admin_headers,
        json={"user": "admin", "content": "looking"},
    )
    assert r.status_code == 200
    assert r.json()["message_id"] == "m1"

    r = client.post(
        f"{base}/workspaces/ws1/tasks",
        headers=admin_headers,
        json={"title": "fix"},
    )
    assert r.status_code == 200
    assert r.json()["task_id"] == "t1"

    r = client.patch(
        f"{base}/workspaces/ws1/tasks/t1",
        headers=admin_headers,
        json={"status": "done"},
    )
    assert r.status_code == 200
    assert r.json()["task_id"] == "t1"

    r = client.post(f"{base}/workspaces/ws1/resolve", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["resolved"] is True

    r = client.get(f"{base}/active-context", headers=admin_headers)
    assert r.status_code == 200
    assert "alerts" in r.json()


# -----------------------------------------------------------------------------
# autoheal_router
# -----------------------------------------------------------------------------
def test_autoheal_router(client, admin_headers, monkeypatch):
    async def pending():
        return [{"alert_id": "a1", "status": "pending"}]

    monkeypatch.setattr("api.autoheal_router.get_pending_approvals", pending)

    async def fake_approve_execute(alert_id, alert):
        return {"success": True, "alert_id": alert_id, "status": "approved"}

    monkeypatch.setattr("gateway.services_client.approve_and_execute", fake_approve_execute)

    async def fake_reject(alert_id, **kwargs):
        return {"success": True, "alert_id": alert_id, "status": "rejected"}

    monkeypatch.setattr("core.auto_heal.reject_repair", fake_reject)

    async def fake_runbook(alert, ctx):
        return {"success": True, "alert_id": "a1", "proposal": "restart"}

    monkeypatch.setattr("api.autoheal_router.is_runbook_available", True)
    monkeypatch.setattr("api.autoheal_router.generate_repair_runbook", fake_runbook)
    monkeypatch.setattr(
        "api.autoheal_router._find_alert_by_id",
        lambda alert_id: {"id": alert_id, "title": "t"},
    )

    async def fake_pending():
        return []

    monkeypatch.setattr("api.autoheal_router.get_pending_approvals", fake_pending)

    headers = _headers(admin_headers)
    base = "/api/v1/approvals"

    r = client.get(f"{base}/pending", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 0

    r = client.patch(f"{base}/a1", headers=headers)
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = client.post(
        f"{base}/reject",
        headers=headers,
        json={"alert_id": "a1", "reason": "not safe"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"

    r = client.post(f"{base}/takeover/a1", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"

    r = client.post(
        f"{base}/propose",
        headers=headers,
        json={"alert_id": "a1"},
    )
    assert r.status_code == 200
    assert r.json()["proposal"] == "restart"


# -----------------------------------------------------------------------------
# infrastructure_router
# -----------------------------------------------------------------------------
def test_infrastructure_router(client, admin_headers, monkeypatch):
    fake_kafka = SimpleNamespace(
        send_message=lambda **kw: True,
        get_cached_messages=lambda: [SimpleNamespace(topic="t1")],
        producer=None,
        _initialized=True,
    )

    class FakeFlinkManager:
        jobs = {"j1": SimpleNamespace(config=SimpleNamespace(job_name="j1"))}

        def create_job(self, config):
            return SimpleNamespace(config=config)

        def get_job_status(self, job_name):
            return {"job_name": job_name, "status": "running"}

    fake_storage = SimpleNamespace(
        get_read_connection_info=lambda: {"read": "ok"},
        get_write_connection_info=lambda: {"write": "ok"},
        health_check=lambda: {"ok": True},
        _initialized=True,
    )

    class FakeConfigCenter:
        def set_config(self, key, value, metadata=None):
            return True

        def get_config_item(self, key):
            return SimpleNamespace(version=7)

        def get_config(self, key):
            return "v"

        def get_all_configs(self):
            return {"k": "v"}

    fake_monitoring = SimpleNamespace(
        get_monitoring_status=lambda: {"alerts": 0},
        metrics_collector=SimpleNamespace(increment_counter=lambda x: None, _initialized=True),
        _initialized=True,
    )

    fake_data_flow = SimpleNamespace(
        get_data_flow_stats=lambda: {
            "total_processed": 1,
            "total_analyzed": 1,
            "total_errors": 0,
            "avg_processing_time_ms": 1.0,
            "error_rate": 0.0,
            "analysis_rate": 1.0,
        },
        start_data_flow=lambda: True,
        stop_data_flow=lambda: True,
        _initialized=True,
    )

    fake_monitoring_system = SimpleNamespace(
        get_monitoring_summary=lambda: {
            "total_alerts": 0,
            "active_alerts": 0,
            "critical_alerts": 0,
            "error_alerts": 0,
            "warning_alerts": 0,
            "total_dashboards": 0,
        },
        get_active_alerts=lambda: [],
        resolve_alert=lambda x: None,
        _initialized=True,
    )

    monkeypatch.setattr("api.infrastructure_router.get_kafka_processor", lambda: fake_kafka)
    monkeypatch.setattr(
        "api.infrastructure_router.get_flink_job_manager", lambda: FakeFlinkManager()
    )
    monkeypatch.setattr(
        "api.infrastructure_router.get_distributed_storage_manager",
        lambda: fake_storage,
    )
    monkeypatch.setattr("api.infrastructure_router.get_config_center", lambda: FakeConfigCenter())
    monkeypatch.setattr(
        "api.infrastructure_router.get_monitoring_infrastructure",
        lambda: fake_monitoring,
    )
    monkeypatch.setattr(
        "api.infrastructure_router.get_l1l2_data_flow_integrator",
        lambda: fake_data_flow,
    )
    monkeypatch.setattr(
        "api.infrastructure_router.get_monitoring_system_integrator",
        lambda: fake_monitoring_system,
    )

    base = "/api/v1/infrastructure"

    r = client.post(
        f"{base}/kafka/send",
        headers=admin_headers,
        json={"topic": "t1", "key": "k1", "value": {"x": 1}},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = client.get(f"{base}/kafka/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_messages"] == 1

    r = client.post(
        f"{base}/flink/job",
        headers=admin_headers,
        json={"job_name": "j1", "job_type": "metrics_aggregation", "parallelism": 2},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "created"

    r = client.get(f"{base}/flink/jobs", headers=admin_headers)
    assert r.status_code == 200
    assert len(r.json()["jobs"]) == 1

    r = client.get(f"{base}/storage/read-connection", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["read"] == "ok"

    r = client.get(f"{base}/storage/write-connection", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["write"] == "ok"

    r = client.get(f"{base}/storage/health", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["ok"] is True

    r = client.post(
        f"{base}/config",
        headers=admin_headers,
        json={"key": "k", "value": "v", "metadata": {}},
    )
    assert r.status_code == 200
    assert r.json()["version"] == 7

    r = client.get(f"{base}/config/k", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["key"] == "k"

    r = client.get(f"{base}/config", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["configs"]["k"] == "v"

    r = client.get(f"{base}/monitoring/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["alerts"] == 0

    r = client.post(f"{base}/monitoring/metrics", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = client.get(f"{base}/data-flow/stats", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_processed"] == 1

    r = client.post(f"{base}/data-flow/start", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = client.post(f"{base}/data-flow/stop", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = client.get(f"{base}/monitoring/summary", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_alerts"] == 0

    r = client.get(f"{base}/alerts", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["alerts"] == []

    r = client.post(f"{base}/alerts/a1/resolve", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["success"] is True

    r = client.get(f"{base}/health", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["kafka"] is True


# -----------------------------------------------------------------------------
# guard_router
# -----------------------------------------------------------------------------
def test_guard_router(client, admin_headers, monkeypatch):
    # RiskLevel is imported at module top

    def fake_analyze(command):
        return {
            "command": command,
            "risk_level": RiskLevel.HIGH,
            "risk_name": "高危",
            "reason": "r",
            "action": "block",
            "safe_alternative": "mv",
            "is_chained": False,
            "chain_count": 1,
        }

    monkeypatch.setattr("api.guard_router.analyze_command", fake_analyze)
    monkeypatch.setattr("api.guard_router.is_command_allowed", lambda cmd: False)
    monkeypatch.setattr("api.guard_router.rewrite_to_safe", lambda cmd: "mv /tmp/x")
    monkeypatch.setattr("api.guard_router.dry_run_preview", lambda cmd: "would delete")
    monkeypatch.setattr(
        "api.guard_router.get_audit_log",
        lambda limit: [
            {
                "command": "rm -rf /tmp",
                "risk_level": "high",
                "result": "blocked",
                "who": "admin",
                "where": "127.0.0.1",
                "what": "rm",
                "when": "2026-01-01T00:00:00Z",
                "trace_id": "t1",
            }
        ],
    )
    monkeypatch.setattr("api.guard_router.record_audit", lambda **kw: None)

    headers = _headers(admin_headers)

    r = client.post("/api/guard/check", headers=headers, json={"command": "rm -rf /tmp"})
    assert r.status_code == 200
    assert r.json()["risk_level"] == "high"

    r = client.post("/api/guard/allowed", headers=headers, json={"command": "rm -rf /tmp"})
    assert r.status_code == 200
    assert r.json()["allowed"] is False

    r = client.post("/api/guard/rewrite", headers=headers, json={"command": "rm -rf /tmp"})
    assert r.status_code == 200
    assert r.json()["changed"] is True

    r = client.post("/api/guard/dryrun", headers=headers, json={"command": "rm -rf /tmp"})
    assert r.status_code == 200
    assert "would delete" in r.json()["preview"]

    r = client.get("/api/guard/audit?limit=10&risk_level=high", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    r = client.get("/api/guard/stats", headers=headers)
    assert r.status_code == 200
    assert "blocked_count" in r.json()

    r = client.get("/api/v1/security/events", headers=headers)
    assert r.status_code == 200
    assert len(r.json()["events"]) == 1

    r = client.get("/api/v1/security/stats", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] == 1


# -----------------------------------------------------------------------------
# plugin_sdk_router
# -----------------------------------------------------------------------------
def test_plugin_sdk_router(client, admin_headers, monkeypatch):
    class FakeManager:
        def get_system_summary(self):
            return {"total_plugins": 2}

        def define_plugin_interface(self, **kwargs):
            return SimpleNamespace(
                interface_id="i1",
                interface_name="n1",
                methods=[],
                events=[],
            )

        def generate_plugin_interface_spec(self, interface_type):
            return {"type": interface_type, "methods": []}

        def register_plugin(self, plugin_id, metadata):
            return True

        def enable_plugin(self, plugin_id):
            return True

        def disable_plugin(self, plugin_id):
            return True

        def list_plugins(self, plugin_type=None, status=None):
            return [{"plugin_id": "p1"}]

        def get_plugin_info(self, plugin_id):
            return {"plugin_id": plugin_id, "name": "n"}

    monkeypatch.setattr(
        "core.plugin_system_manager.get_plugin_system_manager", lambda: FakeManager()
    )

    base = "/api/plugin-system"

    r = client.get(f"{base}/status", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["total_plugins"] == 2

    r = client.post(
        f"{base}/interface/define?interface_id=i1&interface_name=n1",
        headers=admin_headers,
        json={"methods": [], "events": [], "configuration": {}},
    )
    assert r.status_code == 200
    assert r.json()["data"]["interface_id"] == "i1"

    r = client.get(f"{base}/interface/spec/data-collector", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["type"] == "data-collector"

    r = client.post(
        f"{base}/plugin/register?plugin_id=p1&name=n&version=1.0&description=d&author=a&plugin_type=monitoring",
        headers=admin_headers,
        json={"dependencies": []},
    )
    assert r.status_code == 200
    assert r.json()["data"]["registered"] is True

    r = client.post(f"{base}/plugin/p1/enable", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["enabled"] is True

    r = client.post(f"{base}/plugin/p1/disable", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["disabled"] is True

    r = client.get(f"{base}/plugins", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["count"] == 1

    r = client.get(f"{base}/plugin/p1", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["data"]["plugin_id"] == "p1"


# -----------------------------------------------------------------------------
# root_cause_router
# -----------------------------------------------------------------------------
def test_root_cause_router(client, admin_headers, monkeypatch):
    now = datetime.now(timezone.utc)

    class FakePattern:
        pattern_id = "p1"
        root_cause = "rc"
        confidence = 0.9
        frequency = 5
        last_occurrence = now
        resolution_time_avg = 1.0
        effectiveness_score = 0.8

    class FakeHypothesis:
        hypothesis_id = "h1"
        root_cause = "rc"
        confidence = 0.9
        evidence = []
        causal_path = []
        impact_score = 0.5
        verification_status = "verified"
        verification_timestamp = now

    class FakeNode:
        name = "n"
        layer = SimpleNamespace(value="infra")
        health_status = "ok"
        dependencies = set()
        dependents = set()
        last_updated = now

    class FakeEngine:
        topology_graph = {"n1": FakeNode()}
        historical_patterns = {"p1": FakePattern()}
        active_hypotheses = {"h1": FakeHypothesis()}
        hypothesis_history = []

        def _get_topology_summary(self):
            return {"nodes": 1}

        async def discover_topology_realtime(self, metrics):
            return {"found": True}

        async def perform_cross_layer_tracking(self, alert, depth):
            return ["n1"]

        async def match_historical_patterns(self, symptoms):
            return [FakePattern()]

        def learn_historical_pattern(self, *args, **kwargs):
            return None

        async def analyze_root_causes_enhanced(self, alert, metrics, context):
            return [FakeHypothesis()]

        async def predict_root_causes(self, state, horizon):
            return {"issues": []}

        async def verify_root_cause(self, hypothesis, data):
            return {"verified": True}

        def get_analysis_statistics(self):
            return {"total": 1}

    monkeypatch.setattr("api.root_cause_router.ROOT_CAUSE_INTELLIGENCE_AVAILABLE", True)
    monkeypatch.setattr("api.root_cause_router.root_cause_intelligence_engine", FakeEngine())

    base = "/api/v1/root-cause"

    r = client.get(f"{base}/topology", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["topology"]["nodes"] == 1

    r = client.post(
        f"{base}/topology/discover",
        headers=admin_headers,
        json={"metrics_data": {"cpu": 0.8}},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r = client.post(
        f"{base}/cross-layer-track?max_depth=3",
        headers=admin_headers,
        json={"id": "a1"},
    )
    assert r.status_code == 200
    assert r.json()["path_length"] == 1

    r = client.post(
        f"{base}/patterns/match",
        headers=admin_headers,
        json={"symptoms": {"cpu": 0.8}},
    )
    assert r.status_code == 200
    assert r.json()["total_matches"] == 1

    r = client.post(
        f"{base}/patterns/learn",
        headers=admin_headers,
        json={
            "symptoms": {"cpu": 0.8},
            "root_cause": "rc",
            "resolution_time": 1.0,
            "effectiveness": 0.9,
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r = client.get(f"{base}/patterns", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_patterns"] == 1

    r = client.post(
        f"{base}/analyze",
        headers=admin_headers,
        json={"alert": {"id": "a1"}, "metrics_data": {}, "context": {}},
    )
    assert r.status_code == 200
    assert r.json()["total_hypotheses"] == 1

    r = client.post(
        f"{base}/predict",
        headers=admin_headers,
        json={"current_state": {}, "prediction_horizon": 60},
    )
    assert r.status_code == 200
    assert "predictions" in r.json()

    r = client.post(
        f"{base}/verify",
        headers=admin_headers,
        json={"hypothesis_id": "h1", "verification_data": {}},
    )
    assert r.status_code == 200
    assert r.json()["verification_result"]["verified"] is True

    r = client.get(f"{base}/statistics", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["statistics"]["total"] == 1

    r = client.get(f"{base}/hypotheses", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["total_hypotheses"] == 1

    r = client.delete(f"{base}/hypotheses/h1", headers=admin_headers)
    assert r.status_code == 200
    assert r.json()["status"] == "success"
