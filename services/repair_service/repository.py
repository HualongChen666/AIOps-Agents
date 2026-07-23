# -*- coding: utf-8 -*-
"""Repair repository abstraction."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

from services.repair_service.schemas import RepairStatus, RepairTask


class RepairRepository:
    """Abstract repair task repository."""

    async def save(self, task: RepairTask) -> str:
        raise NotImplementedError

    async def get(self, task_id: str) -> Optional[RepairTask]:
        raise NotImplementedError

    async def list(
        self,
        limit: int = 100,
        status: Optional[RepairStatus] = None,
    ) -> List[RepairTask]:
        raise NotImplementedError

    async def update(self, task_id: str, data: Dict[str, Any]) -> bool:
        raise NotImplementedError

    async def delete(self, task_id: str) -> bool:
        raise NotImplementedError

    async def count(self) -> int:
        raise NotImplementedError


class InMemoryRepairRepository(RepairRepository):
    """In-memory repository for tests and local dev."""

    def __init__(self) -> None:
        self._tasks: Dict[str, RepairTask] = {}

    async def save(self, task: RepairTask) -> str:
        if not task.task_id:
            task.task_id = f"REPAIR-{datetime.utcnow().timestamp()}"
        self._tasks[task.task_id] = task
        logger.debug(f"Repository saved repair task {task.task_id}")
        return task.task_id

    async def get(self, task_id: str) -> Optional[RepairTask]:
        return self._tasks.get(task_id)

    async def list(
        self,
        limit: int = 100,
        status: Optional[RepairStatus] = None,
    ) -> List[RepairTask]:
        tasks = list(self._tasks.values())
        if status:
            tasks = [t for t in tasks if t.status == status]
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    async def update(self, task_id: str, data: Dict[str, Any]) -> bool:
        task = self._tasks.get(task_id)
        if not task:
            return False
        merged = task.model_dump() | data
        self._tasks[task_id] = RepairTask.model_validate(merged)
        self._tasks[task_id].updated_at = datetime.utcnow()
        return True

    async def count(self) -> int:
        return len(self._tasks)

    async def delete(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False


async def get_repository(use_in_memory: bool = True) -> RepairRepository:
    """Return repository instance based on configuration."""
    return InMemoryRepairRepository()
