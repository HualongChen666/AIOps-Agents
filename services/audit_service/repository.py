# -*- coding: utf-8 -*-
"""Audit repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

from loguru import logger

from services.audit_service.schemas import (
    AuditEvent,
    AuditEventStatus,
    AuditReport,
    EncryptedBlob,
    OperationLog,
    RetentionPolicy,
    SagaTransaction,
)


class AuditRepository(ABC):
    """Abstract audit repository."""

    @abstractmethod
    async def save_event(self, event: AuditEvent) -> str: ...

    @abstractmethod
    async def get_event(self, event_id: str) -> Optional[AuditEvent]: ...

    @abstractmethod
    async def list_events(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]: ...

    @abstractmethod
    async def save_log(self, log: OperationLog) -> str: ...

    @abstractmethod
    async def list_logs(self, event_id: str) -> List[OperationLog]: ...

    @abstractmethod
    async def save_report(self, report: AuditReport) -> str: ...

    @abstractmethod
    async def list_reports(self, tenant_id: str, limit: int = 100) -> List[AuditReport]: ...

    @abstractmethod
    async def save_blob(self, blob: EncryptedBlob) -> str: ...

    @abstractmethod
    async def get_blob(self, blob_id: str) -> Optional[EncryptedBlob]: ...

    @abstractmethod
    async def save_policy(self, policy: RetentionPolicy) -> str: ...

    @abstractmethod
    async def get_policy(self, tenant_id: str) -> Optional[RetentionPolicy]: ...

    @abstractmethod
    async def save_saga(self, saga: SagaTransaction) -> str: ...

    @abstractmethod
    async def get_saga(self, saga_id: str) -> Optional[SagaTransaction]: ...


class InMemoryAuditRepository(AuditRepository):
    """In-memory audit repository for tests and local dev."""

    def __init__(self) -> None:
        self._events: Dict[str, AuditEvent] = {}
        self._logs: Dict[str, List[OperationLog]] = {}
        self._reports: Dict[str, AuditReport] = {}
        self._blobs: Dict[str, EncryptedBlob] = {}
        self._policies: Dict[str, RetentionPolicy] = {}
        self._sagas: Dict[str, SagaTransaction] = {}

    async def save_event(self, event: AuditEvent) -> str:
        event.status = AuditEventStatus.RECORDED
        event.timestamp = datetime.utcnow()
        self._events[event.event_id] = event
        logger.debug(f"Saved audit event {event.event_id}")
        return event.event_id

    async def get_event(self, event_id: str) -> Optional[AuditEvent]:
        return self._events.get(event_id)

    async def list_events(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        events = [e for e in self._events.values() if tenant_id is None or e.tenant_id == tenant_id]
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    async def save_log(self, log: OperationLog) -> str:
        self._logs.setdefault(log.event_id, []).append(log)
        return log.log_id

    async def list_logs(self, event_id: str) -> List[OperationLog]:
        return self._logs.get(event_id, [])

    async def save_report(self, report: AuditReport) -> str:
        self._reports[report.report_id] = report
        return report.report_id

    async def list_reports(self, tenant_id: str, limit: int = 100) -> List[AuditReport]:
        reports = [r for r in self._reports.values() if r.tenant_id == tenant_id]
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        return reports[:limit]

    async def save_blob(self, blob: EncryptedBlob) -> str:
        self._blobs[blob.blob_id] = blob
        return blob.blob_id

    async def get_blob(self, blob_id: str) -> Optional[EncryptedBlob]:
        return self._blobs.get(blob_id)

    async def save_policy(self, policy: RetentionPolicy) -> str:
        self._policies[policy.tenant_id] = policy
        return policy.policy_id

    async def get_policy(self, tenant_id: str) -> Optional[RetentionPolicy]:
        return self._policies.get(tenant_id)

    async def save_saga(self, saga: SagaTransaction) -> str:
        self._sagas[saga.saga_id] = saga
        return saga.saga_id

    async def get_saga(self, saga_id: str) -> Optional[SagaTransaction]:
        return self._sagas.get(saga_id)


async def get_repository(use_in_memory: bool = True) -> AuditRepository:
    """Return repository instance based on configuration."""
    return InMemoryAuditRepository()
