# -*- coding: utf-8 -*-
"""FastAPI application for the Plugin microservice.

Exposes the :class:`services.plugin_service.service.PluginService` business
logic over HTTP, together with health, Prometheus metrics and a lightweight
RPC surface. Mirrors the structure of ``services/audit_service/main_app.py``.
"""

from __future__ import annotations

import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

from fastapi import Body, Depends, FastAPI, HTTPException, Query
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy.orm import Session
from starlette.responses import Response

from core.models import PluginStatus as CorePluginStatus
from services.plugin_service.config import settings
from services.plugin_service.db import get_db, get_engine
from services.plugin_service.grpc.server import PluginRPCServer
from services.plugin_service.health_check import HealthCheckEngine
from services.plugin_service.metrics import (
    PLUGIN_CONFIG_MUTATIONS,
    PLUGIN_EXECUTION_DURATION,
    PLUGIN_EXECUTIONS,
    PLUGINS_CREATED,
    PLUGINS_DELETED,
    PLUGINS_REGISTERED,
    PLUGINS_UPDATED,
)
from services.plugin_service.saga import PluginSaga
from services.plugin_service.schemas import (
    PluginConfigCreate,
    PluginConfigResponse,
    PluginConfigUpdate,
    PluginCreate,
    PluginExecutionCreate,
    PluginExecutionListResponse,
    PluginExecutionResponse,
    PluginListResponse,
    PluginResponse,
    PluginRunRequest,
    PluginRunResponse,
    PluginStatsResponse,
    PluginUpdate,
)
from services.plugin_service.service import PluginService

_rpc_server = PluginRPCServer()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise the database (fail fast) and register RPC handlers."""
    get_engine()
    logger.info(
        f"plugin-service started (database={settings.database_url if not settings.use_in_memory else 'sqlite://memory'})"
    )
    yield
    logger.info("plugin-service shutting down")


app = FastAPI(
    title="Plugin Service",
    description="Plugin microservice for registration, execution tracking and configuration.",
    version="1.0.0",
    lifespan=lifespan,
)


def get_service(db: Session = Depends(get_db)) -> PluginService:
    """FastAPI dependency building a request-scoped :class:`PluginService`."""
    return PluginService(db)


# ---------------------------------------------------------------------------
# Health / metrics
# ---------------------------------------------------------------------------
@app.get("/health")
async def health(service: PluginService = Depends(get_service)) -> Dict[str, Any]:
    """Report service health plus the number of registered plugins."""
    db_label = "sqlite-memory" if settings.use_in_memory else "postgresql"
    total = service.count_plugins()
    payload = await HealthCheckEngine().check(settings.service_name, total, db_label)
    return payload.model_dump()


@app.get("/metrics")
async def metrics() -> Response:
    """Expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/stats", response_model=PluginStatsResponse)
async def stats(service: PluginService = Depends(get_service)) -> PluginStatsResponse:
    """Aggregate plugin/execution counters."""
    return service.get_stats()


# ---------------------------------------------------------------------------
# Plugin CRUD
# ---------------------------------------------------------------------------
@app.post("/plugins", response_model=PluginResponse, status_code=201)
async def create_plugin(
    plugin_data: PluginCreate,
    created_by: Optional[str] = Query(None, description="Operator creating the plugin"),
    service: PluginService = Depends(get_service),
) -> PluginResponse:
    """Register a new plugin."""
    created = service.create_plugin(plugin_data, created_by=created_by)
    PLUGINS_CREATED.labels(plugin_type=plugin_data.plugin_type.value).inc()
    return created


@app.get("/plugins", response_model=PluginListResponse)
async def list_plugins(
    status: Optional[str] = Query(None, description="Filter by plugin status"),
    plugin_type: Optional[str] = Query(None, description="Filter by plugin type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: PluginService = Depends(get_service),
) -> PluginListResponse:
    """List plugins with optional filters."""
    status_enum: Optional[CorePluginStatus] = None
    if status:
        try:
            status_enum = CorePluginStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=f"Unknown status: {status}") from exc

    items = service.list_plugins(status=status_enum, plugin_type=plugin_type, limit=limit, offset=offset)
    return PluginListResponse(total=service.count_plugins(status=status_enum), plugins=items)


@app.get("/plugins/by-name/{name}", response_model=PluginResponse)
async def get_plugin_by_name(
    name: str,
    service: PluginService = Depends(get_service),
) -> PluginResponse:
    """Look up a plugin by its unique name."""
    plugin = service.get_plugin_by_name(name)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {name}")
    return plugin


@app.get("/plugins/{plugin_id}", response_model=PluginResponse)
async def get_plugin(
    plugin_id: str,
    service: PluginService = Depends(get_service),
) -> PluginResponse:
    """Fetch a plugin by id."""
    plugin = service.get_plugin(plugin_id)
    if plugin is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")
    return plugin


@app.put("/plugins/{plugin_id}", response_model=PluginResponse)
async def update_plugin(
    plugin_id: str,
    plugin_data: PluginUpdate,
    service: PluginService = Depends(get_service),
) -> PluginResponse:
    """Update mutable plugin fields."""
    updated = service.update_plugin(plugin_id, plugin_data)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")
    PLUGINS_UPDATED.inc()
    return updated


@app.delete("/plugins/{plugin_id}")
async def delete_plugin(
    plugin_id: str,
    service: PluginService = Depends(get_service),
) -> Dict[str, Any]:
    """Delete a plugin."""
    if not service.delete_plugin(plugin_id):
        raise HTTPException(status_code=404, detail=f"Plugin not found: {plugin_id}")
    PLUGINS_DELETED.inc()
    return {"plugin_id": plugin_id, "status": "deleted"}


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------
@app.post("/plugins/{name}/run", response_model=PluginRunResponse)
async def run_plugin(
    name: str,
    run_request: PluginRunRequest,
    executed_by: Optional[str] = Query(None),
    service: PluginService = Depends(get_service),
) -> PluginRunResponse:
    """Execute a registered plugin and persist the execution record."""
    start = time.monotonic()
    try:
        result = service.run_plugin(name, run_request, executed_by=executed_by)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    elapsed = time.monotonic() - start
    PLUGIN_EXECUTION_DURATION.labels(plugin=name).observe(elapsed)
    PLUGIN_EXECUTIONS.labels(plugin=name, outcome="success" if result.success else "failure").inc()
    return result


@app.post("/executions", response_model=PluginExecutionResponse, status_code=201)
async def create_execution(
    execution_data: PluginExecutionCreate,
    executed_by: Optional[str] = Query(None),
    service: PluginService = Depends(get_service),
) -> PluginExecutionResponse:
    """Record a plugin execution."""
    return service.create_execution(execution_data, executed_by=executed_by)


@app.get("/executions", response_model=PluginExecutionListResponse)
async def list_executions(
    plugin_id: Optional[str] = Query(None),
    plugin_name: Optional[str] = Query(None),
    success: Optional[bool] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    service: PluginService = Depends(get_service),
) -> PluginExecutionListResponse:
    """List plugin executions with optional filters."""
    items = service.list_executions(
        plugin_id=plugin_id, plugin_name=plugin_name, success=success, limit=limit, offset=offset
    )
    return PluginExecutionListResponse(
        total=service.count_executions(plugin_id=plugin_id, success=success),
        executions=items,
    )


@app.get("/executions/{execution_id}", response_model=PluginExecutionResponse)
async def get_execution(
    execution_id: str,
    service: PluginService = Depends(get_service),
) -> PluginExecutionResponse:
    """Fetch a single execution record."""
    execution = service.get_execution(execution_id)
    if execution is None:
        raise HTTPException(status_code=404, detail=f"Execution not found: {execution_id}")
    return execution


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@app.post("/configs", response_model=PluginConfigResponse, status_code=201)
async def create_config(
    config_data: PluginConfigCreate,
    updated_by: Optional[str] = Query(None),
    service: PluginService = Depends(get_service),
) -> PluginConfigResponse:
    """Create a plugin configuration."""
    created = service.create_config(config_data, updated_by=updated_by)
    PLUGIN_CONFIG_MUTATIONS.labels(operation="create").inc()
    return created


@app.get("/configs/by-plugin/{plugin_id}", response_model=PluginConfigResponse)
async def get_config_by_plugin(
    plugin_id: str,
    service: PluginService = Depends(get_service),
) -> PluginConfigResponse:
    """Fetch the configuration attached to a plugin."""
    config = service.get_config_by_plugin_id(plugin_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"No config for plugin: {plugin_id}")
    return config


@app.get("/configs/{config_id}", response_model=PluginConfigResponse)
async def get_config(
    config_id: str,
    service: PluginService = Depends(get_service),
) -> PluginConfigResponse:
    """Fetch a configuration by id."""
    config = service.get_config(config_id)
    if config is None:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    return config


@app.put("/configs/{config_id}", response_model=PluginConfigResponse)
async def update_config(
    config_id: str,
    config_data: PluginConfigUpdate,
    updated_by: Optional[str] = Query(None),
    service: PluginService = Depends(get_service),
) -> PluginConfigResponse:
    """Update a plugin configuration (bumps its version)."""
    updated = service.update_config(config_id, config_data, updated_by=updated_by)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    PLUGIN_CONFIG_MUTATIONS.labels(operation="update").inc()
    return updated


@app.delete("/configs/{config_id}")
async def delete_config(
    config_id: str,
    service: PluginService = Depends(get_service),
) -> Dict[str, Any]:
    """Delete a plugin configuration."""
    if not service.delete_config(config_id):
        raise HTTPException(status_code=404, detail=f"Config not found: {config_id}")
    PLUGIN_CONFIG_MUTATIONS.labels(operation="delete").inc()
    return {"config_id": config_id, "status": "deleted"}


# ---------------------------------------------------------------------------
# RPC surface
# ---------------------------------------------------------------------------
@app.post("/rpc/{method}")
async def rpc_call(method: str, payload: Dict[str, Any] = Body(default={})) -> Dict[str, Any]:
    """Dispatch a registered RPC method."""
    try:
        result = await _rpc_server.call(method, **payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"method": method, "result": result}


@app.get("/rpc")
async def rpc_methods() -> Dict[str, List[str]]:
    """List the registered RPC methods."""
    return {"methods": _rpc_server.list_methods()}


@app.post("/sagas/plugin-registration")
async def run_registration_saga(
    plugin_data: PluginCreate,
    service: PluginService = Depends(get_service),
) -> Dict[str, Any]:
    """Register a plugin and its configuration inside a single saga.

    If persisting the configuration fails, the plugin row created by the first
    step is removed again so no partial state is left behind.
    """
    created: Dict[str, Any] = {}

    async def register() -> str:
        response = service.create_plugin(plugin_data, created_by="saga")
        created["id"] = response.id
        return response.id

    async def compensate_register() -> None:
        plugin_id = created.get("id")
        if plugin_id:
            service.delete_plugin(plugin_id)

    async def persist_config() -> str:
        plugin_id = created["id"]
        config = service.create_config(
            PluginConfigCreate(
                plugin_id=plugin_id,
                plugin_name=plugin_data.name,
                config_data=plugin_data.default_config or {},
                description="Default configuration created with the plugin",
            ),
            updated_by="saga",
        )
        return config.id

    async def compensate_config() -> None:
        plugin_id = created.get("id")
        if not plugin_id:
            return
        existing = service.get_config_by_plugin_id(plugin_id)
        if existing is not None:
            service.delete_config(existing.id)

    saga = PluginSaga(saga_id=plugin_data.name)
    saga.add_step("register-plugin", register, compensate_register)
    saga.add_step("persist-config", persist_config, compensate_config)
    await saga.execute()

    PLUGINS_REGISTERED.labels(status=saga.status).inc()
    return {
        "saga_id": saga.saga_id,
        "status": saga.status,
        "error": saga.error,
        "results": saga.results,
    }
