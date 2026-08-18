# -*- coding: utf-8 -*-
"""Tests for KnowledgeGraphOrchestrator module."""


import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from extensions.addons.ai_plus.knowledge_graph_service.orchestrator import (
    KnowledgeGraphOrchestrator,
)
from extensions.addons.ai_plus.knowledge_graph_service.cache import CacheManager
from extensions.addons.ai_plus.knowledge_graph_service.graph_store import GraphStore
from extensions.addons.ai_plus.knowledge_graph_service.retry import KnowledgeGraphRetryEngine
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    EntityModelingRequest,
    EntityModelingResponse,
    RelationModelingRequest,
    RelationModelingResponse,
    GraphBuildRequest,
    GraphBuildResponse,
    GraphQueryRequest,
    GraphQueryResponse,
    GraphReasonRequest,
    GraphReasonResponse,
    GraphVisualizationRequest,
    GraphVisualizationResponse,
    ServiceDependencyGraphRequest,
    ServiceDependencyGraphResponse,
    InfrastructureGraphRequest,
    InfrastructureGraphResponse,
    FaultPropagationGraphRequest,
    FaultPropagationGraphResponse,
    ServiceDependency,
    InfrastructureComponent,
    FaultRule,
    FaultState,
    GraphNode,
    GraphEdge,
    Graph,
)


@pytest.fixture
def cache_manager():
    """Create a test cache manager."""
    return CacheManager(redis_url=None)


@pytest.fixture
def retry_engine():
    """Create a test retry engine."""
    return KnowledgeGraphRetryEngine()


@pytest.fixture
def graph_store():
    """Create a test graph store."""
    store = GraphStore()
    return store


@pytest.fixture
def orchestrator(cache_manager, retry_engine, graph_store):
    """Create a test orchestrator."""
    return KnowledgeGraphOrchestrator(
        cache=cache_manager, retry_engine=retry_engine, store=graph_store
    )


class TestKnowledgeGraphOrchestrator:
    """Test cases for KnowledgeGraphOrchestrator class."""

    def test_initialization(self, orchestrator):
        """Test orchestrator initialization."""
        assert orchestrator.cache is not None
        assert orchestrator.retry_engine is not None
        assert orchestrator.store is not None
        assert orchestrator.entity_modeler is not None
        assert orchestrator.relation_modeler is not None
        assert orchestrator.graph_builder is not None
        assert orchestrator.query_engine is not None
        assert orchestrator.reasoning_engine is not None
        assert orchestrator.visualizer is not None
        assert orchestrator.dependency_builder is not None
        assert orchestrator.infrastructure_builder is not None
        assert orchestrator.fault_builder is not None

    def test_initialization_defaults(self):
        """Test orchestrator initialization with defaults."""
        orch = KnowledgeGraphOrchestrator()
        assert orch.cache is not None
        assert orch.retry_engine is not None
        assert orch.store is not None

    def test_new_id(self, orchestrator):
        """Test _new_id generates unique IDs."""
        id1 = orchestrator._new_id()
        id2 = orchestrator._new_id()
        assert id1 != id2
        assert isinstance(id1, str)

    def test_increment_count(self, orchestrator):
        """Test _increment_count increments request counts."""
        orchestrator._increment_count("test_operation")
        assert orchestrator._request_counts["test_operation"] == 1
        orchestrator._increment_count("test_operation")
        assert orchestrator._request_counts["test_operation"] == 2

    def test_list_methods(self, orchestrator):
        """Test list_methods returns all methods."""
        methods = orchestrator.list_methods()
        expected_methods = [
            "model_entity",
            "model_relation",
            "build_graph",
            "query_graph",
            "infer_graph",
            "visualize_graph",
            "build_service_dependency_graph",
            "build_infrastructure_graph",
            "build_fault_propagation_graph",
            "get_stats",
        ]
        for method in expected_methods:
            assert method in methods

    @pytest.mark.asyncio
    async def test_get_stats(self, orchestrator):
        """Test get_stats returns statistics."""
        orchestrator._request_counts["test"] = 5
        orchestrator._graphs["graph1"] = Graph(
            graph_id="graph1",
            name="Test",
            nodes=[GraphNode(node_id="n1", label="N1", node_type="entity")],
            edges=[],
        )

        stats = await orchestrator.get_stats()

        assert stats.service == "knowledge-graph-service"
        assert stats.request_counts == {"test": 5}
        assert stats.graph_entries["graphs"] == 1
        assert stats.graph_entries["nodes"] == 1
        assert stats.graph_entries["edges"] == 0
        assert isinstance(stats.cache_size, int)
        assert isinstance(stats.retry_policies, list)

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, orchestrator):
        """Test get_stats with empty state."""
        stats = await orchestrator.get_stats()

        assert stats.service == "knowledge-graph-service"
        assert stats.request_counts == {}
        assert stats.graph_entries["graphs"] == 0
        assert stats.graph_entries["nodes"] == 0
        assert stats.graph_entries["edges"] == 0

    @pytest.mark.asyncio
    async def test_model_entity(self, orchestrator):
        """Test model_entity."""
        request = EntityModelingRequest(
            entity_name="Test Entity", entity_type="generic"
        )

        response = await orchestrator.model_entity(request)

        assert response.modeled is True
        assert response.entity_name == "Test Entity"
        assert response.entity_type == "generic"
        assert response.node_id is not None
        assert orchestrator._request_counts["model_entity"] == 1

    @pytest.mark.asyncio
    async def test_model_entity_with_properties(self, orchestrator):
        """Test model_entity with properties."""
        request = EntityModelingRequest(
            entity_name="Test Entity",
            entity_type="custom",
            properties={"key": "value"},
        )

        response = await orchestrator.model_entity(request)

        assert response.modeled is True
        assert response.entity_type == "custom"

    @pytest.mark.asyncio
    async def test_model_relation(self, orchestrator):
        """Test model_relation."""
        request = RelationModelingRequest(
            source_name="Source", target_name="Target", relation_type="CONNECTS_TO"
        )

        response = await orchestrator.model_relation(request)

        assert response.modeled is True
        assert response.relation_type == "CONNECTS_TO"
        assert response.source_id is not None
        assert response.target_id is not None
        assert orchestrator._request_counts["model_relation"] == 1

    @pytest.mark.asyncio
    async def test_model_relation_with_properties(self, orchestrator):
        """Test model_relation with properties."""
        request = RelationModelingRequest(
            source_name="Source",
            target_name="Target",
            relation_type="DEPENDS_ON",
            properties={"weight": 1.0},
        )

        response = await orchestrator.model_relation(request)

        assert response.modeled is True
        assert response.relation_type == "DEPENDS_ON"

    @pytest.mark.asyncio
    async def test_build_graph(self, orchestrator):
        """Test build_graph."""
        request = GraphBuildRequest(
            graph_name="test",
            nodes=[GraphNode(node_id="n1", label="N1", node_type="entity")],
            edges=[],
        )

        response = await orchestrator.build_graph(request)

        assert response.built is True
        assert response.graph_id is not None
        assert response.nodes_count == 1
        assert response.edges_count == 0
        assert orchestrator._request_counts["build_graph"] == 1

    @pytest.mark.asyncio
    async def test_build_graph_with_retry(self, orchestrator):
        """Test build_graph with retry on failure."""
        request = GraphBuildRequest(graph_name="test", nodes=[], edges=[])

        # Mock retry engine to succeed on first try
        async def mock_execute(fn, **kwargs):
            return await fn()

        orchestrator.retry_engine.execute = AsyncMock(side_effect=mock_execute)

        response = await orchestrator.build_graph(request)

        assert response.built is True

    @pytest.mark.asyncio
    async def test_build_graph_empty(self, orchestrator):
        """Test build_graph with empty graph."""
        request = GraphBuildRequest(graph_name="empty", nodes=[], edges=[])

        response = await orchestrator.build_graph(request)

        assert response.built is True
        assert response.nodes_count == 0
        assert response.edges_count == 0

    @pytest.mark.asyncio
    async def test_query_graph(self, orchestrator):
        """Test query_graph."""
        # First build a graph
        graph = Graph(
            graph_id="test_graph",
            name="Test",
            nodes=[
                GraphNode(node_id="n1", label="N1", node_type="entity"),
                GraphNode(node_id="n2", label="N2", node_type="entity"),
            ],
            edges=[
                GraphEdge(
                    edge_id="e1", source_id="n1", target_id="n2", relation="CONNECTS_TO"
                )
            ],
        )
        orchestrator._graphs["test_graph"] = graph

        request = GraphQueryRequest(graph_id="test_graph", relation="CONNECTS_TO")

        response = await orchestrator.query_graph(request)

        assert response.graph_id == "test_graph"
        assert len(response.nodes) == 2
        assert len(response.edges) == 1
        assert orchestrator._request_counts["query_graph"] == 1

    @pytest.mark.asyncio
    async def test_query_graph_not_found(self, orchestrator):
        """Test query_graph with non-existent graph."""
        request = GraphQueryRequest(graph_id="nonexistent")

        with pytest.raises(KeyError):
            await orchestrator.query_graph(request)

    @pytest.mark.asyncio
    async def test_infer_graph(self, orchestrator):
        """Test infer_graph."""
        graph = Graph(
            graph_id="test_graph",
            name="Test",
            nodes=[
                GraphNode(node_id="n1", label="N1", node_type="entity"),
                GraphNode(node_id="n2", label="N2", node_type="entity"),
            ],
            edges=[
                GraphEdge(
                    edge_id="e1", source_id="n1", target_id="n2", relation="CONNECTS_TO"
                )
            ],
        )
        orchestrator._graphs["test_graph"] = graph

        request = GraphReasonRequest(graph_id="test_graph", node_id="n1")

        response = await orchestrator.infer_graph(request)

        assert response.graph_id == "test_graph"
        assert response.node_id == "n1"
        assert response.reason_type == "neighbors"
        assert orchestrator._request_counts["infer_graph"] == 1

    @pytest.mark.asyncio
    async def test_infer_graph_not_found(self, orchestrator):
        """Test infer_graph with non-existent graph."""
        request = GraphReasonRequest(graph_id="nonexistent", node_id="n1")

        with pytest.raises(KeyError):
            await orchestrator.infer_graph(request)

    @pytest.mark.asyncio
    async def test_visualize_graph(self, orchestrator):
        """Test visualize_graph."""
        graph = Graph(
            graph_id="test_graph",
            name="Test",
            nodes=[GraphNode(node_id="n1", label="N1", node_type="entity")],
            edges=[],
        )
        orchestrator._graphs["test_graph"] = graph

        request = GraphVisualizationRequest(graph_id="test_graph")

        response = await orchestrator.visualize_graph(request)

        assert response.graph_id == "test_graph"
        assert len(response.nodes) == 1
        assert orchestrator._request_counts["visualize_graph"] == 1

    @pytest.mark.asyncio
    async def test_visualize_graph_not_found(self, orchestrator):
        """Test visualize_graph with non-existent graph."""
        request = GraphVisualizationRequest(graph_id="nonexistent")

        with pytest.raises(KeyError):
            await orchestrator.visualize_graph(request)

    @pytest.mark.asyncio
    async def test_build_service_dependency_graph(self, orchestrator):
        """Test build_service_dependency_graph."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="Service A", depends_on=["Service B"]),
                ServiceDependency(service="Service B", depends_on=[]),
            ]
        )

        response = await orchestrator.build_service_dependency_graph(request)

        assert response.built is True
        assert response.graph_id is not None
        assert response.services_count == 2
        assert orchestrator._request_counts["build_service_dependency_graph"] == 1

    @pytest.mark.asyncio
    async def test_build_service_dependency_graph_empty(self, orchestrator):
        """Test build_service_dependency_graph with empty services."""
        request = ServiceDependencyGraphRequest(services=[])

        response = await orchestrator.build_service_dependency_graph(request)

        assert response.built is True
        assert response.services_count == 0

    @pytest.mark.asyncio
    async def test_build_infrastructure_graph(self, orchestrator):
        """Test build_infrastructure_graph."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Component A",
                    component_type="server",
                    connections=["Component B"],
                ),
                InfrastructureComponent(
                    component_id="Component B", component_type="database", connections=[]
                ),
            ]
        )

        response = await orchestrator.build_infrastructure_graph(request)

        assert response.built is True
        assert response.graph_id is not None
        assert response.components_count == 2
        assert orchestrator._request_counts["build_infrastructure_graph"] == 1

    @pytest.mark.asyncio
    async def test_build_infrastructure_graph_empty(self, orchestrator):
        """Test build_infrastructure_graph with empty components."""
        request = InfrastructureGraphRequest(components=[])

        response = await orchestrator.build_infrastructure_graph(request)

        assert response.built is True
        assert response.components_count == 0

    @pytest.mark.asyncio
    async def test_build_fault_propagation_graph(self, orchestrator):
        """Test build_fault_propagation_graph."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                )
            ],
        )

        response = await orchestrator.build_fault_propagation_graph(request)

        assert response.built is True
        assert response.graph_id is not None
        assert response.states_count == 1
        assert response.rules_count == 1
        assert orchestrator._request_counts["build_fault_propagation_graph"] == 1

    @pytest.mark.asyncio
    async def test_build_fault_propagation_graph_empty(self, orchestrator):
        """Test build_fault_propagation_graph with empty data."""
        request = FaultPropagationGraphRequest(states=[], rules=[])

        response = await orchestrator.build_fault_propagation_graph(request)

        assert response.built is True
        assert response.states_count == 0
        assert response.rules_count == 0

    def test_get_graph_exists(self, orchestrator):
        """Test _get_graph with existing graph."""
        graph = Graph(
            graph_id="test_graph", name="Test", nodes=[], edges=[]
        )
        orchestrator._graphs["test_graph"] = graph

        retrieved = orchestrator._get_graph("test_graph")

        assert retrieved == graph

    def test_get_graph_not_exists(self, orchestrator):
        """Test _get_graph with non-existent graph."""
        with pytest.raises(KeyError):
            orchestrator._get_graph("nonexistent")

    @pytest.mark.asyncio
    async def test_cache_graph_response(self, orchestrator):
        """Test _cache_graph_response."""
        # Build a graph in store
        await orchestrator.store.add_node(
            GraphNode(node_id="n1", label="N1", node_type="entity")
        )
        await orchestrator.store.add_edge(
            GraphEdge(
                edge_id="e1", source_id="n1", target_id="n2", relation="CONNECTS_TO"
            )
        )

        await orchestrator._cache_graph_response("test_graph")

        assert "test_graph" in orchestrator._graphs
        assert orchestrator._graphs["test_graph"].graph_id == "test_graph"

    @pytest.mark.asyncio
    async def test_multiple_operations_increment_counts(self, orchestrator):
        """Test that multiple operations increment counts correctly."""
        await orchestrator.model_entity(
            EntityModelingRequest(entity_name="Test", entity_type="generic")
        )
        await orchestrator.model_entity(
            EntityModelingRequest(entity_name="Test2", entity_type="generic")
        )
        await orchestrator.model_relation(
            RelationModelingRequest(
                source_name="A", target_name="B", relation_type="CONNECTS_TO"
            )
        )

        assert orchestrator._request_counts["model_entity"] == 2
        assert orchestrator._request_counts["model_relation"] == 1

    @pytest.mark.asyncio
    async def test_build_graph_caches_response(self, orchestrator):
        """Test that build_graph caches the response."""
        request = GraphBuildRequest(
            graph_name="test",
            nodes=[GraphNode(node_id="n1", label="N1", node_type="entity")],
            edges=[],
        )

        response = await orchestrator.build_graph(request)

        assert response.graph_id in orchestrator._graphs

    @pytest.mark.asyncio
    async def test_build_service_dependency_graph_caches_response(
        self, orchestrator
    ):
        """Test that build_service_dependency_graph caches the response."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="Service A", depends_on=["Service B"])
            ]
        )

        response = await orchestrator.build_service_dependency_graph(request)

        assert response.graph_id in orchestrator._graphs

    @pytest.mark.asyncio
    async def test_build_infrastructure_graph_caches_response(self, orchestrator):
        """Test that build_infrastructure_graph caches the response."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="Component A", component_type="server", connections=[]
                )
            ]
        )

        response = await orchestrator.build_infrastructure_graph(request)

        assert response.graph_id in orchestrator._graphs

    @pytest.mark.asyncio
    async def test_build_fault_propagation_graph_caches_response(
        self, orchestrator
    ):
        """Test that build_fault_propagation_graph caches the response."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0)
            ],
            rules=[
                FaultRule(
                    source="Database", target="API", condition="down", impact="high"
                )
            ],
        )

        response = await orchestrator.build_fault_propagation_graph(request)

        assert response.graph_id in orchestrator._graphs

    @pytest.mark.asyncio
    async def test_model_entity_caches_in_cache(self, orchestrator):
        """Test that model_entity caches in cache."""
        request = EntityModelingRequest(
            entity_name="Test Entity", entity_type="generic"
        )

        response = await orchestrator.model_entity(request)

        cached = await orchestrator.cache.get(f"entity:{response.node_id}")
        assert cached is not None

    @pytest.mark.asyncio
    async def test_model_relation_caches_in_cache(self, orchestrator):
        """Test that model_relation caches in cache."""
        request = RelationModelingRequest(
            source_name="Source", target_name="Target", relation_type="CONNECTS_TO"
        )

        response = await orchestrator.model_relation(request)

        cached = await orchestrator.cache.get(f"relation:{response.edge_id}")
        assert cached is not None

    @pytest.mark.asyncio
    async def test_query_graph_with_entity_id(self, orchestrator):
        """Test query_graph with entity_id parameter."""
        graph = Graph(
            graph_id="test_graph",
            name="Test",
            nodes=[
                GraphNode(node_id="n1", label="N1", node_type="entity"),
                GraphNode(node_id="n2", label="N2", node_type="entity"),
            ],
            edges=[
                GraphEdge(
                    edge_id="e1", source_id="n1", target_id="n2", relation="CONNECTS_TO"
                )
            ],
        )
        orchestrator._graphs["test_graph"] = graph

        request = GraphQueryRequest(graph_id="test_graph", entity_id="n1", depth=2)

        response = await orchestrator.query_graph(request)

        assert response.graph_id == "test_graph"

    @pytest.mark.asyncio
    async def test_query_graph_with_relation(self, orchestrator):
        """Test query_graph with relation parameter."""
        graph = Graph(
            graph_id="test_graph",
            name="Test",
            nodes=[
                GraphNode(node_id="n1", label="N1", node_type="entity"),
                GraphNode(node_id="n2", label="N2", node_type="entity"),
            ],
            edges=[
                GraphEdge(
                    edge_id="e1", source_id="n1", target_id="n2", relation="CONNECTS_TO"
                )
            ],
        )
        orchestrator._graphs["test_graph"] = graph

        request = GraphQueryRequest(graph_id="test_graph", relation="CONNECTS_TO")

        response = await orchestrator.query_graph(request)

        assert response.graph_id == "test_graph"

    @pytest.mark.asyncio
    async def test_infer_graph_with_different_reason_types(self, orchestrator):
        """Test infer_graph with different reason types."""
        graph = Graph(
            graph_id="test_graph",
            name="Test",
            nodes=[
                GraphNode(node_id="n1", label="N1", node_type="entity"),
                GraphNode(node_id="n2", label="N2", node_type="entity"),
            ],
            edges=[
                GraphEdge(
                    edge_id="e1", source_id="n1", target_id="n2", relation="CONNECTS_TO"
                )
            ],
        )
        orchestrator._graphs["test_graph"] = graph

        for reason_type in ["neighbors", "transitive", "pagerank", "paths"]:
            request = GraphReasonRequest(
                graph_id="test_graph", node_id="n1", reason_type=reason_type
            )
            response = await orchestrator.infer_graph(request)
            assert response.reason_type == reason_type

    @pytest.mark.asyncio
    async def test_visualize_graph_with_custom_dimensions(self, orchestrator):
        """Test visualize_graph with custom dimensions."""
        graph = Graph(
            graph_id="test_graph",
            name="Test",
            nodes=[GraphNode(node_id="n1", label="N1", node_type="entity")],
            edges=[],
        )
        orchestrator._graphs["test_graph"] = graph

        request = GraphVisualizationRequest(graph_id="test_graph", width=1200, height=800)

        response = await orchestrator.visualize_graph(request)

        assert response.graph_id == "test_graph"
        assert len(response.nodes) == 1
