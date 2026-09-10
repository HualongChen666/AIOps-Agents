# -*- coding: utf-8 -*-
"""SQLAlchemy-backed persistence for the audit service.

Production (non in-memory) implementation of :class:`AuditRepository`.
Tables are a faithful transcription of the aggregates in
``services/audit_service/schemas.py``.
"""

from __future__ import annotations

from typing import Any, List, Optional

from sqlalchemy import INTEGER, JSON, Boolean, Column, DateTime, String, Text, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from services.audit_service.repository import AuditRepository
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


class _Base(DeclarativeBase):
    """Declarative base for audit-service owned tables."""


class AuditEventRow(_Base):
    __tablename__ = "audit_service_events"

    event_id = Column(String(128), primary_key=True)
    action = Column(String(64), nullable=False, index=True)
    resource = Column(String(64), nullable=False, index=True)
    user_id = Column(String(128), nullable=True, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_metadata = Column("metadata", JSON, nullable=False)


class OperationLogRow(_Base):
    __tablename__ = "audit_service_operation_logs"

    log_id = Column(String(128), primary_key=True)
    event_id = Column(String(128), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    actor = Column(String(128), nullable=False)
    before_state = Column(JSON, nullable=False)
    after_state = Column(JSON, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)


class AuditReportRow(_Base):
    __tablename__ = "audit_service_reports"

    report_id = Column(String(128), primary_key=True)
    report_type = Column(String(64), nullable=False, index=True)
    tenant_id = Column(String(64), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    generated_at = Column(DateTime, nullable=False, index=True)
    content = Column(Text, nullable=False)
    rendered_template = Column(Text, nullable=False)


class EncryptedBlobRow(_Base):
    __tablename__ = "audit_service_encrypted_blobs"

    blob_id = Column(String(128), primary_key=True)
    ciphertext = Column(Text, nullable=False)
    nonce = Column(String(128), nullable=False)
    tag = Column(String(128), nullable=False)
    algorithm = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, index=True)


class RetentionPolicyRow(_Base):
    __tablename__ = "audit_service_retention_policies"

    policy_id = Column(String(128), primary_key=True)
    tenant_id = Column(String(64), nullable=False, unique=True, index=True)
    ttl_days = Column(INTEGER, nullable=False)
    archive_after_days = Column(INTEGER, nullable=False)
    auto_archive = Column(Boolean, nullable=False)


class SagaTransactionRow(_Base):
    __tablename__ = "audit_service_sagas"

    saga_id = Column(String(128), primary_key=True)
    task_id = Column(String(128), nullable=False, index=True)
    steps = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


class SQLAlchemyAuditRepository(AuditRepository):
    """PostgreSQL-backed audit repository."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_async_engine(database_url, pool_pre_ping=True)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    # -- lifecycle ---------------------------------------------------------
    async def init_schema(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(_Base.metadata.create_all)

    async def close(self) -> None:
        await self._engine.dispose()

    # -- events ------------------------------------------------------------
    async def save_event(self, event: AuditEvent) -> str:
        data = {
            "event_id": event.event_id,
            "action": event.action,
            "resource": event.resource,
            "user_id": event.user_id,
            "tenant_id": event.tenant_id,
            "severity": _enum_value(event.severity),
            "status": _enum_value(event.status),
            "timestamp": event.timestamp,
            "event_metadata": event.metadata or {},
        }
        async with self._session_factory() as session:
            row = await session.get(AuditEventRow, event.event_id)
            if row is None:
                session.add(AuditEventRow(**data))
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            await session.commit()
        return event.event_id

    async def get_event(self, event_id: str) -> Optional[AuditEvent]:
        async with self._session_factory() as session:
            row = await session.get(AuditEventRow, event_id)
        if row is None:
            return None
        return AuditEvent(
            event_id=row.event_id,
            action=row.action,
            resource=row.resource,
            user_id=row.user_id,
            tenant_id=row.tenant_id,
            severity=AuditEventSeverity(row.severity),
            status=AuditEventStatus(row.status),
            timestamp=row.timestamp,
            metadata=row.event_metadata or {},
        )

    async def list_events(
        self,
        tenant_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditEvent]:
        stmt = select(AuditEventRow).order_by(AuditEventRow.timestamp.desc()).limit(limit)
        if tenant_id is not None:
            stmt = stmt.where(AuditEventRow.tenant_id == tenant_id)
        async with self._session_factory() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return [
            AuditEvent(
                event_id=row.event_id,
                action=row.action,
                resource=row.resource,
                user_id=row.user_id,
                tenant_id=row.tenant_id,
                severity=AuditEventSeverity(row.severity),
                status=AuditEventStatus(row.status),
                timestamp=row.timestamp,
                metadata=row.event_metadata or {},
            )
            for row in rows
        ]

    # -- operation logs ----------------------------------------------------
    async def save_log(self, log: OperationLog) -> str:
        data = {
            "log_id": log.log_id,
            "event_id": log.event_id,
            "action": log.action,
            "actor": log.actor,
            "before_state": log.before_state or {},
            "after_state": log.after_state or {},
            "timestamp": log.timestamp,
        }
        async with self._session_factory() as session:
            row = await session.get(OperationLogRow, log.log_id)
            if row is None:
                session.add(OperationLogRow(**data))
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            await session.commit()
        return log.log_id

    async def list_logs(self, event_id: str) -> List[OperationLog]:
        stmt = (
            select(OperationLogRow)
            .where(OperationLogRow.event_id == event_id)
            .order_by(OperationLogRow.timestamp.asc())
        )
        async with self._session_factory() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return [
            OperationLog(
                log_id=row.log_id,
                event_id=row.event_id,
                action=row.action,
                actor=row.actor,
                before_state=row.before_state or {},
                after_state=row.after_state or {},
                timestamp=row.timestamp,
            )
            for row in rows
        ]

    # -- reports -----------------------------------------------------------
    async def save_report(self, report: AuditReport) -> str:
        data = {
            "report_id": report.report_id,
            "report_type": report.report_type,
            "tenant_id": report.tenant_id,
            "start_time": report.start_time,
            "end_time": report.end_time,
            "generated_at": report.generated_at,
            "content": report.content,
            "rendered_template": report.rendered_template,
        }
        async with self._session_factory() as session:
            row = await session.get(AuditReportRow, report.report_id)
            if row is None:
                session.add(AuditReportRow(**data))
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            await session.commit()
        return report.report_id

    async def list_reports(self, tenant_id: str, limit: int = 100) -> List[AuditReport]:
        stmt = (
            select(AuditReportRow)
            .where(AuditReportRow.tenant_id == tenant_id)
            .order_by(AuditReportRow.generated_at.desc())
            .limit(limit)
        )
        async with self._session_factory() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return [
            AuditReport(
                report_id=row.report_id,
                report_type=row.report_type,
                tenant_id=row.tenant_id,
                start_time=row.start_time,
                end_time=row.end_time,
                generated_at=row.generated_at,
                content=row.content,
                rendered_template=row.rendered_template,
            )
            for row in rows
        ]

    # -- encrypted blobs ---------------------------------------------------
    async def save_blob(self, blob: EncryptedBlob) -> str:
        data = {
            "blob_id": blob.blob_id,
            "ciphertext": blob.ciphertext,
            "nonce": blob.nonce,
            "tag": blob.tag,
            "algorithm": blob.algorithm,
            "created_at": blob.created_at,
        }
        async with self._session_factory() as session:
            row = await session.get(EncryptedBlobRow, blob.blob_id)
            if row is None:
                session.add(EncryptedBlobRow(**data))
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            await session.commit()
        return blob.blob_id

    async def get_blob(self, blob_id: str) -> Optional[EncryptedBlob]:
        async with self._session_factory() as session:
            row = await session.get(EncryptedBlobRow, blob_id)
        if row is None:
            return None
        return EncryptedBlob(
            blob_id=row.blob_id,
            ciphertext=row.ciphertext,
            nonce=row.nonce,
            tag=row.tag,
            algorithm=row.algorithm,
            created_at=row.created_at,
        )

    # -- retention policies ------------------------------------------------
    async def save_policy(self, policy: RetentionPolicy) -> str:
        data = {
            "policy_id": policy.policy_id,
            "tenant_id": policy.tenant_id,
            "ttl_days": policy.ttl_days,
            "archive_after_days": policy.archive_after_days,
            "auto_archive": policy.auto_archive,
        }
        async with self._session_factory() as session:
            row = await session.get(RetentionPolicyRow, policy.policy_id)
            if row is None:
                session.add(RetentionPolicyRow(**data))
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            await session.commit()
        return policy.policy_id

    async def get_policy(self, tenant_id: str) -> Optional[RetentionPolicy]:
        stmt = select(RetentionPolicyRow).where(RetentionPolicyRow.tenant_id == tenant_id)
        async with self._session_factory() as session:
            row = (await session.execute(stmt)).scalars().first()
        if row is None:
            return None
        return RetentionPolicy(
            policy_id=row.policy_id,
            tenant_id=row.tenant_id,
            ttl_days=row.ttl_days,
            archive_after_days=row.archive_after_days,
            auto_archive=row.auto_archive,
        )

    # -- sagas -------------------------------------------------------------
    async def save_saga(self, saga: SagaTransaction) -> str:
        data = {
            "saga_id": saga.saga_id,
            "task_id": saga.task_id,
            "steps": [step.model_dump(mode="json") for step in (saga.steps or [])],
            "status": _enum_value(saga.status),
            "created_at": saga.created_at,
        }
        async with self._session_factory() as session:
            row = await session.get(SagaTransactionRow, saga.saga_id)
            if row is None:
                session.add(SagaTransactionRow(**data))
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            await session.commit()
        return saga.saga_id

    async def get_saga(self, saga_id: str) -> Optional[SagaTransaction]:
        async with self._session_factory() as session:
            row = await session.get(SagaTransactionRow, saga_id)
        if row is None:
            return None
        return SagaTransaction(
            saga_id=row.saga_id,
            task_id=row.task_id,
            steps=row.steps or [],
            status=row.status,
            created_at=row.created_at,
        )
