# -*- coding: utf-8 -*-
"""Batch C tests for assigned service modules."""

from __future__ import annotations

import time  # noqa: F401  # Imported for test setup
from typing import Any, Dict, List, Optional  # noqa: F401  # Imported for test setup
from unittest.mock import AsyncMock

import httpx
import pytest  # noqa: F401  # Imported for test setup
from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.agent_orchestration_service.grpc.client import AgentRPCClient
from services.agent_orchestration_service.grpc.server import AgentRPCServer
from services.audit_service.analyzer import AuditAnalyzer
from services.audit_service.event_store import EventStore
from services.audit_service.grpc.client import AuditRPCClient
from services.audit_service.grpc.server import AuditRPCServer
from services.audit_service.repository import InMemoryAuditRepository
from services.audit_service.schemas import (
    AuditEvent,
    AuditEventSeverity,
    AuditEventStatus,
)
from services.repair_service.grpc.client import RPCClient as RepairRPCClient
from services.repair_service.grpc.server import RPCServer as RepairRPCServer
from services.repair_service.health_check import HealthCheckEngine
from services.repair_service.repository import InMemoryRepairRepository
from services.repair_service.schemas import (
    PlatformType,
    RepairExecutionResult,
    RepairRequest,
    RepairStatus,
    RepairStrategy,
    RepairTask,
    RiskLevel,
    VerificationResult,
)
from services.repair_service.strategy_manager import RepairStrategyManager
from services.repair_service.verifier import RepairVerifier

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def alert_client():
    """Provide a test client for the alert collector with reset state."""
    from services.alert_service.collector import app as _alert_app
    from services.alert_service.mq import message_queue
    from services.alert_service.repository import InMemoryAlertRepository

    message_queue.reset()
    with TestClient(_alert_app) as client:
        _alert_app.state.repo = InMemoryAlertRepository()
        _alert_app.state.mq = message_queue
        _alert_app.state.rate_limiter.max_rate = 100_000
        yield client


@pytest.fixture
def verifier_client(monkeypatch):
    """Provide a test client for the repair verifier with fake health checks."""
    from services.repair_service import verifier as _verifier
    from services.repair_service.verifier import RepairVerifierApp

    class FakeHealth:
        async def check_service_status(self, *args, **kwargs):
            return {"success": True, "stdout": "active"}

        async def check_process_exists(self, *args, **kwargs):
            return {"success": False}

        async def check_metric_threshold(self, *args, **kwargs):
            return {"success": True, "stdout": "dropped"}

    monkeypatch.setattr(_verifier, "HealthCheckEngine", lambda timeout: FakeHealth())
    with TestClient(_verifier.app) as client:
        assert isinstance(_verifier.verifier_app, RepairVerifierApp)
        yield client


@pytest.fixture
def fake_httpx_client(monkeypatch):
    """Patch httpx.AsyncClient to return deterministic fake responses."""

    class FakeResponse:
        def __init__(self, data: Dict[str, Any]):
            self.data = data

        def raise_for_status(self):
            return self

        def json(self):
            return self.data

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass

        async def post(self, *args, **kwargs):
            return FakeResponse({"ok": True})

        async def aclose(self):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

    monkeypatch.setattr(httpx, "AsyncClient", FakeAsyncClient)
    yield FakeAsyncClient


# ---------------------------------------------------------------------------
# gRPC-like clients / servers
# ---------------------------------------------------------------------------


async def test_audit_rpc_client_with_server():
    server = AuditRPCServer()

    async def greet(name: str):
        return f"hello {name}"

    server.register("greet", greet)
    client = AuditRPCClient(server=server)
    assert await client.call("greet", name="world") == "hello world"

    with pytest.raises(ValueError, match="Unknown RPC method"):
        await server.call("missing")


async def test_repair_rpc_client_with_server():
    server = RepairRPCServer()

    async def async_echo(value: int):
        return value

    server.register("echo", async_echo)
    client = RepairRPCClient(server=server)
    assert await client.call("echo", value=42) == 42

    with pytest.raises(ValueError, match="Unknown RPC method"):
        await server.call("missing")


async def test_audit_rpc_client_http(fake_httpx_client):
    client = AuditRPCClient(base_url="http://audit-test")
    try:
        assert await client.call("ping") == {"ok": True}
    finally:
        await client.close()


async def test_repair_rpc_client_http(fake_httpx_client):
    client = RepairRPCClient(base_url="http://repair-test")
    try:
        assert await client.call("ping") == {"ok": True}
    finally:
        await client.close()


async def test_rpc_client_without_transport():
    audit = AuditRPCClient()
    with pytest.raises(RuntimeError, match="requires a server instance or base_url"):
        await audit.call("x")

    repair = RepairRPCClient()
    with pytest.raises(RuntimeError, match="requires a server instance or base_url"):
        await repair.call("x")


async def test_agent_orchestration_rpc_client(fake_httpx_client):
    client = AgentRPCClient(base_url="http://agent-test")
    assert await client.call("doit") == {"ok": True}
    assert await client.call("doit", payload={"x": 1}) == {"ok": True}


async def test_agent_orchestration_rpc_server():
    server = AgentRPCServer()

    async def async_mult(x: int, y: int):
        return x * y

    def sync_add(x: int, y: int):
        return x + y

    server.register("mult", async_mult)
    server.register("add", sync_add)
    assert server.list_methods() == ["mult", "add"]
    assert await server.call("mult", x=2, y=3) == 6
    assert await server.call("add", x=1, y=2) == 3

    with pytest.raises(ValueError, match="Unknown RPC method"):
        await server.call("missing")


# ---------------------------------------------------------------------------
# Audit analyzer / event store
# ---------------------------------------------------------------------------


async def test_audit_analyzer():
    repo = InMemoryAuditRepository()
    for i, severity in enumerate(
        [AuditEventSeverity.HIGH, AuditEventSeverity.CRITICAL, AuditEventSeverity.LOW]
    ):
        await repo.save_event(
            AuditEvent(
                event_id=f"e{i}",
                action="read" if i == 0 else "write",
                resource="r",
                user_id="u",
                tenant_id="t1",
                severity=severity,
                status=AuditEventStatus.RECORDED,
            )
        )

    analyzer = AuditAnalyzer(repo)
    analysis = await analyzer.analyze("t1")
    assert analysis["tenant_id"] == "t1"
    assert analysis["total"] == 3
    assert analysis["high_severity_count"] == 2
    assert "top_actions" in analysis
    assert "severity_distribution" in analysis

    alerts = await analyzer.detect_anomalies("t1")
    assert any(a["type"] == "high_severity_events" for a in alerts)

    analysis2 = await analyzer.analyze("missing")
    assert analysis2["total"] == 0
    assert await analyzer.detect_anomalies("missing") == []


async def test_audit_event_store():
    repo = InMemoryAuditRepository()
    store = EventStore(repo)
    event = AuditEvent(
        event_id="evt-1",
        action="login",
        resource="api",
        user_id="u1",
        tenant_id="tenant-a",
        severity=AuditEventSeverity.MEDIUM,
    )
    assert await store.append(event) == "evt-1"
    stream = await store.get_stream("tenant-a")
    assert len(stream) == 1
    projection = await store.project("tenant-a")
    assert projection["tenant_id"] == "tenant-a"
    assert projection["total"] == 1
    assert projection["by_action"]["login"] == 1
    assert projection["by_severity"]["medium"] == 1


# ---------------------------------------------------------------------------
# Alert collector
# ---------------------------------------------------------------------------


def test_alert_collector_health_and_metrics(alert_client):
    resp = alert_client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "alert-collector"

    resp = alert_client.get("/metrics")
    assert resp.status_code == 200


def test_alert_collector_receive_prometheus_alerts(alert_client):
    payload = {
        "version": "4",
        "alerts": [
            {
                "labels": {
                    "alertname": "HighCPU",
                    "instance": "host-1",
                    "severity": "critical",
                    "priority": "P0",
                },
                "annotations": {"summary": "CPU high", "description": "desc"},
                "startsAt": "2024-01-01T00:00:00Z",
            }
        ],
    }
    resp = alert_client.post("/alerts", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["received"] == 1
    assert data["saved"] == 1

    resp = alert_client.get("/alerts")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_alert_collector_generic_sources(alert_client):
    grafana = {
        "title": "disk full",
        "message": "critical disk usage",
        "state": "alerting",
        "evalMatches": [{"metric": "disk_used", "value": 95, "tags": {"host": "host-1"}}],
    }
    resp = alert_client.post("/alerts/grafana", json=grafana)
    assert resp.status_code == 200
    assert resp.json()["saved"] == 1

    zabbix = {
        "hostname": "host-1",
        "alert_name": "memory",
        "message": "high memory",
        "status": "PROBLEM",
        "value": 88,
        "item": "mem",
    }
    resp = alert_client.post("/alerts/zabbix", json=zabbix)
    assert resp.status_code == 200
    assert resp.json()["saved"] == 1

    generic = {"id": "gen-1", "title": "generic alert", "description": "warning"}
    resp = alert_client.post("/alerts/custom", json=generic)
    assert resp.status_code == 200
    assert resp.json()["saved"] == 1


def test_alert_collector_rate_limit_and_errors(alert_client, monkeypatch):
    from services.alert_service import collector as _collector
    from services.alert_service.repository import InMemoryAlertRepository

    # Rate limit exceeded.
    _collector.app.state.rate_limiter.max_rate = 0
    resp = alert_client.post(
        "/alerts",
        json={
            "alerts": [
                {
                    "labels": {"alertname": "x", "severity": "warning"},
                    "annotations": {"summary": "s"},
                }
            ]
        },
    )
    assert resp.status_code == 429
    _collector.app.state.rate_limiter.max_rate = 100_000

    # Generic source validation error (invalid Alert payload).
    resp = alert_client.post("/alerts/generic", json={"id": "bad"})
    assert resp.status_code == 422

    # Processing error during save.
    _collector.app.state.repo = InMemoryAlertRepository()

    async def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(_collector.app.state.repo, "save", boom)
    resp = alert_client.post(
        "/alerts/prometheus",
        json={"id": "bad-1", "title": "x", "message": "y"},
    )
    assert resp.status_code == 500


async def test_alert_collector_private_helpers():
    from services.alert_service.collector import (
        _alert_priority,
        _extract_severity,
        _normalize_alert,
        _parse_prometheus_alert,
        _severity_from_label,
        _SlidingWindowRateLimiter,
    )
    from services.alert_service.schemas import Alert, AlertSeverity, AlertStatus, PrometheusAlert

    assert _severity_from_label("CRITICAL") == AlertSeverity.CRITICAL
    assert _severity_from_label("fatal") == AlertSeverity.FATAL
    assert _severity_from_label("unknown") == AlertSeverity.WARNING

    assert _extract_severity("Something critical happened") == "critical"
    assert _extract_severity("") is None
    assert _extract_severity("nothing") is None

    prom = PrometheusAlert(
        labels={
            "alertname": "Test",
            "instance": "i1",
            "severity": "high",
            "value": "not-a-number",
        },
        annotations={"summary": "s"},
    )
    alert = _parse_prometheus_alert(prom)
    assert alert.alert_type == "Test"
    assert alert.value is None

    alert_resolved = Alert(
        id="a",
        title="t",
        level=AlertSeverity.CRITICAL,
        status=AlertStatus.RESOLVED,
        priority="P0",
    )
    assert _alert_priority(alert_resolved) == -1000

    alert_pending = Alert(  # noqa: F841  # Variable for test verification
        id="a",
        title="t",
        level=AlertSeverity.CRITICAL,
        status=AlertStatus.PENDING,
        priority="P0",
    )
    assert _alert_priority(alert_pending) < 0

    generic = _normalize_alert("generic", {"id": "g1", "title": "t"})
    assert generic.id == "g1"

    list_generic = _normalize_alert("generic", [{"id": "g2", "title": "list"}])
    assert list_generic.id == "g2"

    with pytest.raises(ValueError, match="must be a JSON object"):
        _normalize_alert("generic", "bad")

    # Rate limiter direct usage.
    limiter = _SlidingWindowRateLimiter(max_rate=2)
    assert await limiter.acquire() is True
    assert await limiter.acquire() is True
    assert await limiter.acquire() is False


# ---------------------------------------------------------------------------
# Pattern engine
# ---------------------------------------------------------------------------


def test_pattern_engine():
    import services.alert_service.pattern_engine as pe
    from services.alert_service.schemas import Alert, AlertSeverity

    # No sklearn / small sample rule-based path.
    engine = pe.PatternEngine(min_samples=5)
    a1 = Alert(
        id="1",
        title="cpu high",
        description="cpu critical",
        level=AlertSeverity.CRITICAL,
        category="system",
        alert_type="cpu",
        host="h1",
        metric="cpu",
    )
    engine.train([a1])
    prediction = engine.predict(a1)
    assert prediction == engine._signature(a1)
    assert "unknown" not in prediction

    # Unknown alert.
    unknown = Alert(
        id="2",
        title="new",
        description="new",
        level=AlertSeverity.WARNING,
        category="x",
        alert_type="y",
        host="z",
        metric="m",
    )
    assert engine.predict(unknown) == "unknown"

    patterns = engine.get_patterns()
    assert engine._signature(a1) in patterns


def test_pattern_engine_ml_path(monkeypatch):
    import services.alert_service.pattern_engine as pe
    from services.alert_service.schemas import Alert, AlertSeverity

    class FakeKMeans:
        def __init__(self, n_clusters, random_state):
            self.n_clusters = n_clusters

        def fit(self, X):
            pass

        def predict(self, X):
            return [7]

    class FakeVec:
        def __init__(self, max_features=100):
            pass

        def fit_transform(self, texts):
            return "vectors"

        def transform(self, texts):
            return "vec"

    monkeypatch.setattr(pe, "SKLEARN_AVAILABLE", True, raising=False)
    monkeypatch.setattr(pe, "TfidfVectorizer", FakeVec, raising=False)
    monkeypatch.setattr(pe, "MiniBatchKMeans", FakeKMeans, raising=False)

    engine = pe.PatternEngine(min_samples=1, n_clusters=2)
    a = Alert(
        id="3",
        title="disk full",
        description="disk full on host",
        level=AlertSeverity.HIGH,
        category="infra",
        alert_type="disk",
        host="h2",
        metric="disk",
    )
    engine.train([a, a, a])
    assert engine.predict(a) == "ml-cluster-7"

    # ML predict failure falls back to signature.
    engine._model = type(
        "Bad", (), {"predict": lambda self, X: (_ for _ in ()).throw(RuntimeError("boom"))}
    )()
    assert engine.predict(a) == engine._signature(a)


# ---------------------------------------------------------------------------
# Repair verifier
# ---------------------------------------------------------------------------


def test_repair_verifier_endpoints(verifier_client):
    resp = verifier_client.get("/health")
    assert resp.status_code == 200

    resp = verifier_client.get("/metrics")
    assert resp.status_code == 200

    task = {
        "task_id": "t1",
        "alert_id": "a1",
        "host": "h1",
        "platform": "linux",
        "strategy": {
            "name": "s1",
            "script_key": "service_restart",
            "conditions": {},
            "platform": "linux",
            "risk_level": "medium",
        },
        "result": {"service_name": "redis"},
    }
    result = {"task_id": "t1", "success": True}  # noqa: F841  # Variable for test verification
    resp = verifier_client.post("/verify", json={"task": task, "result": result})
    assert resp.status_code == 200
    data = resp.json()
    assert data["task_id"] == "t1"

    resp = verifier_client.post("/rollback", json={"task": task, "result": result})
    assert resp.status_code == 200
    assert resp.json()["success"] is True

    resp = verifier_client.post("/audit?task_id=t1&event_type=test")
    assert resp.status_code == 200

    resp = verifier_client.get("/audit/t1")
    assert resp.status_code == 200
    assert resp.json()["events"][0]["event_type"] == "test"

    resp = verifier_client.get("/audit/analyze/t1")
    assert resp.status_code == 200
    assert resp.json()["task_id"] == "t1"


async def test_repair_verifier_strategies(monkeypatch):
    from services.repair_service import verifier as _verifier

    class FakeHealth:
        async def check_service_status(self, service, platform):
            return {"success": True}

        async def check_process_exists(self, pid, platform):
            return {"success": True}

        async def check_metric_threshold(self, metric, before, after):
            return {"success": False}

    monkeypatch.setattr(_verifier, "HealthCheckEngine", lambda timeout: FakeHealth())
    verifier = RepairVerifier(timeout=1)

    base_task = RepairTask(
        task_id="t1",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
    )
    cases = [
        ("service_restart", "service_status", {"service_name": "redis"}),
        ("cpu_kill", "process_check", {"pid": 42}),
        ("check_metric", "metric_threshold", {"before": 100.0, "after": 80.0}),
        ("flush_dns", "dns_resolution", {}),
        ("network_check", "port_connectivity", {}),
        ("log_file", "file_exists", {}),
        ("check_log", "log_pattern", {}),
        ("check_http", "http_endpoint", {}),
        ("noop", "noop", {}),
    ]
    for script_key, expected_strategy, result in cases:
        task = base_task.model_copy(
            update={
                "strategy": RepairStrategy(
                    name="s",
                    script_key=script_key,
                    conditions={},
                    platform=PlatformType.LINUX,
                    risk_level=RiskLevel.LOW,
                ),
                "result": result,
            }
        )
        outcome = await verifier.verify(task)
        assert outcome.task_id == "t1"
        assert outcome.strategy == expected_strategy
        assert outcome.verified is not False or expected_strategy == "metric_threshold"

    # No strategy defaults to noop.
    task_none = base_task.model_copy(update={"strategy": None})
    outcome = await verifier.verify(task_none)
    assert outcome.strategy == "noop"

    # Direct custom command method.
    custom = await verifier._verify_custom_command(base_task, None)
    assert custom["verified"] is None

    assert "service_status" in verifier.list_strategies()

    # Exception handling path.
    async def fail(*args, **kwargs):
        raise RuntimeError("fail")

    verifier.health.check_service_status = fail
    task = base_task.model_copy(
        update={
            "strategy": RepairStrategy(
                name="s",
                script_key="service_restart",
                conditions={},
                platform=PlatformType.LINUX,
                risk_level=RiskLevel.LOW,
            )
        }
    )
    outcome = await verifier.verify(task)
    assert outcome.verified is False
    assert outcome.evidence == {"error": "fail"}


# ---------------------------------------------------------------------------
# Repair repository / strategy manager
# ---------------------------------------------------------------------------


async def test_repair_repository():
    repo = InMemoryRepairRepository()
    t1 = RepairTask(
        task_id="",
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        status=RepairStatus.PENDING,
    )
    task_id = await repo.save(t1)
    assert task_id
    assert (await repo.get(task_id)) is t1

    t2 = RepairTask(
        task_id="t2",
        alert_id="a2",
        host="h2",
        platform=PlatformType.WINDOWS,
        status=RepairStatus.SUCCEEDED,
    )
    await repo.save(t2)

    assert await repo.count() == 2
    pending = await repo.list(status=RepairStatus.PENDING)  # noqa: F841  # Variable for test verification
    assert len(pending) == 1

    ok = await repo.update("t2", {"status": RepairStatus.COMPLETED})
    assert ok is True
    assert (await repo.get("t2")).status == RepairStatus.COMPLETED
    assert await repo.update("missing", {}) is False

    assert await repo.delete("t2") is True
    assert await repo.delete("missing") is False
    assert await repo.count() == 1

    from services.repair_service.repository import get_repository

    assert isinstance(await get_repository(), InMemoryRepairRepository)


def test_repair_strategy_manager():
    mgr = RepairStrategyManager()
    strategies = mgr.list_strategies()
    assert len(strategies) >= 20

    req = RepairRequest(
        alert_id="a1",
        host="h1",
        platform=PlatformType.LINUX,
        metric="cpu_percent",
    )
    matched = mgr.match(req)
    assert matched is not None
    assert matched.name == "cpu_high_linux"

    wildcard = RepairRequest(
        alert_id="a2",
        host="h1",
        platform=PlatformType.LINUX,
        metric="web_service_down",
    )
    matched_wild = mgr.match(wildcard)
    assert matched_wild is not None

    no_match = RepairRequest(
        alert_id="a3",
        host="h1",
        platform=PlatformType.MACOS,
        metric="totally_unknown_metric",
    )
    assert mgr.match(no_match) is None

    new_strategy = RepairStrategy(
        name="custom",
        conditions={"metric": "custom_metric", "platform": "linux"},
        script_key="noop",
        platform=PlatformType.LINUX,
        risk_level=RiskLevel.LOW,
        priority=100,
    )
    mgr.add_strategy(new_strategy)
    assert mgr.get_strategy("custom") == new_strategy

    task = mgr.create_task_from_request(req, "TASK-1")
    assert task.task_id == "TASK-1"
    assert task.strategy == mgr.match(req)


# ---------------------------------------------------------------------------
# Health check engine (used by verifier, kept fast via monkeypatch)
# ---------------------------------------------------------------------------


async def test_health_check_engine(monkeypatch):
    # The real engine would shell out; mock _run for speed.
    engine = HealthCheckEngine(timeout=1)

    async def fake_run(command, default_stdout=""):
        return {"success": True, "stdout": default_stdout, "stderr": "", "return_code": 0}

    monkeypatch.setattr(engine, "_run", fake_run)

    status = await engine.check_service_status("redis")
    assert status["success"] is True
    process = await engine.check_process_exists(1234)
    assert process["success"] is True
    metric = await engine.check_metric_threshold("cpu", 100.0, 90.0, threshold_percent=5.0)
    assert metric["success"] is True
