# -*- coding: utf-8 -*-
"""Impact range analysis based on graph traversal."""

from __future__ import annotations

import time
from collections import deque
from typing import Any, Dict, List, Set

from loguru import logger

from services.topology_service.dependency import DependencyGraph
from services.topology_service.metrics import TOPOLOGY_IMPACT_ANALYSIS_DURATION
from services.topology_service.schemas import ImpactRequest, ImpactResult


class ImpactAnalyzer:
    """Analyze impact of changes using BFS/DFS graph traversal."""

    def __init__(self, graph: DependencyGraph) -> None:
        self.graph = graph

    async def __call__(self, request: ImpactRequest) -> ImpactResult:
        """Alias for analyze; allows callable use from FastAPI endpoints."""
        return await self.analyze(request)

    async def analyze(self, request: ImpactRequest) -> ImpactResult:
        """Analyze impact of changing the given nodes."""
        start = time.perf_counter()
        impacted: Set[str] = set()
        paths: List[List[str]] = []

        direction = request.direction.lower()
        for changed_node in request.changed_nodes:
            if direction in ("outbound", "both"):
                outbound = self._bfs(changed_node, "outbound", request.max_depth)
                impacted.update(outbound["nodes"])
                paths.extend(outbound["paths"])
            if direction in ("inbound", "both"):
                inbound = self._bfs(changed_node, "inbound", request.max_depth)
                impacted.update(inbound["nodes"])
                paths.extend(inbound["paths"])

        impacted.discard(*request.changed_nodes)
        duration = time.perf_counter() - start
        TOPOLOGY_IMPACT_ANALYSIS_DURATION.labels(direction=direction).observe(duration)

        impact_score = self._compute_impact_score(
            request.changed_nodes,
            list(impacted),
            request.change_magnitude,
        )

        logger.info(
            f"Impact analysis: {len(request.changed_nodes)} changed nodes, "
            f"{len(impacted)} impacted nodes, score={impact_score:.2f}"
        )

        return ImpactResult(
            changed_nodes=request.changed_nodes,
            impacted_nodes=sorted(impacted),
            paths=paths[:100],
            impact_score=impact_score,
            analysis_duration_seconds=duration,
        )

    def _bfs(
        self,
        start: str,
        direction: str,
        max_depth: int,
    ) -> Dict[str, Any]:
        """Run BFS to collect impacted nodes and paths."""
        visited: Set[str] = set()
        impacted_nodes: Set[str] = set()
        paths: List[List[str]] = []

        queue: deque[tuple[str, int, List[str]]] = deque([(start, 0, [start])])

        while queue:
            current, depth, path = queue.popleft()
            if current in visited or depth >= max_depth:
                continue
            visited.add(current)

            if direction == "outbound":
                adjacency = self.graph._adjacency
            else:
                adjacency = self.graph._reverse_adjacency
            for edge in adjacency.get(current, []):
                neighbor = edge.target if direction == "outbound" else edge.source
                if neighbor not in visited:
                    impacted_nodes.add(neighbor)
                    new_path = path + [neighbor]
                    paths.append(new_path)
                    queue.append((neighbor, depth + 1, new_path))

        impacted_nodes.discard(start)
        return {"nodes": impacted_nodes, "paths": paths}

    def _compute_impact_score(
        self,
        changed_nodes: List[str],
        impacted_nodes: List[str],
        magnitude: float,
    ) -> float:
        """Compute a simple impact score based on affected nodes and magnitude."""
        if not changed_nodes:
            return 0.0
        return round(len(impacted_nodes) * magnitude / len(changed_nodes), 4)

    async def batch_analyze(
        self,
        requests: List[ImpactRequest],
    ) -> List[ImpactResult]:
        """Run multiple impact analyses in batch."""
        return [await self.analyze(req) for req in requests]
