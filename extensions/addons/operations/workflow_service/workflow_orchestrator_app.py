# -*- coding: utf-8 -*-
"""Workflow orchestrator FastAPI microservice."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from .config import settings
from .health_check import HealthCheckEngine
from .orchestrator import WorkflowOrchestrator
from .repository import get_repository
from .schemas import (
    ServiceHealth,
    WorkflowDefinition,
    WorkflowRequest,
    WorkflowTemplate,
)
from .templates import TemplateManager


class WorkflowOrchestratorApp:
    """Container for workflow orchestrator components."""

    def __init__(self) -> None:
        self.repo: Any = None
        self.orchestrator: Optional[WorkflowOrchestrator] = None
        self.templates = TemplateManager()
        self.health = HealthCheckEngine()

    async def init(self) -> None:
        self.repo = await get_repository(settings.use_in_memory)
        self.orchestrator = WorkflowOrchestrator(self.repo)

    async def create_definition(self, definition: WorkflowDefinition) -> Dict[str, Any]:
        await self.repo.save_definition(definition)
        return {"workflow_id": definition.workflow_id, "status": "created"}

    async def start_workflow(self, request: WorkflowRequest) -> Dict[str, Any]:
        if not self.orchestrator:
            raise RuntimeError("Orchestrator not initialized")
        task = await self.orchestrator.create_task(request)
        result = await self.orchestrator.execute(task)
        return result.model_dump()


orchestrator_app: Optional[WorkflowOrchestratorApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator_app
    orchestrator_app = WorkflowOrchestratorApp()
    await orchestrator_app.init()
    logger.info("Workflow orchestrator started")
    yield
    logger.info("Workflow orchestrator stopped")


app = FastAPI(
    title="Workflow Orchestrator",
    description="Orchestrates workflow execution with scheduling, state machines, and retries.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    o = cast(WorkflowOrchestratorApp, orchestrator_app)
    count = len(await o.repo.list_tasks())
    return await o.health.check("workflow-orchestrator", count)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/workflows/definitions")
async def create_definition(definition: WorkflowDefinition) -> Dict[str, Any]:
    o = cast(WorkflowOrchestratorApp, orchestrator_app)
    return await o.create_definition(definition)


@app.get("/workflows/definitions")
async def list_definitions(limit: int = 100) -> Dict[str, Any]:
    o = cast(WorkflowOrchestratorApp, orchestrator_app)
    items = await o.repo.list_definitions(limit=limit)
    return {"total": len(items), "items": [d.model_dump() for d in items]}


@app.post("/workflows/execute")
async def execute_workflow(request: WorkflowRequest) -> Dict[str, Any]:
    o = cast(WorkflowOrchestratorApp, orchestrator_app)
    return await o.start_workflow(request)


@app.get("/workflows/executions")
async def list_executions(limit: int = 100) -> Dict[str, Any]:
    o = cast(WorkflowOrchestratorApp, orchestrator_app)
    items = await o.repo.list_tasks(limit=limit)
    return {"total": len(items), "items": [t.model_dump() for t in items]}


@app.post("/workflows/templates")
async def create_template(template: WorkflowTemplate) -> Dict[str, Any]:
    o = cast(WorkflowOrchestratorApp, orchestrator_app)
    await o.templates.register(template)
    return {"template_id": template.template_id, "status": "created"}


@app.post("/workflows/templates/{template_id}/render")
async def render_template(
    template_id: str,
    params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    o = cast(WorkflowOrchestratorApp, orchestrator_app)
    output = await o.templates.render(template_id, params)
    return {"template_id": template_id, "rendered": output}
