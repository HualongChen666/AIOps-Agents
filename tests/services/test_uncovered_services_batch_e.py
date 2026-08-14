# -*- coding: utf-8 -*-
"""Coverage tests for batch E assigned service modules."""

from __future__ import annotations

import asyncio
import time as std_time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
import yaml
from fastapi.testclient import TestClient

from services.alert_service import flapping_detector as flap_mod
from services.alert_service.flapping_detector import FlappingDetector
from services.alert_service import main as alert_main
from services.alert_service import schemas as alert_schemas
from services.audit_service import compliance as audit_compliance
from services.audit_service import main_app as audit_main_app
from services.audit_service.log_recorder import OperationLogRecorder
from services.audit_service.orchestrator import AuditOrchestrator
from services.audit_service.repository import InMemoryAuditRepository
from services.audit_service.schemas import (
    AuditEvent,
    AuditEventSeverity,
    AuditReport,
    OperationLog,
    RetentionPolicy,
    SagaTransaction,
    ServiceHealth,
)
from services.repair_service.grpc.server import RPCServer
from services.repair_service.runbook_parser import RunbookParser, get_runbook_catalog
from services.repair_service.schemas import RepairRunbook, RepairStep


# ---------------------------------------------------------------------------
# alert_service / main.py
# ---------------------------------------------------------------------------
def test_alert_health():
    with TestClient(alert_main.app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


def test_alert_process_local(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(alert_main, "_AGENT_ORCH_URL", "")
    monkeypatch.setattr(alert_main, "async_insert_alert", AsyncMock(return_value=None))
    monkeypatch.setattr(
        alert_main, "try_auto_heal", AsyncMock(return_value={"healed": True})
    )

    with TestClient(alert_main.app) as client:
        resp = client.post("/process", json={"id": "a1", "severity": "high"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "local"
    assert body["processed"] == 1


def test_alert_process_remote(monkeypatch: pytest.MonkeyPatch):
    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any):
            pass
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: Any, **kwargs: Any):
            return False

        async def post(self, url: str, json: Any = None, **kwargs: Any):
            class Resp:
                @staticmethod
                def raise_for_status():
                    pass

                @staticmethod
                def json():
                    return {"orchestrated": True}

            return Resp()

    monkeypatch.setattr(alert_main, "_AGENT_ORCH_URL", "http://agent-orch")
    monkeypatch.setattr(alert_main.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(alert_main, "async_insert_alert", AsyncMock(return_value=None))
    monkeypatch.setattr(
        alert_main, "try_auto_heal", AsyncMock(return_value={"healed": True})
    )

    with TestClient(alert_main.app) as client:
        resp = client.post("/process", json={"id": "a2", "severity": "high"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "agent_orchestration"


def test_alert_call_agent_orchestration(monkeypatch: pytest.MonkeyPatch):
    class FakeClient:
        def __init__(self, *args: Any, **kwargs: Any):
            pass
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args: Any, **kwargs: Any):
            return False

        async def post(self, url: str, json: Any = None, **kwargs: Any):
            class Resp:
                @staticmethod
                def raise_for_status():
                    pass

                @staticmethod
                def json():
                    return {"ok": True}

            return Resp()

    monkeypatch.setattr(alert_main.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(alert_main, "_AGENT_ORCH_URL", "http://agent-orch")

    result = asyncio.run(alert_main._call_agent_orchestration({"id": "a3"}))
    assert result == {"ok": True}


# ---------------------------------------------------------------------------
# alert_service / schemas.py
# ---------------------------------------------------------------------------
def test_alert_schemas():
    alert = alert_schemas.Alert(id="id-1", title="CPU high", description="load")
    assert alert.title == "CPU high"

    group = alert_schemas.PrometheusAlertGroup(
        groupKey="g1",
        status="RESOLVED",
        commonLabels={"k": "v"},
        commonAnnotations={"a": "b"},
        groupLabels={"role": "db"},
        alerts=[{"labels": {"x": "y"}, "status": "firing"}],
    )
    assert group.status == "resolved"

    agg = alert_schemas.AggregatedAlert(id="agg1", title="Agg")
    assert agg.aggregated_count == 1

    assert alert_schemas.AlertSeverity.CRITICAL == "critical"
    assert alert_schemas.AlertStatus.PENDING == "pending"

    alert_schemas.RoutingRule(name="r1", destination="slack")
    alert_schemas.SuppressionRule(name="s1")
    alert_schemas.EscalationRule(name="e1")
    alert_schemas.ClassificationRule(name="c1", category="infra")
    alert_schemas.RouteResult(route="email", alert_id="a1")
    alert_schemas.ServiceHealth(status="ok", service="alert")
    alert_schemas.NotificationPayload(
        channel="email",
        alert=alert,
        content="details",
    )


def test_alert_schemas_rejection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        alert_schemas, "_moderate_content", lambda text: (False, ["toxic"])
    )
    with pytest.raises(ValueError):
        alert_schemas.Alert(id="id-1", title="bad", description="bad")


# ---------------------------------------------------------------------------
# alert_service / flapping_detector.py
# ---------------------------------------------------------------------------
def test_flapping_detector():
    det = FlappingDetector(window_seconds=10, threshold=2)
    assert det.update("fp1", "firing") is False
    assert det.is_flapping("fp1") is False
    assert det.update("fp1", "resolved") is False
    assert det.update("fp1", "firing") is True
    assert det.is_flapping("fp1") is True

    stats = det.get_stats()
    assert stats["active_states"] == 1
    assert stats["flapping_alerts"] == 1

    det.clear("fp1")
    assert det.is_flapping("fp1") is False
    assert det.get_stats()["active_states"] == 0


def test_flapping_detector_eviction():
    det = FlappingDetector(window_seconds=5, threshold=1)
    state = flap_mod._FlapState(last_status="a")
    state.last_seen = 0.0
    det._states["fp2"] = state

    det._evict(100.0)
    assert "fp2" not in det._states
    assert det.update("fp2", "b") is False


# ---------------------------------------------------------------------------
# audit_service / compliance.py
# ---------------------------------------------------------------------------
def test_compliance_render():
    out = audit_compliance.ComplianceTemplate.render(
        "soc2",
        {
            "tenant_id": "t1",
            "start_time": "2024-01-01",
            "end_time": "2024-12-31",
        },
    )
    assert "t1" in out
    assert "2024-01-01" in out

    unknown = audit_compliance.ComplianceTemplate.render("hipaa", {"tenant_id": "t2"})
    assert "t2" in unknown


# ---------------------------------------------------------------------------
# audit_service / log_recorder.py
# ---------------------------------------------------------------------------
def test_operation_log_recorder():
    repo = InMemoryAuditRepository()
    recorder = OperationLogRecorder(repo)

    async def run():
        log = await recorder.record(
            event_id="e1",
            action="create",
            actor="admin",
            before_state={},
            after_state={"x": 1},
        )
        assert log.log_id == "log-e1"
        fetched = await recorder.query("e1")
        assert len(fetched) == 1

    asyncio.run(run())


# ---------------------------------------------------------------------------
# audit_service / main_app.py
# ---------------------------------------------------------------------------
def test_audit_main_app_endpoints(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(audit_main_app, "_orchestrator", None)

    with TestClient(audit_main_app.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/metrics").status_code == 200

        event = {
            "event_id": "e1",
            "action": "login",
            "resource": "user",
            "user_id": "u1",
            "tenant_id": "t1",
            "severity": "low",
            "metadata": {},
        }
        assert client.post("/events", json=event).status_code == 200
        assert client.get("/events?tenant_id=t1").status_code == 200

        log = {
            "log_id": "l1",
            "event_id": "e1",
            "action": "login",
            "actor": "admin",
        }
        assert client.post("/logs", json=log).status_code == 200
        assert client.get("/logs/e1").status_code == 200

        report_params = (
            "?report_type=soc2&tenant_id=t1"
            "&start_time=2024-01-01T00:00:00"
            "&end_time=2024-12-31T23:59:59"
        )
        assert client.post(f"/reports{report_params}").status_code == 200
        assert client.get("/reports?tenant_id=t1").status_code == 200

        policy = {"policy_id": "p1", "tenant_id": "t1"}
        assert client.post("/policies", json=policy).status_code == 200

        saga = {"saga_id": "s1", "task_id": "t1"}
        assert client.post("/sagas", json=saga).status_code == 200


# ---------------------------------------------------------------------------
# audit_service / orchestrator.py
# ---------------------------------------------------------------------------
def test_audit_orchestrator():
    async def run():
        repo = InMemoryAuditRepository()
        orchestrator = AuditOrchestrator(repo)

        event = AuditEvent(
            event_id="eo1",
            action="login",
            resource="user",
            user_id="u1",
            tenant_id="t1",
            severity=AuditEventSeverity.LOW,
        )
        result = await orchestrator.record_event(event)
        assert result["event_id"] == "eo1"

        log = OperationLog(
            log_id="l1",
            event_id="eo1",
            action="login",
            actor="admin",
        )
        recorded = await orchestrator.record_operation_log(log)
        assert recorded.log_id == "l1"

        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)
        report = await orchestrator.generate_report(
            "soc2", "t1", start, end
        )
        assert isinstance(report, AuditReport)

        policy = await orchestrator.apply_retention("t1", ttl_days=30)
        assert policy.ttl_days == 30

        saga = SagaTransaction(saga_id="s1", task_id="t1")
        completed = await orchestrator.run_saga(saga)
        assert completed.status == "success"

    asyncio.run(run())


# ---------------------------------------------------------------------------
# repair_service / grpc / server.py
# ---------------------------------------------------------------------------
async def _ping_handler(name: str) -> str:
    return f"pong {name}"


async def _add_handler(a: int, b: int) -> int:
    return a + b


def test_rpc_server():
    server = RPCServer()
    server.register("ping", _ping_handler)
    server.register("add", _add_handler)

    assert server.list_methods() == ["ping", "add"]
    assert asyncio.run(server.call("ping", name="world")) == "pong world"
    assert asyncio.run(server.call("add", a=2, b=3)) == 5

    with pytest.raises(ValueError, match="Unknown RPC method"):
        asyncio.run(server.call("missing"))


# ---------------------------------------------------------------------------
# repair_service / runbook_parser.py
# ---------------------------------------------------------------------------
def test_runbook_parser_basic(tmp_path: Path):
    yaml_text = """
runbook_id: rb1
name: Restart service
platform: linux
risk_level: low
steps:
  - name: check service
    command: systemctl status {service}
    timeout_seconds: 30
"""
    runbook = RunbookParser.from_yaml(yaml_text)
    assert runbook.runbook_id == "rb1"
    assert runbook.steps[0].name == "check service"
    assert runbook.steps[0].timeout_seconds == 30

    rendered = RunbookParser.render_command("echo {msg}", {"msg": "hi"})
    assert rendered == "echo hi"
    assert RunbookParser.render_command("echo {missing}", {}) == "echo {missing}"

    errors = RunbookParser.validate(runbook)
    assert errors == []

    bad = RepairRunbook(
        runbook_id="",
        name="bad",
        platform="linux",
        risk_level="low",
        steps=[RepairStep(name="s1", command="")],
    )
    assert RunbookParser.validate(bad)


def test_runbook_parser_errors():
    with pytest.raises(ValueError, match="must be a mapping"):
        RunbookParser.from_yaml("just a string")

    with pytest.raises(ValueError, match="steps.*must be a list"):
        RunbookParser.from_yaml("runbook_id: r\nsteps: notlist")

    with pytest.raises(ValueError, match="Step 0 must be a mapping"):
        RunbookParser.from_yaml("runbook_id: r\nsteps:\n  - 123")


def test_runbook_parser_file(tmp_path: Path):
    path = tmp_path / "rb.yml"
    path.write_text(
        "runbook_id: rb2\nname: x\nsteps:\n  - name: s\n    command: echo\n",
        encoding="utf-8",
    )
    runbook = RunbookParser.from_file(path)
    assert runbook.runbook_id == "rb2"


def test_runbook_parser_examples(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    examples = tmp_path / "examples"
    examples.mkdir()
    (examples / "demo.yml").write_text(
        "runbook_id: demo\nname: Demo\ndescription: Demo runbook\n"
        "platform: linux\nrisk_level: low\nsteps:\n  - name: step\n    command: echo\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(RunbookParser, "EXAMPLE_DIR", examples)

    assert "demo" in RunbookParser.list_example_runbooks()
    loaded = RunbookParser.load_example("demo")
    assert loaded is not None
    assert loaded.runbook_id == "demo"

    catalog = get_runbook_catalog()
    assert catalog["demo"] == "Demo runbook"
