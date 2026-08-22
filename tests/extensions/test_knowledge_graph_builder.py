# -*- coding: utf-8 -*-
"""Comprehensive tests for knowledge graph builder."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from extensions.addons.ai_plus.knowledge_graph_service.builder import GraphBuilder
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    Graph,
    GraphBuildRequest,
    GraphEdge,
    GraphNode,
)


class TestGraphBuilder:
    """Test suite for GraphBuilder class."""

    def test_initialization(self):
        """Test GraphBuilder initialization."""
        mock_store = MagicMock()
        builder = GraphBuilder(mock_store)
        
        assert builder.store is mock_store

    def test_deduplicate_nodes_empty_list(self):
        """Test deduplicating empty node list."""
        result = GraphBuilder._deduplicate_nodes([])
        assert result == []

    def test_deduplicate_nodes_single_node(self):
        """Test deduplicating single node."""
        node = GraphNode(node_id="node1", label="Test", node_type="test")
        result = GraphBuilder._deduplicate_nodes([node])
        
        assert len(result) == 1
        assert result[0] is node

    def test_deduplicate_nodes_no_duplicates(self):
        """Test deduplicating nodes with no duplicates."""
        node1 = GraphNode(node_id="node1", label="Test1", node_type="test")
        node2 = GraphNode(node_id="node2", label="Test2", node_type="test")
        node3 = GraphNode(node_id="node3", label="Test3", node_type="test")
        
        result = GraphBuilder._deduplicate_nodes([node1, node2, node3])
        
        assert len(result) == 3
        assert result[0].node_id == "node1"
        assert result[1].node_id == "node2"
        assert result[2].node_id == "node3"

    def test_deduplicate_nodes_with_duplicates(self):
        """Test deduplicating nodes with duplicate IDs."""
        node1 = GraphNode(node_id="node1", label="Test1", node_type="test")
        node2 = GraphNode(node_id="node1", label="Test2", node_type="test")  # Duplicate ID
        node3 = GraphNode(node_id="node3", label="Test3", node_type="test")
        
        result = GraphBuilder._deduplicate_nodes([node1, node2, node3])
        
        assert len(result) == 2
        # OrderedDict keeps the last occurrence, not the first
        assert result[0].node_id == "node1"
        assert result[0].label == "Test2"  # Last occurrence kept
        assert result[1].node_id == "node3"

    def test_deduplicate_nodes_preserves_order(self):
        """Test that deduplication preserves order of first occurrences."""
        node1 = GraphNode(node_id="node3", label="Test3", node_type="test")
        node2 = GraphNode(node_id="node1", label="Test1", node_type="test")
        node3 = GraphNode(node_id="node2", label="Test2", node_type="test")
        node4 = GraphNode(node_id="node1", label="Test1_dup", node_type="test")  # Duplicate
        
        result = GraphBuilder._deduplicate_nodes([node1, node2, node3, node4])
        
        assert len(result) == 3
        # OrderedDict preserves order of insertion, keeping last occurrence of duplicates
        assert result[0].node_id == "node3"
        assert result[1].node_id == "node1"  # Last occurrence of node1
        assert result[2].node_id == "node2"

    def test_deduplicate_edges_empty_list(self):
        """Test deduplicating empty edge list."""
        result = GraphBuilder._deduplicate_edges([])
        assert result == []

    def test_deduplicate_edges_single_edge(self):
        """Test deduplicating single edge."""
        edge = GraphEdge(edge_id="edge1", source_id="node1", target_id="node2", relation="connects")
        result = GraphBuilder._deduplicate_edges([edge])
        
        assert len(result) == 1
        assert result[0] is edge

    def test_deduplicate_edges_no_duplicates(self):
        """Test deduplicating edges with no duplicates."""
        edge1 = GraphEdge(edge_id="edge1", source_id="node1", target_id="node2", relation="connects")
        edge2 = GraphEdge(edge_id="edge2", source_id="node2", target_id="node3", relation="connects")
        edge3 = GraphEdge(edge_id="edge3", source_id="node3", target_id="node4", relation="connects")
        
        result = GraphBuilder._deduplicate_edges([edge1, edge2, edge3])
        
        assert len(result) == 3
        assert result[0].edge_id == "edge1"
        assert result[1].edge_id == "edge2"
        assert result[2].edge_id == "edge3"

    def test_deduplicate_edges_with_duplicates(self):
        """Test deduplicating edges with duplicate IDs."""
        edge1 = GraphEdge(edge_id="edge1", source_id="node1", target_id="node2", relation="connects")
        edge2 = GraphEdge(edge_id="edge1", source_id="node3", target_id="node4", relation="connects")  # Duplicate ID
        edge3 = GraphEdge(edge_id="edge3", source_id="node5", target_id="node6", relation="connects")
        
        result = GraphBuilder._deduplicate_edges([edge1, edge2, edge3])
        
        assert len(result) == 2
        # OrderedDict keeps the last occurrence, not the first
        assert result[0].edge_id == "edge1"
        assert result[0].source_id == "node3"  # Last occurrence kept
        assert result[1].edge_id == "edge3"

    def test_deduplicate_edges_preserves_order(self):
        """Test that edge deduplication preserves order of first occurrences."""
        edge1 = GraphEdge(edge_id="edge3", source_id="node1", target_id="node2", relation="connects")
        edge2 = GraphEdge(edge_id="edge1", source_id="node3", target_id="node4", relation="connects")
        edge3 = GraphEdge(edge_id="edge2", source_id="node5", target_id="node6", relation="connects")
        edge4 = GraphEdge(edge_id="edge1", source_id="node7", target_id="node8", relation="connects")  # Duplicate
        
        result = GraphBuilder._deduplicate_edges([edge1, edge2, edge3, edge4])
        
        assert len(result) == 3
        # OrderedDict preserves order of insertion, keeping last occurrence of duplicates
        assert result[0].edge_id == "edge3"
        assert result[1].edge_id == "edge1"  # Last occurrence of edge1
        assert result[2].edge_id == "edge2"

    @pytest.mark.asyncio
    async def test_build_graph_basic(self):
        """Test basic graph building."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        request = GraphBuildRequest(
            graph_name="test_graph",
            source="test",
            nodes=[
                GraphNode(node_id="node1", label="Test1", node_type="test"),
                GraphNode(node_id="node2", label="Test2", node_type="test"),
            ],
            edges=[
                GraphEdge(edge_id="edge1", source_id="node1", target_id="node2", relation="connects"),
            ],
        )
        
        result = await builder.build_graph(request)
        
        assert isinstance(result, Graph)
        assert result.name == "test_graph"
        assert len(result.nodes) == 2
        assert len(result.edges) == 1
        assert result.metadata["source"] == "test"
        assert result.graph_id is not None
        mock_store.clear.assert_called_once()
        mock_store.load_graph.assert_called_once()

    @pytest.mark.asyncio
    async def test_build_graph_with_metadata(self):
        """Test graph building with custom metadata."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        request = GraphBuildRequest(
            graph_name="test_graph",
            source="test",
            metadata={"custom": "value", "version": "1.0"},
            nodes=[
                GraphNode(node_id="node1", label="Test1", node_type="test"),
            ],
            edges=[],
        )
        
        result = await builder.build_graph(request)
        
        assert result.metadata["source"] == "test"
        assert result.metadata["custom"] == "value"
        assert result.metadata["version"] == "1.0"

    @pytest.mark.asyncio
    async def test_build_graph_deduplicates_nodes(self):
        """Test that graph building deduplicates nodes."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        request = GraphBuildRequest(
            graph_name="test_graph",
            source="test",
            nodes=[
                GraphNode(node_id="node1", label="Test1", node_type="test"),
                GraphNode(node_id="node1", label="Test1_dup", node_type="test"),  # Duplicate
                GraphNode(node_id="node2", label="Test2", node_type="test"),
            ],
            edges=[],
        )
        
        result = await builder.build_graph(request)
        
        assert len(result.nodes) == 2
        # OrderedDict keeps last occurrence
        assert result.nodes[0].label == "Test1_dup"  # Last occurrence kept

    @pytest.mark.asyncio
    async def test_build_graph_deduplicates_edges(self):
        """Test that graph building deduplicates edges."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        request = GraphBuildRequest(
            graph_name="test_graph",
            source="test",
            nodes=[
                GraphNode(node_id="node1", label="Test1", node_type="test"),
                GraphNode(node_id="node2", label="Test2", node_type="test"),
            ],
            edges=[
                GraphEdge(edge_id="edge1", source_id="node1", target_id="node2", relation="connects"),
                GraphEdge(edge_id="edge1", source_id="node2", target_id="node1", relation="connects"),  # Duplicate
            ],
        )
        
        result = await builder.build_graph(request)
        
        assert len(result.edges) == 1
        # OrderedDict keeps last occurrence
        assert result.edges[0].source_id == "node2"  # Last occurrence kept

    @pytest.mark.asyncio
    async def test_build_graph_empty_nodes_and_edges(self):
        """Test building graph with empty nodes and edges."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        request = GraphBuildRequest(
            graph_name="empty_graph",
            source="test",
            nodes=[],
            edges=[],
        )
        
        result = await builder.build_graph(request)
        
        assert len(result.nodes) == 0
        assert len(result.edges) == 0
        assert result.name == "empty_graph"

    @pytest.mark.asyncio
    async def test_build_graph_unique_graph_id(self):
        """Test that each built graph gets a unique ID."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        request = GraphBuildRequest(
            graph_name="test_graph",
            source="test",
            nodes=[GraphNode(node_id="node1", label="Test1", node_type="test")],
            edges=[],
        )
        
        graph1 = await builder.build_graph(request)
        graph2 = await builder.build_graph(request)
        
        assert graph1.graph_id != graph2.graph_id

    @pytest.mark.asyncio
    async def test_build_graph_calls_store_operations(self):
        """Test that build_graph calls store operations in correct order."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        request = GraphBuildRequest(
            graph_name="test_graph",
            source="test",
            nodes=[GraphNode(node_id="node1", label="Test1", node_type="test")],
            edges=[],
        )
        
        await builder.build_graph(request)
        
        # Verify store operations were called
        assert mock_store.clear.call_count == 1
        assert mock_store.load_graph.call_count == 1

    @pytest.mark.asyncio
    async def test_build_graph_large_dataset(self):
        """Test building graph with large number of nodes and edges."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        # Create 100 nodes and 200 edges
        nodes = [
            GraphNode(node_id=f"node{i}", label=f"Test{i}", node_type="test")
            for i in range(100)
        ]
        edges = [
            GraphEdge(
                edge_id=f"edge{i}",
                source_id=f"node{i % 100}",
                target_id=f"node{(i + 1) % 100}",
                relation="connects"
            )
            for i in range(200)
        ]
        
        request = GraphBuildRequest(
            graph_name="large_graph",
            source="test",
            nodes=nodes,
            edges=edges,
        )
        
        result = await builder.build_graph(request)
        
        assert len(result.nodes) == 100
        assert len(result.edges) == 200

    @pytest.mark.asyncio
    async def test_build_graph_with_all_duplicate_nodes(self):
        """Test building graph where all nodes have the same ID."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        request = GraphBuildRequest(
            graph_name="test_graph",
            source="test",
            nodes=[
                GraphNode(node_id="node1", label="Test1", node_type="test"),
                GraphNode(node_id="node1", label="Test2", node_type="test"),
                GraphNode(node_id="node1", label="Test3", node_type="test"),
            ],
            edges=[],
        )
        
        result = await builder.build_graph(request)
        
        assert len(result.nodes) == 1
        # OrderedDict keeps last occurrence
        assert result.nodes[0].label == "Test3"

    @pytest.mark.asyncio
    async def test_build_graph_with_all_duplicate_edges(self):
        """Test building graph where all edges have the same ID."""
        mock_store = AsyncMock()
        builder = GraphBuilder(mock_store)
        
        request = GraphBuildRequest(
            graph_name="test_graph",
            source="test",
            nodes=[
                GraphNode(node_id="node1", label="Test1", node_type="test"),
                GraphNode(node_id="node2", label="Test2", node_type="test"),
            ],
            edges=[
                GraphEdge(edge_id="edge1", source_id="node1", target_id="node2", relation="connects"),
                GraphEdge(edge_id="edge1", source_id="node2", target_id="node1", relation="connects"),
                GraphEdge(edge_id="edge1", source_id="node1", target_id="node2", relation="connects"),
            ],
        )
        
        result = await builder.build_graph(request)
        
        assert len(result.edges) == 1
        # OrderedDict keeps last occurrence
        assert result.edges[0].source_id == "node1"
