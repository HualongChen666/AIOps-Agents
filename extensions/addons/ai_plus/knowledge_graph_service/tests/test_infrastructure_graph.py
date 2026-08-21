# -*- coding: utf-8 -*-
"""Tests for InfrastructureGraphBuilder module."""

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.infrastructure_graph import (
    InfrastructureGraphBuilder,
)
from extensions.addons.ai_plus.knowledge_graph_service.builder import GraphBuilder
from extensions.addons.ai_plus.knowledge_graph_service.graph_store import GraphStore
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    InfrastructureGraphRequest,
    InfrastructureComponent,
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


@pytest.fixture
def infrastructure_builder(graph_builder):
    """Create a test infrastructure graph builder."""
    return InfrastructureGraphBuilder(graph_builder)


class TestInfrastructureGraphBuilder:
    """Test cases for InfrastructureGraphBuilder class."""

    @pytest.mark.asyncio
    async def test_build_basic_infrastructure_graph(self, infrastructure_builder):
        """Test building basic infrastructure graph."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=["Database B"],
                    properties={"env": "production"},
                ),
                InfrastructureComponent(
                    component_id="Database B",
                    component_type="database",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 2
        assert response.connections_count == 1
        assert response.graph_id is not None

    @pytest.mark.asyncio
    async def test_build_empty_components(self, infrastructure_builder):
        """Test building graph with no components."""
        request = InfrastructureGraphRequest(components=[])

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 0
        assert response.connections_count == 0

    @pytest.mark.asyncio
    async def test_build_single_component_no_connections(self, infrastructure_builder):
        """Test building graph with single component and no connections."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=[],
                )
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 1
        assert response.connections_count == 0

    @pytest.mark.asyncio
    async def test_build_single_component_with_connections(self, infrastructure_builder):
        """Test building graph with single component and connections."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=["Database B", "Cache C"],
                )
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 1
        assert response.connections_count == 2

    @pytest.mark.asyncio
    async def test_normalize_method(self, infrastructure_builder):
        """Test component name normalization."""
        assert infrastructure_builder._normalize("Component A") == "component_a"
        assert infrastructure_builder._normalize("Component-B") == "component_b"
        assert infrastructure_builder._normalize(" Component C ") == "component_c"
        assert infrastructure_builder._normalize("Component-D-E") == "component_d_e"

    def test_normalize_with_spaces(self, infrastructure_builder):
        """Test normalization with multiple spaces."""
        assert infrastructure_builder._normalize("  Component  A  ") == "component__a"

    def test_normalize_with_special_chars(self, infrastructure_builder):
        """Test normalization with special characters."""
        assert infrastructure_builder._normalize("Component@A") == "component@a"
        assert infrastructure_builder._normalize("Component#B") == "component#b"

    @pytest.mark.asyncio
    async def test_build_with_properties(self, infrastructure_builder):
        """Test building graph with component properties."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=["Database B"],
                    properties={"env": "prod", "region": "us-east"},
                ),
                InfrastructureComponent(
                    component_id="Database B",
                    component_type="database",
                    connections=[],
                    properties={"env": "dev", "region": "us-west"},
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 2

    @pytest.mark.asyncio
    async def test_build_duplicate_connections(self, infrastructure_builder):
        """Test building graph with duplicate connections."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=["Database B", "Database B", "Cache C"],
                ),
                InfrastructureComponent(
                    component_id="Database B",
                    component_type="database",
                    connections=[],
                ),
                InfrastructureComponent(
                    component_id="Cache C",
                    component_type="cache",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        # Should deduplicate edges
        assert response.connections_count == 2

    @pytest.mark.asyncio
    async def test_build_complex_topology(self, infrastructure_builder):
        """Test building complex infrastructure topology."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Load Balancer",
                    component_type="lb",
                    connections=["Web Server 1", "Web Server 2"],
                ),
                InfrastructureComponent(
                    component_id="Web Server 1",
                    component_type="server",
                    connections=["Database", "Redis"],
                ),
                InfrastructureComponent(
                    component_id="Web Server 2",
                    component_type="server",
                    connections=["Database", "Redis"],
                ),
                InfrastructureComponent(
                    component_id="Database",
                    component_type="database",
                    connections=[],
                ),
                InfrastructureComponent(
                    component_id="Redis",
                    component_type="cache",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 5
        assert response.connections_count == 6

    @pytest.mark.asyncio
    async def test_build_with_implicit_components(self, infrastructure_builder):
        """Test building graph where connections are not explicitly listed as components."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=["Database B", "Cache C"],
                )
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        # Should create nodes for implicit connections
        assert response.components_count == 1
        assert response.connections_count == 2

    @pytest.mark.asyncio
    async def test_build_with_custom_connection_type(self, infrastructure_builder):
        """Test building with custom connection type."""
        request = InfrastructureGraphRequest(
            connection_type="DEPLOYED_ON",
            components=[
                InfrastructureComponent(
                    component_id="App Server",
                    component_type="server",
                    connections=["Physical Server"],
                ),
                InfrastructureComponent(
                    component_id="Physical Server",
                    component_type="hardware",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        # Check that edges use custom connection type
        graph = await infrastructure_builder.graph_builder.store.as_graph(
            response.graph_id, "test"
        )
        if graph.edges:
            assert graph.edges[0].relation == "DEPLOYED_ON"

    @pytest.mark.asyncio
    async def test_build_with_hyphenated_names(self, infrastructure_builder):
        """Test building with hyphenated component names."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="server-a",
                    component_type="server",
                    connections=["database-b"],
                ),
                InfrastructureComponent(
                    component_id="database-b",
                    component_type="database",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 2
        assert response.connections_count == 1

    @pytest.mark.asyncio
    async def test_build_with_unicode_names(self, infrastructure_builder):
        """Test building with unicode component names."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="服务器A",
                    component_type="server",
                    connections=["数据库B"],
                ),
                InfrastructureComponent(
                    component_id="数据库B",
                    component_type="database",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 2

    @pytest.mark.asyncio
    async def test_build_large_scale(self, infrastructure_builder):
        """Test building large scale infrastructure graph."""
        components = []
        for i in range(50):
            connections = [f"Component {j}" for j in range(i, min(i + 5, 50))]
            components.append(
                InfrastructureComponent(
                    component_id=f"Component {i}",
                    component_type="server",
                    connections=connections,
                )
            )

        request = InfrastructureGraphRequest(components=components)

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 50

    @pytest.mark.asyncio
    async def test_build_preserves_properties(self, infrastructure_builder):
        """Test that component properties are preserved in nodes."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=["Database B"],
                    properties={"version": "1.0", "owner": "team-a"},
                ),
                InfrastructureComponent(
                    component_id="Database B",
                    component_type="database",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        # Check that graph was built with properties
        graph = await infrastructure_builder.graph_builder.store.as_graph(
            response.graph_id, "test"
        )
        server_a_node = next(
            (n for n in graph.nodes if n.node_id == "server_a"), None
        )
        assert server_a_node is not None
        assert server_a_node.properties.get("version") == "1.0"
        assert server_a_node.properties.get("owner") == "team-a"

    @pytest.mark.asyncio
    async def test_build_preserves_component_type(self, infrastructure_builder):
        """Test that component type is preserved in nodes."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=[],
                ),
                InfrastructureComponent(
                    component_id="Database B",
                    component_type="database",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        graph = await infrastructure_builder.graph_builder.store.as_graph(
            response.graph_id, "test"
        )
        server_node = next((n for n in graph.nodes if n.node_id == "server_a"), None)
        db_node = next((n for n in graph.nodes if n.node_id == "database_b"), None)

        assert server_node is not None
        assert server_node.node_type == "server"
        assert db_node is not None
        assert db_node.node_type == "database"

    @pytest.mark.asyncio
    async def test_build_with_empty_connections_list(self, infrastructure_builder):
        """Test building with empty connections list."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=[],
                ),
                InfrastructureComponent(
                    component_id="Database B",
                    component_type="database",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 2
        assert response.connections_count == 0

    @pytest.mark.asyncio
    async def test_build_with_self_connection(self, infrastructure_builder):
        """Test building with self connection (edge case)."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=["Server A"],
                )
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 1
        # Should create edge even if self-referential
        assert response.connections_count == 1

    @pytest.mark.asyncio
    async def test_build_circular_connections(self, infrastructure_builder):
        """Test building with circular connections."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Component A",
                    component_type="server",
                    connections=["Component B"],
                ),
                InfrastructureComponent(
                    component_id="Component B",
                    component_type="server",
                    connections=["Component C"],
                ),
                InfrastructureComponent(
                    component_id="Component C",
                    component_type="server",
                    connections=["Component A"],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 3
        assert response.connections_count == 3

    @pytest.mark.asyncio
    async def test_build_with_numeric_names(self, infrastructure_builder):
        """Test building with numeric-like component names."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server 1",
                    component_type="server",
                    connections=["Database 2"],
                ),
                InfrastructureComponent(
                    component_id="Database 2",
                    component_type="database",
                    connections=[],
                ),
            ]
        )

        response = await infrastructure_builder.build(request)

        assert response.built is True
        assert response.components_count == 2

    @pytest.mark.asyncio
    async def test_build_unknown_component_type(self, infrastructure_builder):
        """Test building with implicit component (unknown type)."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Server A",
                    component_type="server",
                    connections=["Implicit Component"],
                )
            ]
        )

        response = await infrastructure_builder.build(request)

        graph = await infrastructure_builder.graph_builder.store.as_graph(
            response.graph_id, "test"
        )
        implicit_node = next(
            (n for n in graph.nodes if n.node_id == "implicit_component"), None
        )
        assert implicit_node is not None
        # Implicit components should have type "unknown"
        assert implicit_node.node_type == "unknown"
