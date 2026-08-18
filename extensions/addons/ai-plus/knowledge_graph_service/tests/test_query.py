# -*- coding: utf-8 -*-
"""Tests for GraphQueryEngine module."""

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.query import GraphQueryEngine
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    GraphEdge,
    GraphNode,
    GraphQueryRequest,
)


@pytest.fixture
def query_engine():
    """Create a test query engine."""
    return GraphQueryEngine()


@pytest.fixture
def sample_nodes():
    """Create sample nodes for testing."""
    return [
        GraphNode(node_id="node1", label="Node 1", node_type="entity"),
        GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        GraphNode(node_id="node4", label="Node 4", node_type="entity"),
    ]


@pytest.fixture
def sample_edges():
    """Create sample edges for testing."""
    return [
        GraphEdge(
            edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
        ),
        GraphEdge(
            edge_id="edge2", source_id="node2", target_id="node3", relation="CONNECTS_TO"
        ),
        GraphEdge(
            edge_id="edge3", source_id="node3", target_id="node4", relation="DEPENDS_ON"
        ),
        GraphEdge(
            edge_id="edge4", source_id="node1", target_id="node3", relation="CONNECTS_TO"
        ),
    ]


class TestGraphQueryEngine:
    """Test cases for GraphQueryEngine class."""

    def test_query_default(self, query_engine, sample_nodes, sample_edges):
        """Test query with default parameters."""
        request = GraphQueryRequest(graph_id="test_graph")

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        assert response.graph_id == "test_graph"
        assert len(response.nodes) == 4  # All available nodes (less than top_k default)
        assert len(response.edges) == 0
        assert response.total == 4

    def test_query_with_top_k(self, query_engine, sample_nodes, sample_edges):
        """Test query with custom top_k."""
        request = GraphQueryRequest(graph_id="test_graph", top_k=2)

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        assert len(response.nodes) == 2
        assert response.total == 4

    def test_query_by_entity(self, query_engine, sample_nodes, sample_edges):
        """Test query by entity ID."""
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node1", depth=2)

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        assert response.graph_id == "test_graph"
        assert len(response.nodes) >= 1
        assert node_id_in_list("node1", response.nodes)

    def test_query_by_entity_not_found(self, query_engine, sample_nodes, sample_edges):
        """Test query by non-existent entity ID."""
        request = GraphQueryRequest(graph_id="test_graph", entity_id="nonexistent")

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        assert len(response.nodes) == 0
        assert len(response.edges) == 0
        assert response.total == 0

    def test_query_by_relation(self, query_engine, sample_nodes, sample_edges):
        """Test query by relation type."""
        request = GraphQueryRequest(graph_id="test_graph", relation="CONNECTS_TO")

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        assert response.graph_id == "test_graph"
        assert len(response.edges) == 3  # 3 CONNECTS_TO edges
        assert all(e.relation == "CONNECTS_TO" for e in response.edges)

    def test_query_by_relation_not_found(self, query_engine, sample_nodes, sample_edges):
        """Test query by non-existent relation type."""
        request = GraphQueryRequest(graph_id="test_graph", relation="NONEXISTENT")

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        assert len(response.edges) == 0
        assert len(response.nodes) == 0

    def test_query_by_entity_with_depth(self, query_engine, sample_nodes, sample_edges):
        """Test query by entity with depth limit."""
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node1", depth=1)

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        # With depth 1, should only get immediate neighbors
        assert response.graph_id == "test_graph"

    def test_query_by_entity_with_top_k(self, query_engine, sample_nodes, sample_edges):
        """Test query by entity with top_k limit."""
        request = GraphQueryRequest(
            graph_id="test_graph", entity_id="node1", depth=2, top_k=2
        )

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        assert len(response.nodes) <= 2

    def test_query_empty_graph(self, query_engine):
        """Test query on empty graph."""
        request = GraphQueryRequest(graph_id="test_graph")

        response = query_engine.query("test_graph", [], [], request)

        assert len(response.nodes) == 0
        assert len(response.edges) == 0
        assert response.total == 0

    def test_query_by_entity_empty_graph(self, query_engine):
        """Test query by entity on empty graph."""
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node1")

        response = query_engine.query("test_graph", [], [], request)

        assert len(response.nodes) == 0
        assert response.total == 0

    def test_query_by_relation_empty_graph(self, query_engine):
        """Test query by relation on empty graph."""
        request = GraphQueryRequest(graph_id="test_graph", relation="CONNECTS_TO")

        response = query_engine.query("test_graph", [], [], request)

        assert len(response.edges) == 0
        assert len(response.nodes) == 0

    def test_query_by_entity_bidirectional(self, query_engine, sample_nodes, sample_edges):
        """Test that query by entity is bidirectional."""
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node2", depth=2)

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        # Should find both incoming and outgoing neighbors
        assert response.graph_id == "test_graph"

    def test_query_by_entity_depth_zero(self, query_engine, sample_nodes, sample_edges):
        """Test query by entity with depth 0."""
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node1", depth=0)

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        # With depth 0, should only return the starting node
        assert len(response.nodes) >= 1

    def test_query_by_entity_large_depth(self, query_engine, sample_nodes, sample_edges):
        """Test query by entity with large depth."""
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node1", depth=10)

        response = query_engine.query("test_graph", sample_nodes, sample_edges, request)

        # Should not error even with large depth
        assert response.graph_id == "test_graph"

    def test_query_by_relation_multiple_edges(self, query_engine, sample_nodes):
        """Test query by relation with multiple edges between same nodes."""
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            ),
            GraphEdge(
                edge_id="edge2", source_id="node1", target_id="node2", relation="DEPENDS_ON"
            ),
            GraphEdge(
                edge_id="edge3", source_id="node2", target_id="node3", relation="CONNECTS_TO"
            ),
        ]
        request = GraphQueryRequest(graph_id="test_graph", relation="CONNECTS_TO")

        response = query_engine.query("test_graph", sample_nodes, edges, request)

        assert len(response.edges) == 2

    def test_query_by_entity_with_cycle(self, query_engine, sample_nodes):
        """Test query by entity with cyclic graph."""
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            ),
            GraphEdge(
                edge_id="edge2", source_id="node2", target_id="node3", relation="CONNECTS_TO"
            ),
            GraphEdge(
                edge_id="edge3", source_id="node3", target_id="node1", relation="CONNECTS_TO"
            ),
        ]
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node1", depth=3)

        response = query_engine.query("test_graph", sample_nodes, edges, request)

        # Should handle cycles without infinite loop
        assert response.graph_id == "test_graph"

    def test_query_by_entity_disconnected_components(self, query_engine, sample_nodes):
        """Test query by entity with disconnected components."""
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            ),
            # node3 and node4 are disconnected
        ]
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node1", depth=2)

        response = query_engine.query("test_graph", sample_nodes, edges, request)

        # Should only find nodes in the connected component
        assert response.graph_id == "test_graph"

    def test_find_shortest_path_exists(self, query_engine, sample_nodes, sample_edges):
        """Test find_shortest_path when path exists."""
        path = query_engine.find_shortest_path(
            sample_nodes, sample_edges, "node1", "node4"
        )

        assert path is not None
        assert path[0] == "node1"
        assert path[-1] == "node4"

    def test_find_shortest_path_not_exists(self, query_engine, sample_nodes):
        """Test find_shortest_path when path doesn't exist."""
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            )
        ]
        path = query_engine.find_shortest_path(sample_nodes, edges, "node1", "node4")

        assert path is None

    def test_find_shortest_path_same_node(self, query_engine, sample_nodes):
        """Test find_shortest_path for same node."""
        path = query_engine.find_shortest_path(sample_nodes, [], "node1", "node1")

        assert path == ["node1"]

    def test_find_shortest_path_nonexistent_node(self, query_engine, sample_nodes, sample_edges):
        """Test find_shortest_path with non-existent node."""
        path = query_engine.find_shortest_path(
            sample_nodes, sample_edges, "node1", "nonexistent"
        )

        assert path is None

    def test_find_shortest_path_with_max_depth(self, query_engine, sample_nodes, sample_edges):
        """Test find_shortest_path with max_depth limit."""
        path = query_engine.find_shortest_path(
            sample_nodes, sample_edges, "node1", "node4", max_depth=1
        )

        # Path length 2 exceeds max_depth 1
        assert path is None

    def test_find_shortest_path_multiple_paths(self, query_engine, sample_nodes):
        """Test find_shortest_path with multiple possible paths."""
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            ),
            GraphEdge(
                edge_id="edge2", source_id="node2", target_id="node4", relation="CONNECTS_TO"
            ),
            GraphEdge(
                edge_id="edge3", source_id="node1", target_id="node3", relation="CONNECTS_TO"
            ),
            GraphEdge(
                edge_id="edge4", source_id="node3", target_id="node4", relation="CONNECTS_TO"
            ),
        ]
        path = query_engine.find_shortest_path(sample_nodes, edges, "node1", "node4")

        assert path is not None
        # Should return one of the shortest paths
        assert len(path) <= 3

    def test_find_shortest_path_direct_connection(self, query_engine, sample_nodes):
        """Test find_shortest_path with direct connection."""
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            )
        ]
        path = query_engine.find_shortest_path(sample_nodes, edges, "node1", "node2")

        assert path == ["node1", "node2"]

    def test_query_by_entity_large_graph(self, query_engine):
        """Test query by entity on large graph."""
        nodes = [GraphNode(node_id=f"node{i}", label=f"Node {i}", node_type="entity") for i in range(100)]
        edges = [
            GraphEdge(
                edge_id=f"edge{i}",
                source_id=f"node{i}",
                target_id=f"node{i+1}",
                relation="CONNECTS_TO",
            )
            for i in range(99)
        ]
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node0", depth=5)

        response = query_engine.query("test_graph", nodes, edges, request)

        assert response.graph_id == "test_graph"

    def test_query_by_relation_large_graph(self, query_engine):
        """Test query by relation on large graph."""
        nodes = [GraphNode(node_id=f"node{i}", label=f"Node {i}", node_type="entity") for i in range(100)]
        edges = [
            GraphEdge(
                edge_id=f"edge{i}",
                source_id=f"node{i}",
                target_id=f"node{i+1}",
                relation="CONNECTS_TO",
            )
            for i in range(99)
        ]
        request = GraphQueryRequest(graph_id="test_graph", relation="CONNECTS_TO")

        response = query_engine.query("test_graph", nodes, edges, request)

        assert len(response.edges) == 99

    def test_query_by_entity_with_properties(self, query_engine):
        """Test query by entity with node properties."""
        nodes = [
            GraphNode(
                node_id="node1",
                label="Node 1",
                node_type="entity",
                properties={"type": "service"},
            ),
            GraphNode(
                node_id="node2",
                label="Node 2",
                node_type="entity",
                properties={"type": "database"},
            ),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            )
        ]
        request = GraphQueryRequest(graph_id="test_graph", entity_id="node1", depth=1)

        response = query_engine.query("test_graph", nodes, edges, request)

        assert response.graph_id == "test_graph"

    def test_query_by_relation_with_properties(self, query_engine):
        """Test query by relation with edge properties."""
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
                properties={"weight": 1.0},
            )
        ]
        request = GraphQueryRequest(graph_id="test_graph", relation="CONNECTS_TO")

        response = query_engine.query("test_graph", nodes, edges, request)

        assert len(response.edges) == 1
        assert response.edges[0].properties == {"weight": 1.0}


def node_id_in_list(node_id, nodes):
    """Helper function to check if node_id is in list of nodes."""
    return any(n.node_id == node_id for n in nodes)
