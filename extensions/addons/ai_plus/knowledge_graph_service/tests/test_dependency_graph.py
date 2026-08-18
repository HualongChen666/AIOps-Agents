# -*- coding: utf-8 -*-
"""Tests for ServiceDependencyGraphBuilder module."""

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.dependency_graph import (
    ServiceDependencyGraphBuilder,
)
from extensions.addons.ai_plus.knowledge_graph_service.builder import GraphBuilder
from extensions.addons.ai_plus.knowledge_graph_service.graph_store import GraphStore
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    ServiceDependencyGraphRequest,
    ServiceDependency,
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
def dependency_builder(graph_builder):
    """Create a test service dependency graph builder."""
    return ServiceDependencyGraphBuilder(graph_builder)


class TestServiceDependencyGraphBuilder:
    """Test cases for ServiceDependencyGraphBuilder class."""

    @pytest.mark.asyncio
    async def test_build_basic_dependency_graph(self, dependency_builder):
        """Test building basic service dependency graph."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(
                    service="Service A",
                    depends_on=["Service B", "Service C"],
                    properties={"env": "production"},
                ),
                ServiceDependency(service="Service B", depends_on=["Service D"]),
                ServiceDependency(service="Service C", depends_on=[]),
                ServiceDependency(service="Service D", depends_on=[]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 4
        assert response.dependencies_count == 3
        assert response.graph_id is not None

    @pytest.mark.asyncio
    async def test_build_empty_services(self, dependency_builder):
        """Test building graph with no services."""
        request = ServiceDependencyGraphRequest(services=[])

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 0
        assert response.dependencies_count == 0

    @pytest.mark.asyncio
    async def test_build_single_service_no_deps(self, dependency_builder):
        """Test building graph with single service and no dependencies."""
        request = ServiceDependencyGraphRequest(
            services=[ServiceDependency(service="Service A", depends_on=[])]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 1
        assert response.dependencies_count == 0

    @pytest.mark.asyncio
    async def test_build_single_service_with_deps(self, dependency_builder):
        """Test building graph with single service and dependencies."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(
                    service="Service A", depends_on=["Service B", "Service C"]
                )
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 1
        assert response.dependencies_count == 2

    @pytest.mark.asyncio
    async def test_normalize_method(self, dependency_builder):
        """Test service name normalization."""
        assert dependency_builder._normalize("Service A") == "service_a"
        assert dependency_builder._normalize("Service-B") == "service_b"
        assert dependency_builder._normalize(" Service C ") == "service_c"
        assert dependency_builder._normalize("Service-D-E") == "service_d_e"

    def test_normalize_with_spaces(self, dependency_builder):
        """Test normalization with multiple spaces."""
        assert dependency_builder._normalize("  Service  A  ") == "service__a"

    def test_normalize_with_special_chars(self, dependency_builder):
        """Test normalization with special characters."""
        assert dependency_builder._normalize("Service@A") == "service@a"
        assert dependency_builder._normalize("Service#B") == "service#b"

    @pytest.mark.asyncio
    async def test_build_with_properties(self, dependency_builder):
        """Test building graph with service properties."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(
                    service="Service A",
                    depends_on=["Service B"],
                    properties={"env": "prod", "region": "us-east"},
                ),
                ServiceDependency(
                    service="Service B",
                    depends_on=[],
                    properties={"env": "dev", "region": "us-west"},
                ),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 2

    @pytest.mark.asyncio
    async def test_build_duplicate_dependencies(self, dependency_builder):
        """Test building graph with duplicate dependencies."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(
                    service="Service A",
                    depends_on=["Service B", "Service B", "Service C"],
                ),
                ServiceDependency(service="Service B", depends_on=[]),
                ServiceDependency(service="Service C", depends_on=[]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        # Should deduplicate edges
        assert response.dependencies_count == 2

    @pytest.mark.asyncio
    async def test_build_circular_dependencies(self, dependency_builder):
        """Test building graph with circular dependencies."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="Service A", depends_on=["Service B"]),
                ServiceDependency(service="Service B", depends_on=["Service C"]),
                ServiceDependency(service="Service C", depends_on=["Service A"]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 3
        assert response.dependencies_count == 3

    @pytest.mark.asyncio
    async def test_build_complex_dependency_tree(self, dependency_builder):
        """Test building complex dependency tree."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(
                    service="Frontend", depends_on=["API Gateway", "Auth Service"]
                ),
                ServiceDependency(
                    service="API Gateway", depends_on=["User Service", "Order Service"]
                ),
                ServiceDependency(service="User Service", depends_on=["Database"]),
                ServiceDependency(service="Order Service", depends_on=["Database"]),
                ServiceDependency(service="Auth Service", depends_on=["Database"]),
                ServiceDependency(service="Database", depends_on=[]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 6
        assert response.dependencies_count == 7

    @pytest.mark.asyncio
    async def test_build_with_implicit_dependencies(self, dependency_builder):
        """Test building graph where dependencies are not explicitly listed as services."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(
                    service="Service A", depends_on=["Service B", "Service C"]
                )
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        # Should create nodes for implicit dependencies
        assert response.services_count == 1
        assert response.dependencies_count == 2

    @pytest.mark.asyncio
    async def test_build_with_case_insensitive(self, dependency_builder):
        """Test that service names are case-insensitive."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="Service A", depends_on=["service b"]),
                ServiceDependency(service="Service B", depends_on=[]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        # Should treat "service b" and "Service B" as the same
        assert response.dependencies_count == 1

    @pytest.mark.asyncio
    async def test_build_with_hyphenated_names(self, dependency_builder):
        """Test building with hyphenated service names."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="service-a", depends_on=["service-b"]),
                ServiceDependency(service="service-b", depends_on=[]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 2
        assert response.dependencies_count == 1

    @pytest.mark.asyncio
    async def test_build_large_scale(self, dependency_builder):
        """Test building large scale dependency graph."""
        services = []
        for i in range(50):
            deps = [f"Service {j}" for j in range(i, min(i + 5, 50))]
            services.append(ServiceDependency(service=f"Service {i}", depends_on=deps))

        request = ServiceDependencyGraphRequest(services=services)

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 50

    @pytest.mark.asyncio
    async def test_build_with_empty_depends_on(self, dependency_builder):
        """Test building with empty depends_on list."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="Service A", depends_on=[]),
                ServiceDependency(service="Service B", depends_on=[]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 2
        assert response.dependencies_count == 0

    @pytest.mark.asyncio
    async def test_build_with_self_dependency(self, dependency_builder):
        """Test building with self dependency (edge case)."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="Service A", depends_on=["Service A"])
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 1
        # Should create edge even if self-referential
        assert response.dependencies_count == 1

    @pytest.mark.asyncio
    async def test_build_preserves_properties(self, dependency_builder):
        """Test that service properties are preserved in nodes."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(
                    service="Service A",
                    depends_on=["Service B"],
                    properties={"version": "1.0", "owner": "team-a"},
                ),
                ServiceDependency(service="Service B", depends_on=[]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        # Check that graph was built with properties
        graph = await dependency_builder.graph_builder.store.as_graph(
            response.graph_id, "test"
        )
        service_a_node = next(
            (n for n in graph.nodes if n.node_id == "service_a"), None
        )
        assert service_a_node is not None
        assert service_a_node.properties.get("version") == "1.0"
        assert service_a_node.properties.get("owner") == "team-a"

    @pytest.mark.asyncio
    async def test_build_with_unicode_names(self, dependency_builder):
        """Test building with unicode service names."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="服务A", depends_on=["服务B"]),
                ServiceDependency(service="服务B", depends_on=[]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 2

    @pytest.mark.asyncio
    async def test_build_with_numeric_names(self, dependency_builder):
        """Test building with numeric-like service names."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="Service 1", depends_on=["Service 2"]),
                ServiceDependency(service="Service 2", depends_on=[]),
            ]
        )

        response = await dependency_builder.build(request)

        assert response.built is True
        assert response.services_count == 2
