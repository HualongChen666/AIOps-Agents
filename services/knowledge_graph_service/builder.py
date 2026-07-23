# -*- coding: utf-8 -*-
"""Graph construction algorithms for the Knowledge Graph service."""

from __future__ import annotations

import uuid
from collections import OrderedDict
from typing import List

from .graph_store import GraphStore
from .schemas import Graph, GraphBuildRequest, GraphEdge, GraphNode


class GraphBuilder:
    """Build and persist graphs from node/edge requests."""

    def __init__(self, store: GraphStore) -> None:
        self.store = store

    @staticmethod
    def _deduplicate_nodes(nodes: List[GraphNode]) -> List[GraphNode]:
        """Remove duplicate nodes by ID while preserving order."""
        seen: OrderedDict[str, GraphNode] = OrderedDict()
        for node in nodes:
            seen[node.node_id] = node
        return list(seen.values())

    @staticmethod
    def _deduplicate_edges(edges: List[GraphEdge]) -> List[GraphEdge]:
        """Remove duplicate edges by ID while preserving order."""
        seen: OrderedDict[str, GraphEdge] = OrderedDict()
        for edge in edges:
            seen[edge.edge_id] = edge
        return list(seen.values())

    async def build_graph(self, request: GraphBuildRequest) -> Graph:
        """Construct a graph from a build request and persist it."""
        graph_id = str(uuid.uuid4())
        nodes = self._deduplicate_nodes(request.nodes)
        edges = self._deduplicate_edges(request.edges)

        graph = Graph(
            graph_id=graph_id,
            name=request.graph_name,
            nodes=nodes,
            edges=edges,
            metadata={"source": request.source, **request.metadata},
        )

        await self.store.clear()
        await self.store.load_graph(graph)

        return graph
