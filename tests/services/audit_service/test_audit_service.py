# -*- coding: utf-8 -*-
"""Tests for audit microservice (task 28)."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from services.audit_service.alerting import AlertingEngine
from services.audit_service.analyzer import AuditAnalyzer
from services.audit_service.encryption import AuditEncryption
from services.audit_service.event_router import AuditEventRouter
from services.audit_service.event_store import EventStore
from services.audit_service.event_tracker import AuditEventTracker
from services.audit_service.graphql_api import AuditGraphQL
from services.audit_service.log_recorder import OperationLogRecorder
from services.audit_service.orchestrator import AuditOrchestrator
from services.audit_service.query import AuditQuery
from services.audit_service.report_generator import ReportGenerator
from services.audit_service.repository import InMemoryAuditRepository
from services.audit_service.retention import RetentionManager
from services.audit_service.schemas import (
    AuditEvent,
    AuditEventSeverity,
    AuditEventStatus,
    SagaStep,
    SagaTransaction,
)


@pytest.fixture
async def repo():
    return InMemoryAuditRepository()


@pytest.fixture
async def orchestrator(repo):
    return AuditOrchestrator(repo)


@pytest.mark.asyncio
async def test_event_store_append(repo):
    store = EventStore(repo)
    event = AuditEvent(event_id="e1", action="login", resource="user", user_id="u1")
    event_id = await store.append(event)
    assert event_id == "e1"
    assert (await repo.get_event("e1")).status == AuditEventStatus.RECORDED


@pytest.mark.asyncio
async def test_query_search(repo):
    query = AuditQuery(repo)
    await repo.save_event(
        AuditEvent(event_id="e1", action="login", resource="r", user_id="u1", tenant_id="t1")
    )
    await repo.save_event(
        AuditEvent(event_id="e2", action="logout", resource="r", user_id="u1", tenant_id="t1")
    )
    results = await query.search(tenant_id="t1", action="login")
    assert len(results) == 1


@pytest.mark.asyncio
async def test_analyzer_detect_anomalies(repo):
    analyzer = AuditAnalyzer(repo)
    await repo.save_event(
        AuditEvent(
            event_id="e1",
            action="admin_login",
            resource="r",
            user_id="u1",
            tenant_id="t1",
            severity=AuditEventSeverity.CRITICAL,
        )
    )
    anomalies = await analyzer.detect_anomalies("t1")
    assert any(a["type"] == "high_severity_events" for a in anomalies)


@pytest.mark.asyncio
async def test_log_recorder(repo):
    recorder = OperationLogRecorder(repo)
    log = await recorder.record("e1", "update", "u1", {"a": 1}, {"a": 2})
    assert log.event_id == "e1"


@pytest.mark.asyncio
async def test_event_tracker(repo):
    tracker = AuditEventTracker(repo)
    event = AuditEvent(
        event_id="e1", action="login", resource="r", user_id="u1", severity=AuditEventSeverity.HIGH
    )
    route = await tracker.track(event)
    assert route == "priority-queue"


@pytest.mark.asyncio
async def test_event_router():
    router = AuditEventRouter()
    event = AuditEvent(
        event_id="e1", action="login", resource="r", user_id="u1", severity=AuditEventSeverity.HIGH
    )
    queue = await router.route(event)
    assert queue == "priority"


@pytest.mark.asyncio
async def test_report_generator(repo):
    now = datetime.utcnow()
    await repo.save_event(
        AuditEvent(
            event_id="e1", action="login", resource="r", user_id="u1", tenant_id="t1", timestamp=now
        )
    )
    generator = ReportGenerator(repo)
    report = await generator.generate(
        "soc2", "t1", now - timedelta(hours=1), now + timedelta(hours=1)
    )
    assert report.tenant_id == "t1"
    assert "t1" in report.content


@pytest.mark.asyncio
async def test_encryption():
    engine = AuditEncryption("test-key-32-bytes-long!!!")
    blob = engine.encrypt_event("e1", "sensitive data")
    assert blob.blob_id == "e1"
    decrypted = engine.decrypt_blob(blob)
    assert decrypted == "sensitive data"


@pytest.mark.asyncio
async def test_retention(repo):
    retention = RetentionManager(repo)
    policy = await retention.apply_policy("t1", ttl_days=30, archive_after_days=7)
    assert policy.ttl_days == 30


@pytest.mark.asyncio
async def test_graphql(repo):
    await repo.save_event(
        AuditEvent(event_id="e1", action="login", resource="r", user_id="u1", tenant_id="t1")
    )
    gql = AuditGraphQL(repo)
    result = await gql.query(["event_id", "action"], tenant_id="t1")
    assert result["total"] == 1
    assert "event_id" in result["data"][0]


@pytest.mark.asyncio
async def test_alerting(repo):
    alerting = AlertingEngine(repo)
    event = AuditEvent(
        event_id="e1",
        action="admin_delete",
        resource="r",
        user_id="u1",
        severity=AuditEventSeverity.CRITICAL,
    )
    triggered = await alerting.evaluate(event)
    assert any(t.rule_id == "r1" for t in triggered)


@pytest.mark.asyncio
async def test_orchestrator_record_event(orchestrator):
    event = AuditEvent(event_id="e1", action="login", resource="user", user_id="u1")
    result = await orchestrator.record_event(event)
    assert result["event_id"] == "e1"


@pytest.mark.asyncio
async def test_saga(orchestrator):
    saga = SagaTransaction(
        saga_id="s1",
        task_id="t1",
        steps=[
            SagaStep(step_id="s1", service="audit", action="log", compensation="undo_log"),
        ],
    )
    result = await orchestrator.run_saga(saga)
    assert result.status == "success"


@pytest.mark.asyncio
async def test_config():
    from services.audit_service.config import settings

    assert settings.service_name == "audit-service"


@pytest.mark.asyncio
async def test_rpc():
    from services.audit_service.grpc.client import AuditRPCClient
    from services.audit_service.grpc.server import AuditRPCServer

    server = AuditRPCServer()
    server.register("echo", lambda **kwargs: kwargs)
    client = AuditRPCClient(server=server)
    result = await client.call("echo", message="hi")
    assert result == {"message": "hi"}
    assert "echo" in server.list_methods()
