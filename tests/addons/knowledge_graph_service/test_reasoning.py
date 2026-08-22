# -*- coding: utf-8 -*-
"""Tests for GraphReasoningEngine module."""

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.reasoning import (
    GraphReasoningEngine,
)
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    GraphEdge,
    GraphNode,
    GraphReasonRequest,
)


class TestGraphReasoningEngine:
    """Test cases for GraphReasoningEngine class."""

    def test_reason_neighbors(self):
        """Test reasoning for neighbors."""
        engine = GraphReasoningEngine()
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
                source_id="node1",
                target_id="node3",
                relation="DEPENDS_ON",
            ),
        ]
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="neighbors"
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 2
        assert len(response.results) == 2
        assert response.results[0]["node_id"] == "node2"
        assert response.results[1]["node_id"] == "node3"

    def test_reason_neighbors_with_relation_filter(self):
        """Test reasoning for neighbors with relation filter."""
        engine = GraphReasoningEngine()
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
                source_id="node1",
                target_id="node3",
                relation="DEPENDS_ON",
            ),
        ]
        request = GraphReasonRequest(
            graph_id="graph1",
            node_id="node1",
            reason_type="neighbors",
            relation="CONNECTS_TO",
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 1
        assert len(response.results) == 1
        assert response.results[0]["node_id"] == "node2"
        assert response.results[0]["relation"] == "CONNECTS_TO"

    def test_reason_transitive_closure(self):
        """Test reasoning for transitive closure."""
        engine = GraphReasoningEngine()
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
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="transitive", max_depth=3
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 2
        assert len(response.results) == 2
        # Should include node2 at distance 1 and node3 at distance 2
        distances = {r["node_id"]: r["distance"] for r in response.results}
        assert distances["node2"] == 1
        assert distances["node3"] == 2

    def test_reason_transitive_closure_with_relation_filter(self):
        """Test transitive closure with relation filter."""
        engine = GraphReasoningEngine()
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
        request = GraphReasonRequest(
            graph_id="graph1",
            node_id="node1",
            reason_type="transitive",
            relation="CONNECTS_TO",
            max_depth=3,
        )

        response = engine.reason("graph1", nodes, edges, request)

        # Should only include node2 since node3 is reached via DEPENDS_ON
        assert response.total == 1
        assert response.results[0]["node_id"] == "node2"

    def test_reason_pagerank(self):
        """Test PageRank reasoning."""
        engine = GraphReasoningEngine()
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
                source_id="node1",
                target_id="node3",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="pagerank"
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 3
        assert len(response.results) == 3
        # All results should have scores
        for result in response.results:
            assert "score" in result
            assert isinstance(result["score"], float)

    def test_reason_paths(self):
        """Test path reasoning."""
        engine = GraphReasoningEngine()
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
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="paths", max_depth=3
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total >= 1
        # Should include at least the direct path
        paths = [r["path"] for r in response.results]
        assert ["node1", "node2"] in paths or ["node1", "node2", "node3"] in paths

    def test_reason_paths_with_relation_filter(self):
        """Test path reasoning with relation filter."""
        engine = GraphReasoningEngine()
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
        request = GraphReasonRequest(
            graph_id="graph1",
            node_id="node1",
            reason_type="paths",
            relation="CONNECTS_TO",
            max_depth=3,
        )

        response = engine.reason("graph1", nodes, edges, request)

        # Should only include paths using CONNECTS_TO relation
        for result in response.results:
            path = result["path"]
            assert len(path) <= 2  # Only node1 -> node2

    def test_reason_unknown_type_defaults_to_neighbors(self):
        """Test that unknown reason type defaults to neighbors."""
        engine = GraphReasoningEngine()
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
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="unknown"
        )

        response = engine.reason("graph1", nodes, edges, request)

        # Should default to neighbors
        assert response.total == 1
        assert response.results[0]["node_id"] == "node2"

    def test_reason_node_not_found(self):
        """Test reasoning when node doesn't exist."""
        engine = GraphReasoningEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
        ]
        edges = []
        request = GraphReasonRequest(
            graph_id="graph1", node_id="nonexistent", reason_type="neighbors"
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 0
        assert len(response.results) == 0

    def test_reason_empty_graph(self):
        """Test reasoning on empty graph."""
        engine = GraphReasoningEngine()
        nodes = []
        edges = []
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="neighbors"
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 0
        assert len(response.results) == 0

    def test_reason_pagerank_empty_graph(self):
        """Test PageRank on empty graph."""
        engine = GraphReasoningEngine()
        nodes = []
        edges = []
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="pagerank"
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 0
        assert len(response.results) == 0

    def test_reason_transitive_closure_max_depth(self):
        """Test transitive closure with max depth limit."""
        engine = GraphReasoningEngine()
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
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="transitive", max_depth=2
        )

        response = engine.reason("graph1", nodes, edges, request)

        # Should only include nodes within depth 2
        assert response.total == 2
        node_ids = {r["node_id"] for r in response.results}
        assert node_ids == {"node2", "node3"}

    def test_reason_paths_max_depth(self):
        """Test path reasoning with max depth limit."""
        engine = GraphReasoningEngine()
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
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="paths", max_depth=2
        )

        response = engine.reason("graph1", nodes, edges, request)

        # All paths should be within max depth
        for result in response.results:
            assert len(result["path"]) <= 3  # max_depth + 1

    def test_reason_neighbors_no_edges(self):
        """Test neighbors reasoning when node has no edges."""
        engine = GraphReasoningEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = []
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="neighbors"
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 0
        assert len(response.results) == 0

    def test_reason_transitive_closure_circular(self):
        """Test transitive closure with circular references."""
        engine = GraphReasoningEngine()
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
            GraphEdge(
                edge_id="edge3",
                source_id="node3",
                target_id="node1",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="transitive", max_depth=3
        )

        response = engine.reason("graph1", nodes, edges, request)

        # Should handle circular references without infinite loop
        # The algorithm includes the starting node when it's reachable via a cycle
        assert response.total == 3
        node_ids = {r["node_id"] for r in response.results}
        assert node_ids == {"node1", "node2", "node3"}

    def test_reason_paths_no_cycles(self):
        """Test that path reasoning doesn't include cycles."""
        engine = GraphReasoningEngine()
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
            GraphEdge(
                edge_id="edge2",
                source_id="node2",
                target_id="node1",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="paths", max_depth=3
        )

        response = engine.reason("graph1", nodes, edges, request)

        # Paths should not contain cycles
        for result in response.results:
            path = result["path"]
            assert len(path) == len(set(path))

    def test_reason_pagerank_single_node(self):
        """Test PageRank with single node."""
        engine = GraphReasoningEngine()
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
        ]
        edges = []
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="pagerank"
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 1
        assert response.results[0]["node_id"] == "node1"
        # With damping factor 0.85, single node score converges to 1.0
        # But initial distribution is 1.0/1 = 1.0, after iterations it's (1-0.85)/1 + 0.85*0 = 0.15
        # Actually the algorithm gives it a score based on the damping factor
        assert 0 < response.results[0]["score"] <= 1.0

    def test_reason_neighbors_with_properties(self):
        """Test that edge properties are included in neighbor results."""
        engine = GraphReasoningEngine()
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
                properties={"weight": 0.5, "type": "strong"},
            ),
        ]
        request = GraphReasonRequest(
            graph_id="graph1", node_id="node1", reason_type="neighbors"
        )

        response = engine.reason("graph1", nodes, edges, request)

        assert response.total == 1
        assert response.results[0]["properties"] == {"weight": 0.5, "type": "strong"}
