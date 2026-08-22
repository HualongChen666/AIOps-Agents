# -*- coding: utf-8 -*-
"""Service dependency graph builder for the Knowledge Graph service."""

from __future__ import annotations

from typing import Dict, List, Set

from .builder import GraphBuilder
from .schemas import (
    GraphBuildRequest,
    GraphEdge,
    GraphNode,
    ServiceDependencyGraphRequest,
    ServiceDependencyGraphResponse,
)


class ServiceDependencyGraphBuilder:
    """Construct service dependency graphs."""

    def __init__(self, graph_builder: GraphBuilder) -> None:
        self.graph_builder = graph_builder

    def _normalize(self, name: str) -> str:
        """Normalize a service name to a node identifier."""
        return name.strip().lower().replace(" ", "_").replace("-", "_")

    async def build(self, request: ServiceDependencyGraphRequest) -> ServiceDependencyGraphResponse:
        """Build a graph from service dependencies."""
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        seen_nodes: Dict[str, GraphNode] = {}

        all_services: Set[str] = {self._normalize(dep.service) for dep in request.services}
        for dep in request.services:
            for dependency in dep.depends_on:
                all_services.add(self._normalize(dependency))

        for service_id in sorted(all_services):
            properties: Dict[str, str] = {"kind": "service"}
            original = next(
                (d for d in request.services if self._normalize(d.service) == service_id), None
            )
            if original:
                properties.update(original.properties)
            node = GraphNode(
                node_id=service_id,
                label=service_id,
                node_type="service",
                properties=properties,
            )
            seen_nodes[service_id] = node
            nodes.append(node)

        edge_id_set: Set[str] = set()
        for dep in request.services:
            source = self._normalize(dep.service)
            for dependency in dep.depends_on:
                target = self._normalize(dependency)
                edge_id = f"{source}__DEPENDS_ON__{target}"
                if edge_id in edge_id_set:
                    continue
                edge_id_set.add(edge_id)
                edges.append(
                    GraphEdge(
                        edge_id=edge_id,
                        source_id=source,
                        target_id=target,
                        relation="DEPENDS_ON",
                    )
                )

        build_request = GraphBuildRequest(
            graph_name="service-dependency-graph",
            nodes=nodes,
            edges=edges,
            source="service_dependencies",
        )
        graph = await self.graph_builder.build_graph(build_request)

        return ServiceDependencyGraphResponse(
            graph_id=graph.graph_id,
            services_count=len({d.service for d in request.services}),
            dependencies_count=len(graph.edges),
            built=True,
        )
