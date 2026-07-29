# -*- coding: utf-8 -*-
"""Workflow scheduler FastAPI microservice."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.workflow_service.config import settings
from services.workflow_service.health_check import HealthCheckEngine
from services.workflow_service.orchestrator import WorkflowOrchestrator
from services.workflow_service.repository import get_repository
from services.workflow_service.scheduler import WorkflowScheduler
from services.workflow_service.schemas import ScheduledTask, ServiceHealth


class WorkflowSchedulerApp:
    """Container for workflow scheduler components."""

    def __init__(self) -> None:
        self.repo: Any = None
        self.scheduler: Optional[WorkflowScheduler] = None
        self.orchestrator: Optional[WorkflowOrchestrator] = None
        self.health = HealthCheckEngine()

    async def init(self) -> None:
        self.repo = await get_repository(settings.use_in_memory)
        self.scheduler = WorkflowScheduler(poll_interval=settings.scheduler_poll_interval_seconds)
        self.orchestrator = WorkflowOrchestrator(self.repo)
        self.scheduler.register_handler(self._handle_request)

    async def _handle_request(self, request: Any) -> Any:
        if self.orchestrator is None:
            raise RuntimeError("Scheduler not initialized")
        return await self.orchestrator.create_task(request)


scheduler_app_instance: Optional[WorkflowSchedulerApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler_app_instance
    scheduler_app_instance = WorkflowSchedulerApp()
    await scheduler_app_instance.init()
    logger.info("Workflow scheduler started")
    yield
    logger.info("Workflow scheduler stopped")


app = FastAPI(
    title="Workflow Scheduler",
    description="Schedules and queues workflow tasks.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    s = cast(WorkflowSchedulerApp, scheduler_app_instance)
    count = len(await s.repo.list_tasks())
    return await s.health.check("workflow-scheduler", count)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/workflows/schedule")
async def schedule_workflow(schedule: ScheduledTask) -> Dict[str, Any]:
    s = cast(WorkflowSchedulerApp, scheduler_app_instance)
    if s.scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    schedule_id = await s.scheduler.schedule(schedule)
    return {"schedule_id": schedule_id}


@app.post("/workflows/queue")
async def enqueue_workflow(request: Any) -> Dict[str, Any]:
    s = cast(WorkflowSchedulerApp, scheduler_app_instance)
    if s.scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    queued_id = await s.scheduler.enqueue(request)
    return {"queued_id": queued_id}


@app.post("/workflows/run-once")
async def run_scheduler_once() -> Dict[str, Any]:
    s = cast(WorkflowSchedulerApp, scheduler_app_instance)
    if s.scheduler is None:
        raise RuntimeError("Scheduler not initialized")
    results = await s.scheduler.run_once()
    return {"triggered": len(results)}
