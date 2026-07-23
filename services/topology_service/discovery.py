# -*- coding: utf-8 -*-
"""Service topology discovery based on configuration and API calls."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List

from loguru import logger

from services.topology_service.metrics import (
    TOPOLOGY_ACTIVE_DISCOVERIES,
    TOPOLOGY_DISCOVERED_EDGES,
    TOPOLOGY_DISCOVERED_NODES,
    TOPOLOGY_DISCOVERY_DURATION,
)
from services.topology_service.schemas import (
    DiscoveryRequest,
    ServiceTopology,
    TopologyEdge,
    TopologyNode,
    TopologyStatus,
)

# Built-in topology catalogue for config-based discovery
DEFAULT_TOPOLOGY_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "core": [
        {"node_id": "agent", "name": "Agent", "node_type": "service"},
        {"node_id": "collect", "name": "Collector", "node_type": "service"},
        {"node_id": "process", "name": "Processor", "node_type": "service"},
        {"node_id": "store", "name": "Data Store", "node_type": "database"},
    ],
    "ai": [
        {"node_id": "ai-router", "name": "AI Router", "node_type": "service"},
        {"node_id": "llm-1", "name": "LLM Provider 1", "node_type": "external"},
        {"node_id": "llm-2", "name": "LLM Provider 2", "node_type": "external"},
    ],
    "api": [
        {"node_id": "api-gateway", "name": "API Gateway", "node_type": "load_balancer"},
        {"node_id": "auth", "name": "Auth Service", "node_type": "service"},
        {"node_id": "metrics", "name": "Metrics Service", "node_type": "service"},
    ],
}

DEFAULT_EDGES: List[Dict[str, Any]] = [
    {"source": "agent", "target": "collect", "edge_type": "calls"},
    {"source": "collect", "target": "process", "edge_type": "publishes_to"},
    {"source": "process", "target": "store", "edge_type": "depends_on"},
    {"source": "api-gateway", "target": "auth", "edge_type": "calls"},
    {"source": "api-gateway", "target": "metrics", "edge_type": "calls"},
    {"source": "ai-router", "target": "llm-1", "edge_type": "calls"},
    {"source": "ai-router", "target": "llm-2", "edge_type": "calls"},
]


class TopologyDiscoveryEngine:
    """Discover service topology from config catalog or API calls."""

    def __init__(self, api_client: Any = None) -> None:
        self.api_client = api_client

    async def discover(
        self,
        request: DiscoveryRequest,
    ) -> ServiceTopology:
        """Run topology discovery based on request source and scope."""
        TOPOLOGY_ACTIVE_DISCOVERIES.inc()
        start = time.perf_counter()
        try:
            topology = ServiceTopology(
                topology_id=f"TOPO-{uuid.uuid4().hex[:16].upper()}",
                status=TopologyStatus.DISCOVERING,
            )

            if request.source == "api" and self.api_client:
                nodes, edges = await self._discover_from_api(request)
            else:
                nodes, edges = await self._discover_from_config(request)

            topology.nodes = nodes
            topology.edges = edges
            topology.status = TopologyStatus.DISCOVERED
            topology.metadata = {
                "source": request.source,
                "scope": request.scope,
                "requested_by": request.requested_by,
            }

            duration = time.perf_counter() - start
            TOPOLOGY_DISCOVERY_DURATION.labels(source=request.source).observe(duration)
            TOPOLOGY_DISCOVERED_NODES.labels(source=request.source).inc(len(nodes))
            TOPOLOGY_DISCOVERED_EDGES.labels(source=request.source).inc(len(edges))

            return topology
        finally:
            TOPOLOGY_ACTIVE_DISCOVERIES.dec()

    async def _discover_from_config(
        self,
        request: DiscoveryRequest,
    ) -> tuple[List[TopologyNode], List[TopologyEdge]]:
        """Discover topology from built-in configuration catalog."""
        await asyncio.sleep(0.001)
        scope = request.scope.lower()
        raw_nodes: List[Dict[str, Any]] = []
        if scope == "all":
            for group in DEFAULT_TOPOLOGY_CATALOG.values():
                raw_nodes.extend(group)
        else:
            raw_nodes = DEFAULT_TOPOLOGY_CATALOG.get(scope, [])

        nodes = [TopologyNode(**n) for n in raw_nodes]
        node_ids = {n.node_id for n in nodes}

        edges = []
        for e in DEFAULT_EDGES:
            if e["source"] in node_ids and e["target"] in node_ids:
                edges.append(TopologyEdge(**e))

        logger.info(f"Discovered {len(nodes)} nodes and {len(edges)} edges from config")
        return nodes, edges

    async def _discover_from_api(
        self,
        request: DiscoveryRequest,
    ) -> tuple[List[TopologyNode], List[TopologyEdge]]:
        """Discover topology from external API; falls back to config if unavailable."""
        if not self.api_client:
            logger.warning("No API client configured; falling back to config discovery")
            return await self._discover_from_config(request)
        try:
            result = await self.api_client.fetch_topology(request.scope, request.filters)
            nodes = [TopologyNode(**n) for n in result.get("nodes", [])]
            edges = [TopologyEdge(**e) for e in result.get("edges", [])]
            return nodes, edges
        except Exception as exc:
            logger.error(f"API discovery failed: {exc}; falling back to config")
            return await self._discover_from_config(request)

    async def batch_discover(
        self,
        requests: List[DiscoveryRequest],
    ) -> List[ServiceTopology]:
        """Run discovery for multiple scopes in parallel."""
        return await asyncio.gather(*[self.discover(req) for req in requests])
