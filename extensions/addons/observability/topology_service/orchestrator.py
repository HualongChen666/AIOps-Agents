# -*- coding: utf-8 -*-
"""Topology orchestrator microservice."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, Dict, Optional, cast

from fastapi import FastAPI
from loguru import logger
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.topology_service.config import settings
from services.topology_service.health_check import HealthCheckEngine
from services.topology_service.repository import get_repository
from services.topology_service.schemas import (
    DiscoveryRequest,
    ImpactRequest,
    ServiceHealth,
    VisualizationConfig,
)


class TopologyOrchestratorApp:
    """Container for topology orchestrator components."""

    def __init__(self) -> None:
        self.repo: Any = None
        self.discovery: Any = None
        self.graph: Any = None
        self.impact: Any = None
        self.visualizer: Any = None
        self.versioning: Any = None
        self.audit: Any = None
        self.realtime: Any = None
        self.saga: Any = None
        self.health = HealthCheckEngine()

    async def init(self) -> None:
        from services.topology_service.audit import TopologyAuditStore
        from services.topology_service.dependency import DependencyGraph, DependencyModelingEngine
        from services.topology_service.discovery import TopologyDiscoveryEngine
        from services.topology_service.impact import ImpactAnalyzer
        from services.topology_service.realtime import RealtimeTopologyManager
        from services.topology_service.versioning import TopologyVersionManager
        from services.topology_service.visualization import TopologyVisualizer

        self.repo = await get_repository(settings.use_in_memory)
        self.discovery = TopologyDiscoveryEngine()
        self.graph = DependencyModelingEngine(DependencyGraph())
        self.impact = ImpactAnalyzer(self.graph.graph)
        self.visualizer = TopologyVisualizer()
        self.versioning = TopologyVersionManager()
        self.audit = TopologyAuditStore()
        self.realtime = RealtimeTopologyManager()

    async def discover(self, request: DiscoveryRequest) -> Dict[str, Any]:
        topology = await self.discovery.discover(request)
        await self.repo.save(topology)
        await self.graph.model_dependencies(topology)
        await self.audit.record(
            topology.topology_id,
            "discovered",
            request.requested_by,
            {"node_count": len(topology.nodes), "edge_count": len(topology.edges)},
        )
        return cast(Dict[str, Any], topology.model_dump())

    async def analyze_impact(self, topology_id: str, request: ImpactRequest) -> Dict[str, Any]:
        topology = await self.repo.get(topology_id)
        if not topology:
            return {"error": "topology not found"}
        await self.graph.model_dependencies(topology)
        result = await self.impact.analyze(request)
        await self.audit.record(
            topology_id,
            "impact_analyzed",
            "system",
            {"changed_nodes": request.changed_nodes, "impact_score": result.impact_score},
        )
        return cast(Dict[str, Any], result.model_dump())

    async def visualize(
        self,
        topology_id: str,
        config: Optional[VisualizationConfig],
    ) -> Dict[str, Any]:
        topology = await self.repo.get(topology_id)
        if not topology:
            return {"error": "topology not found"}
        result = await self.visualizer.generate(topology, config)
        return cast(Dict[str, Any], result.model_dump())


orchestrator_app: Optional[TopologyOrchestratorApp] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator_app
    orchestrator_app = TopologyOrchestratorApp()
    await orchestrator_app.init()
    logger.info("Topology orchestrator started")
    yield
    logger.info("Topology orchestrator stopped")


app = FastAPI(
    title="Topology Orchestrator",
    description="Discovers service topology and coordinates analysis.",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    o = cast(TopologyOrchestratorApp, orchestrator_app)
    count = await o.repo.count()
    return ServiceHealth(status="ok", service="topology-orchestrator", topology_count=count)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/topologies")
async def create_topology(request: DiscoveryRequest) -> Dict[str, Any]:
    o = cast(TopologyOrchestratorApp, orchestrator_app)
    return await o.discover(request)


@app.get("/topologies")
async def list_topologies(limit: int = 100) -> Dict[str, Any]:
    o = cast(TopologyOrchestratorApp, orchestrator_app)
    items = await o.repo.list(limit=limit)
    return {"total": len(items), "items": [t.model_dump() for t in items]}


@app.get("/topologies/{topology_id}")
async def get_topology(topology_id: str) -> Dict[str, Any]:
    o = cast(TopologyOrchestratorApp, orchestrator_app)
    topology = await o.repo.get(topology_id)
    if not topology:
        return {"error": "topology not found"}
    return cast(Dict[str, Any], topology.model_dump())


@app.post("/topologies/{topology_id}/impact")
async def analyze_topology_impact(topology_id: str, request: ImpactRequest) -> Dict[str, Any]:
    o = cast(TopologyOrchestratorApp, orchestrator_app)
    return await o.analyze_impact(topology_id, request)


@app.post("/topologies/{topology_id}/visualize")
async def visualize_topology(
    topology_id: str,
    config: Optional[VisualizationConfig] = None,
) -> Dict[str, Any]:
    o = cast(TopologyOrchestratorApp, orchestrator_app)
    return await o.visualize(topology_id, config)


@app.post("/topologies/{topology_id}/version")
async def commit_topology_version(
    topology_id: str,
    message: str = "Topology snapshot",
) -> Dict[str, Any]:
    o = cast(TopologyOrchestratorApp, orchestrator_app)
    topology = await o.repo.get(topology_id)
    if not topology:
        return {"error": "topology not found"}
    version = await o.versioning.commit(topology, message)
    return cast(Dict[str, Any], version.model_dump())
