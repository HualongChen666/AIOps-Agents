# -*- coding: utf-8 -*-
"""Tests for main_app.py module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from extensions.addons.ai_plus.knowledge_graph_service.main_app import (
    app,
    get_orchestrator,
)
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    EntityModelingRequest,
    FaultPropagationGraphRequest,
    FaultRule,
    FaultState,
    GraphBuildRequest,
    GraphQueryRequest,
    GraphReasonRequest,
    GraphVisualizationRequest,
    InfrastructureComponent,
    InfrastructureGraphRequest,
    ServiceDependency,
    ServiceDependencyGraphRequest,
)


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = MagicMock()
    orchestrator.cache = AsyncMock()
    orchestrator.cache.connect = AsyncMock()
    orchestrator.store = AsyncMock()
    orchestrator.store.connect = AsyncMock()
    return orchestrator


@pytest.fixture
def client(mock_orchestrator):
    """Create a test client with mocked orchestrator."""
    with patch(
        "extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator",
        return_value=mock_orchestrator,
    ):
        yield TestClient(app)


class TestMainApp:
    """Test cases for main_app.py FastAPI endpoints."""

    def test_health_endpoint(self, client, mock_orchestrator):
        """Test /health endpoint."""
        mock_orchestrator.cache = AsyncMock()
        mock_orchestrator.store = AsyncMock()
        mock_orchestrator.cache.connect = AsyncMock()
        mock_orchestrator.store.connect = AsyncMock()

        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data

    def test_metrics_endpoint(self, client):
        """Test /metrics endpoint."""
        response = client.get("/metrics")

        assert response.status_code == 200
        # Prometheus metrics format
        assert "text/plain" in response.headers["content-type"]

    def test_stats_endpoint(self, client, mock_orchestrator):
        """Test /stats endpoint."""
        mock_orchestrator.get_stats = AsyncMock(
            return_value=MagicMock(
                service="test",
                request_counts={},
                graph_entries={},
                cache_size=0,
                retry_policies=[],
            )
        )

        response = client.get("/stats")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data

    def test_entity_model_endpoint(self, client, mock_orchestrator):
        """Test /entity/model endpoint."""
        mock_orchestrator.model_entity = AsyncMock(
            return_value=MagicMock(
                node_id="node1",
                entity_name="Test Entity",
                entity_type="generic",
                modeled=True,
            )
        )

        request = EntityModelingRequest(entity_name="Test Entity", entity_type="generic")

        response = client.post("/entity/model", json=request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "node1"
        assert data["modeled"] is True

    def test_entity_model_endpoint_error(self, client, mock_orchestrator):
        """Test /entity/model endpoint with error."""
        mock_orchestrator.model_entity = AsyncMock(side_effect=Exception("Test error"))

        request = EntityModelingRequest(entity_name="Test Entity", entity_type="generic")

        response = client.post("/entity/model", json=request.model_dump())

        assert response.status_code == 500

    def test_relation_model_endpoint(self, client, mock_orchestrator):
        """Test /relation/model endpoint."""
        mock_orchestrator.model_relation = AsyncMock(
            return_value=MagicMock(
                edge_id="edge1",
                source_id="node1",
                target_id="node2",
                relation_type="CONNECTS_TO",
                modeled=True,
            )
        )

        from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
            RelationModelingRequest,
        )

        request = RelationModelingRequest(
            source_name="Node 1", target_name="Node 2", relation_type="CONNECTS_TO"
        )

        response = client.post("/relation/model", json=request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert data["edge_id"] == "edge1"
        assert data["modeled"] is True

    def test_graph_build_endpoint(self, client, mock_orchestrator):
        """Test /graph/build endpoint."""
        from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
            GraphEdge,
            GraphNode,
        )

        mock_orchestrator.build_graph = AsyncMock(
            return_value=MagicMock(graph_id="graph1", nodes_count=2, edges_count=1, built=True)
        )

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

        response = client.post("/graph/build", json=request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "graph1"
        assert data["built"] is True

    def test_graph_query_endpoint(self, client, mock_orchestrator):
        """Test /graph/query endpoint."""
        mock_orchestrator.query_graph = AsyncMock(
            return_value=MagicMock(
                graph_id="graph1",
                nodes=[],
                edges=[],
                total=0,
            )
        )

        request = GraphQueryRequest(graph_id="graph1")

        response = client.post("/graph/query", json=request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "graph1"

    def test_graph_query_endpoint_not_found(self, client, mock_orchestrator):
        """Test /graph/query endpoint with graph not found."""
        mock_orchestrator.query_graph = AsyncMock(side_effect=KeyError("Graph not found"))

        request = GraphQueryRequest(graph_id="nonexistent")

        response = client.post("/graph/query", json=request.model_dump())

        assert response.status_code == 404

    def test_graph_reason_endpoint(self, client, mock_orchestrator):
        """Test /graph/reason endpoint."""
        mock_orchestrator.infer_graph = AsyncMock(
            return_value=MagicMock(
                graph_id="graph1",
                node_id="node1",
                reason_type="neighbors",
                results=[],
                total=0,
            )
        )

        request = GraphReasonRequest(graph_id="graph1", node_id="node1", reason_type="neighbors")

        response = client.post("/graph/reason", json=request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "graph1"

    def test_graph_reason_endpoint_not_found(self, client, mock_orchestrator):
        """Test /graph/reason endpoint with graph not found."""
        mock_orchestrator.infer_graph = AsyncMock(side_effect=KeyError("Graph not found"))

        request = GraphReasonRequest(
            graph_id="nonexistent", node_id="node1", reason_type="neighbors"
        )

        response = client.post("/graph/reason", json=request.model_dump())

        assert response.status_code == 404

    def test_graph_visualize_endpoint(self, client, mock_orchestrator):
        """Test /graph/visualize endpoint."""
        mock_orchestrator.visualize_graph = AsyncMock(
            return_value=MagicMock(
                graph_id="graph1",
                nodes=[],
                edges=[],
            )
        )

        request = GraphVisualizationRequest(graph_id="graph1")

        response = client.post("/graph/visualize", json=request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "graph1"

    def test_graph_visualize_endpoint_not_found(self, client, mock_orchestrator):
        """Test /graph/visualize endpoint with graph not found."""
        mock_orchestrator.visualize_graph = AsyncMock(side_effect=KeyError("Graph not found"))

        request = GraphVisualizationRequest(graph_id="nonexistent")

        response = client.post("/graph/visualize", json=request.model_dump())

        assert response.status_code == 404

    def test_service_dependency_build_endpoint(self, client, mock_orchestrator):
        """Test /service-dependency/build endpoint."""
        mock_orchestrator.build_service_dependency_graph = AsyncMock(
            return_value=MagicMock(
                graph_id="graph1",
                services_count=2,
                dependencies_count=1,
                built=True,
            )
        )

        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="Service A", depends_on=["Service B"]),
                ServiceDependency(service="Service B", depends_on=[]),
            ]
        )

        response = client.post("/service-dependency/build", json=request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "graph1"
        assert data["built"] is True

    def test_infrastructure_build_endpoint(self, client, mock_orchestrator):
        """Test /infrastructure/build endpoint."""
        mock_orchestrator.build_infrastructure_graph = AsyncMock(
            return_value=MagicMock(
                graph_id="graph1",
                components_count=2,
                connections_count=1,
                built=True,
            )
        )

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

        response = client.post("/infrastructure/build", json=request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "graph1"
        assert data["built"] is True

    def test_fault_propagation_build_endpoint(self, client, mock_orchestrator):
        """Test /fault-propagation/build endpoint."""
        mock_orchestrator.build_fault_propagation_graph = AsyncMock(
            return_value=MagicMock(
                graph_id="graph1",
                states_count=1,
                rules_count=1,
                impacted_count=1,
                built=True,
            )
        )

        request = FaultPropagationGraphRequest(
            states=[FaultState(component_id="Database", fault_type="down", severity=1.0)],
            rules=[FaultRule(source="Database", target="API", condition="down", impact="high")],
        )

        response = client.post("/fault-propagation/build", json=request.model_dump())

        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "graph1"
        assert data["built"] is True

    def test_rpc_list_methods(self, client, mock_orchestrator):
        """Test RPC list_methods endpoint."""
        mock_orchestrator.list_methods = MagicMock(
            return_value=[
                "model_entity",
                "model_relation",
                "build_graph",
            ]
        )

        response = client.post("/rpc/list_methods")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "model_entity" in data

    def test_rpc_stats(self, client, mock_orchestrator):
        """Test RPC stats endpoint."""
        mock_orchestrator.get_stats = AsyncMock(
            return_value=MagicMock(
                service="test",
                request_counts={},
                graph_entries={},
                cache_size=0,
                retry_policies=[],
            )
        )

        response = client.post("/rpc/stats")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data

    def test_rpc_unknown_method(self, client, mock_orchestrator):
        """Test RPC with unknown method."""
        mock_orchestrator.list_methods = MagicMock(return_value=["model_entity"])

        response = client.post("/rpc/unknown_method")

        assert response.status_code == 404

    def test_rpc_with_payload(self, client, mock_orchestrator):
        """Test RPC with payload."""
        mock_orchestrator.list_methods = MagicMock(return_value=["model_entity"])
        mock_orchestrator.model_entity = AsyncMock(
            return_value=MagicMock(
                node_id="node1",
                entity_name="Test",
                entity_type="generic",
                modeled=True,
            )
        )

        payload = {"entity_name": "Test", "entity_type": "generic"}

        response = client.post("/rpc/model_entity", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "node1"

    def test_rpc_error_handling(self, client, mock_orchestrator):
        """Test RPC error handling."""
        mock_orchestrator.list_methods = MagicMock(return_value=["model_entity"])
        mock_orchestrator.model_entity = AsyncMock(side_effect=KeyError("Test error"))

        payload = {"entity_name": "Test", "entity_type": "generic"}

        response = client.post("/rpc/model_entity", json=payload)

        assert response.status_code == 404

    def test_startup_event(self, mock_orchestrator):
        """Test startup event."""
        with patch(
            "extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator",
            return_value=mock_orchestrator,
        ):
            # Simulate startup
            import asyncio

            from extensions.addons.ai_plus.knowledge_graph_service.main_app import startup

            asyncio.run(startup())

            mock_orchestrator.cache.connect.assert_called_once()
            mock_orchestrator.store.connect.assert_called_once()
