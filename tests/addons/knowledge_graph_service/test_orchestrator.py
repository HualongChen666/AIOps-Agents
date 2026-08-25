# -*- coding: utf-8 -*-
"""Tests for KnowledgeGraphOrchestrator module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from extensions.addons.ai_plus.knowledge_graph_service.cache import CacheManager
from extensions.addons.ai_plus.knowledge_graph_service.graph_store import GraphStore
from extensions.addons.ai_plus.knowledge_graph_service.orchestrator import (
    KnowledgeGraphOrchestrator,
)
from extensions.addons.ai_plus.knowledge_graph_service.retry import KnowledgeGraphRetryEngine
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    EntityModelingRequest,
    FaultPropagationGraphRequest,
    FaultRule,
    FaultState,
    Graph,
    GraphBuildRequest,
    GraphEdge,
    GraphNode,
    GraphQueryRequest,
    GraphReasonRequest,
    GraphVisualizationRequest,
    InfrastructureComponent,
    InfrastructureGraphRequest,
    RelationModelingRequest,
    ServiceDependency,
    ServiceDependencyGraphRequest,
)


@pytest.fixture
def mock_cache():
    """Create a mock cache manager."""
    cache = AsyncMock()
    cache.connect = AsyncMock()
    cache.get = AsyncMock()
    cache.set = AsyncMock()
    cache.delete = AsyncMock()
    cache.clear = AsyncMock()
    cache._memory = {}
    return cache


@pytest.fixture
def mock_store():
    """Create a mock graph store."""
    store = AsyncMock()
    store.connect = AsyncMock()
    store.clear = AsyncMock()
    store.load_graph = AsyncMock()
    store.as_graph = AsyncMock()
    store._nodes = {}
    store._edges = []
    return store


@pytest.fixture
def mock_retry_engine():
    """Create a mock retry engine."""
    engine = MagicMock()
    engine.execute = AsyncMock()
    engine.list_policies = MagicMock(return_value=["default"])
    return engine


@pytest.fixture
def orchestrator(mock_cache, mock_retry_engine, mock_store):
    """Create a test orchestrator with mocked dependencies."""
    return KnowledgeGraphOrchestrator(
        cache=mock_cache, retry_engine=mock_retry_engine, store=mock_store
    )


class TestKnowledgeGraphOrchestrator:
    """Test cases for KnowledgeGraphOrchestrator class."""

    def test_initialization(self, mock_cache, mock_retry_engine, mock_store):
        """Test orchestrator initialization."""
        orchestrator = KnowledgeGraphOrchestrator(
            cache=mock_cache, retry_engine=mock_retry_engine, store=mock_store
        )

        assert orchestrator.cache == mock_cache
        assert orchestrator.retry_engine == mock_retry_engine
        assert orchestrator.store == mock_store
        assert orchestrator.entity_modeler is not None
        assert orchestrator.relation_modeler is not None
        assert orchestrator.graph_builder is not None
        assert orchestrator.query_engine is not None
        assert orchestrator.reasoning_engine is not None
        assert orchestrator.visualizer is not None

    def test_initialization_defaults(self):
        """Test orchestrator initialization with defaults."""
        orchestrator = KnowledgeGraphOrchestrator()

        assert orchestrator.cache is not None
        assert orchestrator.retry_engine is not None
        assert orchestrator.store is not None

    def test_list_methods(self, orchestrator):
        """Test list_methods."""
        methods = orchestrator.list_methods()

        assert isinstance(methods, list)
        assert "model_entity" in methods
        assert "model_relation" in methods
        assert "build_graph" in methods
        assert "query_graph" in methods
        assert "infer_graph" in methods
        assert "visualize_graph" in methods
        assert "build_service_dependency_graph" in methods
        assert "build_infrastructure_graph" in methods
        assert "build_fault_propagation_graph" in methods
        assert "get_stats" in methods

    @pytest.mark.asyncio
    async def test_get_stats(self, orchestrator):
        """Test get_stats."""
        orchestrator._request_counts = {"model_entity": 5, "build_graph": 3}
        orchestrator._graphs = {
            "graph1": Graph(
                graph_id="graph1",
                name="Graph 1",
                nodes=[GraphNode(node_id="n1", label="N1", node_type="entity")],
                edges=[],
            )
        }

        stats = await orchestrator.get_stats()

        assert stats.service == orchestrator.settings.service_name
        assert stats.request_counts == {"model_entity": 5, "build_graph": 3}
        assert stats.graph_entries["graphs"] == 1
        assert stats.graph_entries["nodes"] == 1
        assert stats.graph_entries["edges"] == 0
        assert stats.cache_size == len(orchestrator.cache._memory)

    @pytest.mark.asyncio
    async def test_model_entity(self, orchestrator):
        """Test model_entity."""
        request = EntityModelingRequest(entity_name="Test Entity", entity_type="generic")

        response = await orchestrator.model_entity(request)

        assert response.modeled is True
        assert response.entity_name == "Test Entity"
        assert response.entity_type == "generic"
        assert response.node_id is not None
        assert orchestrator._request_counts["model_entity"] == 1

    @pytest.mark.asyncio
    async def test_model_relation(self, orchestrator):
        """Test model_relation."""
        request = RelationModelingRequest(
            source_name="Node 1", target_name="Node 2", relation_type="CONNECTS_TO"
        )

        response = await orchestrator.model_relation(request)

        assert response.modeled is True
        assert response.relation_type == "CONNECTS_TO"
        assert response.edge_id is not None
        assert orchestrator._request_counts["model_relation"] == 1

    @pytest.mark.asyncio
    async def test_build_graph(self, orchestrator, mock_store, mock_retry_engine):
        """Test build_graph."""
        request = GraphBuildRequest(
            graph_name="test-graph",
            nodes=[
                GraphNode(node_id="node1", label="Node 1", node_type="entity"),
                GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            ],
            edges=[
                GraphEdge(
                    edge_id="edge1",
                    source_id="node1",
                    target_id="node2",
                    relation="CONNECTS_TO",
                )
            ],
        )

        mock_graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=request.nodes,
            edges=request.edges,
        )
        mock_retry_engine.execute = AsyncMock(return_value=mock_graph)
        mock_store.as_graph = AsyncMock(return_value=mock_graph)

        response = await orchestrator.build_graph(request)

        assert response.built is True
        assert response.graph_id == "graph1"
        assert response.nodes_count == 2
        assert response.edges_count == 1
        assert orchestrator._request_counts["build_graph"] == 1

    @pytest.mark.asyncio
    async def test_query_graph(self, orchestrator):
        """Test query_graph."""
        graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=[
                GraphNode(node_id="node1", label="Node 1", node_type="entity"),
                GraphNode(node_id="node2", label="Node 2", node_type="entity"),
            ],
            edges=[
                GraphEdge(
                    edge_id="edge1",
                    source_id="node1",
                    target_id="node2",
                    relation="CONNECTS_TO",
                )
            ],
        )
        orchestrator._graphs["graph1"] = graph

        request = GraphQueryRequest(graph_id="graph1")

        response = await orchestrator.query_graph(request)

        assert response.graph_id == "graph1"
        assert orchestrator._request_counts["query_graph"] == 1

    @pytest.mark.asyncio
    async def test_query_graph_not_found(self, orchestrator):
        """Test query_graph with graph not found."""
        request = GraphQueryRequest(graph_id="nonexistent")

        with pytest.raises(KeyError):
            await orchestrator.query_graph(request)

    @pytest.mark.asyncio
    async def test_infer_graph(self, orchestrator):
        """Test infer_graph."""
        graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=[
                GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            ],
            edges=[],
        )
        orchestrator._graphs["graph1"] = graph

        request = GraphReasonRequest(graph_id="graph1", node_id="node1", reason_type="neighbors")

        response = await orchestrator.infer_graph(request)

        assert response.graph_id == "graph1"
        assert orchestrator._request_counts["infer_graph"] == 1

    @pytest.mark.asyncio
    async def test_infer_graph_not_found(self, orchestrator):
        """Test infer_graph with graph not found."""
        request = GraphReasonRequest(
            graph_id="nonexistent", node_id="node1", reason_type="neighbors"
        )

        with pytest.raises(KeyError):
            await orchestrator.infer_graph(request)

    @pytest.mark.asyncio
    async def test_visualize_graph(self, orchestrator):
        """Test visualize_graph."""
        graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=[
                GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            ],
            edges=[],
        )
        orchestrator._graphs["graph1"] = graph

        request = GraphVisualizationRequest(graph_id="graph1")

        response = await orchestrator.visualize_graph(request)

        assert response.graph_id == "graph1"
        assert orchestrator._request_counts["visualize_graph"] == 1

    @pytest.mark.asyncio
    async def test_visualize_graph_not_found(self, orchestrator):
        """Test visualize_graph with graph not found."""
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
        assert orchestrator._request_counts["build_service_dependency_graph"] == 1

    @pytest.mark.asyncio
    async def test_build_infrastructure_graph(self, orchestrator):
        """Test build_infrastructure_graph."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="comp1", component_type="server", connections=["comp2"]
                ),
                InfrastructureComponent(
                    component_id="comp2", component_type="database", connections=[]
                ),
            ]
        )

        response = await orchestrator.build_infrastructure_graph(request)

        assert response.built is True
        assert response.graph_id is not None
        assert orchestrator._request_counts["build_infrastructure_graph"] == 1

    @pytest.mark.asyncio
    async def test_build_fault_propagation_graph(self, orchestrator):
        """Test build_fault_propagation_graph."""
        request = FaultPropagationGraphRequest(
            states=[FaultState(component_id="Database", fault_type="down", severity=1.0)],
            rules=[FaultRule(source="Database", target="API", condition="down", impact="high")],
        )

        response = await orchestrator.build_fault_propagation_graph(request)

        assert response.built is True
        assert response.graph_id is not None
        assert orchestrator._request_counts["build_fault_propagation_graph"] == 1

    def test_get_graph(self, orchestrator):
        """Test _get_graph."""
        graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=[],
            edges=[],
        )
        orchestrator._graphs["graph1"] = graph

        result = orchestrator._get_graph("graph1")

        assert result == graph

    def test_get_graph_not_found(self, orchestrator):
        """Test _get_graph with graph not found."""
        with pytest.raises(KeyError):
            orchestrator._get_graph("nonexistent")

    @pytest.mark.asyncio
    async def test_cache_graph_response(self, orchestrator, mock_store):
        """Test _cache_graph_response."""
        graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=[],
            edges=[],
        )
        mock_store.as_graph = AsyncMock(return_value=graph)

        await orchestrator._cache_graph_response("graph1")

        assert "graph1" in orchestrator._graphs
        assert orchestrator._graphs["graph1"] == graph

    @pytest.mark.asyncio
    async def test_new_id(self, orchestrator):
        """Test _new_id generates unique IDs."""
        id1 = orchestrator._new_id()
        id2 = orchestrator._new_id()

        assert id1 != id2
        assert isinstance(id1, str)
        assert isinstance(id2, str)

    def test_increment_count(self, orchestrator):
        """Test _increment_count."""
        orchestrator._increment_count("test_operation")

        assert orchestrator._request_counts["test_operation"] == 1

        orchestrator._increment_count("test_operation")

        assert orchestrator._request_counts["test_operation"] == 2

    @pytest.mark.asyncio
    async def test_model_entity_with_properties(self, orchestrator):
        """Test model_entity with custom properties."""
        request = EntityModelingRequest(
            entity_name="Test Entity",
            entity_type="custom",
            properties={"key1": "value1", "key2": "value2"},
        )

        response = await orchestrator.model_entity(request)

        assert response.modeled is True
        assert response.entity_type == "custom"

    @pytest.mark.asyncio
    async def test_model_relation_with_properties(self, orchestrator):
        """Test model_relation with custom properties."""
        request = RelationModelingRequest(
            source_name="Node 1",
            target_name="Node 2",
            relation_type="CONNECTS_TO",
            properties={"weight": 0.5},
        )

        response = await orchestrator.model_relation(request)

        assert response.modeled is True
        assert response.relation_type == "CONNECTS_TO"

    @pytest.mark.asyncio
    async def test_build_graph_empty(self, orchestrator, mock_store, mock_retry_engine):
        """Test build_graph with empty graph."""
        request = GraphBuildRequest(graph_name="empty-graph", nodes=[], edges=[])

        mock_graph = Graph(
            graph_id="graph1",
            name="empty-graph",
            nodes=[],
            edges=[],
        )
        mock_retry_engine.execute = AsyncMock(return_value=mock_graph)
        mock_store.as_graph = AsyncMock(return_value=mock_graph)

        response = await orchestrator.build_graph(request)

        assert response.built is True
        assert response.nodes_count == 0
        assert response.edges_count == 0

    @pytest.mark.asyncio
    async def test_build_graph_with_metadata(self, orchestrator, mock_store, mock_retry_engine):
        """Test build_graph with metadata."""
        request = GraphBuildRequest(
            graph_name="test-graph",
            nodes=[],
            edges=[],
            metadata={"custom": "value"},
        )

        mock_graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=[],
            edges=[],
            metadata={"custom": "value"},
        )
        mock_retry_engine.execute = AsyncMock(return_value=mock_graph)
        mock_store.as_graph = AsyncMock(return_value=mock_graph)

        response = await orchestrator.build_graph(request)

        assert response.built is True

    @pytest.mark.asyncio
    async def test_query_graph_with_filters(self, orchestrator):
        """Test query_graph with filters."""
        graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=[
                GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            ],
            edges=[],
        )
        orchestrator._graphs["graph1"] = graph

        request = GraphQueryRequest(graph_id="graph1", entity_id="node1", depth=2, top_k=10)

        response = await orchestrator.query_graph(request)

        assert response.graph_id == "graph1"

    @pytest.mark.asyncio
    async def test_infer_graph_different_types(self, orchestrator):
        """Test infer_graph with different reason types."""
        graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=[
                GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            ],
            edges=[],
        )
        orchestrator._graphs["graph1"] = graph

        for reason_type in ["neighbors", "transitive", "pagerank", "paths"]:
            request = GraphReasonRequest(
                graph_id="graph1", node_id="node1", reason_type=reason_type
            )

            response = await orchestrator.infer_graph(request)

            assert response.graph_id == "graph1"
            assert response.reason_type == reason_type

    @pytest.mark.asyncio
    async def test_visualize_graph_with_dimensions(self, orchestrator):
        """Test visualize_graph with custom dimensions."""
        graph = Graph(
            graph_id="graph1",
            name="test-graph",
            nodes=[
                GraphNode(node_id="node1", label="Node 1", node_type="entity"),
            ],
            edges=[],
        )
        orchestrator._graphs["graph1"] = graph

        request = GraphVisualizationRequest(graph_id="graph1", width=1024, height=768)

        response = await orchestrator.visualize_graph(request)

        assert response.graph_id == "graph1"

    @pytest.mark.asyncio
    async def test_build_service_dependency_complex(self, orchestrator):
        """Test build_service_dependency_graph with complex dependencies."""
        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(
                    service="Frontend",
                    depends_on=["API Gateway", "Auth Service"],
                ),
                ServiceDependency(service="API Gateway", depends_on=["User Service"]),
                ServiceDependency(service="Auth Service", depends_on=["User Service"]),
                ServiceDependency(service="User Service", depends_on=[]),
            ]
        )

        response = await orchestrator.build_service_dependency_graph(request)

        assert response.built is True
        assert response.services_count == 4

    @pytest.mark.asyncio
    async def test_build_infrastructure_complex(self, orchestrator):
        """Test build_infrastructure_graph with complex topology."""
        request = InfrastructureGraphRequest(
            components=[
                InfrastructureComponent(
                    component_id="web1",
                    component_type="web_server",
                    connections=["db1", "cache1"],
                ),
                InfrastructureComponent(
                    component_id="db1",
                    component_type="database",
                    connections=[],
                ),
                InfrastructureComponent(
                    component_id="cache1",
                    component_type="cache",
                    connections=[],
                ),
            ]
        )

        response = await orchestrator.build_infrastructure_graph(request)

        assert response.built is True
        assert response.components_count == 3

    @pytest.mark.asyncio
    async def test_build_fault_propagation_complex(self, orchestrator):
        """Test build_fault_propagation_graph with complex rules."""
        request = FaultPropagationGraphRequest(
            states=[
                FaultState(component_id="Database", fault_type="down", severity=1.0),
                FaultState(component_id="Cache", fault_type="timeout", severity=0.8),
            ],
            rules=[
                FaultRule(source="Database", target="API", condition="down", impact="critical"),
                FaultRule(source="Cache", target="API", condition="timeout", impact="high"),
                FaultRule(source="API", target="Frontend", condition="*", impact="medium"),
            ],
        )

        response = await orchestrator.build_fault_propagation_graph(request)

        assert response.built is True
        assert response.states_count == 2
        assert response.rules_count == 3
