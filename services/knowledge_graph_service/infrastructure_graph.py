# -*- coding: utf-8 -*-
"""Infrastructure graph builder for the Knowledge Graph service."""

from __future__ import annotations

from typing import Dict, List, Set

from .builder import GraphBuilder
from .schemas import (
    GraphBuildRequest,
    GraphEdge,
    GraphNode,
    InfrastructureGraphRequest,
    InfrastructureGraphResponse,
)


class InfrastructureGraphBuilder:
    """Construct infrastructure topology graphs."""

    def __init__(self, graph_builder: GraphBuilder) -> None:
        self.graph_builder = graph_builder

    def _normalize(self, name: str) -> str:
        """Normalize a component name to a node identifier."""
        return name.strip().lower().replace(" ", "_").replace("-", "_")

    async def build(self, request: InfrastructureGraphRequest) -> InfrastructureGraphResponse:
        """Build a graph from infrastructure components and connections."""
        nodes: List[GraphNode] = []
        edges: List[GraphEdge] = []
        seen_nodes: Dict[str, GraphNode] = {}

        all_components: Set[str] = set()
        for component in request.components:
            all_components.add(self._normalize(component.component_id))
            for connection in component.connections:
                all_components.add(self._normalize(connection))

        for component_id in sorted(all_components):
            original = next(
                (c for c in request.components if self._normalize(c.component_id) == component_id),
                None,
            )
            component_type = original.component_type if original else "unknown"
            properties: Dict[str, str] = {"kind": "infrastructure"}
            if original:
                properties.update(original.properties)
            seen_nodes[component_id] = GraphNode(
                node_id=component_id,
                label=component_id,
                node_type=component_type,
                properties=properties,
            )

        nodes = list(seen_nodes.values())

        edge_id_set: Set[str] = set()
        for component in request.components:
            source = self._normalize(component.component_id)
            for connection in component.connections:
                target = self._normalize(connection)
                edge_id = f"{source}__{request.connection_type}__{target}"
                if edge_id in edge_id_set:
                    continue
                edge_id_set.add(edge_id)
                edges.append(
                    GraphEdge(
                        edge_id=edge_id,
                        source_id=source,
                        target_id=target,
                        relation=request.connection_type,
                    )
                )

        build_request = GraphBuildRequest(
            graph_name="infrastructure-graph",
            nodes=nodes,
            edges=edges,
            source="infrastructure",
        )
        graph = await self.graph_builder.build_graph(build_request)

        return InfrastructureGraphResponse(
            graph_id=graph.graph_id,
            components_count=len(request.components),
            connections_count=len(graph.edges),
            built=True,
        )
