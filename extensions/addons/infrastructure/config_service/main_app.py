# -*- coding: utf-8 -*-
"""Config service main FastAPI application."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, WebSocket
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.config_service.config import settings
from services.config_service.health_check import HealthCheckEngine
from services.config_service.metrics import CONFIG_HOT_UPDATES, CONFIG_VERSIONS, CONFIGS_CREATED
from services.config_service.orchestrator import ConfigOrchestrator
from services.config_service.repository import InMemoryConfigRepository
from services.config_service.schemas import (
    ConfigValue,
    ConfigVersion,
    SagaTransaction,
    ServiceHealth,
)

_orchestrator: Optional[ConfigOrchestrator] = None


def get_orchestrator() -> ConfigOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = ConfigOrchestrator(InMemoryConfigRepository(), settings.encryption_key)
    return _orchestrator


app = FastAPI(
    title="Config Service",
    description="Configuration microservice with version control, hot updates, and encryption.",
    version="0.1.0",
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    o = get_orchestrator()
    count = len(await o.repo.list_configs("default"))
    return await HealthCheckEngine().check("config-service", count)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/configs", response_model=ConfigValue)
async def create_config(config: ConfigValue) -> ConfigValue:
    o = get_orchestrator()
    created = await o.create_config(config)
    CONFIGS_CREATED.labels(namespace=created.namespace).inc()
    return created


@app.get("/configs")
async def list_configs(namespace: str = "default", limit: int = 100) -> Dict[str, Any]:
    o = get_orchestrator()
    configs = await o.configs.list(namespace, limit)
    return {"total": len(configs), "items": [c.model_dump() for c in configs]}


@app.post("/configs/snapshots")
async def create_snapshot(namespace: str = "default") -> Dict[str, Any]:
    o = get_orchestrator()
    snapshot = await o.snapshot(namespace)
    return snapshot.model_dump()


@app.post("/configs/snapshots/{snapshot_id}/restore")
async def restore_snapshot(snapshot_id: str) -> Dict[str, Any]:
    o = get_orchestrator()
    restored = await o.restore(snapshot_id)
    return {"restored": len(restored), "ids": restored}


@app.post("/configs/versions")
async def commit_version(namespace: str, message: str, author: str = "system") -> ConfigVersion:
    o = get_orchestrator()
    version = await o.commit_version(namespace, message, author)
    CONFIG_VERSIONS.labels(namespace=version.namespace).inc()
    return version


@app.get("/configs/versions")
async def list_versions(namespace: str = "default", limit: int = 100) -> Dict[str, Any]:
    o = get_orchestrator()
    versions = await o.versions.list(namespace, limit)
    return {"total": len(versions), "items": [v.model_dump() for v in versions]}


@app.get("/configs/{config_id}", response_model=ConfigValue)
async def get_config(config_id: str) -> ConfigValue:
    o = get_orchestrator()
    config = await o.configs.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@app.patch("/configs/{config_id}", response_model=ConfigValue)
async def update_config(config_id: str, value: str, updated_by: str = "system") -> ConfigValue:
    o = get_orchestrator()
    updated = await o.update_config(config_id, value, updated_by)
    if not updated:
        raise HTTPException(status_code=404, detail="Config not found")
    CONFIG_HOT_UPDATES.labels(namespace=updated.namespace).inc()
    return updated


@app.delete("/configs/{config_id}")
async def delete_config(config_id: str) -> Dict[str, Any]:
    o = get_orchestrator()
    success = await o.configs.delete(config_id)
    if not success:
        raise HTTPException(status_code=404, detail="Config not found")
    return {"deleted": True}


@app.get("/namespaces")
async def list_namespaces() -> Dict[str, Any]:
    o = get_orchestrator()
    namespaces = await o.namespaces.list_namespaces()
    return {"namespaces": namespaces}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    o = get_orchestrator()
    await o.hot_updates.subscribe("default", websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"ack: {data}")
    except Exception as e:
        logging.exception("Unexpected exception: %s", e)
        logging.warning("Suppressed exception", exc_info=True)
        pass


@app.post("/sagas")
async def execute_saga(saga: SagaTransaction) -> Dict[str, Any]:
    o = get_orchestrator()
    result = await o.run_saga(saga)
    return result.model_dump()
