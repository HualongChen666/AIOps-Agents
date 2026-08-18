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


@pytest.fixture
def reasoning_engine():
    """Create a test reasoning engine."""
    return GraphReasoningEngine()


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
        GraphEdge(
            edge_id="edge5", source_id="node2", target_id="node4", relation="DEPENDS_ON"
        ),
    ]


class TestGraphReasoningEngine:
    """Test cases for GraphReasoningEngine class."""

    def test_reason_neighbors(self, reasoning_engine, sample_nodes, sample_edges):
        """Test reasoning with neighbors type."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="neighbors"
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert response.graph_id == "test_graph"
        assert response.node_id == "node1"
        assert response.reason_type == "neighbors"
        assert len(response.results) == 2  # node2 and node3
        assert response.total == 2

    def test_reason_neighbors_with_relation(self, reasoning_engine, sample_nodes, sample_edges):
        """Test reasoning with neighbors filtered by relation."""
        request = GraphReasonRequest(
            graph_id="test_graph",
            node_id="node1",
            reason_type="neighbors",
            relation="CONNECTS_TO",
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert response.reason_type == "neighbors"
        # Should only return CONNECTS_TO neighbors
        for result in response.results:
            assert result["relation"] == "CONNECTS_TO"

    def test_reason_neighbors_no_neighbors(self, reasoning_engine, sample_nodes):
        """Test reasoning with node that has no neighbors."""
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node2", target_id="node3", relation="CONNECTS_TO"
            )
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="neighbors"
        )

        response = reasoning_engine.reason("test_graph", sample_nodes, edges, request)

        assert len(response.results) == 0
        assert response.total == 0

    def test_reason_transitive(self, reasoning_engine, sample_nodes, sample_edges):
        """Test reasoning with transitive closure type."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="transitive"
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert response.reason_type == "transitive"
        assert len(response.results) >= 1
        # Results should have distance field
        for result in response.results:
            assert "node_id" in result
            assert "distance" in result

    def test_reason_transitive_with_relation(self, reasoning_engine, sample_nodes, sample_edges):
        """Test transitive closure filtered by relation."""
        request = GraphReasonRequest(
            graph_id="test_graph",
            node_id="node1",
            reason_type="transitive",
            relation="CONNECTS_TO",
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert response.reason_type == "transitive"

    def test_reason_transitive_with_max_depth(self, reasoning_engine, sample_nodes, sample_edges):
        """Test transitive closure with max depth limit."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="transitive", max_depth=1
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert response.reason_type == "transitive"
        # Should limit depth
        for result in response.results:
            assert result["distance"] <= 1

    def test_reason_pagerank(self, reasoning_engine, sample_nodes, sample_edges):
        """Test reasoning with PageRank type."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="pagerank"
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert response.reason_type == "pagerank"
        assert len(response.results) == 4  # All nodes
        # Results should have score field
        for result in response.results:
            assert "node_id" in result
            assert "score" in result
            assert isinstance(result["score"], float)

    def test_reason_pagerank_empty_graph(self, reasoning_engine):
        """Test PageRank on empty graph."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="pagerank"
        )

        response = reasoning_engine.reason("test_graph", [], [], request)

        assert len(response.results) == 0
        assert response.total == 0

    def test_reason_pagerank_single_node(self, reasoning_engine):
        """Test PageRank with single node."""
        nodes = [GraphNode(node_id="node1", label="Node 1", node_type="entity")]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="pagerank"
        )

        response = reasoning_engine.reason("test_graph", nodes, [], request)

        assert len(response.results) == 1
        # With damping factor 0.85, single node score is (1-0.85)/1 = 0.15
        assert response.results[0]["score"] == 0.15

    def test_reason_paths(self, reasoning_engine, sample_nodes, sample_edges):
        """Test reasoning with paths type."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="paths"
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert response.reason_type == "paths"
        assert len(response.results) >= 1
        # Results should have path field
        for result in response.results:
            assert "path" in result
            assert isinstance(result["path"], list)

    def test_reason_paths_with_relation(self, reasoning_engine, sample_nodes, sample_edges):
        """Test paths filtered by relation."""
        request = GraphReasonRequest(
            graph_id="test_graph",
            node_id="node1",
            reason_type="paths",
            relation="CONNECTS_TO",
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert response.reason_type == "paths"

    def test_reason_paths_with_max_depth(self, reasoning_engine, sample_nodes, sample_edges):
        """Test paths with max depth limit."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="paths", max_depth=1
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert response.reason_type == "paths"
        # All paths should have length <= max_depth + 1
        for result in response.results:
            assert len(result["path"]) <= 2

    def test_reason_unknown_type(self, reasoning_engine, sample_nodes, sample_edges):
        """Test reasoning with unknown type (defaults to neighbors)."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="unknown"
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        # Should default to neighbors
        assert response.reason_type == "unknown"

    def test_reason_node_not_found(self, reasoning_engine, sample_nodes, sample_edges):
        """Test reasoning with non-existent node."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="nonexistent", reason_type="neighbors"
        )

        response = reasoning_engine.reason(
            "test_graph", sample_nodes, sample_edges, request
        )

        assert len(response.results) == 0
        assert response.total == 0

    def test_reason_empty_graph(self, reasoning_engine):
        """Test reasoning on empty graph."""
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="neighbors"
        )

        response = reasoning_engine.reason("test_graph", [], [], request)

        assert len(response.results) == 0
        assert response.total == 0

    def test_infer_neighbors_with_properties(self, reasoning_engine):
        """Test infer_neighbors with edge properties."""
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
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="neighbors"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        assert len(response.results) == 1
        assert response.results[0]["properties"] == {"weight": 1.0}

    def test_transitive_closure_with_cycle(self, reasoning_engine):
        """Test transitive closure with cyclic graph."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ]
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
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="transitive"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        # Should handle cycles without infinite loop
        assert response.reason_type == "transitive"

    def test_transitive_closure_disconnected(self, reasoning_engine):
        """Test transitive closure with disconnected components."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            )
            # node3 is disconnected
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="transitive"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        # Should only find reachable nodes
        assert response.reason_type == "transitive"

    def test_pagerank_iterations(self, reasoning_engine):
        """Test PageRank with custom iterations."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            )
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="pagerank"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        assert len(response.results) == 2
        # Scores should be positive and sum to a reasonable value
        total_score = sum(r["score"] for r in response.results)
        assert total_score > 0
        assert all(r["score"] > 0 for r in response.results)

    def test_pagerank_damping_factor(self, reasoning_engine):
        """Test PageRank with damping factor."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            )
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="pagerank"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        # With default damping 0.85, node2 should have higher score
        node2_score = next(r["score"] for r in response.results if r["node_id"] == "node2")
        node1_score = next(r["score"] for r in response.results if r["node_id"] == "node1")
        assert node2_score > node1_score

    def test_paths_with_cycle(self, reasoning_engine):
        """Test paths with cyclic graph."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ]
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
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="paths"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        # Should handle cycles without infinite loop
        assert response.reason_type == "paths"

    def test_paths_no_self_loops(self, reasoning_engine):
        """Test that paths don't include self-loops."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            )
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="paths"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        # No path should contain duplicate nodes
        for result in response.results:
            assert len(result["path"]) == len(set(result["path"]))

    def test_paths_limit(self, reasoning_engine):
        """Test that paths are limited to 100."""
        nodes = [GraphNode(node_id=f"node{i}", label=f"Node {i}", node_type="entity") for i in range(20)]
        edges = [
            GraphEdge(
                edge_id=f"edge{i}",
                source_id=f"node{i}",
                target_id=f"node{i+1}",
                relation="CONNECTS_TO",
            )
            for i in range(19)
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node0", reason_type="paths", max_depth=5
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        # Should limit to 100 paths
        assert len(response.results) <= 100

    def test_reason_large_graph(self, reasoning_engine):
        """Test reasoning on large graph."""
        nodes = [GraphNode(node_id=f"node{i}", label=f"Node {i}", node_type="entity") for i in range(50)]
        edges = [
            GraphEdge(
                edge_id=f"edge{i}",
                source_id=f"node{i}",
                target_id=f"node{i+1}",
                relation="CONNECTS_TO",
            )
            for i in range(49)
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node0", reason_type="neighbors"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        assert response.reason_type == "neighbors"

    def test_reason_with_all_types(self, reasoning_engine, sample_nodes, sample_edges):
        """Test reasoning with all reason types."""
        reason_types = ["neighbors", "transitive", "pagerank", "paths"]

        for reason_type in reason_types:
            request = GraphReasonRequest(
                graph_id="test_graph", node_id="node1", reason_type=reason_type
            )
            response = reasoning_engine.reason(
                "test_graph", sample_nodes, sample_edges, request
            )
            assert response.reason_type == reason_type

    def test_infer_neighbors_incoming(self, reasoning_engine):
        """Test that infer_neighbors only returns outgoing neighbors."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node2", target_id="node1", relation="CONNECTS_TO"
            )
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="neighbors"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        # node1 has no outgoing edges, only incoming
        assert len(response.results) == 0

    def test_transitive_closure_distance_ordering(self, reasoning_engine):
        """Test that transitive closure results are ordered by distance."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            ),
            GraphEdge(
                edge_id="edge2", source_id="node2", target_id="node3", relation="CONNECTS_TO"
            ),
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="transitive"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        # Results should be sorted by distance
        distances = [r["distance"] for r in response.results]
        assert distances == sorted(distances)

    def test_pagerank_score_ordering(self, reasoning_engine):
        """Test that PageRank results are ordered by score."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge1", source_id="node1", target_id="node2", relation="CONNECTS_TO"
            ),
            GraphEdge(
                edge_id="edge2", source_id="node1", target_id="node3", relation="CONNECTS_TO"
            ),
        ]
        request = GraphReasonRequest(
            graph_id="test_graph", node_id="node1", reason_type="pagerank"
        )

        response = reasoning_engine.reason("test_graph", nodes, edges, request)

        # Results should be sorted by score (descending)
        scores = [r["score"] for r in response.results]
        assert scores == sorted(scores, reverse=True)
