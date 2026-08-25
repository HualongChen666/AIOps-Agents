# -*- coding: utf-8 -*-
"""Workflow repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from extensions.addons.operations.workflow_service.schemas import (
    ScheduledTask,
    WorkflowDefinition,
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


async def get_repository(use_in_memory: bool = True) -> WorkflowRepository:
    """Return repository instance based on configuration."""
    return InMemoryWorkflowRepository()
