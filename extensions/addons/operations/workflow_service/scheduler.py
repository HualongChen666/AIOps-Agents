# -*- coding: utf-8 -*-
"""Task scheduling mechanism (Celery-like abstraction)."""

from __future__ import annotations

import asyncio
import uuid
from collections import deque
from datetime import datetime, timedelta
from typing import Any, Callable, Coroutine, Dict, List

from loguru import logger

from services.workflow_service.metrics import WORKFLOW_SCHEDULED_TASKS
from services.workflow_service.schemas import ScheduledTask, WorkflowRequest, WorkflowTask


class WorkflowScheduler:
    """In-memory scheduler with queue management and periodic polling."""

    def __init__(self, poll_interval: float = 1.0) -> None:
        self.poll_interval = poll_interval
        self._queue: deque[WorkflowRequest] = deque()
        self._schedules: Dict[str, ScheduledTask] = {}
        self._handlers: List[Callable[[WorkflowRequest], Coroutine[Any, Any, WorkflowTask]]] = []
        self._running = False

    def register_handler(
        self,
        handler: Callable[[WorkflowRequest], Coroutine[Any, Any, WorkflowTask]],
    ) -> None:
        self._handlers.append(handler)

    async def enqueue(self, request: WorkflowRequest) -> str:
        self._queue.append(request)
        logger.info(f"Enqueued workflow request {request.workflow_id}")
        return f"SCHEDULED-{uuid.uuid4().hex[:16].upper()}"

    async def schedule(self, schedule: ScheduledTask) -> str:
        schedule.next_run = datetime.utcnow() + timedelta(seconds=1)
        self._schedules[schedule.schedule_id] = schedule
        WORKFLOW_SCHEDULED_TASKS.labels(workflow_id=schedule.workflow_id).set(len(self._schedules))
        return schedule.schedule_id

    async def run_once(self) -> List[WorkflowTask]:
        results: List[WorkflowTask] = []
        now = datetime.utcnow()
        due = [
            s for s in self._schedules.values() if s.enabled and s.next_run and s.next_run <= now
        ]
        for schedule in due:
            for handler in self._handlers:
                request = WorkflowRequest(
                    workflow_id=schedule.workflow_id,
                    params=schedule.params,
                )
                try:
                    result = await handler(request)
                    results.append(result)
                except Exception as exc:
                    logger.error(f"Scheduled workflow {schedule.workflow_id} failed: {exc}")
            schedule.next_run = now + timedelta(seconds=10)

        while self._queue:
            request = self._queue.popleft()
            for handler in self._handlers:
                try:
                    result = await handler(request)
                    results.append(result)
                except Exception as exc:
                    logger.error(f"Queued workflow {request.workflow_id} failed: {exc}")

        return results

    async def start(self) -> None:
        self._running = True
        while self._running:
            await self.run_once()
            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False
