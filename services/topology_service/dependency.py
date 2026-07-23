# -*- coding: utf-8 -*-
"""Dependency relationship modeling based on graph database abstraction."""

from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from services.topology_service.schemas import (
    DependencyRequest,
    EdgeType,
    ServiceTopology,
    TopologyEdge,
    TopologyNode,
)


class DependencyGraph:
    """In-memory graph model for service dependencies; can be backed by Neo4j/ArangoDB."""

    def __init__(self) -> None:
        self._nodes: Dict[str, TopologyNode] = {}
        self._edges: List[TopologyEdge] = []
        self._adjacency: Dict[str, List[TopologyEdge]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[TopologyEdge]] = defaultdict(list)

    def load_topology(self, topology: ServiceTopology) -> None:
        """Load nodes and edges from a ServiceTopology."""
        self._nodes = {n.node_id: n for n in topology.nodes}
        self._edges = topology.edges[:]
        self._adjacency.clear()
        self._reverse_adjacency.clear()
        for edge in self._edges:
            self._adjacency[edge.source].append(edge)
            self._reverse_adjacency[edge.target].append(edge)

    def add_node(self, node: TopologyNode) -> None:
        self._nodes[node.node_id] = node

    def add_edge(self, edge: TopologyEdge) -> None:
        self._edges.append(edge)
        self._adjacency[edge.source].append(edge)
        self._reverse_adjacency[edge.target].append(edge)

    def get_dependencies(
        self,
        service_name: str,
        edge_type: Optional[EdgeType] = None,
        depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """Return dependencies of a service up to a given depth."""
        results: List[Dict[str, Any]] = []
        visited: Set[str] = set()
        queue: List[tuple[str, int]] = [(service_name, 0)]

        while queue:
            current, current_depth = queue.pop(0)
            if current_depth >= depth or current in visited:
                continue
            visited.add(current)
            for edge in self._adjacency.get(current, []):
                if edge_type and edge.edge_type != edge_type:
                    continue
                target = self._nodes.get(edge.target)
                if target:
                    results.append(
                        {
                            "node": target.model_dump(),
                            "edge": edge.model_dump(),
                            "depth": current_depth + 1,
                        }
                    )
                queue.append((edge.target, current_depth + 1))

        return results

    def get_dependents(
        self,
        service_name: str,
        edge_type: Optional[EdgeType] = None,
        depth: int = 2,
    ) -> List[Dict[str, Any]]:
        """Return services that depend on the given service."""
        results: List[Dict[str, Any]] = []
        visited: Set[str] = set()
        queue: List[tuple[str, int]] = [(service_name, 0)]

        while queue:
            current, current_depth = queue.pop(0)
            if current_depth >= depth or current in visited:
                continue
            visited.add(current)
            for edge in self._reverse_adjacency.get(current, []):
                if edge_type and edge.edge_type != edge_type:
                    continue
                source = self._nodes.get(edge.source)
                if source:
                    results.append(
                        {
                            "node": source.model_dump(),
                            "edge": edge.model_dump(),
                            "depth": current_depth + 1,
                        }
                    )
                queue.append((edge.source, current_depth + 1))

        return results

    def find_all_paths(
        self,
        source: str,
        target: str,
        max_depth: int = 10,
    ) -> List[List[str]]:
        """Find all paths between two nodes using DFS."""
        paths: List[List[str]] = []
        stack: List[tuple[str, List[str]]] = [(source, [source])]

        while stack:
            current, path = stack.pop()
            if current == target and len(path) > 1:
                paths.append(path)
                continue
            if len(path) >= max_depth:
                continue
            for edge in self._adjacency.get(current, []):
                if edge.target not in path:
                    stack.append((edge.target, path + [edge.target]))

        return paths

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.model_dump() for n in self._nodes.values()],
            "edges": [e.model_dump() for e in self._edges],
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
        }


class DependencyModelingEngine:
    """Model and query service dependencies."""

    def __init__(self, graph: Optional[DependencyGraph] = None) -> None:
        self.graph = graph or DependencyGraph()

    async def model_dependencies(
        self,
        topology: ServiceTopology,
    ) -> DependencyGraph:
        """Build dependency graph from topology and cache summary."""
        start = time.perf_counter()
        self.graph.load_topology(topology)
        duration = time.perf_counter() - start
        logger.info(
            f"Modeled dependencies for {topology.topology_id}: "
            f"{len(topology.nodes)} nodes, {len(topology.edges)} edges in {duration:.4f}s"
        )
        return self.graph

    async def query_dependencies(self, request: DependencyRequest) -> List[Dict[str, Any]]:
        """Query dependencies for a service."""
        return self.graph.get_dependencies(
            request.service_name,
            edge_type=request.dependency_type,
            depth=request.depth,
        )
