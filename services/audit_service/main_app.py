# -*- coding: utf-8 -*-
"""Audit service main FastAPI application."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.audit_service.health_check import HealthCheckEngine
from services.audit_service.metrics import AUDIT_EVENTS_RECORDED
from services.audit_service.orchestrator import AuditOrchestrator
from services.audit_service.repository import InMemoryAuditRepository
from services.audit_service.schemas import (
    AuditEvent,
    OperationLog,
    RetentionPolicy,
    SagaTransaction,
    ServiceHealth,
)

_orchestrator: Optional[AuditOrchestrator] = None


def get_orchestrator() -> AuditOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AuditOrchestrator(InMemoryAuditRepository())
    return _orchestrator


app = FastAPI(
    title="Audit Service",
    description="Audit microservice for logging, event tracking, compliance, and alerts.",
    version="0.1.0",
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    o = get_orchestrator()
    count = len(await o.repo.list_events(limit=100000))
    return await HealthCheckEngine().check("audit-service", count)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/events")
async def record_event(event: AuditEvent) -> Dict[str, Any]:
    o = get_orchestrator()
    result = await o.record_event(event)
    AUDIT_EVENTS_RECORDED.labels(severity=event.severity, tenant=event.tenant_id).inc()
    return result


@app.get("/events")
async def list_events(
    tenant_id: Optional[str] = None,
    action: Optional[str] = None,
    severity: Optional[str] = None,
    limit: int = 100,
) -> Dict[str, Any]:
    o = get_orchestrator()
    events = await o.query.search(tenant_id, action, severity, limit)
    return {"total": len(events), "items": [e.model_dump() for e in events]}


@app.post("/logs")
async def record_log(log: OperationLog) -> Dict[str, Any]:
    o = get_orchestrator()
    await o.record_operation_log(log)
    return {"log_id": log.log_id, "status": "recorded"}


@app.get("/logs/{event_id}")
async def get_logs(event_id: str) -> Dict[str, Any]:
    o = get_orchestrator()
    logs = await o.repo.list_logs(event_id)
    return {"total": len(logs), "items": [log.model_dump() for log in logs]}


@app.post("/reports")
async def create_report(
    report_type: str,
    tenant_id: str,
    start_time: datetime,
    end_time: datetime,
) -> Dict[str, Any]:
    o = get_orchestrator()
    report = await o.generate_report(report_type, tenant_id, start_time, end_time)
    return report.model_dump()


@app.get("/reports")
async def list_reports(tenant_id: str, limit: int = 100) -> Dict[str, Any]:
    o = get_orchestrator()
    reports = await o.repo.list_reports(tenant_id, limit)
    return {"total": len(reports), "items": [r.model_dump() for r in reports]}


@app.post("/policies")
async def create_policy(policy: RetentionPolicy) -> Dict[str, Any]:
    o = get_orchestrator()
    await o.repo.save_policy(policy)
    return {"policy_id": policy.policy_id, "status": "created"}


@app.post("/sagas")
async def execute_saga(saga: SagaTransaction) -> Dict[str, Any]:
    o = get_orchestrator()
    result = await o.run_saga(saga)
    return result.model_dump()
