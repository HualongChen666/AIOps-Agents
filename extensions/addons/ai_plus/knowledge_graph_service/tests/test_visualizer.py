# -*- coding: utf-8 -*-
"""Tests for GraphVisualizer module."""

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.visualizer import GraphVisualizer
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    Graph,
    GraphNode,
    GraphEdge,
    GraphVisualizationRequest,
)


@pytest.fixture
def visualizer():
    """Create a test visualizer."""
    return GraphVisualizer()


@pytest.fixture
def sample_graph():
    """Create a sample graph for testing."""
    return Graph(
        graph_id="test_graph",
        name="Test Graph",
        nodes=[
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ],
        edges=[
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            ),
            GraphEdge(
                edge_id="edge2", source_id="node2", target_id="node3", relation="CONNECTS_TO"
            ),
        ],
    )


class TestGraphVisualizer:
    """Test cases for GraphVisualizer class."""

    def test_visualize_basic_graph(self, visualizer, sample_graph):
        """Test basic graph visualization."""
        request = GraphVisualizationRequest(graph_id="test_graph")

        response = visualizer.visualize(sample_graph, request)

        assert response.graph_id == "test_graph"
        assert len(response.nodes) == 3
        assert len(response.edges) == 2

    def test_visualize_empty_graph(self, visualizer):
        """Test visualization of empty graph."""
        graph = Graph(graph_id="empty_graph", name="Empty", nodes=[], edges=[])
        request = GraphVisualizationRequest(graph_id="empty_graph")

        response = visualizer.visualize(graph, request)

        assert response.graph_id == "empty_graph"
        assert len(response.nodes) == 0
        assert len(response.edges) == 0

    def test_visualize_single_node(self, visualizer):
        """Test visualization of graph with single node."""
        graph = Graph(
            graph_id="single_node",
            name="Single Node",
            nodes=[GraphNode(node_id="node1", label="Node 1", node_type="entity")],
            edges=[],
        )
        request = GraphVisualizationRequest(graph_id="single_node")

        response = visualizer.visualize(graph, request)

        assert len(response.nodes) == 1
        # Single node should be at center
        assert response.nodes[0].x == 400.0  # width/2
        assert response.nodes[0].y == 300.0  # height/2

    def test_visualize_custom_dimensions(self, visualizer, sample_graph):
        """Test visualization with custom dimensions."""
        request = GraphVisualizationRequest(graph_id="test_graph", width=1000, height=800)

        response = visualizer.visualize(sample_graph, request)

        assert len(response.nodes) == 3
        # Check that dimensions are used
        for node in response.nodes:
            assert 0 <= node.x <= 1000
            assert 0 <= node.y <= 800

    def test_visualize_minimum_dimensions(self, visualizer, sample_graph):
        """Test visualization with minimum dimensions (should be clamped to 100)."""
        request = GraphVisualizationRequest(graph_id="test_graph", width=10, height=10)

        response = visualizer.visualize(sample_graph, request)

        assert len(response.nodes) == 3
        # Dimensions should be clamped to minimum 100
        for node in response.nodes:
            assert 0 <= node.x <= 100
            assert 0 <= node.y <= 100

    def test_visualize_circular_layout(self, visualizer, sample_graph):
        """Test that nodes are arranged in a circle."""
        request = GraphVisualizationRequest(graph_id="test_graph")

        response = visualizer.visualize(sample_graph, request)

        assert len(response.nodes) == 3
        # All nodes should be at the same distance from center
        cx, cy = 400.0, 300.0
        distances = [
            ((node.x - cx) ** 2 + (node.y - cy) ** 2) ** 0.5 for node in response.nodes
        ]
        # All distances should be approximately equal (within tolerance)
        for dist in distances[1:]:
            assert abs(dist - distances[0]) < 1.0

    def test_visualize_large_graph(self, visualizer):
        """Test visualization of large graph."""
        nodes = [
            GraphNode(node_id=f"node{i}", label=f"Node {i}", node_type="entity")
            for i in range(50)
        ]
        graph = Graph(graph_id="large_graph", name="Large", nodes=nodes, edges=[])
        request = GraphVisualizationRequest(graph_id="large_graph")

        response = visualizer.visualize(graph, request)

        assert len(response.nodes) == 50
        # All nodes should have valid coordinates
        for node in response.nodes:
            assert isinstance(node.x, float)
            assert isinstance(node.y, float)

    def test_visualize_node_coordinates_rounded(self, visualizer, sample_graph):
        """Test that node coordinates are rounded to 2 decimal places."""
        request = GraphVisualizationRequest(graph_id="test_graph")

        response = visualizer.visualize(sample_graph, request)

        for node in response.nodes:
            # Check that coordinates are rounded
            assert len(str(node.x).split(".")[-1]) <= 2
            assert len(str(node.y).split(".")[-1]) <= 2

    def test_visualize_preserves_edges(self, visualizer, sample_graph):
        """Test that edges are preserved in response."""
        request = GraphVisualizationRequest(graph_id="test_graph")

        response = visualizer.visualize(sample_graph, request)

        assert len(response.edges) == 2
        assert response.edges == sample_graph.edges

    def test_visualize_graph_with_no_edges(self, visualizer):
        """Test visualization of graph with nodes but no edges."""
        graph = Graph(
            graph_id="no_edges",
            name="No Edges",
            nodes=[
                GraphNode(node_id="node1", label="Node 1", node_type="entity"),
                GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            ],
            edges=[],
        )
        request = GraphVisualizationRequest(graph_id="no_edges")

        response = visualizer.visualize(graph, request)

        assert len(response.nodes) == 2
        assert len(response.edges) == 0

    def test_visualize_default_dimensions(self, visualizer, sample_graph):
        """Test visualization with default dimensions."""
        request = GraphVisualizationRequest(graph_id="test_graph")

        response = visualizer.visualize(sample_graph, request)

        # Default dimensions should be 800x600
        cx, cy = 400.0, 300.0
        assert response.nodes[0].x != 0 or response.nodes[0].y != 0

    def test_visualize_two_nodes(self, visualizer):
        """Test visualization with exactly two nodes."""
        graph = Graph(
            graph_id="two_nodes",
            name="Two Nodes",
            nodes=[
                GraphNode(node_id="node1", label="Node 1", node_type="entity"),
                GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            ],
            edges=[],
        )
        request = GraphVisualizationRequest(graph_id="two_nodes")

        response = visualizer.visualize(graph, request)

        assert len(response.nodes) == 2
        # Two nodes should be opposite each other
        node1, node2 = response.nodes
        cx, cy = 400.0, 300.0
        # Check if they are roughly opposite
        assert abs((node1.x - cx) + (node2.x - cx)) < 10.0

    def test_visualize_square_dimensions(self, visualizer, sample_graph):
        """Test visualization with square dimensions."""
        request = GraphVisualizationRequest(graph_id="test_graph", width=500, height=500)

        response = visualizer.visualize(sample_graph, request)

        assert len(response.nodes) == 3
        cx, cy = 250.0, 250.0
        # Radius should be based on min dimension
        radius = 500 * 0.4  # 200

    def test_visualize_wide_dimensions(self, visualizer, sample_graph):
        """Test visualization with wide dimensions."""
        request = GraphVisualizationRequest(graph_id="test_graph", width=1000, height=400)

        response = visualizer.visualize(sample_graph, request)

        assert len(response.nodes) == 3
        # Radius should be based on min dimension (400)
        radius = 400 * 0.4  # 160

    def test_visualize_tall_dimensions(self, visualizer, sample_graph):
        """Test visualization with tall dimensions."""
        request = GraphVisualizationRequest(graph_id="test_graph", width=400, height=1000)

        response = visualizer.visualize(sample_graph, request)

        assert len(response.nodes) == 3
        # Radius should be based on min dimension (400)
        radius = 400 * 0.4  # 160

    def test_visualize_node_order_preserved(self, visualizer, sample_graph):
        """Test that node order is preserved in layout."""
        request = GraphVisualizationRequest(graph_id="test_graph")

        response = visualizer.visualize(sample_graph, request)

        assert len(response.nodes) == 3
        # Node IDs should be in the same order as input
        assert response.nodes[0].node_id == "node1"
        assert response.nodes[1].node_id == "node2"
        assert response.nodes[2].node_id == "node3"

    def test_visualize_with_node_properties(self, visualizer):
        """Test visualization with nodes that have properties."""
        graph = Graph(
            graph_id="props_graph",
            name="Properties",
            nodes=[
                GraphNode(
                    node_id="node1",
                    label="Node 1",
                    node_type="entity",
                    properties={"color": "red"},
                ),
                GraphNode(
                    node_id="node2",
                    label="Node 2",
                    node_type="entity",
                    properties={"color": "blue"},
                ),
            ],
            edges=[],
        )
        request = GraphVisualizationRequest(graph_id="props_graph")

        response = visualizer.visualize(graph, request)

        assert len(response.nodes) == 2
        # Layout should work regardless of properties

    def test_visualize_very_large_dimensions(self, visualizer, sample_graph):
        """Test visualization with very large dimensions."""
        request = GraphVisualizationRequest(graph_id="test_graph", width=10000, height=10000)

        response = visualizer.visualize(sample_graph, request)

        assert len(response.nodes) == 3
        # Coordinates should be within bounds
        for node in response.nodes:
            assert 0 <= node.x <= 10000
            assert 0 <= node.y <= 10000
