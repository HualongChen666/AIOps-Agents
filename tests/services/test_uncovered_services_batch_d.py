# -*- coding: utf-8 -*-
"""Batch D coverage tests for assigned service modules."""

import asyncio
import time
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import services.agent_orchestration_service.main_app as agent_main
import services.alert_service.escalator as escalator_module
import services.alert_service.notifier as notifier
import services.audit_service.encryption as audit_encryption
import services.audit_service.grpc.server as audit_grpc_server
import services.audit_service.graphql_api as graphql_api
import services.audit_service.query as audit_query
import services.audit_service.report_generator as report_generator
import services.audit_service.repository as audit_repository
import services.repair_service.audit as repair_audit
import services.repair_service.main as repair_main

from services.alert_service.schemas import Alert, AlertSeverity, EscalationRule
from services.audit_service.schemas import (
    AuditEvent,
    AuditEventSeverity,
    AuditEventStatus,
    AuditReport,
    EncryptedBlob,
    OperationLog,
    RetentionPolicy,
    SagaTransaction,
)
from services.repair_service.schemas import AuditEvent as RepairAuditEvent


@pytest.fixture(autouse=True)
def _reset_message_queue():
    from services.alert_service.mq import message_queue

    message_queue.reset()
    yield


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# services/audit_service/grpc/server.py
# ---------------------------------------------------------------------------
def test_audit_rpc_server():
    server = audit_grpc_server.AuditRPCServer()

    async def async_double(x):
        return x * 2

    def sync_inc(x):
        return x + 1

    server.register("double", async_double)
    server.register("inc", sync_inc)

    assert server.list_methods() == ["double", "inc"]
    assert _run(server.call("double", x=5)) == 10
    assert _run(server.call("inc", x=2)) == 3

    with pytest.raises(ValueError, match="Unknown RPC method"):
        _run(server.call("missing"))


# ---------------------------------------------------------------------------
# services/alert_service/escalator.py
# ---------------------------------------------------------------------------
def test_escalator(monkeypatch):
    monkeypatch.setattr(escalator_module.time, "time", lambda: 100.0)

    chain = escalator_module.EscalationChain(
        levels=["l1", "l2", "l3"], fallback_channels=["a", "b"]
    )
    assert chain.next_level("l1") == "l2"
    assert chain.next_level("l3") is None
    assert chain.next_level("missing") is None

    esc = escalator_module.Escalator(chain=chain, fallback_channels=["email"])
    assert esc.fallback_channels == ["email"]

    rule = EscalationRule(
        name="r1",
        level_threshold=AlertSeverity.HIGH,
        time_threshold_seconds=60,
        escalation_target="l1",
    )
    esc.add_rule(rule)
    assert esc.list_rules() == [rule]

    disabled = EscalationRule(
        name="r_disabled",
        level_threshold=AlertSeverity.INFO,
        time_threshold_seconds=0,
        escalation_target="page",
        enabled=False,
    )
    esc.add_rule(disabled)

    alert = Alert(id="a1", level=AlertSeverity.CRITICAL, title="boom")
    esc.track(alert)
    monkeypatch.setattr(escalator_module.time, "time", lambda: 200.0)

    assert esc.should_escalate(alert) == "l1"
    assert alert.status == "escalated"

    payload = esc.escalate(
        alert,
        context={
            "investigation_summary": "investigating",
            "dashboard_url": "https://dash.io",
        },
    )
    assert payload["escalation_target"] == "l1"
    assert payload["fallback_channels"] == ["email"]
    assert payload["context"]["investigation_summary"] == "investigating"
    assert payload["context"]["links"] == {"dashboard_url": "https://dash.io"}
    assert payload["context"]["next_escalation_level"] == "l2"

    low = Alert(id="a2", level=AlertSeverity.WARNING, title="warn")
    esc.track(low)
    assert esc.should_escalate(low) is None
    assert esc.resolve("a1")
    assert not esc.resolve("a1")

    esc.track(Alert(id="a3", level=AlertSeverity.INFO, title="info"))
    assert esc.clear() == 2
    assert esc.clear() == 0


# ---------------------------------------------------------------------------
# services/audit_service/graphql_api.py
# ---------------------------------------------------------------------------
def test_audit_graphql():
    repo = audit_repository.InMemoryAuditRepository()

    async def seed():
        await repo.save_event(
            AuditEvent(
                event_id="e1",
                action="login",
                resource="db",
                user_id="u1",
                tenant_id="t1",
                severity=AuditEventSeverity.HIGH,
            )
        )
        await repo.save_event(
            AuditEvent(
                event_id="e2",
                action="logout",
                resource="db",
                user_id="u2",
                tenant_id="t1",
                severity=AuditEventSeverity.LOW,
            )
        )

    _run(seed())
    gql = graphql_api.AuditGraphQL(repo)

    async def run():
        result = await gql.query(["event_id", "action"], tenant_id="t1", limit=10)
        assert result["total"] == 2
        assert list(result["data"][0].keys()) == ["event_id", "action"]

        full = await gql.query([], tenant_id="t1")
        assert "event_id" in full["data"][0]

    _run(run())
    selected = graphql_api.AuditGraphQL._select(
        AuditEvent(
            event_id="e3",
            action="x",
            resource="r",
            user_id="u",
            severity=AuditEventSeverity.CRITICAL,
        ),
        ["severity"],
    )
    assert selected == {"severity": AuditEventSeverity.CRITICAL}


# ---------------------------------------------------------------------------
# services/agent_orchestration_service/main_app.py
# ---------------------------------------------------------------------------
class _FakeOrchestrator:
    async def get_stats(self):
        return {
            "service": "agent",
            "request_counts": {},
            "retry_policies": ["exponential"],
            "cache_size": 0,
        }

    def list_methods(self):
        return [
            "decompose_task",
            "run_agent",
            "coordinate",
            "collaborate",
            "aggregate",
            "handle_error",
            "get_stats",
            "cause_error",
        ]

    async def decompose_task(self, request):
        return {
            "task": request.task,
            "subtasks": [
                {
                    "task_id": "t1",
                    "description": "Collect and observe relevant metrics.",
                    "agent_type": "monitor",
                    "input_data": {},
                    "dependencies": [],
                }
            ],
            "plan_id": "p1",
        }

    async def run_agent(self, request):
        return {
            "agent_type": request.agent_type.value,
            "result": {
                "agent_type": request.agent_type.value,
                "output": "ok",
                "confidence": 0.5,
            },
            "latency_ms": 1.0,
        }

    async def coordinate(self, request):
        return {
            "plan_id": request.plan_id or "p1",
            "results": [],
            "completed": [],
            "failed": [],
            "latency_ms": 0.0,
        }

    async def collaborate(self, request):
        return {
            "task": request.task,
            "results": [],
            "aggregated_output": "agg",
            "plan_id": "p1",
            "latency_ms": 0.0,
        }

    async def aggregate(self, request=None, **kwargs):
        results = getattr(request, "results", kwargs.get("results", []))
        strategy = getattr(request, "strategy", kwargs.get("strategy", "concat"))
        return {
            "aggregated_output": "out",
            "result_count": len(results),
            "strategy": strategy,
        }

    async def handle_error(self, request):
        return {
            "recovered": True,
            "strategy": "retry",
            "next_steps": ["retry"],
            "message": "ok",
        }

    async def cause_error(self):
        raise RuntimeError("boom")


def test_agent_orchestration_endpoints(monkeypatch):
    monkeypatch.setattr(agent_main, "get_orchestrator", _FakeOrchestrator)

    with TestClient(agent_main.app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/metrics").status_code == 200
        assert client.get("/stats").status_code == 200
        assert client.get("/agents").status_code == 200

        assert (
            client.post("/decompose", json={"task": "monitor and report"}).status_code
            == 200
        )
        assert (
            client.post(
                "/run/monitor",
                json={"agent_type": "monitor", "input_data": {"task": "x"}},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/coordinate",
                json={
                    "subtasks": [
                        {"task_id": "t1", "description": "d", "agent_type": "monitor"}
                    ]
                },
            ).status_code
            == 200
        )
        assert (
            client.post("/collaborate", json={"task": "fix"}).status_code == 200
        )
        assert (
            client.post(
                "/aggregate",
                json={
                    "results": [
                        {
                            "agent_type": "monitor",
                            "output": "o",
                            "confidence": 0.5,
                        }
                    ],
                    "strategy": "concat",
                },
            ).status_code
            == 200
        )
        assert (
            client.post("/handle-error", json={"error": "timeout"}).status_code
            == 200
        )

        assert client.post("/rpc/list_methods").status_code == 200
        assert client.post("/rpc/stats").status_code == 200
        assert (
            client.post("/rpc/decompose_task", json={"task": "monitor"}).status_code
            == 200
        )
        assert (
            client.post(
                "/rpc/run_agent",
                json={"agent_type": "monitor", "input_data": {}},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/rpc/aggregate",
                json={
                    "results": [
                        {
                            "agent_type": "monitor",
                            "output": "o",
                            "confidence": 0.5,
                        }
                    ],
                    "strategy": "concat",
                },
            ).status_code
            == 200
        )
        assert client.post("/rpc/unknown").status_code == 404
        assert client.post("/rpc/cause_error").status_code == 500


def test_agent_orchestration_error(monkeypatch):
    class BadOrchestrator:
        async def decompose_task(self, request):
            raise RuntimeError("fail")

    monkeypatch.setattr(agent_main, "get_orchestrator", lambda: BadOrchestrator())

    with TestClient(agent_main.app) as client:
        r = client.post("/decompose", json={"task": "x"})
        assert r.status_code == 500


# ---------------------------------------------------------------------------
# services/audit_service/query.py
# ---------------------------------------------------------------------------
def test_audit_query():
    repo = audit_repository.InMemoryAuditRepository()

    async def seed():
        await repo.save_event(
            AuditEvent(
                event_id="e1",
                action="login",
                resource="r",
                user_id="u1",
                tenant_id="t1",
                severity=AuditEventSeverity.HIGH,
            )
        )
        await repo.save_event(
            AuditEvent(
                event_id="e2",
                action="login",
                resource="r",
                user_id="u2",
                tenant_id="t1",
                severity=AuditEventSeverity.LOW,
            )
        )
        await repo.save_event(
            AuditEvent(
                event_id="e3",
                action="logout",
                resource="r",
                user_id="u3",
                tenant_id="t2",
                severity=AuditEventSeverity.HIGH,
            )
        )

    _run(seed())
    q = audit_query.AuditQuery(repo)

    async def run():
        assert len(await q.search(tenant_id="t1", action="login")) == 2
        assert (
            len(await q.search(tenant_id="t1", severity=AuditEventSeverity.HIGH.value))
            == 1
        )
        assert len(await q.search(tenant_id="t2")) == 1
        analysis = await q.analyze("t1")
        assert analysis["total"] == 2
        assert analysis["by_action"]["login"] == 2
        assert analysis["by_severity"][AuditEventSeverity.LOW] == 1

    _run(run())


# ---------------------------------------------------------------------------
# services/audit_service/report_generator.py
# ---------------------------------------------------------------------------
def test_audit_report_generator():
    repo = audit_repository.InMemoryAuditRepository()
    now = datetime.utcnow()
    e1 = AuditEvent(
        event_id="e1",
        action="a",
        resource="r",
        user_id="u1",
        tenant_id="t1",
        severity=AuditEventSeverity.LOW,
        timestamp=now - timedelta(hours=2),
    )
    e2 = AuditEvent(
        event_id="e2",
        action="a",
        resource="r",
        user_id="u2",
        tenant_id="t1",
        severity=AuditEventSeverity.HIGH,
        timestamp=now,
    )
    repo._events = {"e1": e1, "e2": e2}
    rg = report_generator.ReportGenerator(repo)

    async def run():
        r = await rg.generate(
            "soc2",
            "t1",
            now - timedelta(hours=1),
            now + timedelta(hours=1),
        )
        assert r.report_type == "soc2"
        assert "t1" in r.content
        assert r.tenant_id == "t1"

        r2 = await rg.generate(
            "gdpr",
            "t1",
            now - timedelta(hours=3),
            now + timedelta(hours=3),
        )
        assert "GDPR" in r2.content

        r3 = await rg.generate(
            "unknown",
            "t1",
            now - timedelta(hours=1),
            now + timedelta(hours=1),
        )
        assert r3.content

    _run(run())


# ---------------------------------------------------------------------------
# services/audit_service/repository.py
# ---------------------------------------------------------------------------
def test_audit_repository():
    repo = audit_repository.InMemoryAuditRepository()
    e1 = AuditEvent(
        event_id="e1",
        action="a",
        resource="r",
        user_id="u1",
        tenant_id="t1",
    )
    e2 = AuditEvent(
        event_id="e2",
        action="b",
        resource="r",
        user_id="u2",
        tenant_id="t2",
    )
    now = datetime.utcnow()
    report = AuditReport(
        report_id="r1",
        report_type="soc2",
        tenant_id="t1",
        start_time=now,
        end_time=now,
        content="content",
    )
    blob = EncryptedBlob(blob_id="b1", ciphertext="c", nonce="n", tag="t")
    policy = RetentionPolicy(policy_id="p1", tenant_id="t1", ttl_days=30)
    saga = SagaTransaction(saga_id="s1", task_id="task1")
    log = OperationLog(log_id="l1", event_id="e1", action="a", actor="u")

    async def run():
        assert await repo.save_event(e1) == "e1"
        assert e1.status == AuditEventStatus.RECORDED
        await repo.save_event(e2)

        assert await repo.get_event("e1") is e1
        assert await repo.get_event("missing") is None
        assert len(await repo.list_events(tenant_id="t1")) == 1
        assert len(await repo.list_events(limit=1)) == 1

        assert await repo.save_log(log) == "l1"
        assert await repo.list_logs("e1") == [log]

        assert await repo.save_report(report) == "r1"
        assert await repo.list_reports("t1") == [report]

        assert await repo.save_blob(blob) == "b1"
        assert await repo.get_blob("b1") is blob

        assert await repo.save_policy(policy) == "p1"
        assert await repo.get_policy("t1") is policy

        assert await repo.save_saga(saga) == "s1"
        assert await repo.get_saga("s1") is saga

        r2 = await audit_repository.get_repository()
        assert isinstance(r2, audit_repository.InMemoryAuditRepository)

    _run(run())


# ---------------------------------------------------------------------------
# services/alert_service/notifier.py
# ---------------------------------------------------------------------------
class FakeAsyncClient:
    def __init__(self, is_success=True, exc=None):
        self.is_success = is_success
        self.exc = exc

    async def post(self, *args, **kwargs):
        if self.exc:
            raise self.exc
        return SimpleNamespace(is_success=self.is_success, status_code=200)

    async def aclose(self):
        pass


def _set_notifier_service(service):
    notifier.app.state.service = service
    notifier.app.state.start_time = time.time()


def test_notifier_endpoints(monkeypatch):
    client = TestClient(notifier.app)

    _set_notifier_service(
        notifier.NotificationService(
            webhook_url="http://webhook", client=FakeAsyncClient(is_success=True)
        )
    )
    assert client.get("/health").status_code == 200
    assert client.get("/metrics").status_code == 200

    r = client.post(
        "/notify",
        json={"id": "a1", "title": "boom", "level": "critical"},
    )
    assert r.status_code == 200
    assert r.json()["success"] is True

    _set_notifier_service(notifier.NotificationService(webhook_url=""))
    r = client.post("/notify", json={"id": "a2", "title": "info", "level": "info"})
    assert r.json()["channel"] == "none"

    _set_notifier_service(
        notifier.NotificationService(
            webhook_url="http://webhook", client=FakeAsyncClient(exc=Exception("net"))
        )
    )
    r = client.post(
        "/notify",
        json={"id": "a3", "title": "fail", "level": "critical"},
    )
    assert r.json()["success"] is False

    r = client.get("/history?limit=10")
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    client.close()


def test_notifier_consume_loop():
    service = notifier.NotificationService(webhook_url="", client=FakeAsyncClient())
    service.notify = AsyncMock()

    async def run():
        shutdown = asyncio.Event()
        task = asyncio.create_task(service.consume_loop(shutdown))
        await notifier.message_queue.publish(
            "alerts.routed",
            {
                "type": "routed_alert",
                "alert": {
                    "id": "a1",
                    "title": "boom",
                    "level": "critical",
                },
            },
        )
        await notifier.message_queue.publish(
            "alerts.routed",
            {
                "type": "routed_alert",
                "alert": {"bad": "data"},
            },
        )
        await asyncio.sleep(0.3)
        shutdown.set()
        await task

    _run(run())
    assert service.notify.called


def test_notifier_lifespan(monkeypatch):
    class FakeService:
        def __init__(self, **kwargs):
            self.client = SimpleNamespace(aclose=AsyncMock())

        async def consume_loop(self, shutdown):
            pass

    monkeypatch.setattr(notifier, "NotificationService", FakeService)

    async def run():
        async with notifier.lifespan(notifier.app):
            assert isinstance(notifier.app.state.service, FakeService)
            assert hasattr(notifier.app.state.shutdown, "is_set")

    _run(run())


# ---------------------------------------------------------------------------
# services/repair_service/audit.py
# ---------------------------------------------------------------------------
def test_repair_audit_store(monkeypatch):
    monkeypatch.setattr(repair_audit, "REPAIR_AUDIT_EVENTS", MagicMock())
    store = repair_audit.AuditStore()

    async def run():
        e1 = await store.record("t1", "start", actor="user", payload={"x": 1})
        e2 = await store.record("t1", "end", actor="system")
        await store.record("t2", "start")

        assert len(await store.get_events("t1")) == 2
        assert e1 in await store.get_events("t1")

        all_events = await store.query(limit=10)
        assert len(all_events) >= 2

        start_events = await store.query(event_type="start", limit=10)
        assert all(e.event_type == "start" for e in start_events)

        analysis = await store.analyze("t1")
        assert analysis["task_id"] == "t1"
        assert analysis["total_events"] == 2
        assert "start" in analysis["event_types"]
        assert analysis["first_event"] is not None
        assert analysis["last_event"] is not None

        await store.snapshot("t1", {"state": "ok"})
        assert any(e.event_type == "snapshot" for e in await store.get_events("t1"))

    _run(run())


# ---------------------------------------------------------------------------
# services/audit_service/encryption.py
# ---------------------------------------------------------------------------
def test_audit_encryption():
    engine = audit_encryption.AESEncryption("secret-key-32")
    enc = engine.encrypt("hello world")
    assert "ciphertext" in enc
    assert enc["nonce"]
    assert enc["tag"]
    assert engine.decrypt(enc["ciphertext"]) == "hello world"

    audit = audit_encryption.AuditEncryption("another-key")
    blob = audit.encrypt_event("e1", "secret message")
    assert blob.blob_id == "e1"
    assert blob.ciphertext
    assert audit.decrypt_blob(blob) == "secret message"


# ---------------------------------------------------------------------------
# services/repair_service/main.py
# ---------------------------------------------------------------------------
class FakeHealState:
    def __init__(self, alert):
        self.alert = alert
        self.fix_applied = False
        self.error = None
        self.runbook = None
        self.analysis = None


async def fake_approve(alert_id, approver):
    return {"success": True}


def test_repair_main(monkeypatch):
    monkeypatch.setattr(repair_main, "repairs", {})
    monkeypatch.setattr(repair_main, "HealState", FakeHealState)
    monkeypatch.setattr(repair_main, "core_approve_repair", fake_approve)

    async def fake_run_success(state):
        state.fix_applied = True
        state.error = None
        state.runbook = "fixed"
        return state

    monkeypatch.setattr(repair_main, "run_heal", fake_run_success)

    with TestClient(repair_main.app) as client:
        assert client.get("/health").json()["status"] == "healthy"

        r = client.post("/repairs", json={"alert_id": "A1", "host": "h1"})
        assert r.status_code == 200
        task_id = r.json()["task_id"]

        r = client.post(f"/repairs/{task_id}/approve")
        assert r.status_code == 200
        assert r.json()["success"] is True
        assert r.json()["status"] == "completed"

        r = client.post("/repairs/missing/approve")
        assert r.status_code == 404

    async def fake_run_fail(state):
        state.fix_applied = False
        state.error = "boom"
        return state

    monkeypatch.setattr(repair_main, "run_heal", fake_run_fail)
    monkeypatch.setattr(repair_main, "repairs", {})

    with TestClient(repair_main.app) as client:
        r = client.post("/repairs", json={"alert_id": "A2"})
        task_id = r.json()["task_id"]
        r = client.post(f"/repairs/{task_id}/approve")
        assert r.status_code == 200
        assert r.json()["success"] is False
        assert r.json()["status"] == "failed"
