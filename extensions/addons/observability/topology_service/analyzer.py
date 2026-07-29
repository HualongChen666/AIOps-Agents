# -*- coding: utf-8 -*-
"""Topology analyzer microservice."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.topology_service.config import settings
from services.topology_service.dependency import DependencyGraph, DependencyModelingEngine
from services.topology_service.health_check import HealthCheckEngine
from services.topology_service.impact import ImpactAnalyzer
from services.topology_service.repository import get_repository
from services.topology_service.schemas import DependencyRequest, ImpactRequest, ServiceHealth


class TopologyAnalyzerApp:
    """Container for topology analyzer components."""

    def __init__(self) -> None:
        self.repo: Any = None
        self.graph = DependencyGraph()
        self.modeling = DependencyModelingEngine(self.graph)
        self.impact_analyzer = ImpactAnalyzer(self.graph)
        self.health = HealthCheckEngine()

    async def init(self) -> None:
        self.repo = await get_repository(settings.use_in_memory)

    async def dependencies(self, topology_id: str, request: DependencyRequest) -> Dict[str, Any]:
        topology = await self.repo.get(topology_id)
        if not topology:
            return {"error": "topology not found"}
        await self.modeling.model_dependencies(topology)
        return {
            "topology_id": topology_id,
            "service": request.service_name,
            "dependencies": self.graph.get_dependencies(
                request.service_name,
                request.dependency_type,
                request.depth,
            ),
        }

    async def analyze_impact(self, topology_id: str, request: ImpactRequest) -> Dict[str, Any]:
        topology = await self.repo.get(topology_id)
        if not topology:
            return {"error": "topology not found"}
        await self.modeling.model_dependencies(topology)
        result = await self.impact_analyzer.analyze(request)
        return result.model_dump()


analyzer_app: Optional[TopologyAnalyzerApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global analyzer_app
    analyzer_app = TopologyAnalyzerApp()
    await analyzer_app.init()
    logger.info("Topology analyzer started")
    yield
    logger.info("Topology analyzer stopped")


app = FastAPI(
    title="Topology Analyzer",
    description="Analyzes service dependencies and impact.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    a = cast(TopologyAnalyzerApp, analyzer_app)
    count = await a.repo.count()
    return ServiceHealth(status="ok", service="topology-analyzer", topology_count=count)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/topologies/{topology_id}/dependencies")
async def get_dependencies(topology_id: str, request: DependencyRequest) -> Dict[str, Any]:
    a = cast(TopologyAnalyzerApp, analyzer_app)
    return await a.dependencies(topology_id, request)


@app.post("/topologies/{topology_id}/impact")
async def get_impact(topology_id: str, request: ImpactRequest) -> Dict[str, Any]:
    a = cast(TopologyAnalyzerApp, analyzer_app)
    return await a.analyze_impact(topology_id, request)
