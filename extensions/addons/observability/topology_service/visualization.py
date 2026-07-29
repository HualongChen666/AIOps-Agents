# -*- coding: utf-8 -*-
"""D3.js compatible topology visualization generation."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Any, Dict, Optional

from services.topology_service.metrics import TOPOLOGY_VISUALIZATION_REQUESTS
from services.topology_service.schemas import (
    D3Visualization,
    ServiceTopology,
    TopologyEdge,
    TopologyNode,
    VisualizationConfig,
)


class TopologyVisualizer:
    """Generate D3.js compatible visualization data."""

    def __init__(self, default_config: Optional[VisualizationConfig] = None) -> None:
        self.default_config = default_config or VisualizationConfig()

    async def generate(
        self,
        topology: ServiceTopology,
        config: Optional[VisualizationConfig] = None,
    ) -> D3Visualization:
        """Generate D3.js nodes and links."""
        cfg = config or self.default_config
        TOPOLOGY_VISUALIZATION_REQUESTS.labels(layout=cfg.layout).inc()

        nodes = [
            self._format_node(n, i, len(topology.nodes), cfg) for i, n in enumerate(topology.nodes)
        ]
        links = [self._format_link(e) for e in topology.edges]

        return D3Visualization(
            nodes=nodes,
            links=links,
            config=cfg,
            generated_at=datetime.utcnow(),
        )

    def _format_node(
        self,
        node: TopologyNode,
        index: int,
        total: int,
        config: VisualizationConfig,
    ) -> Dict[str, Any]:
        """Format a topology node for D3.js."""
        if node.x is None or node.y is None:
            angle = 2 * math.pi * index / max(total, 1)
            radius = min(config.width, config.height) * 0.35
            x = config.width / 2 + radius * math.cos(angle)
            y = config.height / 2 + radius * math.sin(angle)
        else:
            x = node.x
            y = node.y

        return {
            "id": node.node_id,
            "name": node.name,
            "type": (
                node.node_type.value if hasattr(node.node_type, "value") else str(node.node_type)
            ),
            "health": node.health,
            "x": x,
            "y": y,
            "r": 8,
            "metadata": node.metadata,
        }

    def _format_link(self, edge: TopologyEdge) -> Dict[str, Any]:
        """Format a topology edge for D3.js."""
        return {
            "source": edge.source,
            "target": edge.target,
            "type": (
                edge.edge_type.value if hasattr(edge.edge_type, "value") else str(edge.edge_type)
            ),
            "weight": edge.weight,
            "metadata": edge.metadata,
        }
