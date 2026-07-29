# -*- coding: utf-8 -*-
"""Graph visualization rendering for the Knowledge Graph service."""

from __future__ import annotations

import math
from typing import List

from .schemas import (
    Graph,
    GraphVisualizationRequest,
    GraphVisualizationResponse,
    NodeLayout,
)


class GraphVisualizer:
    """Generate simple 2D layouts for graph visualization."""

    def visualize(
        self, graph: Graph, request: GraphVisualizationRequest
    ) -> GraphVisualizationResponse:
        """Generate a layout for the graph."""
        nodes = graph.nodes
        layouts: List[NodeLayout] = []

        if not nodes:
            return GraphVisualizationResponse(
                graph_id=graph.graph_id, nodes=layouts, edges=graph.edges
            )

        width = max(request.width, 100)
        height = max(request.height, 100)
        cx = width / 2.0
        cy = height / 2.0
        radius = min(width, height) * 0.4

        count = len(nodes)
        if count == 1:
            layouts = [NodeLayout(node_id=nodes[0].node_id, x=cx, y=cy)]
        else:
            for i, node in enumerate(nodes):
                angle = 2 * math.pi * i / count
                x = cx + radius * math.cos(angle)
                y = cy + radius * math.sin(angle)
                layouts.append(NodeLayout(node_id=node.node_id, x=round(x, 2), y=round(y, 2)))

        return GraphVisualizationResponse(graph_id=graph.graph_id, nodes=layouts, edges=graph.edges)
