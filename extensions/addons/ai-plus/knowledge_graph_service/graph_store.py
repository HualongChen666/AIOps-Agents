# -*- coding: utf-8 -*-
"""Graph storage with optional Neo4j backend and in-memory fallback."""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .schemas import Graph, GraphEdge, GraphNode

try:
    import neo4j

    _NEO4J_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    neo4j = None  # type: ignore[assignment]
    _NEO4J_AVAILABLE = False


class GraphStore:
    """Graph store backed by Neo4j when available, otherwise in-memory."""

    def __init__(
        self,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
    ) -> None:
        self._neo4j_uri = neo4j_uri or ""
        self._neo4j_user = neo4j_user or ""
        self._neo4j_password = neo4j_password or ""
        self._driver: Any = None
        self._in_memory: bool = True

        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[GraphEdge] = []
        self._index: Dict[str, List[GraphEdge]] = defaultdict(list)

    @property
    def is_connected(self) -> bool:
        """Return True if a Neo4j driver is active."""
        return self._driver is not None

    async def connect(self) -> None:
        """Try to connect to Neo4j if configured."""
        if not _NEO4J_AVAILABLE or not self._neo4j_uri:
            logger.info("Neo4j not available or not configured; using in-memory graph store")
            return
        try:
            self._driver = neo4j.AsyncGraphDatabase.driver(
                self._neo4j_uri,
                auth=(self._neo4j_user, self._neo4j_password),
            )
            await self._driver.verify_connectivity()
            self._in_memory = False
            logger.info("Connected to Neo4j graph store")
        except Exception as exc:
            logger.warning(f"Neo4j connection failed: {exc}; using in-memory graph store")
            self._driver = None
            self._in_memory = True

    async def close(self) -> None:
        """Close Neo4j driver if open."""
        if self._driver is not None:
            try:
                await self._driver.close()
            except Exception as exc:
                logger.debug(f"Neo4j close failed: {exc}")
            finally:
                self._driver = None

    def _new_id(self) -> str:
        return str(uuid.uuid4())

    async def add_node(self, node: GraphNode) -> str:
        """Add a node to the graph store."""
        if not node.node_id:
            node.node_id = self._new_id()
        if self._driver is not None and not self._in_memory:
            try:
                await self._driver.execute_query(
                    "MERGE (n:Entity {node_id: $node_id}) "
                    "SET n.label = $label, n.node_type = $node_type, "
                    "n.properties = $properties",
                    {
                        "node_id": node.node_id,
                        "label": node.label,
                        "node_type": node.node_type,
                        "properties": node.properties,
                    },
                )
            except Exception as exc:
                logger.debug(f"Neo4j add_node failed: {exc}; falling back to memory")
                self._nodes[node.node_id] = node
        else:
            self._nodes[node.node_id] = node
        return node.node_id

    async def add_edge(self, edge: GraphEdge) -> str:
        """Add an edge to the graph store."""
        if not edge.edge_id:
            edge.edge_id = self._new_id()
        if self._driver is not None and not self._in_memory:
            try:
                await self._driver.execute_query(
                    "MATCH (a:Entity {node_id: $source_id}) "
                    "MATCH (b:Entity {node_id: $target_id}) "
                    "MERGE (a)-[r:RELATES {edge_id: $edge_id}]->(b) "
                    "SET r.relation = $relation, r.properties = $properties",
                    {
                        "edge_id": edge.edge_id,
                        "source_id": edge.source_id,
                        "target_id": edge.target_id,
                        "relation": edge.relation,
                        "properties": edge.properties,
                    },
                )
            except Exception as exc:
                logger.debug(f"Neo4j add_edge failed: {exc}; falling back to memory")
                self._edges.append(edge)
                self._index[edge.source_id].append(edge)
        else:
            self._edges.append(edge)
            self._index[edge.source_id].append(edge)
        return edge.edge_id

    async def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Retrieve a node by ID."""
        return self._nodes.get(node_id)

    async def get_neighbors(self, node_id: str) -> List[GraphEdge]:
        """Return outgoing edges from a node."""
        return [e for e in self._edges if e.source_id == node_id]

    async def query_nodes(
        self, label: Optional[str] = None, node_type: Optional[str] = None
    ) -> List[GraphNode]:
        """Query nodes by label or type."""
        results: List[GraphNode] = []
        for node in self._nodes.values():
            if label and node.label != label:
                continue
            if node_type and node.node_type != node_type:
                continue
            results.append(node)
        return results

    async def query_edges(self, relation: Optional[str] = None) -> List[GraphEdge]:
        """Query edges by relation type."""
        if not relation:
            return list(self._edges)
        return [e for e in self._edges if e.relation == relation]

    def _collect_nodes(self, edges: List[GraphEdge]) -> List[GraphNode]:
        node_ids = {e.source_id for e in edges} | {e.target_id for e in edges}
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    async def find_paths(self, start_id: str, end_id: str, max_depth: int = 5) -> List[List[str]]:
        """Find all simple paths between two nodes up to max_depth."""
        paths: List[List[str]] = []
        queue: List[Tuple[str, List[str]]] = [(start_id, [start_id])]
        while queue:
            current, path = queue.pop(0)
            if current == end_id and len(path) > 1:
                paths.append(path)
                continue
            if len(path) >= max_depth:
                continue
            for edge in self._edges:
                if edge.source_id == current and edge.target_id not in path:
                    queue.append((edge.target_id, path + [edge.target_id]))
        return paths

    async def load_graph(self, graph: Graph) -> None:
        """Load an entire graph into the store."""
        for node in graph.nodes:
            await self.add_node(node)
        for edge in graph.edges:
            await self.add_edge(edge)

    async def as_graph(self, graph_id: str, name: str = "graph") -> Graph:
        """Return the current in-memory store as a Graph object."""
        return Graph(
            graph_id=graph_id,
            name=name,
            nodes=list(self._nodes.values()),
            edges=list(self._edges),
        )

    async def clear(self) -> None:
        """Clear the in-memory store."""
        self._nodes.clear()
        self._edges.clear()
        self._index.clear()