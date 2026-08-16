# -*- coding: utf-8 -*-
"""Repair repository abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from loguru import logger

import importlib

import sys

from services.repair_service.schemas import RepairStatus, RepairTask


class RepairRepository(ABC):
    """Abstract repair task repository."""

    @abstractmethod
    async def save(self, task: RepairTask) -> str: ...

    @abstractmethod
    async def get(self, task_id: str) -> Optional[RepairTask]: ...

    @abstractmethod
    async def list(
        self,
        limit: int = 100,
        status: Optional[RepairStatus] = None,
    ) -> List[RepairTask]: ...

    @abstractmethod
    async def update(self, task_id: str, data: Dict[str, Any]) -> bool: ...

    @abstractmethod
    async def delete(self, task_id: str) -> bool: ...

    @abstractmethod
    async def count(self) -> int: ...


# Keep the in-memory repository class stable across module reloads so that
# import-time references and runtime factory instances stay the same object.
_IN_MEMORY_REPO_KEY = "_aiops_repair_inmemory_repo_class"
if _IN_MEMORY_REPO_KEY not in sys.modules:
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

    sys.modules[_IN_MEMORY_REPO_KEY] = InMemoryRepairRepository
else:
    InMemoryRepairRepository = sys.modules[_IN_MEMORY_REPO_KEY]


async def get_repository(use_in_memory: bool = True) -> RepairRepository:
    """Return repository instance based on configuration."""
    return InMemoryRepairRepository()
