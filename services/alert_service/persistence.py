# -*- coding: utf-8 -*-
"""SQLAlchemy-backed persistence for the alert service.

Production (non in-memory) implementation of :class:`AlertRepository`.
The table below is a faithful transcription of the ``Alert`` schema in
``services/alert_service/schemas.py``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    delete,
    func,
    select,
)
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from services.alert_service.repository import AlertRepository
from services.alert_service.schemas import Alert, AlertSeverity, AlertStatus


class _Base(DeclarativeBase):
    """Declarative base for alert-service owned tables."""


class AlertRow(_Base):
    """Relational representation of :class:`Alert`."""

    __tablename__ = "alert_service_alerts"

    id = Column(String(128), primary_key=True)
    level = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    category = Column(String(64), nullable=False, index=True)
    alert_type = Column(String(64), nullable=False)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=False, default="")
    desc = Column(Text, nullable=True)
    metric = Column(String(255), nullable=True)
    value = Column(Float, nullable=True)
    detected_at = Column(DateTime, nullable=False, index=True)
    metric_time = Column(DateTime, nullable=True)
    host = Column(String(255), nullable=True, index=True)
    service = Column(String(255), nullable=True)
    platform = Column(String(32), nullable=False)
    priority = Column(String(8), nullable=False)
    source = Column(String(64), nullable=False)
    severity = Column(String(32), nullable=True)
    fingerprint = Column(String(255), nullable=True, index=True)
    trace_id = Column(String(128), nullable=True)
    labels = Column(JSON, nullable=False)
    annotations = Column(JSON, nullable=False)
    raw = Column(JSON, nullable=False)
    routed_to = Column(String(255), nullable=True)
    suppressed = Column(Boolean, nullable=False, default=False)
    suppression_reason = Column(Text, nullable=True)
    aggregated_count = Column(Integer, nullable=False, default=1)
    prev_suppressed = Column(Integer, nullable=False, default=0)
    tags = Column(JSON, nullable=False)


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _to_row(alert: Alert) -> Dict[str, Any]:
    """Convert an :class:`Alert` into column values."""
    return {
        "id": alert.id,
        "level": _enum_value(alert.level),
        "status": _enum_value(alert.status),
        "category": alert.category,
        "alert_type": alert.alert_type,
        "title": alert.title,
        "description": alert.description,
        "desc": alert.desc,
        "metric": alert.metric,
        "value": alert.value,
        "detected_at": alert.detected_at,
        "metric_time": alert.metric_time,
        "host": alert.host,
        "service": alert.service,
        "platform": alert.platform,
        "priority": alert.priority,
        "source": alert.source,
        "severity": alert.severity,
        "fingerprint": alert.fingerprint,
        "trace_id": alert.trace_id,
        "labels": alert.labels or {},
        "annotations": alert.annotations or {},
        "raw": alert.raw or {},
        "routed_to": alert.routed_to,
        "suppressed": alert.suppressed,
        "suppression_reason": alert.suppression_reason,
        "aggregated_count": alert.aggregated_count,
        "prev_suppressed": alert.prev_suppressed,
        "tags": alert.tags or {},
    }


def _from_row(row: AlertRow) -> Alert:
    """Rebuild an :class:`Alert` from a stored row."""
    return Alert(
        id=row.id,
        level=AlertSeverity(row.level),
        status=AlertStatus(row.status),
        category=row.category,
        alert_type=row.alert_type,
        title=row.title,
        description=row.description,
        desc=row.desc,
        metric=row.metric,
        value=row.value,
        detected_at=row.detected_at,
        metric_time=row.metric_time,
        host=row.host,
        service=row.service,
        platform=row.platform,
        priority=row.priority,
        source=row.source,
        severity=row.severity,
        fingerprint=row.fingerprint,
        trace_id=row.trace_id,
        labels=row.labels or {},
        annotations=row.annotations or {},
        raw=row.raw or {},
        routed_to=row.routed_to,
        suppressed=row.suppressed,
        suppression_reason=row.suppression_reason,
        aggregated_count=row.aggregated_count,
        prev_suppressed=row.prev_suppressed,
        tags=row.tags or {},
    )


class SQLAlchemyAlertRepository(AlertRepository):
    """PostgreSQL-backed alert repository."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_async_engine(database_url, pool_pre_ping=True)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    # -- lifecycle ---------------------------------------------------------
    async def init_schema(self) -> None:
        async with self._engine.begin() as conn:
            await conn.run_sync(_Base.metadata.create_all)

    async def close(self) -> None:
        await self._engine.dispose()

    # -- AlertRepository ---------------------------------------------------
    async def save(self, alert: Alert) -> str:
        if not alert.id:
            alert.id = f"alert-{datetime.utcnow().timestamp()}"
        data = _to_row(alert)
        async with self._session_factory() as session:
            row = await session.get(AlertRow, alert.id)
            if row is None:
                session.add(AlertRow(**data))
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            await session.commit()
        return alert.id

    async def get(self, alert_id: str) -> Optional[Alert]:
        async with self._session_factory() as session:
            row = await session.get(AlertRow, alert_id)
        return _from_row(row) if row is not None else None

    async def list(
        self,
        limit: int = 100,
        status: Optional[AlertStatus] = None,
        level: Optional[str] = None,
    ) -> List[Alert]:
        stmt = select(AlertRow).order_by(AlertRow.detected_at.desc()).limit(limit)
        if status is not None:
            stmt = stmt.where(AlertRow.status == _enum_value(status))
        if level is not None:
            stmt = stmt.where(AlertRow.level == level)
        async with self._session_factory() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return [_from_row(row) for row in rows]

    async def update(self, alert_id: str, data: Dict[str, Any]) -> bool:
        async with self._session_factory() as session:
            row = await session.get(AlertRow, alert_id)
            if row is None:
                return False
            for key, value in data.items():
                if key == "id" or not hasattr(row, key):
                    continue
                setattr(row, key, _enum_value(value))
            await session.commit()
        return True

    async def count(self) -> int:
        async with self._session_factory() as session:
            total = await session.execute(select(func.count()).select_from(AlertRow))
        return int(total.scalar_one())

    async def delete(self, alert_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(delete(AlertRow).where(AlertRow.id == alert_id))
            await session.commit()
        return bool(result.rowcount)

    async def clear(self) -> int:
        async with self._session_factory() as session:
            total = int((await session.execute(select(func.count()).select_from(AlertRow))).scalar_one())
            await session.execute(delete(AlertRow))
            await session.commit()
        return total
