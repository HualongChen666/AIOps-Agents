# -*- coding: utf-8 -*-
"""SQLAlchemy-backed persistence for the repair service.

Production (non in-memory) implementation of :class:`RepairRepository`.
The table below is a faithful transcription of the ``RepairTask`` schema in
``services/repair_service/schemas.py`` (scalar fields become columns, nested
structures become JSON columns).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, String, delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from services.repair_service.repository import RepairRepository
from services.repair_service.schemas import (
    PlatformType,
    RepairRunbook,
    RepairStatus,
    RepairStrategy,
    RepairTask,
)


class _Base(DeclarativeBase):
    """Declarative base for repair-service owned tables."""


class RepairTaskRow(_Base):
    """Relational representation of :class:`RepairTask`."""

    __tablename__ = "repair_service_tasks"

    task_id = Column(String(128), primary_key=True)
    alert_id = Column(String(128), nullable=False, index=True)
    host = Column(String(255), nullable=False, index=True)
    platform = Column(String(32), nullable=False, index=True)
    status = Column(String(32), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, index=True)
    updated_at = Column(DateTime, nullable=False)
    runbook = Column(JSON, nullable=True)
    strategy = Column(JSON, nullable=True)
    result = Column(JSON, nullable=False)
    audit_log = Column(JSON, nullable=False)
    rollback_result = Column(JSON, nullable=True)


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _to_row(task: RepairTask) -> Dict[str, Any]:
    """Convert a :class:`RepairTask` into column values."""
    return {
        "task_id": task.task_id,
        "alert_id": task.alert_id,
        "host": task.host,
        "platform": _enum_value(task.platform),
        "status": _enum_value(task.status),
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "runbook": task.runbook.model_dump(mode="json") if task.runbook else None,
        "strategy": task.strategy.model_dump(mode="json") if task.strategy else None,
        "result": task.result or {},
        "audit_log": task.audit_log or [],
        "rollback_result": task.rollback_result,
    }


def _from_row(row: RepairTaskRow) -> RepairTask:
    """Rebuild a :class:`RepairTask` from a stored row."""
    return RepairTask(
        task_id=row.task_id,
        alert_id=row.alert_id,
        host=row.host,
        platform=PlatformType(row.platform),
        status=RepairStatus(row.status),
        created_at=row.created_at,
        updated_at=row.updated_at,
        runbook=RepairRunbook.model_validate(row.runbook) if row.runbook else None,
        strategy=RepairStrategy.model_validate(row.strategy) if row.strategy else None,
        result=row.result or {},
        audit_log=row.audit_log or [],
        rollback_result=row.rollback_result,
    )


class SQLAlchemyRepairRepository(RepairRepository):
    """PostgreSQL-backed repair task repository."""

    def __init__(self, database_url: str) -> None:
        self._engine = create_async_engine(database_url, pool_pre_ping=True)
        self._session_factory = async_sessionmaker(self._engine, expire_on_commit=False)

    # -- lifecycle ---------------------------------------------------------
    async def init_schema(self) -> None:
        """Create the service-owned tables if they do not exist yet."""
        async with self._engine.begin() as conn:
            await conn.run_sync(_Base.metadata.create_all)

    async def close(self) -> None:
        await self._engine.dispose()

    # -- RepairRepository --------------------------------------------------
    async def save(self, task: RepairTask) -> str:
        if not task.task_id:
            task.task_id = f"REPAIR-{datetime.utcnow().timestamp()}"
        data = _to_row(task)
        async with self._session_factory() as session:
            row = await session.get(RepairTaskRow, task.task_id)
            if row is None:
                session.add(RepairTaskRow(**data))
            else:
                for key, value in data.items():
                    setattr(row, key, value)
            await session.commit()
        return task.task_id

    async def get(self, task_id: str) -> Optional[RepairTask]:
        async with self._session_factory() as session:
            row = await session.get(RepairTaskRow, task_id)
        return _from_row(row) if row is not None else None

    async def list(
        self,
        limit: int = 100,
        status: Optional[RepairStatus] = None,
    ) -> List[RepairTask]:
        stmt = (
            select(RepairTaskRow)
            .order_by(RepairTaskRow.created_at.desc())
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(RepairTaskRow.status == _enum_value(status))
        async with self._session_factory() as session:
            rows = (await session.execute(stmt)).scalars().all()
        return [_from_row(row) for row in rows]

    async def update(self, task_id: str, data: Dict[str, Any]) -> bool:
        async with self._session_factory() as session:
            row = await session.get(RepairTaskRow, task_id)
            if row is None:
                return False
            for key, value in data.items():
                if key == "task_id" or not hasattr(row, key):
                    continue
                setattr(row, key, _enum_value(value))
            row.updated_at = datetime.utcnow()
            await session.commit()
        return True

    async def delete(self, task_id: str) -> bool:
        async with self._session_factory() as session:
            result = await session.execute(
                delete(RepairTaskRow).where(RepairTaskRow.task_id == task_id)
            )
            await session.commit()
        return bool(result.rowcount)

    async def count(self) -> int:
        async with self._session_factory() as session:
            total = await session.execute(select(func.count()).select_from(RepairTaskRow))
        return int(total.scalar_one())
