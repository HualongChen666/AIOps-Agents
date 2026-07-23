# -*- coding: utf-8 -*-
"""Audit orchestrator domain logic."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from services.audit_service.alerting import AlertingEngine
from services.audit_service.analyzer import AuditAnalyzer
from services.audit_service.event_router import AuditEventRouter
from services.audit_service.event_store import EventStore
from services.audit_service.event_tracker import AuditEventTracker
from services.audit_service.graphql_api import AuditGraphQL
from services.audit_service.log_recorder import OperationLogRecorder
from services.audit_service.query import AuditQuery
from services.audit_service.report_generator import ReportGenerator
from services.audit_service.repository import AuditRepository
from services.audit_service.retention import RetentionManager
from services.audit_service.saga import SagaOrchestrator
from services.audit_service.schemas import (
    AuditEvent,
    AuditReport,
    OperationLog,
    RetentionPolicy,
    SagaTransaction,
)


class AuditOrchestrator:
    """Coordinates audit microservice operations."""

    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo
        self.event_store = EventStore(repo)
        self.log_recorder = OperationLogRecorder(repo)
        self.query = AuditQuery(repo)
        self.analyzer = AuditAnalyzer(repo)
        self.tracker = AuditEventTracker(repo)
        self.router = AuditEventRouter()
        self.report_generator = ReportGenerator(repo)
        self.retention = RetentionManager(repo)
        self.graphql = AuditGraphQL(repo)
        self.alerting = AlertingEngine(repo)

    async def record_event(self, event: AuditEvent) -> Dict[str, Any]:
        await self.event_store.append(event)
        route = await self.tracker.track(event)
        await self.router.route(event)
        alerts = await self.alerting.evaluate(event)
        return {"event_id": event.event_id, "route": route, "alerts": [a.rule_id for a in alerts]}

    async def record_operation_log(self, log: OperationLog) -> OperationLog:
        await self.repo.save_log(log)
        return log

    async def generate_report(
        self,
        report_type: str,
        tenant_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> AuditReport:
        return await self.report_generator.generate(report_type, tenant_id, start_time, end_time)

    async def apply_retention(
        self,
        tenant_id: str,
        ttl_days: int = 365,
        archive_after_days: int = 90,
        auto_archive: bool = True,
    ) -> RetentionPolicy:
        return await self.retention.apply_policy(
            tenant_id, ttl_days, archive_after_days, auto_archive
        )

    async def run_saga(self, saga: SagaTransaction) -> SagaTransaction:
        orchestrator = SagaOrchestrator(self.repo)
        return await orchestrator.execute(saga)
