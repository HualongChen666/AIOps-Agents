# -*- coding: utf-8 -*-
"""Comprehensive tests for knowledge graph store."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.graph_store import GraphStore
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    Graph,
    GraphEdge,
    GraphNode,
)


class TestGraphStore:
    """Test suite for GraphStore class."""

    def test_initialization_default(self):
        """Test GraphStore initialization with default parameters."""
        store = GraphStore()

        assert store._neo4j_uri == ""
        assert store._neo4j_user == ""
        assert store._neo4j_password == ""
        assert store._driver is None
        assert store._in_memory is True
        assert store._nodes == {}
        assert store._edges == []

    def test_initialization_with_parameters(self):
        """Test GraphStore initialization with Neo4j parameters."""
        store = GraphStore(
            neo4j_uri="bolt://localhost:7687", neo4j_user="neo4j", neo4j_password="password"
        )

        assert store._neo4j_uri == "bolt://localhost:7687"
        assert store._neo4j_user == "neo4j"
        assert store._neo4j_password == "password"
        assert store._driver is None
        assert store._in_memory is True

    def test_is_connected_no_driver(self):
        """Test is_connected property when no driver is set."""
        store = GraphStore()
        assert store.is_connected is False

    def test_is_connected_with_driver(self):
        """Test is_connected property when driver is set."""
        store = GraphStore()
        store._driver = MagicMock()
        assert store.is_connected is True

    @pytest.mark.asyncio
    async def test_connect_no_neo4j_available(self):
        """Test connect when Neo4j is not available."""
        with patch(
            "extensions.addons.ai_plus.knowledge_graph_service.graph_store._NEO4J_AVAILABLE", False
        ):
            store = GraphStore(neo4j_uri="bolt://localhost:7687")
            await store.connect()

            assert store._driver is None
            assert store._in_memory is True

    @pytest.mark.asyncio
    async def test_connect_no_uri_configured(self):
        """Test connect when no URI is configured."""
        store = GraphStore()
        await store.connect()

        assert store._driver is None
        assert store._in_memory is True

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """Test successful Neo4j connection."""
        with patch(
            "extensions.addons.ai_plus.knowledge_graph_service.graph_store._NEO4J_AVAILABLE", True
        ):
            with patch(
                "extensions.addons.ai_plus.knowledge_graph_service.graph_store.neo4j"
            ) as mock_neo4j:
                mock_driver = AsyncMock()
                mock_driver.verify_connectivity = AsyncMock()
                mock_neo4j.AsyncGraphDatabase.driver.return_value = mock_driver

                store = GraphStore(
                    neo4j_uri="bolt://localhost:7687", neo4j_user="neo4j", neo4j_password="password"
                )
                await store.connect()

                assert store._driver is mock_driver
                assert store._in_memory is False
                mock_neo4j.AsyncGraphDatabase.driver.assert_called_once()
                mock_driver.verify_connectivity.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test Neo4j connection failure."""
        with patch(
            "extensions.addons.ai_plus.knowledge_graph_service.graph_store._NEO4J_AVAILABLE", True
        ):
            with patch(
                "extensions.addons.ai_plus.knowledge_graph_service.graph_store.neo4j"
            ) as mock_neo4j:
                mock_driver = AsyncMock()
                mock_driver.verify_connectivity.side_effect = Exception("Connection failed")
                mock_neo4j.AsyncGraphDatabase.driver.return_value = mock_driver

                store = GraphStore(
                    neo4j_uri="bolt://localhost:7687", neo4j_user="neo4j", neo4j_password="password"
                )
                await store.connect()

                assert store._driver is None
                assert store._in_memory is True

    @pytest.mark.asyncio
    async def test_close_no_driver(self):
        """Test close when no driver is set."""
        store = GraphStore()
        await store.close()

        assert store._driver is None

    @pytest.mark.asyncio
    async def test_close_with_driver(self):
        """Test closing Neo4j driver."""
        store = GraphStore()
        mock_driver = AsyncMock()
        store._driver = mock_driver

        await store.close()

        mock_driver.close.assert_called_once()
        assert store._driver is None

    @pytest.mark.asyncio
    async def test_close_driver_exception(self):
        """Test close when driver close raises exception."""
        store = GraphStore()
        mock_driver = AsyncMock()
        mock_driver.close.side_effect = Exception("Close failed")
        store._driver = mock_driver

        await store.close()

        assert store._driver is None  # Should still set to None

    @pytest.mark.asyncio
    async def test_add_node_with_id(self):
        """Test adding a node with existing ID."""
        store = GraphStore()
        node = GraphNode(node_id="node1", label="Test", node_type="test", properties={})

        result = await store.add_node(node)

        assert result == "node1"
        assert "node1" in store._nodes
        assert store._nodes["node1"] is node

    @pytest.mark.asyncio
    async def test_add_node_without_id(self):
        """Test adding a node without ID generates one."""
        store = GraphStore()
        node = GraphNode(node_id="", label="Test", node_type="test", properties={})

        result = await store.add_node(node)

        assert result is not None
        assert result != ""
        assert node.node_id == result
        assert result in store._nodes

    @pytest.mark.asyncio
    async def test_add_node_with_neo4j_success(self):
        """Test adding node with Neo4j backend success."""
        with patch(
            "extensions.addons.ai_plus.knowledge_graph_service.graph_store._NEO4J_AVAILABLE", True
        ):
            store = GraphStore()
            mock_driver = AsyncMock()
            mock_driver.execute_query = AsyncMock()
            store._driver = mock_driver
            store._in_memory = False

            node = GraphNode(node_id="node1", label="Test", node_type="test", properties={})
            result = await store.add_node(node)

            assert result == "node1"
            mock_driver.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_node_with_neo4j_failure_fallback(self):
        """Test adding node with Neo4j failure falls back to memory."""
        with patch(
            "extensions.addons.ai_plus.knowledge_graph_service.graph_store._NEO4J_AVAILABLE", True
        ):
            store = GraphStore()
            mock_driver = AsyncMock()
            mock_driver.execute_query.side_effect = Exception("Neo4j error")
            store._driver = mock_driver
            store._in_memory = False

            node = GraphNode(node_id="node1", label="Test", node_type="test", properties={})
            result = await store.add_node(node)

            assert result == "node1"
            assert "node1" in store._nodes

    @pytest.mark.asyncio
    async def test_add_edge_with_id(self):
        """Test adding an edge with existing ID."""
        store = GraphStore()
        edge = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )

        result = await store.add_edge(edge)

        assert result == "edge1"
        assert edge in store._edges
        assert edge in store._index["node1"]

    @pytest.mark.asyncio
    async def test_add_edge_without_id(self):
        """Test adding an edge without ID generates one."""
        store = GraphStore()
        edge = GraphEdge(
            edge_id="", source_id="node1", target_id="node2", relation="connects", properties={}
        )

        result = await store.add_edge(edge)

        assert result is not None
        assert result != ""
        assert edge.edge_id == result
        assert edge in store._edges

    @pytest.mark.asyncio
    async def test_add_edge_with_neo4j_success(self):
        """Test adding edge with Neo4j backend success."""
        with patch(
            "extensions.addons.ai_plus.knowledge_graph_service.graph_store._NEO4J_AVAILABLE", True
        ):
            store = GraphStore()
            mock_driver = AsyncMock()
            mock_driver.execute_query = AsyncMock()
            store._driver = mock_driver
            store._in_memory = False

            edge = GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="connects",
                properties={},
            )
            result = await store.add_edge(edge)

            assert result == "edge1"
            mock_driver.execute_query.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_edge_with_neo4j_failure_fallback(self):
        """Test adding edge with Neo4j failure falls back to memory."""
        with patch(
            "extensions.addons.ai_plus.knowledge_graph_service.graph_store._NEO4J_AVAILABLE", True
        ):
            store = GraphStore()
            mock_driver = AsyncMock()
            mock_driver.execute_query.side_effect = Exception("Neo4j error")
            store._driver = mock_driver
            store._in_memory = False

            edge = GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="connects",
                properties={},
            )
            result = await store.add_edge(edge)

            assert result == "edge1"
            assert edge in store._edges
            assert edge in store._index["node1"]

    @pytest.mark.asyncio
    async def test_get_node_exists(self):
        """Test getting an existing node."""
        store = GraphStore()
        node = GraphNode(node_id="node1", label="Test", node_type="test", properties={})
        store._nodes["node1"] = node

        result = await store.get_node("node1")

        assert result is node

    @pytest.mark.asyncio
    async def test_get_node_not_exists(self):
        """Test getting a non-existent node."""
        store = GraphStore()

        result = await store.get_node("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_neighbors(self):
        """Test getting neighbors of a node."""
        store = GraphStore()
        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        edge2 = GraphEdge(
            edge_id="edge2",
            source_id="node1",
            target_id="node3",
            relation="connects",
            properties={},
        )
        edge3 = GraphEdge(
            edge_id="edge3",
            source_id="node2",
            target_id="node4",
            relation="connects",
            properties={},
        )
        store._edges = [edge1, edge2, edge3]

        result = await store.get_neighbors("node1")

        assert len(result) == 2
        assert edge1 in result
        assert edge2 in result
        assert edge3 not in result

    @pytest.mark.asyncio
    async def test_get_neighbors_no_edges(self):
        """Test getting neighbors when node has no outgoing edges."""
        store = GraphStore()
        edge = GraphEdge(
            edge_id="edge1",
            source_id="node2",
            target_id="node3",
            relation="connects",
            properties={},
        )
        store._edges = [edge]

        result = await store.get_neighbors("node1")

        assert result == []

    @pytest.mark.asyncio
    async def test_query_nodes_no_filters(self):
        """Test querying nodes without filters."""
        store = GraphStore()
        node1 = GraphNode(node_id="node1", label="Test1", node_type="type1", properties={})
        node2 = GraphNode(node_id="node2", label="Test2", node_type="type2", properties={})
        store._nodes = {"node1": node1, "node2": node2}

        result = await store.query_nodes()

        assert len(result) == 2
        assert node1 in result
        assert node2 in result

    @pytest.mark.asyncio
    async def test_query_nodes_by_label(self):
        """Test querying nodes by label."""
        store = GraphStore()
        node1 = GraphNode(node_id="node1", label="Test1", node_type="type1", properties={})
        node2 = GraphNode(node_id="node2", label="Test2", node_type="type2", properties={})
        node3 = GraphNode(node_id="node3", label="Test1", node_type="type3", properties={})
        store._nodes = {"node1": node1, "node2": node2, "node3": node3}

        result = await store.query_nodes(label="Test1")

        assert len(result) == 2
        assert node1 in result
        assert node3 in result
        assert node2 not in result

    @pytest.mark.asyncio
    async def test_query_nodes_by_type(self):
        """Test querying nodes by type."""
        store = GraphStore()
        node1 = GraphNode(node_id="node1", label="Test1", node_type="type1", properties={})
        node2 = GraphNode(node_id="node2", label="Test2", node_type="type2", properties={})
        node3 = GraphNode(node_id="node3", label="Test3", node_type="type1", properties={})
        store._nodes = {"node1": node1, "node2": node2, "node3": node3}

        result = await store.query_nodes(node_type="type1")

        assert len(result) == 2
        assert node1 in result
        assert node3 in result
        assert node2 not in result

    @pytest.mark.asyncio
    async def test_query_nodes_both_filters(self):
        """Test querying nodes with both label and type filters."""
        store = GraphStore()
        node1 = GraphNode(node_id="node1", label="Test1", node_type="type1", properties={})
        node2 = GraphNode(node_id="node2", label="Test1", node_type="type2", properties={})
        node3 = GraphNode(node_id="node3", label="Test2", node_type="type1", properties={})
        store._nodes = {"node1": node1, "node2": node2, "node3": node3}

        result = await store.query_nodes(label="Test1", node_type="type1")

        assert len(result) == 1
        assert node1 in result

    @pytest.mark.asyncio
    async def test_query_edges_no_filter(self):
        """Test querying edges without filter."""
        store = GraphStore()
        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        edge2 = GraphEdge(
            edge_id="edge2", source_id="node2", target_id="node3", relation="depends", properties={}
        )
        store._edges = [edge1, edge2]

        result = await store.query_edges()

        assert len(result) == 2
        assert edge1 in result
        assert edge2 in result

    @pytest.mark.asyncio
    async def test_query_edges_by_relation(self):
        """Test querying edges by relation type."""
        store = GraphStore()
        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        edge2 = GraphEdge(
            edge_id="edge2", source_id="node2", target_id="node3", relation="depends", properties={}
        )
        edge3 = GraphEdge(
            edge_id="edge3",
            source_id="node3",
            target_id="node4",
            relation="connects",
            properties={},
        )
        store._edges = [edge1, edge2, edge3]

        result = await store.query_edges(relation="connects")

        assert len(result) == 2
        assert edge1 in result
        assert edge3 in result
        assert edge2 not in result

    def test_collect_nodes(self):
        """Test collecting nodes from edges."""
        store = GraphStore()
        node1 = GraphNode(node_id="node1", label="Test1", node_type="type1", properties={})
        node2 = GraphNode(node_id="node2", label="Test2", node_type="type2", properties={})
        node3 = GraphNode(node_id="node3", label="Test3", node_type="type3", properties={})
        store._nodes = {"node1": node1, "node2": node2, "node3": node3}

        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        edge2 = GraphEdge(
            edge_id="edge2",
            source_id="node2",
            target_id="node3",
            relation="connects",
            properties={},
        )

        result = store._collect_nodes([edge1, edge2])

        assert len(result) == 3
        assert node1 in result
        assert node2 in result
        assert node3 in result

    def test_collect_nodes_missing_nodes(self):
        """Test collecting nodes when some nodes are missing."""
        store = GraphStore()
        node1 = GraphNode(node_id="node1", label="Test1", node_type="type1", properties={})
        store._nodes = {"node1": node1}

        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        edge2 = GraphEdge(
            edge_id="edge2",
            source_id="node2",
            target_id="node3",
            relation="connects",
            properties={},
        )

        result = store._collect_nodes([edge1, edge2])

        assert len(result) == 1
        assert node1 in result

    @pytest.mark.asyncio
    async def test_find_paths_direct_connection(self):
        """Test finding paths with direct connection."""
        store = GraphStore()
        edge = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        store._edges = [edge]

        result = await store.find_paths("node1", "node2")

        assert len(result) == 1
        assert result[0] == ["node1", "node2"]

    @pytest.mark.asyncio
    async def test_find_paths_multi_hop(self):
        """Test finding paths with multiple hops."""
        store = GraphStore()
        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        edge2 = GraphEdge(
            edge_id="edge2",
            source_id="node2",
            target_id="node3",
            relation="connects",
            properties={},
        )
        edge3 = GraphEdge(
            edge_id="edge3",
            source_id="node3",
            target_id="node4",
            relation="connects",
            properties={},
        )
        store._edges = [edge1, edge2, edge3]

        result = await store.find_paths("node1", "node4")

        assert len(result) == 1
        assert result[0] == ["node1", "node2", "node3", "node4"]

    @pytest.mark.asyncio
    async def test_find_paths_no_path(self):
        """Test finding paths when no path exists."""
        store = GraphStore()
        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        edge2 = GraphEdge(
            edge_id="edge2",
            source_id="node3",
            target_id="node4",
            relation="connects",
            properties={},
        )
        store._edges = [edge1, edge2]

        result = await store.find_paths("node1", "node4")

        assert result == []

    @pytest.mark.asyncio
    async def test_find_paths_max_depth_limit(self):
        """Test finding paths respects max depth limit."""
        store = GraphStore()
        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        edge2 = GraphEdge(
            edge_id="edge2",
            source_id="node2",
            target_id="node3",
            relation="connects",
            properties={},
        )
        edge3 = GraphEdge(
            edge_id="edge3",
            source_id="node3",
            target_id="node4",
            relation="connects",
            properties={},
        )
        store._edges = [edge1, edge2, edge3]

        result = await store.find_paths("node1", "node4", max_depth=2)

        assert result == []  # Path requires depth 3 but max is 2

    @pytest.mark.asyncio
    async def test_find_paths_same_node(self):
        """Test finding paths from node to itself."""
        store = GraphStore()
        edge = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        store._edges = [edge]

        result = await store.find_paths("node1", "node1")

        assert result == []  # No path from node to itself (requires len > 1)

    @pytest.mark.asyncio
    async def test_find_paths_multiple_paths(self):
        """Test finding multiple paths between nodes."""
        store = GraphStore()
        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        edge2 = GraphEdge(
            edge_id="edge2",
            source_id="node1",
            target_id="node3",
            relation="connects",
            properties={},
        )
        edge3 = GraphEdge(
            edge_id="edge3",
            source_id="node2",
            target_id="node4",
            relation="connects",
            properties={},
        )
        edge4 = GraphEdge(
            edge_id="edge4",
            source_id="node3",
            target_id="node4",
            relation="connects",
            properties={},
        )
        store._edges = [edge1, edge2, edge3, edge4]

        result = await store.find_paths("node1", "node4")

        assert len(result) == 2
        paths = sorted(result)
        assert paths[0] == ["node1", "node2", "node4"]
        assert paths[1] == ["node1", "node3", "node4"]

    @pytest.mark.asyncio
    async def test_load_graph(self):
        """Test loading a graph into the store."""
        store = GraphStore()
        graph = Graph(
            graph_id="graph1",
            name="test_graph",
            nodes=[
                GraphNode(node_id="node1", label="Test1", node_type="type1", properties={}),
                GraphNode(node_id="node2", label="Test2", node_type="type2", properties={}),
            ],
            edges=[
                GraphEdge(
                    edge_id="edge1",
                    source_id="node1",
                    target_id="node2",
                    relation="connects",
                    properties={},
                ),
            ],
        )

        await store.load_graph(graph)

        assert len(store._nodes) == 2
        assert len(store._edges) == 1
        assert "node1" in store._nodes
        assert "node2" in store._nodes

    @pytest.mark.asyncio
    async def test_as_graph(self):
        """Test converting store to Graph object."""
        store = GraphStore()
        node1 = GraphNode(node_id="node1", label="Test1", node_type="type1", properties={})
        node2 = GraphNode(node_id="node2", label="Test2", node_type="type2", properties={})
        edge1 = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={},
        )
        store._nodes = {"node1": node1, "node2": node2}
        store._edges = [edge1]

        result = await store.as_graph("graph1", "test_graph")

        assert isinstance(result, Graph)
        assert result.graph_id == "graph1"
        assert result.name == "test_graph"
        assert len(result.nodes) == 2
        assert len(result.edges) == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        """Test clearing the store."""
        store = GraphStore()
        store._nodes = {
            "node1": GraphNode(node_id="node1", label="Test", node_type="test", properties={})
        }
        store._edges = [
            GraphEdge(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation="connects",
                properties={},
            )
        ]
        store._index["node1"] = store._edges.copy()

        await store.clear()

        assert store._nodes == {}
        assert store._edges == []
        assert store._index == {}

    @pytest.mark.asyncio
    async def test_clear_empty_store(self):
        """Test clearing an already empty store."""
        store = GraphStore()

        await store.clear()

        assert store._nodes == {}
        assert store._edges == []
        assert store._index == {}

    @pytest.mark.asyncio
    async def test_integration_add_and_query(self):
        """Test integration of adding nodes and querying them."""
        store = GraphStore()

        node1 = GraphNode(
            node_id="node1",
            label="Server",
            node_type="infrastructure",
            properties={"ip": "192.168.1.1"},
        )
        node2 = GraphNode(
            node_id="node2",
            label="Database",
            node_type="infrastructure",
            properties={"ip": "192.168.1.2"},
        )

        await store.add_node(node1)
        await store.add_node(node2)

        edge = GraphEdge(
            edge_id="edge1",
            source_id="node1",
            target_id="node2",
            relation="connects",
            properties={"protocol": "tcp"},
        )
        await store.add_edge(edge)

        nodes = await store.query_nodes(node_type="infrastructure")
        assert len(nodes) == 2

        neighbors = await store.get_neighbors("node1")
        assert len(neighbors) == 1
        assert neighbors[0].target_id == "node2"
