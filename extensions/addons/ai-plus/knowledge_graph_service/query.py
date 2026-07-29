# -*- coding: utf-8 -*-
"""Graph query operations for the Knowledge Graph service."""

from __future__ import annotations

from collections import deque
from typing import List, Optional, Set, Tuple

from .schemas import GraphEdge, GraphNode, GraphQueryRequest, GraphQueryResponse


class GraphQueryEngine:
    """Query a graph by entity, relation, or path."""

    def query(
        self,
        graph_id: str,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        request: GraphQueryRequest,
    ) -> GraphQueryResponse:
        """Execute a graph query."""
        if request.entity_id:
            return self._query_by_entity(
                graph_id, nodes, edges, request.entity_id, request.depth, request.top_k
            )
        if request.relation:
            return self._query_by_relation(graph_id, nodes, edges, request.relation)
        return GraphQueryResponse(
            graph_id=graph_id,
            nodes=nodes[: request.top_k],
            edges=[],
            total=len(nodes),
        )

    def _query_by_entity(
        self,
        graph_id: str,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        entity_id: str,
        depth: int,
        top_k: int,
    ) -> GraphQueryResponse:
        """Return the subgraph reachable from an entity up to a depth."""
        node_index = {node.node_id: node for node in nodes}
        if entity_id not in node_index:
            return GraphQueryResponse(graph_id=graph_id, nodes=[], edges=[], total=0)

        visited: Set[str] = {entity_id}
        queue: deque = deque([(entity_id, 0)])
        while queue:
            current, current_depth = queue.popleft()
            if current_depth >= depth:
                continue
            for edge in edges:
                if edge.source_id == current and edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, current_depth + 1))
                if edge.target_id == current and edge.source_id not in visited:
                    visited.add(edge.source_id)
                    queue.append((edge.source_id, current_depth + 1))

        result_nodes = [node_index[nid] for nid in visited if nid in node_index]
        result_edges = [e for e in edges if e.source_id in visited and e.target_id in visited]

        return GraphQueryResponse(
            graph_id=graph_id,
            nodes=result_nodes[:top_k],
            edges=result_edges[:top_k],
            total=len(result_nodes),
        )

    def _query_by_relation(
        self,
        graph_id: str,
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        relation: str,
    ) -> GraphQueryResponse:
        """Return all edges of a given relation type and connected nodes."""
        result_edges = [e for e in edges if e.relation == relation]
        node_ids = {e.source_id for e in result_edges} | {e.target_id for e in result_edges}
        node_index = {node.node_id: node for node in nodes}
        result_nodes = [node_index[nid] for nid in node_ids if nid in node_index]

        return GraphQueryResponse(
            graph_id=graph_id,
            nodes=result_nodes,
            edges=result_edges,
            total=len(result_nodes),
        )

    @staticmethod
    def find_shortest_path(
        nodes: List[GraphNode],
        edges: List[GraphEdge],
        start_id: str,
        end_id: str,
        max_depth: int = 5,
    ) -> Optional[List[str]]:
        """Find the shortest path between two nodes using BFS."""
        node_ids = {n.node_id for n in nodes}
        if start_id not in node_ids or end_id not in node_ids:
            return None
        visited: Set[str] = {start_id}
        queue: deque[Tuple[str, List[str]]] = deque([(start_id, [start_id])])

        while queue:
            current, path = queue.popleft()
            if current == end_id:
                return path
            if len(path) >= max_depth:
                continue
            for edge in edges:
                if edge.source_id == current and edge.target_id not in visited:
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, path + [edge.target_id]))
        return None
