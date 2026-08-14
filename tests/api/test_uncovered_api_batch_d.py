# -*- coding: utf-8 -*-
"""Real API coverage tests for the Phase 3/4 uncovered routers."""

import asyncio
import pathlib
import tempfile
from datetime import datetime
from types import SimpleNamespace
from typing import Any

import pytest

import api.ai_router
import api.dashboard_router
import api.grpc_router
import api.i18n_router
import api.priority_router
import api.repair_scripts_router
import api.service_monitoring_router
import api.team_collaboration_router
import api.teams_router
import api.topology_router
import api.tracing_router
import api.users_router
import api.workflow_router
import api.workflow_visualization_router
import core.ai_engine
import core.authentication
import core.db_engine
import core.service_monitoring_manager
import core.stats_engine

pytestmark = [pytest.mark.api]


def _patch_core_auth(monkeypatch: Any) -> None:
    async def fake_is_token_revoked(token: str, redis_client: Any = None) -> bool:
        return False

    async def fake_get_user(username: str) -> Any:
        return core.authentication.User(
            username=username, role="admin", disabled=False
        )

    monkeypatch.setattr(core.authentication, "is_token_revoked", fake_is_token_revoked)
    monkeypatch.setattr(core.authentication, "get_user", fake_get_user)


# ---------------------------------------------------------------------------
# AI router
# ---------------------------------------------------------------------------
def _patch_ai(monkeypatch: Any) -> None:
    async def fake_analyze(
        query: str,
        metrics_snapshot: str | None,
        platform: str,
        rich_context: dict | None,
        validate_json: bool,
    ) -> dict[str, Any]:
        return {
            "data_assessment": {
                "reliability_score": 0.9,
                "reliability_concerns": [],
            },
            "candidates": [],
            "multi_root_cause_note": "",
            "escalation_recommended": False,
            "escalation_reason": "",
            "recommended_action": "restart the service",
        }

    monkeypatch.setattr(api.ai_router, "analyze", fake_analyze)
    monkeypatch.setattr(api.ai_router, "get_cached_snapshot", lambda: None)
    monkeypatch.setattr(
        api.ai_router,
        "collect_all",
        lambda: {
            "cpu": {"usage_percent": 12.3},
            "memory": {"usage_percent": 45.6},
            "disk": [{"usage_percent": 78.9}],
        },
    )

    async def fake_collect_rich(snapshot: Any) -> dict[str, Any]:
        return {
            "top_processes": [{"name": "python", "cpu": 1.0, "memory": 2.0}],
            "recent_alerts": [{"id": "a1", "value": "85"}],
            "recent_repairs": [{"success": True, "script_name": "r1"}],
            "stats": {"current_anomalies": 1},
        }

    monkeypatch.setattr(
        api.ai_router.ai_context_service, "collect_rich_context", fake_collect_rich
    )

    async def fake_summary() -> dict[str, Any]:
        return {
            "current_anomalies": 1,
            "heal_rate": 0.5,
            "total_alerts": 2,
            "mttr": 3.0,
        }

    monkeypatch.setattr(core.stats_engine, "get_real_summary", fake_summary)
    monkeypatch.setattr(
        core.db_engine,
        "query_repairs",
        lambda today_only, limit: [
            {
                "success": True,
                "rule_name": "rule-1",
                "script_key": "script-1",
                "repair_duration_sec": 1,
                "platform": "windows",
            }
        ],
    )


def test_ai_analyze_success(client, admin_headers, monkeypatch):
    _patch_ai(monkeypatch)
    payload = {
        "query": "CPU usage is high, please analyze",
        "include_metrics": True,
        "platform": "windows",
        "include_rich_context": True,
    }
    resp = client.post("/api/ai/analyze", headers=admin_headers, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "analysis" in data
    assert data["platform"] == "windows"
    assert data["context_summary"]["rich_enabled"] is True
    assert "metrics_context" in data


def test_ai_analyze_validation(client, admin_headers):
    resp = client.post(
        "/api/ai/analyze", headers=admin_headers, json={"query": "   "}
    )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Workflow visualization router
# ---------------------------------------------------------------------------
def _patch_workflow_vis(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        api.workflow_visualization_router,
        "get_workflow_definitions",
        lambda: {
            "wf1": {
                "name": "Workflow One",
                "description": "First workflow",
                "steps": [
                    {"key": "start", "title": "Start", "desc": "begin"},
                    "middle_step",
                    {"key": "end", "title": "End", "desc": "finish"},
                ],
            }
        },
    )


def test_workflow_visualization_page_not_found(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        api.workflow_visualization_router,
        "BASE_DIR",
        pathlib.Path(tempfile.mkdtemp()),
    )
    resp = client.get("/workflow/visualization", headers=admin_headers)
    assert resp.status_code == 404
    assert "Workflow visualization page not found" in resp.text


def test_workflow_structure(client, admin_headers, monkeypatch):
    _patch_workflow_vis(monkeypatch)
    resp = client.get("/workflow/structure", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data and "edges" in data
    assert data["metadata"]["workflow_key"] == "wf1"

    resp2 = client.get("/workflow/structure?key=missing", headers=admin_headers)
    assert resp2.status_code == 404


# ---------------------------------------------------------------------------
# Service monitoring router
# ---------------------------------------------------------------------------
class _FakeServiceMonitoringManager:
    def get_monitoring_summary(self) -> dict[str, Any]:
        return {"monitored_services": 3, "active_alerts": 1}

    def record_metric(self, **kwargs: Any) -> None:
        return None

    def get_service_metrics(self, service_name: str, time_range: Any) -> list[Any]:
        return [
            SimpleNamespace(
                metric_name="cpu",
                value=55.5,
                timestamp=datetime.utcnow(),
                labels={"host": "h1"},
            )
        ]

    def analyze_service_performance(self, service_name: str, time_range: Any) -> dict[str, Any]:
        return {
            "service_name": service_name,
            "avg_response_time": 120.0,
            "error_rate": 0.01,
        }

    def detect_anomaly(
        self, metric_name: str, service_name: str, current_value: float
    ) -> Any:
        return SimpleNamespace(
            service_name=service_name,
            metric_name=metric_name,
            is_anomaly=True,
            anomaly_score=0.95,
            expected_value=10.0,
            actual_value=current_value,
            timestamp=datetime.utcnow(),
        )

    def create_alert_rule(self, **kwargs: Any) -> None:
        return None

    def check_alert_rules(self) -> list[Any]:
        return [
            SimpleNamespace(
                alert_id="a1",
                service_name="svc",
                severity=core.service_monitoring_manager.AlertSeverity.WARNING,
                message="CPU high",
                metric_name="cpu",
                threshold=80.0,
                current_value=95.0,
                timestamp=datetime.utcnow(),
            )
        ]


def _patch_service_monitoring(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        core.service_monitoring_manager,
        "get_service_monitoring_manager",
        _FakeServiceMonitoringManager,
    )


def test_service_monitoring_status(client, admin_headers, monkeypatch):
    _patch_service_monitoring(monkeypatch)
    resp = client.get("/api/service-monitoring/status", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["monitored_services"] == 3


def test_service_monitoring_record_metric(client, admin_headers, monkeypatch):
    _patch_service_monitoring(monkeypatch)
    resp = client.post(
        "/api/service-monitoring/metric",
        headers=admin_headers,
        params={
            "metric_name": "cpu",
            "service_name": "api-service",
            "value": 42.0,
            "metric_type": "gauge",
        },
    )
    assert resp.status_code == 200
    assert "cpu recorded for api-service" in resp.json()["message"]


def test_service_monitoring_metrics(client, admin_headers, monkeypatch):
    _patch_service_monitoring(monkeypatch)
    resp = client.get(
        "/api/service-monitoring/metrics/api-service",
        headers=admin_headers,
        params={"time_range_hours": 2},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["count"] == 1


def test_service_monitoring_analysis(client, admin_headers, monkeypatch):
    _patch_service_monitoring(monkeypatch)
    resp = client.get(
        "/api/service-monitoring/analysis/api-service",
        headers=admin_headers,
        params={"time_range_hours": 2},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["avg_response_time"] == 120.0


def test_service_monitoring_anomaly(client, admin_headers, monkeypatch):
    _patch_service_monitoring(monkeypatch)
    resp = client.post(
        "/api/service-monitoring/anomaly/detect",
        headers=admin_headers,
        params={
            "metric_name": "cpu",
            "service_name": "api-service",
            "current_value": 99.0,
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["is_anomaly"] is True


def test_service_monitoring_alert_rule(client, admin_headers, monkeypatch):
    _patch_service_monitoring(monkeypatch)
    resp = client.post(
        "/api/service-monitoring/alert-rule",
        headers=admin_headers,
        params={
            "rule_id": "rule-1",
            "service_name": "api-service",
            "metric_name": "cpu",
            "threshold": 80.0,
            "comparison": "greater_than",
            "severity": "warning",
        },
    )
    assert resp.status_code == 200
    assert "rule-1 created" in resp.json()["message"]


def test_service_monitoring_alert_check(client, admin_headers, monkeypatch):
    _patch_service_monitoring(monkeypatch)
    resp = client.post("/api/service-monitoring/alert/check", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["count"] == 1


# ---------------------------------------------------------------------------
# I18n router
# ---------------------------------------------------------------------------
def test_i18n_status(client, admin_headers):
    resp = client.get("/api/i18n/status", headers=admin_headers)
    assert resp.status_code == 200
    assert "total_locales" in resp.json()["data"]


def test_i18n_locales(client, admin_headers):
    resp = client.get("/api/i18n/locales", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"]["locales"], list)


def test_i18n_locale_info_and_set(client, admin_headers):
    resp = client.get("/api/i18n/locales/en-US", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["locale_id"] == "en-US"

    resp = client.post(
        "/api/i18n/locale/set",
        headers=admin_headers,
        params={"locale_id": "en-US"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["set"] is True


def test_i18n_translate_and_update(client, admin_headers):
    resp = client.get(
        "/api/i18n/translate",
        headers=admin_headers,
        params={"key": "hello", "namespace": "common", "language": "zh"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["key"] == "hello"

    resp = client.put(
        "/api/i18n/translate",
        headers=admin_headers,
        params={
            "key": "hello",
            "translation": "你好",
            "namespace": "common",
            "language": "zh-CN",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["translation"] == "你好"


def test_i18n_formats(client, admin_headers):
    resp = client.get(
        "/api/i18n/format/number",
        headers=admin_headers,
        params={"number": 1234.5, "locale": "en-US", "decimals": 2},
    )
    assert resp.status_code == 200
    assert "formatted" in resp.json()["data"]

    resp = client.get(
        "/api/i18n/format/currency",
        headers=admin_headers,
        params={"amount": 99.99, "locale": "en-US"},
    )
    assert resp.status_code == 200
    assert "formatted" in resp.json()["data"]

    resp = client.get(
        "/api/i18n/format/date",
        headers=admin_headers,
        params={"date_str": "2026-08-10T12:00:00", "locale": "en-US"},
    )
    assert resp.status_code == 200
    assert "formatted" in resp.json()["data"]


# ---------------------------------------------------------------------------
# Workflow router
# ---------------------------------------------------------------------------
def _patch_workflow(monkeypatch: Any) -> None:
    defs = {
        "wf1": {
            "name": "Workflow One",
            "description": "desc",
            "steps": [
                {"key": "a", "title": "A", "desc": ""},
                {"key": "b", "title": "B", "desc": ""},
            ],
        }
    }
    monkeypatch.setattr(api.workflow_router, "WORKFLOW_DEFINITIONS", defs)
    monkeypatch.setattr(api.workflow_router, "get_workflow_definitions", lambda: defs)
    monkeypatch.setattr(
        api.workflow_router,
        "create_workflow_definition",
        lambda key, payload: {"key": key, **payload},
    )
    monkeypatch.setattr(
        api.workflow_router,
        "update_workflow_definition",
        lambda key, payload: {"updated": key, **payload},
    )
    monkeypatch.setattr(
        api.workflow_router, "delete_workflow_definition", lambda key: None
    )

    async def fake_stream(key: str):
        yield {"type": "workflow_start", "wf_name": key}
        yield {"type": "step_complete", "node_key": "a"}
        yield {"type": "workflow_done", "total_ms": 100}

    monkeypatch.setattr(api.workflow_router, "simulate_workflow_stream", fake_stream)
    monkeypatch.setattr(api.workflow_router, "parse_json_workflow", lambda s: object())

    async def fake_execute(dag: Any) -> Any:
        return SimpleNamespace(
            workflow_id="w-1",
            run_id="r-1",
            status=SimpleNamespace(value="completed"),
            results={"a": "ok"},
            errors=[],
        )

    monkeypatch.setattr(api.workflow_router._executor, "execute", fake_execute)


def test_workflow_list(client, admin_headers, monkeypatch):
    _patch_workflow(monkeypatch)
    resp = client.get("/api/v1/workflows/definitions", headers=admin_headers)
    assert resp.status_code == 200
    assert "wf1" in resp.json()


def test_workflow_get(client, admin_headers, monkeypatch):
    _patch_workflow(monkeypatch)
    resp = client.get("/api/v1/workflows/definitions/wf1", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["name"] == "Workflow One"

    resp2 = client.get("/api/v1/workflows/definitions/missing", headers=admin_headers)
    assert resp2.status_code == 404


def test_workflow_create_update_delete(client, admin_headers, monkeypatch):
    _patch_workflow(monkeypatch)
    body = {
        "wf_key": "new_wf",
        "name": "New Workflow",
        "steps": [{"key": "s1", "title": "Step 1", "desc": ""}],
    }
    resp = client.post(
        "/api/v1/workflows/definitions", headers=admin_headers, json=body
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["key"] == "new_wf"

    resp = client.put(
        "/api/v1/workflows/definitions/new_wf",
        headers=admin_headers,
        json={"name": "Updated"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == "new_wf"

    resp = client.delete(
        "/api/v1/workflows/definitions/new_wf", headers=admin_headers
    )
    assert resp.status_code == 200


def test_workflow_simulate(client, admin_headers, monkeypatch):
    _patch_workflow(monkeypatch)
    resp = client.get(
        "/api/v1/workflows/simulate/wf1",
        headers=admin_headers,
        timeout=3.0,
    )
    assert resp.status_code == 200
    assert "workflow_start" in resp.text


def test_workflow_concurrent(client, admin_headers):
    resp = client.get("/api/v1/workflows/concurrent", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "max_concurrent" in data and "in_use" in data


def test_workflow_execute(client, admin_headers, monkeypatch):
    _patch_workflow(monkeypatch)
    resp = client.post(
        "/api/v1/workflows/execute",
        headers=admin_headers,
        json={"workflow": {"nodes": [{"id": "a", "type": "noop"}]}},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["workflow_id"] == "w-1"
    assert data["status"] == "completed"


# ---------------------------------------------------------------------------
# Team collaboration router
# ---------------------------------------------------------------------------
def _patch_team_collaboration(monkeypatch: Any) -> None:
    async def list_teams() -> list[dict[str, Any]]:
        return [{"id": "team-1", "name": "SRE"}]

    async def get_oncall(id: str) -> dict[str, Any]:
        return {"primary": "alice", "secondary": "bob"}

    async def create_handoff(
        team_id: str, from_user: str | None, to_user: str | None, notes: str
    ) -> dict[str, Any]:
        return {"id": "h1", "team_id": team_id, "notes": notes}

    async def list_handoffs(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"id": "h1", "notes": "notes"}]

    async def escalate(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"escalated": True}

    async def list_dashboards(*args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return [{"id": "d1", "name": "Main"}]

    monkeypatch.setattr(api.team_collaboration_router, "list_teams", list_teams)
    monkeypatch.setattr(api.team_collaboration_router, "get_team_oncall", get_oncall)
    monkeypatch.setattr(api.team_collaboration_router, "create_handoff", create_handoff)
    monkeypatch.setattr(api.team_collaboration_router, "list_handoffs", list_handoffs)
    monkeypatch.setattr(
        api.team_collaboration_router, "escalate_incident", escalate
    )
    monkeypatch.setattr(api.team_collaboration_router, "list_dashboards", list_dashboards)


def test_team_collaboration(client, admin_headers, monkeypatch):
    _patch_team_collaboration(monkeypatch)

    resp = client.get("/api/v1/team-collaboration/teams", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()[0]["id"] == "team-1"

    resp = client.get(
        "/api/v1/team-collaboration/teams/team-1/oncall", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["primary"] == "alice"

    resp = client.post(
        "/api/v1/team-collaboration/teams/team-1/handoffs",
        headers=admin_headers,
        json={"notes": "handing over"},
    )
    assert resp.status_code == 201
    assert resp.json()["notes"] == "handing over"

    resp = client.get(
        "/api/v1/team-collaboration/teams/team-1/handoffs", headers=admin_headers
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.post(
        "/api/v1/team-collaboration/incidents/inc-1/escalate",
        headers=admin_headers,
        json={"team_id": "team-1", "reason": "page needed"},
    )
    assert resp.status_code == 200
    assert resp.json()["escalated"] is True

    resp = client.get(
        "/api/v1/team-collaboration/dashboards",
        headers=admin_headers,
        params={"team_id": "team-1"},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# Repair scripts router
# ---------------------------------------------------------------------------
class _FakeRepairStrategy:
    def get_scripts(self) -> list[dict[str, Any]]:
        return [{"key": "kill_process", "name": "Kill process"}]


def _patch_repair_scripts(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        api.repair_scripts_router,
        "get_all_platform_strategies",
        lambda: {"windows": _FakeRepairStrategy()},
    )
    monkeypatch.setattr(
        api.repair_scripts_router,
        "get_platform_strategy",
        lambda p: _FakeRepairStrategy(),
    )


def test_repair_scripts(client, admin_headers, monkeypatch):
    _patch_repair_scripts(monkeypatch)
    resp = client.get("/api/v1/repair-scripts/", headers=admin_headers)
    assert resp.status_code == 200
    assert "windows" in resp.json()["scripts"]

    resp = client.get("/api/v1/repair-scripts/windows", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["platform"] == "windows"
    assert len(resp.json()["scripts"]) == 1


# ---------------------------------------------------------------------------
# Teams (Microsoft Teams integration) router
# ---------------------------------------------------------------------------
def _patch_teams(monkeypatch: Any) -> None:
    async def post_message(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"message_id": "m1"}

    async def post_interactive_message(*args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"card_id": "c1"}

    def handle_instruction(
        text: str, user_id: str, user_name: str, channel: str, verified: bool
    ) -> dict[str, Any]:
        return {"command": text.strip(), "user": user_id}

    monkeypatch.setattr(api.teams_router, "post_message", post_message)
    monkeypatch.setattr(
        api.teams_router, "post_interactive_message", post_interactive_message
    )
    monkeypatch.setattr(api.teams_router, "handle_instruction", handle_instruction)
    monkeypatch.setattr(
        api.teams_router,
        "get_current_active_user",
        lambda: {"username": "admin", "role": "admin"},
    )


def test_teams_message(client, admin_headers, monkeypatch):
    _patch_core_auth(monkeypatch)
    _patch_teams(monkeypatch)
    resp = client.post(
        "/api/teams/message",
        headers=admin_headers,
        json={"text": "CPU high", "title": "Alert", "channel": "General"},
    )
    assert resp.status_code == 200
    assert resp.json()["success"] is True
    assert resp.json()["data"]["message_id"] == "m1"


def test_teams_interactive(client, admin_headers, monkeypatch):
    _patch_core_auth(monkeypatch)
    _patch_teams(monkeypatch)
    resp = client.post(
        "/api/teams/interactive",
        headers=admin_headers,
        json={
            "title": "Ack",
            "description": "High CPU",
            "actions": [
                {"title": "Ack", "type": "Action.Submit", "action": "ack"}
            ],
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["card_id"] == "c1"


def test_teams_events(client, admin_headers, monkeypatch):
    _patch_core_auth(monkeypatch)
    _patch_teams(monkeypatch)
    resp = client.post(
        "/api/teams/events",
        headers=admin_headers,
        json={"text": "ack incident-1", "from": "alice", "channel": "General"},
    )
    assert resp.status_code == 200
    assert resp.json()["action"]["command"] == "ack incident-1"

    resp = client.post(
        "/api/teams/events",
        headers=admin_headers,
        json={"value": {"action": "approve", "value": "incident-1"}},
    )
    assert resp.status_code == 200
    assert resp.json()["action"]["type"] == "approve"


# ---------------------------------------------------------------------------
# Priority router
# ---------------------------------------------------------------------------
class _FakeAssessor:
    def assess(self, **kwargs: Any) -> Any:
        return SimpleNamespace(
            to_dict=lambda: {"impact_level": "high"}, impact_level="high"
        )


class _FakeRanker:
    def rank_alerts(self, alerts: list[dict[str, Any]]) -> list[Any]:
        return [
            SimpleNamespace(alert_id="a1", priority=1),
            SimpleNamespace(alert_id="a2", priority=2),
        ]


class _FakeSLAScheduler:
    def get_sla_status(self, service: str) -> dict[str, Any]:
        return {"service": service, "compliance": 0.98}


def _patch_priority(monkeypatch: Any) -> None:
    monkeypatch.setattr(api.priority_router, "_assessor", _FakeAssessor())
    monkeypatch.setattr(api.priority_router, "_ranker", _FakeRanker())
    monkeypatch.setattr(api.priority_router, "_sla_scheduler", _FakeSLAScheduler())


def test_priority(client, admin_headers, monkeypatch):
    _patch_priority(monkeypatch)
    resp = client.get("/priority/health", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["priority_available"] is True

    resp = client.post(
        "/priority/assess",
        headers=admin_headers,
        json={
            "service": "api-service",
            "affected_users": 1000,
            "revenue_per_minute": 500.0,
            "sla_violation": True,
            "context": {},
        },
    )
    assert resp.status_code == 200
    assert resp.json()["impact_level"] == "high"

    resp = client.post(
        "/priority/rank",
        headers=admin_headers,
        json=[{"alert_id": "a1"}, {"alert_id": "a2"}],
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = client.get(
        "/priority/sla/status",
        headers=admin_headers,
        params={"service": "api-service"},
    )
    assert resp.status_code == 200
    assert resp.json()["service"] == "api-service"


# ---------------------------------------------------------------------------
# gRPC router
# ---------------------------------------------------------------------------
class _FakeGrpcServer:
    started = False
    stopped = False

    async def start(self) -> None:
        self.started = True

    async def stop(self) -> None:
        self.stopped = True


def _patch_grpc(monkeypatch: Any) -> None:
    monkeypatch.setattr(api.grpc_router, "_grpc_server", _FakeGrpcServer())


def test_grpc(client, admin_headers, monkeypatch):
    _patch_grpc(monkeypatch)
    resp = client.get("/grpc/health", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["grpc_available"] is True
    assert resp.json()["server_running"] is True

    resp = client.post("/grpc/start", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "started"

    resp = client.post("/grpc/stop", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "stopped"


# ---------------------------------------------------------------------------
# Topology router
# ---------------------------------------------------------------------------
def _patch_topology(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        api.topology_router, "TOPOLOGY_TYPES", {"k8s": "Kubernetes", "host": "Host"}
    )
    monkeypatch.setattr(
        api.topology_router,
        "get_topology_status",
        lambda key: {"nodes": [], "active_flows": [], "node_count": 0},
    )
    monkeypatch.setattr(api.topology_router, "update_node_health", lambda n, s: None)

    async def fake_full_link() -> dict[str, Any]:
        return {"nodes": [{"id": "n1"}], "edges": []}

    monkeypatch.setattr(
        api.topology_router, "get_full_link_topology", fake_full_link
    )
    monkeypatch.setattr(
        api.topology_router,
        "get_node_timeline",
        lambda node: {"summary": {"total": 0}, "events": []},
    )


def test_topology_types(client, admin_headers, monkeypatch):
    _patch_topology(monkeypatch)
    resp = client.get("/api/v1/topologies/types", headers=admin_headers)
    assert resp.status_code == 200
    assert any(t["key"] == "k8s" for t in resp.json()["types"])


def test_topology_status(client, admin_headers, monkeypatch):
    _patch_topology(monkeypatch)
    resp = client.get("/api/v1/topologies/status/k8s", headers=admin_headers)
    assert resp.status_code == 200
    assert "node_count" in resp.json()

    resp2 = client.get(
        "/api/v1/topologies/status/invalid!key", headers=admin_headers
    )
    assert resp2.status_code == 422


def test_topology_node_health(client, admin_headers, monkeypatch):
    _patch_topology(monkeypatch)
    resp = client.post(
        "/api/v1/topologies/node/health",
        headers=admin_headers,
        json={"node_id": "agent", "status": "warning"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["node_id"] == "agent" and data["health"] == "warning"

    resp2 = client.post(
        "/api/v1/topologies/node/health",
        headers=admin_headers,
        json={"node_id": "bad!id", "status": "critical"},
    )
    assert resp2.status_code == 422


def test_topology_full_link_and_timeline(client, admin_headers, monkeypatch):
    _patch_topology(monkeypatch)
    resp = client.get("/api/v1/topologies/full-link", headers=admin_headers)
    assert resp.status_code == 200
    assert "nodes" in resp.json()

    resp = client.get(
        "/api/v1/topologies/node/agent/timeline",
        headers=admin_headers,
        params={"hours": 2, "limit": 10},
    )
    assert resp.status_code == 200
    assert "summary" in resp.json()


def test_topology_cache_clear(client, admin_headers):
    resp = client.post("/api/v1/topologies/cache/clear", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ---------------------------------------------------------------------------
# Dashboard router
# ---------------------------------------------------------------------------
def test_dashboard_summary(client, admin_headers, monkeypatch):
    _patch_core_auth(monkeypatch)
    resp = client.get("/dashboard/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert isinstance(data["total_hosts"], int)
    assert "total_alerts" in data
    assert "pending_repairs" in data


# ---------------------------------------------------------------------------
# Tracing router
# ---------------------------------------------------------------------------
def test_tracing_dashboard(client, admin_headers):
    resp = client.get("/api/tracing/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"


def test_tracing_traces(client, admin_headers):
    resp = client.get(
        "/api/tracing/traces",
        headers=admin_headers,
        params={"limit": 5},
    )
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)

    resp = client.get(
        "/api/tracing/traces",
        headers=admin_headers,
        params={"limit": 5, "min_duration": "10ms", "max_duration": "1s"},
    )
    assert resp.status_code == 200


def test_tracing_trace_details(client, admin_headers):
    resp = client.get(
        "/api/tracing/traces/abc123def4567890", headers=admin_headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["data"]["trace_id"] == "abc123def4567890"


def test_tracing_topology(client, admin_headers):
    resp = client.get("/api/tracing/topology", headers=admin_headers)
    assert resp.status_code == 200
    assert "nodes" in resp.json()["data"]


def test_tracing_performance_hotspots(client, admin_headers):
    resp = client.get(
        "/api/tracing/performance/hotspots",
        headers=admin_headers,
        params={"service_name": "host-0"},
    )
    assert resp.status_code == 200
    assert "slow_operations" in resp.json()["data"]


def test_tracing_error_analysis(client, admin_headers):
    resp = client.get("/api/tracing/errors/analysis", headers=admin_headers)
    assert resp.status_code == 200
    assert "error_count" in resp.json()["data"]


def test_tracing_export_config(client, admin_headers):
    resp = client.get("/api/tracing/export/trace-config", headers=admin_headers)
    assert resp.status_code == 200
    assert "otlp_endpoint" in resp.json()["data"]


# ---------------------------------------------------------------------------
# Users router
# ---------------------------------------------------------------------------
def test_users_crud(client, admin_headers):
    # list
    resp = client.get("/api/v1/users/", headers=admin_headers)
    assert resp.status_code == 200
    users = resp.json()
    assert isinstance(users, list)

    # me
    resp = client.get("/api/v1/users/me", headers=admin_headers)
    assert resp.status_code == 200
    admin_id = resp.json()["id"]

    # create operator
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": "op_test", "password": "pass123!", "role": "operator"},
    )
    assert resp.status_code == 201
    op_id = resp.json()["id"]
    assert resp.json()["role"] == "operator"

    # duplicate username
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": "op_test", "password": "pass123!", "role": "operator"},
    )
    assert resp.status_code == 400

    # invalid role
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": "bad_user", "password": "pass123!", "role": "super"},
    )
    assert resp.status_code == 400

    # get user
    resp = client.get(f"/api/v1/users/{op_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "op_test"

    # update own password
    resp = client.put(
        f"/api/v1/users/{admin_id}",
        headers=admin_headers,
        json={"new_password": "newpass123!"},
    )
    assert resp.status_code == 200

    # update operator role and status
    resp = client.put(
        f"/api/v1/users/{op_id}",
        headers=admin_headers,
        json={"role": "business", "is_active": False},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "business"
    assert resp.json()["is_active"] is False

    # permissions
    resp = client.get(f"/api/v1/users/{op_id}/permissions", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []

    resp = client.put(
        f"/api/v1/users/{op_id}/permissions",
        headers=admin_headers,
        json={"permissions": [{"asset_id": 1, "permission": "view"}]},
    )
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["permission"] == "view"

    resp = client.put(
        f"/api/v1/users/{op_id}/permissions",
        headers=admin_headers,
        json={"permissions": [{"asset_id": 1, "permission": "own"}]},
    )
    assert resp.status_code == 400

    # delete
    resp = client.delete(f"/api/v1/users/{op_id}", headers=admin_headers)
    assert resp.status_code == 200


def test_users_extra_auth_and_errors(client, admin_headers, monkeypatch):
    # last-admin protections on self (admin id 1)
    resp = client.get("/api/v1/users/me", headers=admin_headers)
    admin_id = resp.json()["id"]

    resp = client.put(
        f"/api/v1/users/{admin_id}",
        headers=admin_headers,
        json={"role": "operator"},
    )
    assert resp.status_code == 400
    resp = client.put(
        f"/api/v1/users/{admin_id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert resp.status_code == 400
    resp = client.delete(f"/api/v1/users/{admin_id}", headers=admin_headers)
    assert resp.status_code == 400

    # exercise max_admin_check by creating admins up to the limit
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": "admin2", "password": "pass123!", "role": "admin"},
    )
    assert resp.status_code == 201
    admin2_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": "admin3", "password": "pass123!", "role": "admin"},
    )
    assert resp.status_code == 201
    admin3_id = resp.json()["id"]

    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": "admin4", "password": "pass123!", "role": "admin"},
    )
    assert resp.status_code == 400

    # non-admin access controls
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": "op2", "password": "pass123!", "role": "operator"},
    )
    assert resp.status_code == 201
    op2_id = resp.json()["id"]
    op_token = client.post(
        "/api/v1/auth/login",
        json={"username": "op2", "password": "pass123!"},
    ).json()["access_token"]
    op_headers = {"Authorization": f"Bearer {op_token}"}

    # cannot view another user
    resp = client.get(f"/api/v1/users/{admin_id}", headers=op_headers)
    assert resp.status_code == 403

    # cannot update another user
    resp = client.put(
        f"/api/v1/users/{admin_id}",
        headers=op_headers,
        json={"new_password": "hacked!"},
    )
    assert resp.status_code == 403

    # operator cannot set admin-only fields
    resp = client.put(
        f"/api/v1/users/{op2_id}",
        headers=op_headers,
        json={"role": "admin"},
    )
    assert resp.status_code == 403

    # operator can change own password
    resp = client.put(
        f"/api/v1/users/{op2_id}",
        headers=op_headers,
        json={"new_password": "newpass123!"},
    )
    assert resp.status_code == 200

    # permissions 404 for missing user
    resp = client.get("/api/v1/users/9999/permissions", headers=admin_headers)
    assert resp.status_code == 404

    # cleanup
    client.delete(f"/api/v1/users/{op2_id}", headers=admin_headers)
    client.delete(f"/api/v1/users/{admin2_id}", headers=admin_headers)
    client.delete(f"/api/v1/users/{admin3_id}", headers=admin_headers)


# ---------------------------------------------------------------------------
# Additional error / edge case coverage
# ---------------------------------------------------------------------------
def test_ai_analyze_error_paths(client, admin_headers, monkeypatch):
    _patch_ai(monkeypatch)
    # rich context fails gracefully
    async def fail_rich(snapshot: Any) -> dict[str, Any]:
        raise RuntimeError("rich ctx fail")

    monkeypatch.setattr(
        api.ai_router.ai_context_service, "collect_rich_context", fail_rich
    )
    monkeypatch.setattr(
        api.ai_router, "get_cached_snapshot", lambda: {"not_dict": True}
    )
    resp = client.post(
        "/api/ai/analyze",
        headers=admin_headers,
        json={
            "query": "something",
            "include_metrics": True,
            "include_rich_context": True,
        },
    )
    assert resp.status_code == 200

    # analyze engine exception -> 500
    async def fail_analyze(*args, **kwargs):
        raise RuntimeError("ai boom")

    monkeypatch.setattr(api.ai_router, "analyze", fail_analyze)
    resp = client.post(
        "/api/ai/analyze",
        headers=admin_headers,
        json={"query": "fail", "include_metrics": False},
    )
    assert resp.status_code == 500

    # invalid string result falls back
    async def bad_string(*args, **kwargs):
        return "not-json"

    monkeypatch.setattr(api.ai_router, "analyze", bad_string)
    resp = client.post(
        "/api/ai/analyze",
        headers=admin_headers,
        json={"query": "bad", "include_metrics": False},
    )
    assert resp.status_code == 200


def test_workflow_router_errors(client, admin_headers, monkeypatch):
    _patch_workflow(monkeypatch)
    # create with bad value from engine
    monkeypatch.setattr(
        api.workflow_router,
        "create_workflow_definition",
        lambda key, payload: (_ for _ in ()).throw(ValueError("invalid key")),
    )
    resp = client.post(
        "/api/v1/workflows/definitions",
        headers=admin_headers,
        json={
            "wf_key": "bad",
            "name": "Bad",
            "steps": [{"key": "s", "title": "S"}],
        },
    )
    assert resp.status_code == 400

    # update empty payload
    monkeypatch.setattr(
        api.workflow_router,
        "create_workflow_definition",
        lambda key, payload: {"key": key, **payload},
    )
    resp = client.put(
        "/api/v1/workflows/definitions/wf1",
        headers=admin_headers,
        json={},
    )
    assert resp.status_code == 400

    # update missing workflow
    monkeypatch.setattr(
        api.workflow_router,
        "update_workflow_definition",
        lambda key, payload: (_ for _ in ()).throw(ValueError("不存在 workflow")),
    )
    resp = client.put(
        "/api/v1/workflows/definitions/missing",
        headers=admin_headers,
        json={"name": "X"},
    )
    assert resp.status_code == 404

    # delete missing workflow
    monkeypatch.setattr(
        api.workflow_router,
        "delete_workflow_definition",
        lambda key: (_ for _ in ()).throw(ValueError("不存在 workflow")),
    )
    resp = client.delete("/api/v1/workflows/definitions/missing", headers=admin_headers)
    assert resp.status_code == 404

    # execute with invalid DSL
    monkeypatch.setattr(
        api.workflow_router,
        "parse_json_workflow",
        lambda s: (_ for _ in ()).throw(ValueError("invalid workflow")),
    )
    resp = client.post(
        "/api/v1/workflows/execute",
        headers=admin_headers,
        json={"workflow": {"bad": "dsl"}},
    )
    assert resp.status_code == 400

    # simulate when semaphore is full -> 503
    monkeypatch.setattr(api.workflow_router._sse_semaphore, "locked", lambda: True)
    monkeypatch.setattr(api.workflow_router._sse_semaphore, "_value", 0)
    resp = client.get("/api/v1/workflows/simulate/wf1", headers=admin_headers)
    assert resp.status_code == 503


def test_service_monitoring_errors(client, admin_headers, monkeypatch):
    class FailingManager:
        def __getattr__(self, name: str):
            def raiser(*args, **kwargs):
                raise RuntimeError("boom")

            return raiser

    monkeypatch.setattr(
        core.service_monitoring_manager,
        "get_service_monitoring_manager",
        FailingManager,
    )
    resp = client.get("/api/service-monitoring/status", headers=admin_headers)
    assert resp.status_code == 500
    resp = client.get(
        "/api/service-monitoring/metrics/svc", headers=admin_headers
    )
    assert resp.status_code == 500

    # invalid metric type raises inside endpoint and is caught
    class GoodManager:
        def __getattr__(self, name: str):
            return lambda *args, **kwargs: None

    monkeypatch.setattr(
        core.service_monitoring_manager,
        "get_service_monitoring_manager",
        GoodManager,
    )
    resp = client.post(
        "/api/service-monitoring/metric",
        headers=admin_headers,
        params={
            "metric_name": "cpu",
            "service_name": "svc",
            "value": 1.0,
            "metric_type": "badtype",
        },
    )
    assert resp.status_code == 500


def test_i18n_errors(client, admin_headers, monkeypatch):
    class BadManager:
        def __getattr__(self, name: str):
            def raiser(*args, **kwargs):
                raise RuntimeError("i18n fail")

            return raiser

        @property
        def locales(self):
            return {}

    monkeypatch.setattr(
        core.i18n_manager, "get_i18n_manager", lambda: BadManager()
    )
    resp = client.get("/api/i18n/status", headers=admin_headers)
    assert resp.status_code == 500

    # invalid language value in translate
    monkeypatch.setattr(core.i18n_manager, "get_i18n_manager", lambda: BadManager())
    resp = client.get(
        "/api/i18n/translate",
        headers=admin_headers,
        params={"key": "hello", "namespace": "common", "language": "xx"},
    )
    assert resp.status_code == 500


def test_team_collaboration_errors(client, admin_headers, monkeypatch):
    async def raise_value(*args, **kwargs):
        raise ValueError("not found")

    async def raise_runtime(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(api.team_collaboration_router, "list_teams", raise_runtime)
    resp = client.get("/api/v1/team-collaboration/teams", headers=admin_headers)
    assert resp.status_code == 500

    monkeypatch.setattr(
        api.team_collaboration_router, "get_team_oncall", raise_value
    )
    resp = client.get(
        "/api/v1/team-collaboration/teams/unknown/oncall", headers=admin_headers
    )
    assert resp.status_code == 404

    monkeypatch.setattr(
        api.team_collaboration_router, "create_handoff", raise_value
    )
    resp = client.post(
        "/api/v1/team-collaboration/teams/unknown/handoffs",
        headers=admin_headers,
        json={"notes": "x"},
    )
    assert resp.status_code == 404

    monkeypatch.setattr(
        api.team_collaboration_router, "escalate_incident", raise_value
    )
    resp = client.post(
        "/api/v1/team-collaboration/incidents/inc-1/escalate",
        headers=admin_headers,
        json={"team_id": "unknown"},
    )
    assert resp.status_code == 400


def test_repair_scripts_errors(client, admin_headers, monkeypatch):
    monkeypatch.setattr(
        api.repair_scripts_router,
        "get_all_platform_strategies",
        lambda: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    resp = client.get("/api/v1/repair-scripts/", headers=admin_headers)
    assert resp.status_code == 500

    monkeypatch.setattr(
        api.repair_scripts_router,
        "get_platform_strategy",
        lambda p: (_ for _ in ()).throw(ValueError("bad platform")),
    )
    resp = client.get("/api/v1/repair-scripts/badplatform", headers=admin_headers)
    assert resp.status_code == 400

    monkeypatch.setattr(
        api.repair_scripts_router,
        "get_platform_strategy",
        lambda p: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    resp = client.get("/api/v1/repair-scripts/linux", headers=admin_headers)
    assert resp.status_code == 500


def test_priority_router_degraded(client, admin_headers, monkeypatch):
    monkeypatch.setattr(api.priority_router, "PRIORITY_AVAILABLE", False)
    monkeypatch.setattr(api.priority_router, "_assessor", None)
    monkeypatch.setattr(api.priority_router, "_ranker", None)
    monkeypatch.setattr(api.priority_router, "_sla_scheduler", None)

    resp = client.get("/priority/health", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["priority_available"] is False

    resp = client.post("/priority/assess", headers=admin_headers, json={})
    assert resp.status_code == 503
    resp = client.post("/priority/rank", headers=admin_headers, json=[])
    assert resp.status_code == 503
    resp = client.get("/priority/sla/status", headers=admin_headers, params={"service": "x"})
    assert resp.status_code == 503


def test_priority_router_exceptions(client, admin_headers, monkeypatch):
    _patch_priority(monkeypatch)
    monkeypatch.setattr(
        api.priority_router._assessor, "assess", lambda **kwargs: (_ for _ in ()).throw(RuntimeError("assess fail"))
    )
    resp = client.post(
        "/priority/assess",
        headers=admin_headers,
        json={"service": "x", "affected_users": 1, "revenue_per_minute": 1, "sla_violation": False},
    )
    assert resp.status_code == 500


def test_grpc_degraded_and_failures(client, admin_headers, monkeypatch):
    monkeypatch.setattr(api.grpc_router, "GRPC_AVAILABLE", False)
    monkeypatch.setattr(api.grpc_router, "_grpc_server", None)
    resp = client.get("/grpc/health", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["grpc_available"] is False
    resp = client.post("/grpc/start", headers=admin_headers)
    assert resp.status_code == 503
    resp = client.post("/grpc/stop", headers=admin_headers)
    assert resp.status_code == 503

    class FailingServer:
        async def start(self):
            raise RuntimeError("start failed")

        async def stop(self):
            raise RuntimeError("stop failed")

    monkeypatch.setattr(api.grpc_router, "GRPC_AVAILABLE", True)
    monkeypatch.setattr(api.grpc_router, "_grpc_server", FailingServer())
    resp = client.post("/grpc/start", headers=admin_headers)
    assert resp.status_code == 500
    resp = client.post("/grpc/stop", headers=admin_headers)
    assert resp.status_code == 500


def test_teams_router_errors(client, admin_headers, monkeypatch):
    _patch_core_auth(monkeypatch)
    _patch_teams(monkeypatch)
    async def raise_runtime(*args, **kwargs):
        raise RuntimeError("teams boom")

    monkeypatch.setattr(api.teams_router, "post_message", raise_runtime)
    resp = client.post(
        "/api/teams/message",
        headers=admin_headers,
        json={"text": "x"},
    )
    assert resp.status_code == 503

    async def raise_valueerror(*args, **kwargs):
        raise ValueError("bad")

    monkeypatch.setattr(api.teams_router, "post_interactive_message", raise_valueerror)
    resp = client.post(
        "/api/teams/interactive",
        headers=admin_headers,
        json={"title": "x", "description": "y", "actions": []},
    )
    assert resp.status_code == 500

    # reject action branch and empty payload
    resp = client.post(
        "/api/teams/events",
        headers=admin_headers,
        json={"value": {"action": "reject", "value": "incident-1"}},
    )
    assert resp.status_code == 200
    assert resp.json()["action"]["type"] == "reject"

    resp = client.post("/api/teams/events", headers=admin_headers, json={})
    assert resp.status_code == 200
    assert "message" in resp.json()


def test_topology_router_errors(client, admin_headers, monkeypatch):
    _patch_topology(monkeypatch)
    monkeypatch.setattr(
        api.topology_router,
        "get_topology_status",
        lambda key: {"error": f"unknown {key}"},
    )
    resp = client.get("/api/v1/topologies/status/unknown", headers=admin_headers)
    assert resp.status_code == 404

    monkeypatch.setattr(
        api.topology_router,
        "update_node_health",
        lambda node, status: (_ for _ in ()).throw(ValueError("bad node")),
    )
    resp = client.post(
        "/api/v1/topologies/node/health",
        headers=admin_headers,
        json={"node_id": "agent", "status": "warning"},
    )
    assert resp.status_code == 400

    monkeypatch.setattr(
        api.topology_router,
        "get_full_link_topology",
        lambda: (_ for _ in ()).throw(RuntimeError("full link fail")),
    )
    resp = client.get("/api/v1/topologies/full-link", headers=admin_headers)
    assert resp.status_code == 500

    monkeypatch.setattr(
        api.topology_router,
        "get_node_timeline",
        lambda node: (_ for _ in ()).throw(RuntimeError("timeline fail")),
    )
    resp = client.get(
        "/api/v1/topologies/node/agent/timeline", headers=admin_headers
    )
    assert resp.status_code == 500

    # long node id validation
    resp = client.get(
        f"/api/v1/topologies/node/{'x' * 70}/timeline", headers=admin_headers
    )
    assert resp.status_code == 422


def test_tracing_real_backend_and_errors(client, admin_headers, monkeypatch):
    import httpx

    class FakeResponse:
        status_code = 200
        def json(self):
            return {
                "data": ["svc-1"],
                "total": 1,
            }
        def raise_for_status(self):
            pass

    def fake_get(url, *args, **kwargs):
        return FakeResponse()

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setenv("JAEGER_QUERY_URL", "http://jaeger-test")

    resp = client.get("/api/tracing/dashboard", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["source"] == "jaeger"

    resp = client.get("/api/tracing/traces", headers=admin_headers, params={"limit": 5})
    assert resp.status_code == 200
    assert resp.json()["data"] == ["svc-1"]
    assert resp.json()["total"] == 1

    resp = client.get(
        "/api/tracing/traces/abc123def4567890", headers=admin_headers
    )
    assert resp.status_code == 200
    assert resp.json()["source"] == "jaeger"

    # invalid duration filters
    resp = client.get(
        "/api/tracing/traces",
        headers=admin_headers,
        params={"limit": 5, "min_duration": "bad"},
    )
    assert resp.status_code == 200

