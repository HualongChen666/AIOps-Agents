# -*- coding: utf-8 -*-
"""Tests for GraphQueryEngine module."""

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.query import GraphQueryEngine
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    GraphEdge,
    GraphNode,
    GraphQueryRequest,
)


class TestGraphQueryEngine:
    """Test cases for GraphQueryEngine class."""

    def test_query_no_filters(self):
        """Test query with no filters."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            )
        ]
        request = GraphQueryRequest(graph_id="graph1", top_k=10)

        response = engine.query("graph1", nodes, edges, request)

        assert len(response.nodes) == 2
        assert len(response.edges) == 0
        assert response.total == 2

    def test_query_by_entity(self):
        """Test query by entity ID."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge2",
                source_id="node2",
                target_id="node3",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", depth=2, top_k=10)

        response = engine.query("graph1", nodes, edges, request)

        assert len(response.nodes) == 3
        assert len(response.edges) == 2
        assert response.total == 3

    def test_query_by_entity_not_found(self):
        """Test query by entity ID when entity doesn't exist."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
        ]
        edges = []
        request = GraphQueryRequest(graph_id="graph1", entity_id="nonexistent", depth=2, top_k=10)

        response = engine.query("graph1", nodes, edges, request)

        assert len(response.nodes) == 0
        assert len(response.edges) == 0
        assert response.total == 0

    def test_query_by_relation(self):
        """Test query by relation type."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge2",
                source_id="node2",
                target_id="node3",
                relation="DEPENDS_ON",
            ),
        ]
        request = GraphQueryRequest(graph_id="graph1", relation="CONNECTS_TO")

        response = engine.query("graph1", nodes, edges, request)

        assert len(response.nodes) == 2
        assert len(response.edges) == 1
        assert response.edges[0].relation == "CONNECTS_TO"

    def test_query_by_entity_depth_limit(self):
        """Test query by entity with depth limit."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
            GraphNode(node_id="node4", label="Node 4", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge2",
                source_id="node2",
                target_id="node3",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge3",
                source_id="node3",
                target_id="node4",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", depth=1, top_k=10)

        response = engine.query("graph1", nodes, edges, request)

        # Should only include node1 and node2 (depth 1)
        assert len(response.nodes) == 2
        assert len(response.edges) == 1

    def test_query_by_entity_top_k(self):
        """Test query by entity with top_k limit."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id=f"node{i}", label=f"Node {i}", node_type="entity")
            for i in range(10)
        ]
        edges = [
            GraphEdge(
                edge_id=f"edge{i}",
                source_id="node0",
                target_id=f"node{i}",
                relation="CONNECTS_TO",
            )
            for i in range(1, 10)
        ]
        request = GraphQueryRequest(graph_id="graph1", entity_id="node0", depth=1, top_k=5)

        response = engine.query("graph1", nodes, edges, request)

        # Should limit to 5 nodes
        assert len(response.nodes) == 5

    def test_query_by_entity_bidirectional(self):
        """Test query by entity with bidirectional edges."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge2",
                source_id="node3",
                target_id="node1",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", depth=1, top_k=10)

        response = engine.query("graph1", nodes, edges, request)

        # Should include both incoming and outgoing neighbors
        assert len(response.nodes) == 3
        assert len(response.edges) == 2

    def test_query_by_relation_no_matches(self):
        """Test query by relation with no matches."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphQueryRequest(graph_id="graph1", relation="DEPENDS_ON")

        response = engine.query("graph1", nodes, edges, request)

        assert len(response.nodes) == 0
        assert len(response.edges) == 0

    def test_query_empty_graph(self):
        """Test query on empty graph."""
        engine = GraphQueryEngine()
        nodes = []
        edges = []
        request = GraphQueryRequest(graph_id="graph1", top_k=10)

        response = engine.query("graph1", nodes, edges, request)

        assert len(response.nodes) == 0
        assert len(response.edges) == 0
        assert response.total == 0

    def test_find_shortest_path_exists(self):
        """Test finding shortest path when path exists."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge2",
                source_id="node2",
                target_id="node3",
                relation="CONNECTS_TO",
            ),
        ]

        path = engine.find_shortest_path(nodes, edges, "node1", "node3")

        assert path == ["node1", "node2", "node3"]

    def test_find_shortest_path_no_path(self):
        """Test finding shortest path when no path exists."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = []

        path = engine.find_shortest_path(nodes, edges, "node1", "node2")

        assert path is None

    def test_find_shortest_path_invalid_nodes(self):
        """Test finding shortest path with invalid node IDs."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
        ]
        edges = []

        path = engine.find_shortest_path(nodes, edges, "node1", "nonexistent")

        assert path is None

    def test_find_shortest_path_max_depth(self):
        """Test finding shortest path with max depth limit."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
            GraphNode(node_id="node4", label="Node 4", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge2",
                source_id="node2",
                target_id="node3",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge3",
                source_id="node3",
                target_id="node4",
                relation="CONNECTS_TO",
            ),
        ]

        path = engine.find_shortest_path(nodes, edges, "node1", "node4", max_depth=2)

        # Path length 3 exceeds max_depth 2
        assert path is None

    def test_find_shortest_path_same_node(self):
        """Test finding shortest path from node to itself."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
        ]
        edges = []

        path = engine.find_shortest_path(nodes, edges, "node1", "node1")

        assert path == ["node1"]

    def test_query_by_entity_zero_depth(self):
        """Test query by entity with zero depth."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", depth=0, top_k=10)

        response = engine.query("graph1", nodes, edges, request)

        # Should only include the starting node
        assert len(response.nodes) == 1
        assert response.nodes[0].node_id == "node1"
        assert len(response.edges) == 0

    def test_query_by_entity_complex_graph(self):
        """Test query by entity on complex graph with multiple paths."""
        engine = GraphQueryEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
            GraphNode(node_id="node4", label="Node 4", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge2",
                source_id="node1",
                target_id="node3",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge3",
                source_id="node2",
                target_id="node4",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge4",
                source_id="node3",
                target_id="node4",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", depth=2, top_k=10)

        response = engine.query("graph1", nodes, edges, request)

        # Should include all nodes reachable within depth 2
        assert len(response.nodes) == 4
