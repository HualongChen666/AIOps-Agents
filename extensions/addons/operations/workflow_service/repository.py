# -*- coding: utf-8 -*-
"""Workflow repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy.orm import Session

from core.database import SessionLocal
from core.models import (
    Workflow,
    WorkflowExecution,
    WorkflowScheduleRecord,
    WorkflowVersionRecord,
)

from extensions.addons.operations.workflow_service.schemas import (
    ScheduledTask,
    WorkflowDefinition,
    WorkflowStatus,
    WorkflowTask,
    WorkflowVersion,
)


class WorkflowRepository(ABC):
    """Abstract workflow repository."""

    @abstractmethod
    async def save_task(self, task: WorkflowTask) -> str: ...

    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[WorkflowTask]: ...

    @abstractmethod
    async def list_tasks(self, limit: int = 100) -> List[WorkflowTask]: ...

    @abstractmethod
    async def update_task(self, task_id: str, data: Dict[str, Any]) -> bool: ...

    @abstractmethod
    async def delete_task(self, task_id: str) -> bool: ...

    @abstractmethod
    async def save_definition(self, definition: WorkflowDefinition) -> str: ...

    @abstractmethod
    async def get_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]: ...

    @abstractmethod
    async def list_definitions(self, limit: int = 100) -> List[WorkflowDefinition]: ...


class InMemoryWorkflowRepository(WorkflowRepository):
    """In-memory repository for tests and local dev."""

    def __init__(self) -> None:
        self._tasks: Dict[str, WorkflowTask] = {}
        self._definitions: Dict[str, WorkflowDefinition] = {}
        self._versions: Dict[str, List[WorkflowVersion]] = {}
        self._schedules: Dict[str, ScheduledTask] = {}

    async def save_task(self, task: WorkflowTask) -> str:
        if not task.task_id:
            raise ValueError("task_id is required")
        task.updated_at = datetime.utcnow()
        self._tasks[task.task_id] = task
        logger.debug(f"Repository saved workflow task {task.task_id}")
        return task.task_id

    async def get_task(self, task_id: str) -> Optional[WorkflowTask]:
        return self._tasks.get(task_id)

    async def list_tasks(self, limit: int = 100) -> List[WorkflowTask]:
        tasks = sorted(self._tasks.values(), key=lambda t: t.updated_at, reverse=True)
        return tasks[:limit]

    async def update_task(self, task_id: str, data: Dict[str, Any]) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        merged = task.model_dump() | data
        self._tasks[task_id] = WorkflowTask.model_validate(merged)
        self._tasks[task_id].updated_at = datetime.utcnow()
        return True

    async def delete_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    async def save_definition(self, definition: WorkflowDefinition) -> str:
        self._definitions[definition.workflow_id] = definition
        return definition.workflow_id

    async def get_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return self._definitions.get(workflow_id)

    async def list_definitions(self, limit: int = 100) -> List[WorkflowDefinition]:
        defs = sorted(self._definitions.values(), key=lambda d: d.workflow_id)
        return defs[:limit]

    async def save_version(self, workflow_id: str, version: WorkflowVersion) -> str:
        self._versions.setdefault(workflow_id, []).append(version)
        return version.version

    async def list_versions(self, workflow_id: str, limit: int = 100) -> List[WorkflowVersion]:
        return self._versions.get(workflow_id, [])[-limit:]

    async def save_schedule(self, schedule: ScheduledTask) -> str:
        self._schedules[schedule.schedule_id] = schedule
        return schedule.schedule_id

    async def list_schedules(self, limit: int = 100) -> List[ScheduledTask]:
        return list(self._schedules.values())[:limit]


class DatabaseWorkflowRepository(WorkflowRepository):
    """Database-backed workflow repository."""

    def __init__(self) -> None:
        pass

    async def save_task(self, task: WorkflowTask) -> str:
        """Save workflow task to database."""
        db = SessionLocal()
        try:
            # Create workflow execution record
            execution = WorkflowExecution(
                id=task.task_id,
                workflow_id=task.workflow_id,
                status=task.status.value,
                result=task.result,
                started_at=task.created_at,
                executor=task.params.get("executor", "system"),
            )
            db.add(execution)
            db.commit()
            logger.debug(f"Repository saved workflow task {task.task_id} to database")
            return task.task_id
        finally:
            db.close()

    async def get_task(self, task_id: str) -> Optional[WorkflowTask]:
        """Get workflow task from database."""
        db = SessionLocal()
        try:
            execution = db.query(WorkflowExecution).filter(
                WorkflowExecution.id == task_id
            ).first()
            if not execution:
                return None
            
            return WorkflowTask(
                task_id=execution.id,
                workflow_id=execution.workflow_id,
                status=WorkflowStatus(execution.status),
                result=execution.result or {},
                created_at=execution.started_at,
                updated_at=execution.completed_at or execution.started_at,
            )
        finally:
            db.close()

    async def list_tasks(self, limit: int = 100) -> List[WorkflowTask]:
        """List workflow tasks from database."""
        db = SessionLocal()
        try:
            executions = db.query(WorkflowExecution).order_by(
                WorkflowExecution.started_at.desc()
            ).limit(limit).all()
            
            tasks = []
            for execution in executions:
                tasks.append(WorkflowTask(
                    task_id=execution.id,
                    workflow_id=execution.workflow_id,
                    status=WorkflowStatus(execution.status),
                    result=execution.result or {},
                    created_at=execution.started_at,
                    updated_at=execution.completed_at or execution.started_at,
                ))
            return tasks
        finally:
            db.close()

    async def update_task(self, task_id: str, data: Dict[str, Any]) -> bool:
        """Update workflow task in database."""
        db = SessionLocal()
        try:
            execution = db.query(WorkflowExecution).filter(
                WorkflowExecution.id == task_id
            ).first()
            if not execution:
                return False
            
            if "status" in data:
                execution.status = data["status"]
            if "result" in data:
                execution.result = data["result"]
            if "error_message" in data:
                execution.error_message = data["error_message"]
            if "completed_at" in data:
                execution.completed_at = data["completed_at"]
            
            db.commit()
            return True
        finally:
            db.close()

    async def delete_task(self, task_id: str) -> bool:
        """Delete workflow task from database."""
        db = SessionLocal()
        try:
            execution = db.query(WorkflowExecution).filter(
                WorkflowExecution.id == task_id
            ).first()
            if not execution:
                return False
            
            db.delete(execution)
            db.commit()
            return True
        finally:
            db.close()

    async def save_definition(self, definition: WorkflowDefinition) -> str:
        """Save workflow definition to database."""
        db = SessionLocal()
        try:
            workflow = Workflow(
                id=definition.workflow_id,
                name=definition.name,
                description=definition.description,
                definition=definition.model_dump(),
                status="active",
                version=1,
            )
            db.add(workflow)
            db.commit()
            logger.debug(f"Repository saved workflow definition {definition.workflow_id} to database")
            return definition.workflow_id
        finally:
            db.close()

    async def get_definition(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get workflow definition from database."""
        db = SessionLocal()
        try:
            workflow = db.query(Workflow).filter(
                Workflow.id == workflow_id
            ).first()
            if not workflow:
                return None
            
            return WorkflowDefinition(
                workflow_id=workflow.id,
                name=workflow.name,
                description=workflow.description or "",
                nodes=workflow.definition.get("nodes", []),
                schedule=workflow.definition.get("schedule"),
                metadata=workflow.definition.get("metadata", {}),
            )
        finally:
            db.close()

    async def list_definitions(self, limit: int = 100) -> List[WorkflowDefinition]:
        """List workflow definitions from database."""
        db = SessionLocal()
        try:
            workflows = db.query(Workflow).order_by(Workflow.id).limit(limit).all()
            
            definitions = []
            for workflow in workflows:
                definitions.append(WorkflowDefinition(
                    workflow_id=workflow.id,
                    name=workflow.name,
                    description=workflow.description or "",
                    nodes=workflow.definition.get("nodes", []),
                    schedule=workflow.definition.get("schedule"),
                    metadata=workflow.definition.get("metadata", {}),
                ))
            return definitions
        finally:
            db.close()

    async def save_version(self, workflow_id: str, version: WorkflowVersion) -> str:
        """Persist a workflow version snapshot.

        Idempotent on ``(workflow_id, version)``: re-saving the same version
        updates its commit hash / message instead of raising a unique
        constraint error.
        """
        db = SessionLocal()
        try:
            record = (
                db.query(WorkflowVersionRecord)
                .filter(
                    WorkflowVersionRecord.workflow_id == workflow_id,
                    WorkflowVersionRecord.version == version.version,
                )
                .first()
            )
            if record is None:
                record = WorkflowVersionRecord(
                    id=f"{workflow_id}:{version.version}",
                    workflow_id=workflow_id,
                    version=version.version,
                    commit_hash=version.commit_hash,
                    message=version.message,
                    created_at=version.created_at,
                )
                db.add(record)
            else:
                record.commit_hash = version.commit_hash
                record.message = version.message
            db.commit()
            logger.debug(
                f"Repository saved workflow version {workflow_id}@{version.version} to database"
            )
            return version.version
        finally:
            db.close()

    async def list_versions(self, workflow_id: str, limit: int = 100) -> List[WorkflowVersion]:
        """List persisted version snapshots for *workflow_id*, newest first."""
        db = SessionLocal()
        try:
            rows = (
                db.query(WorkflowVersionRecord)
                .filter(WorkflowVersionRecord.workflow_id == workflow_id)
                .order_by(WorkflowVersionRecord.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                WorkflowVersion(
                    version=row.version,
                    workflow_id=row.workflow_id,
                    commit_hash=row.commit_hash,
                    message=row.message or "",
                    created_at=row.created_at,
                )
                for row in rows
            ]
        finally:
            db.close()

    async def save_schedule(self, schedule: ScheduledTask) -> str:
        """Persist (upsert) a scheduled workflow task."""
        db = SessionLocal()
        try:
            record = (
                db.query(WorkflowScheduleRecord)
                .filter(WorkflowScheduleRecord.id == schedule.schedule_id)
                .first()
            )
            if record is None:
                record = WorkflowScheduleRecord(
                    id=schedule.schedule_id,
                    workflow_id=schedule.workflow_id,
                    cron=schedule.cron,
                    next_run=schedule.next_run,
                    enabled=schedule.enabled,
                    params=schedule.params,
                )
                db.add(record)
            else:
                record.workflow_id = schedule.workflow_id
                record.cron = schedule.cron
                record.next_run = schedule.next_run
                record.enabled = schedule.enabled
                record.params = schedule.params
            db.commit()
            logger.debug(
                f"Repository saved workflow schedule {schedule.schedule_id} to database"
            )
            return schedule.schedule_id
        finally:
            db.close()

    async def list_schedules(self, limit: int = 100) -> List[ScheduledTask]:
        """List persisted workflow schedules, soonest ``next_run`` first."""
        db = SessionLocal()
        try:
            rows = (
                db.query(WorkflowScheduleRecord)
                .order_by(
                    WorkflowScheduleRecord.next_run.is_(None),
                    WorkflowScheduleRecord.next_run.asc(),
                )
                .limit(limit)
                .all()
            )
            return [
                ScheduledTask(
                    schedule_id=row.id,
                    workflow_id=row.workflow_id,
                    cron=row.cron,
                    next_run=row.next_run,
                    enabled=row.enabled,
                    params=row.params or {},
                )
                for row in rows
            ]
        finally:
            db.close()


async def get_repository(use_in_memory: bool = False) -> WorkflowRepository:
    """Return repository instance based on configuration."""
    if use_in_memory:
        return InMemoryWorkflowRepository()
    return DatabaseWorkflowRepository()
