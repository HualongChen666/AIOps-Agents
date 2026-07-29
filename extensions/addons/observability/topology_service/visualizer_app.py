# -*- coding: utf-8 -*-
"""Topology visualizer microservice."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.topology_service.config import settings
from services.topology_service.health_check import HealthCheckEngine
from services.topology_service.realtime import RealtimeTopologyManager
from services.topology_service.repository import get_repository
from services.topology_service.schemas import ServiceHealth, VisualizationConfig
from services.topology_service.visualization import TopologyVisualizer


class TopologyVisualizerApp:
    """Container for topology visualizer components."""

    def __init__(self) -> None:
        self.repo: Any = None
        self.visualizer = TopologyVisualizer()
        self.realtime = RealtimeTopologyManager()
        self.health = HealthCheckEngine()

    async def init(self) -> None:
        self.repo = await get_repository(settings.use_in_memory)

    async def visualize(
        self,
        topology_id: str,
        config: Optional[VisualizationConfig],
    ) -> Dict[str, Any]:
        topology = await self.repo.get(topology_id)
        if not topology:
            return {"error": "topology not found"}
        result = await self.visualizer.generate(topology, config)
        return result.model_dump()


visualizer_app: Optional[TopologyVisualizerApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global visualizer_app
    visualizer_app = TopologyVisualizerApp()
    await visualizer_app.init()
    logger.info("Topology visualizer started")
    yield
    logger.info("Topology visualizer stopped")


app = FastAPI(
    title="Topology Visualizer",
    description="Generates D3.js visualizations and real-time topology updates.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    v = cast(TopologyVisualizerApp, visualizer_app)
    count = await v.repo.count()
    return ServiceHealth(status="ok", service="topology-visualizer", topology_count=count)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/topologies/{topology_id}/visualize")
async def visualize_topology(
    topology_id: str,
    config: Optional[VisualizationConfig] = None,
) -> Dict[str, Any]:
    v = cast(TopologyVisualizerApp, visualizer_app)
    return await v.visualize(topology_id, config)


@app.websocket("/ws/topologies/{topology_id}")
async def topology_websocket(websocket: WebSocket, topology_id: str):
    v = cast(TopologyVisualizerApp, visualizer_app)
    await websocket.accept()
    queue = await v.realtime.connect()
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
    except WebSocketDisconnect:
        await v.realtime.disconnect(queue)
