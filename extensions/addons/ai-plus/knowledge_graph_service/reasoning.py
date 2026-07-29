# -*- coding: utf-8 -*-
"""Graph reasoning algorithms for the Knowledge Graph service."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional

from .schemas import GraphEdge, GraphNode, GraphReasonRequest, GraphReasonResponse


class GraphReasoningEngine:
    """Reason over graphs using neighborhood, path, and centrality algorithms."""

    def reason(
        self,
        graph_id: str,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        request: GraphReasonRequest,
    ) -> GraphReasonResponse:
        """Dispatch reasoning by type."""
        node_index = {node.node_id: node for node in nodes}
        if request.node_id not in node_index:
            return GraphReasonResponse(
                graph_id=graph_id,
                node_id=request.node_id,
                reason_type=request.reason_type,
                results=[],
                total=0,
            )

        if request.reason_type == "neighbors":
            results = self._infer_neighbors(request.node_id, edges, request.relation)
        elif request.reason_type == "transitive":
            results = self._transitive_closure(
                request.node_id, edges, request.relation, request.max_depth
            )
        elif request.reason_type == "pagerank":
            results = self._page_rank(nodes, edges)
        elif request.reason_type == "paths":
            results = self._all_paths(
                request.node_id, nodes, edges, request.relation, request.max_depth
            )
        else:
            results = self._infer_neighbors(request.node_id, edges, request.relation)

        return GraphReasonResponse(
            graph_id=graph_id,
            node_id=request.node_id,
            reason_type=request.reason_type,
            results=results,
            total=len(results),
        )

    def _infer_neighbors(
        self, node_id: str, edges: List[GraphEdge], relation: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return outgoing neighbors, optionally filtered by relation."""
        results: List[Dict[str, Any]] = []
        for edge in edges:
            if edge.source_id == node_id:
                if relation and edge.relation != relation:
                    continue
                results.append(
                    {
                        "node_id": edge.target_id,
                        "relation": edge.relation,
                        "properties": edge.properties,
                    }
                )
        return results

    def _transitive_closure(
        self,
        start_id: str,
        edges: List[GraphEdge],
        relation: Optional[str] = None,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find nodes reachable via transitive relationships."""
        reachable: Dict[str, int] = {}

        def dfs(current: str, depth: int) -> None:
            for edge in edges:
                if edge.source_id != current:
                    continue
                if relation and edge.relation != relation:
                    continue
                if edge.target_id not in reachable or reachable[edge.target_id] > depth:
                    reachable[edge.target_id] = depth
                if depth < max_depth:
                    dfs(edge.target_id, depth + 1)

        dfs(start_id, 1)
        return [
            {"node_id": node_id, "distance": distance}
            for node_id, distance in sorted(reachable.items(), key=lambda x: x[1])
        ]

    def _page_rank(
        self,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        iterations: int = 10,
        damping: float = 0.85,
    ) -> List[Dict[str, Any]]:
        """Compute a simple PageRank score for each node."""
        node_ids = [node.node_id for node in nodes]
        if not node_ids:
            return []
        scores: Dict[str, float] = {node_id: 1.0 / len(node_ids) for node_id in node_ids}
        outgoing: Dict[str, List[str]] = defaultdict(list)
        for edge in edges:
            outgoing[edge.source_id].append(edge.target_id)

        for _ in range(iterations):
            new_scores: Dict[str, float] = {}
            for node_id in node_ids:
                incoming = sum(
                    scores[src] / max(len(outgoing[src]), 1)
                    for src, targets in outgoing.items()
                    if node_id in targets
                )
                new_scores[node_id] = (1 - damping) / len(node_ids) + damping * incoming
            scores = new_scores

        return sorted(
            [{"node_id": node_id, "score": round(score, 6)} for node_id, score in scores.items()],
            key=lambda x: x["score"],
            reverse=True,
        )

    def _all_paths(
        self,
        start_id: str,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        relation: Optional[str] = None,
        max_depth: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find simple paths starting from a node."""
        paths: List[List[str]] = []

        def dfs(current: str, path: List[str]) -> None:
            if len(path) > max_depth:
                return
            for edge in edges:
                if edge.source_id != current:
                    continue
                if relation and edge.relation != relation:
                    continue
                if edge.target_id in path:
                    continue
                new_path = path + [edge.target_id]
                paths.append(new_path)
                dfs(edge.target_id, new_path)

        dfs(start_id, [start_id])
        return [{"path": path} for path in paths[:100]]
