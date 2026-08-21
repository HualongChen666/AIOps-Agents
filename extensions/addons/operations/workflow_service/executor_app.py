# -*- coding: utf-8 -*-
"""Workflow executor FastAPI microservice."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .config import settings
from .health_check import HealthCheckEngine
from .metrics import WORKFLOW_ACTIVE_EXECUTIONS
from .orchestrator import WorkflowOrchestrator
from .repository import get_repository
from .schemas import ServiceHealth, WorkflowRequest


class WorkflowExecutorApp:
    """Container for workflow executor components."""

    def __init__(self) -> None:
        self.repo: Any = None
        self.orchestrator: Optional[WorkflowOrchestrator] = None
        self.health = HealthCheckEngine()

    async def init(self) -> None:
        self.repo = await get_repository(settings.use_in_memory)
        self.orchestrator = WorkflowOrchestrator(self.repo)

    async def execute(self, request: WorkflowRequest) -> Dict[str, Any]:
        if self.orchestrator is None:
            raise RuntimeError("Executor not initialized")
        WORKFLOW_ACTIVE_EXECUTIONS.inc()
        try:
            task = await self.orchestrator.create_task(request)
            result = await self.orchestrator.execute(task)
            return result.model_dump()
        finally:
            WORKFLOW_ACTIVE_EXECUTIONS.dec()


executor_app: Optional[WorkflowExecutorApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global executor_app
    executor_app = WorkflowExecutorApp()
    await executor_app.init()
    logger.info("Workflow executor started")
    yield
    logger.info("Workflow executor stopped")


app = FastAPI(
    title="Workflow Executor",
    description="Executes workflows with monitoring and retry.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    e = cast(WorkflowExecutorApp, executor_app)
    count = len(await e.repo.list_tasks())
    return await e.health.check("workflow-executor", count)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/workflows/execute")
async def execute_workflow(request: WorkflowRequest) -> Dict[str, Any]:
    e = cast(WorkflowExecutorApp, executor_app)
    if e.orchestrator is None:
        raise RuntimeError("Executor not initialized")
    return await e.execute(request)
