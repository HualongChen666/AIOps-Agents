# -*- coding: utf-8 -*-
"""Tests for knowledge_graph_service/query.py module."""

import pytest
# Import the module to ensure coverage tracking
import extensions.addons.ai_plus.knowledge_graph_service.query as query_module
from extensions.addons.ai_plus.knowledge_graph_service.query import GraphQueryEngine
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    GraphNode,
    GraphEdge,
    GraphQueryRequest,
    GraphQueryResponse,
)

# Simple fixture to avoid database issues
@pytest.fixture(autouse=True)
def isolate_tests():
    """Isolate tests from global conftest."""
    yield


class TestGraphQueryEngine:
    """Test the GraphQueryEngine class."""

    @pytest.fixture
    def sample_nodes(self):
        """Create sample graph nodes."""
        return [
            GraphNode(node_id="node1", label="Server 1", node_type="server", properties={"name": "server1"}),
            GraphNode(node_id="node2", label="Server 2", node_type="server", properties={"name": "server2"}),
            GraphNode(node_id="node3", label="Database 1", node_type="database", properties={"name": "db1"}),
            GraphNode(node_id="node4", label="Service 1", node_type="service", properties={"name": "svc1"}),
            GraphNode(node_id="node5", label="Load Balancer 1", node_type="loadbalancer", properties={"name": "lb1"}),
        ]

    @pytest.fixture
    def sample_edges(self):
        """Create sample graph edges."""
        return [
            GraphEdge(edge_id="edge1", source_id="node1", target_id="node2", relation="connects"),
            GraphEdge(edge_id="edge2", source_id="node2", target_id="node3", relation="depends_on"),
            GraphEdge(edge_id="edge3", source_id="node3", target_id="node4", relation="hosts"),
            GraphEdge(edge_id="edge4", source_id="node4", target_id="node5", relation="behind"),
            GraphEdge(edge_id="edge5", source_id="node1", target_id="node5", relation="connects"),
        ]

    @pytest.fixture
    def engine(self):
        """Create a GraphQueryEngine instance."""
        return GraphQueryEngine()

    def test_query_default(self, engine, sample_nodes, sample_edges):
        """Test default query (no entity_id or relation)."""
        request = GraphQueryRequest(graph_id="graph1", entity_id=None, relation=None, depth=2, top_k=3)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert result.graph_id == "graph1"
        assert len(result.nodes) == 3  # top_k limit
        assert result.edges == []
        assert result.total == 5  # total nodes

    def test_query_default_top_k_all(self, engine, sample_nodes, sample_edges):
        """Test default query with top_k larger than node count."""
        request = GraphQueryRequest(graph_id="graph1", entity_id=None, relation=None, depth=2, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert len(result.nodes) == 5
        assert result.total == 5

    def test_query_by_entity_basic(self, engine, sample_nodes, sample_edges):
        """Test query by entity ID."""
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", relation=None, depth=1, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert result.graph_id == "graph1"
        assert len(result.nodes) >= 1
        assert any(node.node_id == "node1" for node in result.nodes)
        assert result.total >= 1

    def test_query_by_entity_depth_0(self, engine, sample_nodes, sample_edges):
        """Test query by entity with depth 0."""
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", relation=None, depth=0, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert len(result.nodes) == 1
        assert result.nodes[0].node_id == "node1"
        assert result.total == 1

    def test_query_by_entity_depth_1(self, engine, sample_nodes, sample_edges):
        """Test query by entity with depth 1."""
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", relation=None, depth=1, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        # Should include node1 and its direct neighbors (node2, node5)
        node_ids = {node.node_id for node in result.nodes}
        assert "node1" in node_ids
        assert len(node_ids) >= 2

    def test_query_by_entity_depth_2(self, engine, sample_nodes, sample_edges):
        """Test query by entity with depth 2."""
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", relation=None, depth=2, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        # Should include node1, neighbors, and neighbors of neighbors
        node_ids = {node.node_id for node in result.nodes}
        assert "node1" in node_ids
        assert len(node_ids) >= 3

    def test_query_by_entity_nonexistent(self, engine, sample_nodes, sample_edges):
        """Test query by non-existent entity ID."""
        request = GraphQueryRequest(graph_id="graph1", entity_id="nonexistent", relation=None, depth=2, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert result.nodes == []
        assert result.edges == []
        assert result.total == 0

    def test_query_by_entity_with_top_k(self, engine, sample_nodes, sample_edges):
        """Test query by entity with top_k limit."""
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", relation=None, depth=2, top_k=2)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert len(result.nodes) <= 2
        assert result.total >= 2  # Total should reflect all found nodes

    def test_query_by_relation(self, engine, sample_nodes, sample_edges):
        """Test query by relation type."""
        request = GraphQueryRequest(graph_id="graph1", entity_id=None, relation="connects", depth=2, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert result.graph_id == "graph1"
        assert len(result.edges) == 2  # Two "connects" edges
        assert all(edge.relation == "connects" for edge in result.edges)
        assert result.total >= 2

    def test_query_by_relation_single_edge(self, engine, sample_nodes, sample_edges):
        """Test query by relation with single matching edge."""
        request = GraphQueryRequest(graph_id="graph1", entity_id=None, relation="hosts", depth=2, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert len(result.edges) == 1
        assert result.edges[0].relation == "hosts"

    def test_query_by_relation_nonexistent(self, engine, sample_nodes, sample_edges):
        """Test query by non-existent relation."""
        request = GraphQueryRequest(graph_id="graph1", entity_id=None, relation="nonexistent", depth=2, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert result.edges == []
        assert result.nodes == []
        assert result.total == 0

    def test_query_by_relation_connected_nodes(self, engine, sample_nodes, sample_edges):
        """Test that relation query includes connected nodes."""
        request = GraphQueryRequest(graph_id="graph1", entity_id=None, relation="depends_on", depth=2, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        # Should include node2 and node3 which are connected by "depends_on"
        node_ids = {node.node_id for node in result.nodes}
        assert "node2" in node_ids
        assert "node3" in node_ids

    def test_query_bidirectional_edges(self, engine, sample_nodes, sample_edges):
        """Test that bidirectional edge traversal works."""
        # Add a reverse edge
        edges = sample_edges + [
            GraphEdge(edge_id="edge6", source_id="node3", target_id="node2", relation="reverse_depends")
        ]
        
        request = GraphQueryRequest(graph_id="graph1", entity_id="node2", relation=None, depth=1, top_k=10)
        result = engine.query("graph1", sample_nodes, edges, request)
        
        node_ids = {node.node_id for node in result.nodes}
        # Should include neighbors in both directions
        assert "node1" in node_ids or "node3" in node_ids

    def test_query_empty_graph(self, engine):
        """Test query on empty graph."""
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", relation=None, depth=2, top_k=10)
        result = engine.query("graph1", [], [], request)
        
        assert result.nodes == []
        assert result.edges == []
        assert result.total == 0

    def test_query_empty_nodes_with_edges(self, engine):
        """Test query with edges but no nodes."""
        edges = [GraphEdge(edge_id="edge1", source_id="node1", target_id="node2", relation="test")]
        request = GraphQueryRequest(graph_id="graph1", entity_id=None, relation="test", depth=2, top_k=10)
        result = engine.query("graph1", [], edges, request)
        
        assert result.edges == [edges[0]]
        assert result.nodes == []
        assert result.total == 0

    def test_find_shortest_path_direct_connection(self, engine, sample_nodes, sample_edges):
        """Test finding shortest path with direct connection."""
        path = engine.find_shortest_path(sample_nodes, sample_edges, "node1", "node2")
        
        assert path is not None
        assert path[0] == "node1"
        assert path[-1] == "node2"

    def test_find_shortest_path_multi_hop(self, engine, sample_nodes, sample_edges):
        """Test finding shortest path with multiple hops."""
        path = engine.find_shortest_path(sample_nodes, sample_edges, "node1", "node3")
        
        assert path is not None
        assert path[0] == "node1"
        assert path[-1] == "node3"
        assert len(path) >= 2

    def test_find_shortest_path_no_path(self, engine, sample_nodes, sample_edges):
        """Test finding shortest path when no path exists."""
        # Add isolated node
        nodes = sample_nodes + [GraphNode(node_id="isolated", label="Isolated", node_type="test", properties={})]
        
        path = engine.find_shortest_path(nodes, sample_edges, "node1", "isolated")
        
        assert path is None

    def test_find_shortest_path_nonexistent_start(self, engine, sample_nodes, sample_edges):
        """Test finding shortest path with non-existent start node."""
        path = engine.find_shortest_path(sample_nodes, sample_edges, "nonexistent", "node1")
        
        assert path is None

    def test_find_shortest_path_nonexistent_end(self, engine, sample_nodes, sample_edges):
        """Test finding shortest path with non-existent end node."""
        path = engine.find_shortest_path(sample_nodes, sample_edges, "node1", "nonexistent")
        
        assert path is None

    def test_find_shortest_path_same_node(self, engine, sample_nodes, sample_edges):
        """Test finding shortest path from node to itself."""
        path = engine.find_shortest_path(sample_nodes, sample_edges, "node1", "node1")
        
        assert path is not None
        assert path == ["node1"]

    def test_find_shortest_path_max_depth_limit(self, engine, sample_nodes, sample_edges):
        """Test that max_depth limits the search."""
        path = engine.find_shortest_path(sample_nodes, sample_edges, "node1", "node4", max_depth=1)
        
        # With max_depth=1, should not find path that requires multiple hops
        # node1 -> node2 -> node3 -> node4 requires 3 hops
        assert path is None or len(path) <= 2

    def test_find_shortest_path_max_depth_sufficient(self, engine, sample_nodes, sample_edges):
        """Test that sufficient max_depth allows finding path."""
        path = engine.find_shortest_path(sample_nodes, sample_edges, "node1", "node4", max_depth=5)
        
        assert path is not None
        assert path[0] == "node1"
        assert path[-1] == "node4"

    def test_find_shortest_path_empty_graph(self, engine):
        """Test finding shortest path in empty graph."""
        path = engine.find_shortest_path([], [], "node1", "node2")
        
        assert path is None

    def test_query_entity_id_priority_over_relation(self, engine, sample_nodes, sample_edges):
        """Test that entity_id takes priority over relation when both are provided."""
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", relation="connects", depth=1, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        # Should use entity query, not relation query
        node_ids = {node.node_id for node in result.nodes}
        assert "node1" in node_ids

    def test_query_response_structure(self, engine, sample_nodes, sample_edges):
        """Test that query response has correct structure."""
        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", relation=None, depth=1, top_k=10)
        result = engine.query("graph1", sample_nodes, sample_edges, request)
        
        assert isinstance(result, GraphQueryResponse)
        assert hasattr(result, 'graph_id')
        assert hasattr(result, 'nodes')
        assert hasattr(result, 'edges')
        assert hasattr(result, 'total')
        assert isinstance(result.nodes, list)
        assert isinstance(result.edges, list)
        assert isinstance(result.total, int)

    def test_query_complex_graph(self, engine):
        """Test query on a more complex graph structure."""
        nodes = [
            GraphNode(node_id=f"node{i}", label=f"Node {i}", node_type="test", properties={"id": i})
            for i in range(10)
        ]
        edges = [
            GraphEdge(edge_id=f"edge{i}", source_id=f"node{i}", target_id=f"node{i+1}", relation="link")
            for i in range(9)
        ]
        
        request = GraphQueryRequest(graph_id="complex_graph", entity_id="node0", relation=None, depth=3, top_k=10)
        result = engine.query("complex_graph", nodes, edges, request)
        
        assert result.total >= 4  # node0 + 3 neighbors
        assert result.graph_id == "complex_graph"

    def test_query_with_circular_dependencies(self, engine):
        """Test query on graph with circular dependencies."""
        nodes = [
            GraphNode(node_id="a", label="A", node_type="test", properties={}),
            GraphNode(node_id="b", label="B", node_type="test", properties={}),
            GraphNode(node_id="c", label="C", node_type="test", properties={}),
        ]
        edges = [
            GraphEdge(edge_id="e1", source_id="a", target_id="b", relation="dep"),
            GraphEdge(edge_id="e2", source_id="b", target_id="c", relation="dep"),
            GraphEdge(edge_id="e3", source_id="c", target_id="a", relation="dep"),
        ]
        
        request = GraphQueryRequest(graph_id="circular_graph", entity_id="a", relation=None, depth=5, top_k=10)
        result = engine.query("circular_graph", nodes, edges, request)
        
        # Should handle circular dependencies without infinite loop
        assert result.total == 3  # All nodes should be visited
        node_ids = {node.node_id for node in result.nodes}
        assert node_ids == {"a", "b", "c"}

    def test_query_disconnected_components(self, engine):
        """Test query on graph with disconnected components."""
        nodes = [
            GraphNode(node_id="a1", label="A1", node_type="test", properties={}),
            GraphNode(node_id="a2", label="A2", node_type="test", properties={}),
            GraphNode(node_id="b1", label="B1", node_type="test", properties={}),
            GraphNode(node_id="b2", label="B2", node_type="test", properties={}),
        ]
        edges = [
            GraphEdge(edge_id="e1", source_id="a1", target_id="a2", relation="link"),
            GraphEdge(edge_id="e2", source_id="b1", target_id="b2", relation="link"),
        ]
        
        request = GraphQueryRequest(graph_id="disconnected_graph", entity_id="a1", relation=None, depth=2, top_k=10)
        result = engine.query("disconnected_graph", nodes, edges, request)
        
        # Should only return component containing a1
        node_ids = {node.node_id for node in result.nodes}
        assert "a1" in node_ids
        assert "a2" in node_ids
        assert "b1" not in node_ids
        assert "b2" not in node_ids
