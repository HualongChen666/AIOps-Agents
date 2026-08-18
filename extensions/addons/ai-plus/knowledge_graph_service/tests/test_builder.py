# -*- coding: utf-8 -*-
"""Tests for GraphBuilder module."""

import pytest
from collections import OrderedDict

from extensions.addons.ai_plus.knowledge_graph_service.builder import GraphBuilder
from extensions.addons.ai_plus.knowledge_graph_service.graph_store import GraphStore
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    GraphBuildRequest,
    GraphEdge,
    GraphNode,
)


@pytest.fixture
async def graph_store():
    """Create a test graph store."""
    store = GraphStore()
    await store.connect()
    return store


@pytest.fixture
def graph_builder(graph_store):
    """Create a test graph builder."""
    return GraphBuilder(graph_store)


class TestGraphBuilder:
    """Test cases for GraphBuilder class."""

    @pytest.mark.asyncio
    async def test_build_graph_basic(self, graph_builder):
        """Test basic graph building with nodes and edges."""
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
        request = GraphBuildRequest(
            graph_name="test-graph", nodes=nodes, edges=edges, source="test"
        )

        graph = await graph_builder.build_graph(request)

        assert graph.name == "test-graph"
        assert len(graph.nodes) == 2
        assert len(graph.edges) == 1
        assert graph.metadata["source"] == "test"

    @pytest.mark.asyncio
    async def test_build_graph_empty(self, graph_builder):
        """Test building an empty graph."""
        request = GraphBuildRequest(
            graph_name="empty-graph", nodes=[], edges=[], source="test"
        )

        graph = await graph_builder.build_graph(request)

        assert graph.name == "empty-graph"
        assert len(graph.nodes) == 0
        assert len(graph.edges) == 0

    @pytest.mark.asyncio
    async def test_build_graph_with_metadata(self, graph_builder):
        """Test building graph with custom metadata."""
        nodes = [GraphNode(node_id="node1", label="Node 1", node_type="entity")]
        request = GraphBuildRequest(
            graph_name="test-graph",
            nodes=nodes,
            edges=[],
            source="test",
            metadata={"custom_key": "custom_value"},
        )

        graph = await graph_builder.build_graph(request)

        assert graph.metadata["source"] == "test"
        assert graph.metadata["custom_key"] == "custom_value"

    @pytest.mark.asyncio
    async def test_deduplicate_nodes(self, graph_builder):
        """Test node deduplication."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node1", label="Node 1 Duplicate", node_type="entity"),
        ]
        request = GraphBuildRequest(
            graph_name="test-graph", nodes=nodes, edges=[], source="test"
        )

        graph = await graph_builder.build_graph(request)

        assert len(graph.nodes) == 2
        node_ids = {node.node_id for node in graph.nodes}
        assert node_ids == {"node1", "node2"}

    @pytest.mark.asyncio
    async def test_deduplicate_edges(self, graph_builder):
        """Test edge deduplication."""
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
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphBuildRequest(
            graph_name="test-graph", nodes=nodes, edges=edges, source="test"
        )

        graph = await graph_builder.build_graph(request)

        assert len(graph.edges) == 1

    def test_deduplicate_nodes_static(self):
        """Test static node deduplication method."""
        nodes = [
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            GraphNode(node_id="node1", label="Node 1 Duplicate", node_type="entity"),
        ]

        deduplicated = GraphBuilder._deduplicate_nodes(nodes)

        assert len(deduplicated) == 2
        assert isinstance(deduplicated, list)
        # Check order is preserved
        assert deduplicated[0].node_id == "node1"
        assert deduplicated[1].node_id == "node2"

    def test_deduplicate_edges_static(self):
        """Test static edge deduplication method."""
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
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
        ]

        deduplicated = GraphBuilder._deduplicate_edges(edges)

        assert len(deduplicated) == 2
        assert isinstance(deduplicated, list)

    def test_deduplicate_nodes_empty(self):
        """Test deduplication with empty list."""
        deduplicated = GraphBuilder._deduplicate_nodes([])
        assert deduplicated == []

    def test_deduplicate_edges_empty(self):
        """Test edge deduplication with empty list."""
        deduplicated = GraphBuilder._deduplicate_edges([])
        assert deduplicated == []

    def test_deduplicate_nodes_single(self):
        """Test deduplication with single node."""
        nodes = [GraphNode(node_id="node1", label="Node 1", node_type="entity")]
        deduplicated = GraphBuilder._deduplicate_nodes(nodes)
        assert len(deduplicated) == 1
        assert deduplicated[0].node_id == "node1"

    def test_deduplicate_edges_single(self):
        """Test edge deduplication with single edge."""
        edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            )
        ]
        deduplicated = GraphBuilder._deduplicate_edges(edges)
        assert len(deduplicated) == 1
        assert deduplicated[0].edge_id == "edge1"

    @pytest.mark.asyncio
    async def test_build_graph_large_dataset(self, graph_builder):
        """Test building graph with large dataset."""
        nodes = [
            GraphNode(node_id=f"node{i}", label=f"Node {i}", node_type="entity")
            for i in range(100)
        ]
        edges = [
            GraphEdge(
                edge_id=f"edge{i}",
                source_id=f"node{i}",
                target_id=f"node{i+1}",
                relation="CONNECTS_TO",
            )
            for i in range(99)
        ]
        request = GraphBuildRequest(
            graph_name="large-graph", nodes=nodes, edges=edges, source="test"
        )

        graph = await graph_builder.build_graph(request)

        assert len(graph.nodes) == 100
        assert len(graph.edges) == 99

    @pytest.mark.asyncio
    async def test_build_graph_clears_store(self, graph_builder, graph_store):
        """Test that build_graph clears the store before loading."""
        # First graph
        nodes1 = [GraphNode(node_id="node1", label="Node 1", node_type="entity")]
        request1 = GraphBuildRequest(
            graph_name="graph1", nodes=nodes1, edges=[], source="test"
        )
        await graph_builder.build_graph(request1)

        # Second graph should clear the first
        nodes2 = [GraphNode(node_id="node2", label="Node 2", node_type="entity")]
        request2 = GraphBuildRequest(
            graph_name="graph2", nodes=nodes2, edges=[], source="test"
        )
        await graph_builder.build_graph(request2)

        # Check store only has second graph
        all_nodes = await graph_store.query_nodes()
        assert len(all_nodes) == 1
        assert all_nodes[0].node_id == "node2"

    @pytest.mark.asyncio
    async def test_build_graph_preserves_order(self, graph_builder):
        """Test that node and edge order is preserved."""
        nodes = [
            GraphNode(node_id="node3", label="Node 3", node_type="entity"),
            GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            GraphNode(node_id="node2", label="Node 2", node_type="entity"),
        ]
        edges = [
            GraphEdge(
                edge_id="edge3",
                source_id="node3",
                target_id="node1",
                relation="CONNECTS_TO",
            ),
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="CONNECTS_TO",
            ),
        ]
        request = GraphBuildRequest(
            graph_name="test-graph", nodes=nodes, edges=edges, source="test"
        )

        graph = await graph_builder.build_graph(request)

        assert graph.nodes[0].node_id == "node3"
        assert graph.nodes[1].node_id == "node1"
        assert graph.nodes[2].node_id == "node2"
        assert graph.edges[0].edge_id == "edge3"
        assert graph.edges[1].edge_id == "edge1"
