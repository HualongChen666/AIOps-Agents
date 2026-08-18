# -*- coding: utf-8 -*-
"""Tests for main_app.py module."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

from extensions.addons.ai_plus.knowledge_graph_service.main_app import (
    app,
    get_orchestrator,
)
from extensions.addons.ai_plus.knowledge_graph_service.schemas import (
    EntityModelingRequest,
    RelationModelingRequest,
    GraphBuildRequest,
    GraphQueryRequest,
    GraphReasonRequest,
    GraphVisualizationRequest,
    ServiceDependencyGraphRequest,
    InfrastructureGraphRequest,
    FaultPropagationGraphRequest,
    ServiceDependency,
    InfrastructureComponent,
    FaultRule,
    FaultState,
    GraphNode,
    GraphEdge,
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_orchestrator():
    """Create a mock orchestrator."""
    orchestrator = MagicMock()
    orchestrator.cache = AsyncMock()
    orchestrator.cache.connect = AsyncMock()
    orchestrator.store = AsyncMock()
    orchestrator.store.connect = AsyncMock()
    orchestrator._request_counts = {}
    orchestrator._graphs = {}
    return orchestrator


@pytest.fixture
def mock_health_check():
    """Create a mock health check."""
    with patch(
        "extensions.addons.ai_plus.knowledge_graph_service.main_app.HealthCheckEngine"
    ) as mock:
        engine = MagicMock()
        engine.check = AsyncMock(return_value={"status": "ok", "service": "test", "environment": "test"})
        mock.return_value = engine
        yield mock


class TestMainApp:
    """Test cases for main_app.py module."""

    def test_get_orchestrator_singleton(self):
        """Test that get_orchestrator returns singleton instance."""
        orch1 = get_orchestrator()
        orch2 = get_orchestrator()
        assert orch1 is orch2

    def test_health_endpoint(self, client, mock_health_check):
        """Test health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data

    def test_metrics_endpoint(self, client):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Metrics endpoint returns text/plain with prometheus metrics

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_stats_endpoint(self, mock_get_orch, client):
        """Test stats endpoint."""
        mock_orch = MagicMock()
        mock_orch.get_stats = AsyncMock(
            return_value={
                "service": "test",
                "request_counts": {},
                "graph_entries": {},
                "cache_size": 0,
                "retry_policies": [],
            }
        )
        mock_get_orch.return_value = mock_orch

        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_model_entity_endpoint(self, mock_get_orch, client):
        """Test model entity endpoint."""
        mock_orch = MagicMock()
        mock_orch.model_entity = AsyncMock(
            return_value={
                "node_id": "test_node",
                "entity_name": "Test Entity",
                "entity_type": "generic",
                "modeled": True,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = EntityModelingRequest(
            entity_name="Test Entity", entity_type="generic"
        )
        response = client.post("/entity/model", json=request.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["node_id"] == "test_node"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_model_entity_exception(self, mock_get_orch, client):
        """Test model entity endpoint with exception."""
        mock_orch = MagicMock()
        mock_orch.model_entity = AsyncMock(side_effect=Exception("Test error"))
        mock_get_orch.return_value = mock_orch

        request = EntityModelingRequest(
            entity_name="Test Entity", entity_type="generic"
        )
        response = client.post("/entity/model", json=request.model_dump())
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_model_relation_endpoint(self, mock_get_orch, client):
        """Test model relation endpoint."""
        mock_orch = MagicMock()
        mock_orch.model_relation = AsyncMock(
            return_value={
                "edge_id": "test_edge",
                "source_id": "source",
                "target_id": "target",
                "relation_type": "CONNECTS_TO",
                "modeled": True,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = RelationModelingRequest(
            source_name="Source", target_name="Target", relation_type="CONNECTS_TO"
        )
        response = client.post("/relation/model", json=request.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["edge_id"] == "test_edge"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_model_relation_exception(self, mock_get_orch, client):
        """Test model relation endpoint with exception."""
        mock_orch = MagicMock()
        mock_orch.model_relation = AsyncMock(side_effect=Exception("Test error"))
        mock_get_orch.return_value = mock_orch

        request = RelationModelingRequest(
            source_name="Source", target_name="Target", relation_type="CONNECTS_TO"
        )
        response = client.post("/relation/model", json=request.model_dump())
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_build_graph_endpoint(self, mock_get_orch, client):
        """Test build graph endpoint."""
        mock_orch = MagicMock()
        mock_orch.build_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "nodes_count": 2,
                "edges_count": 1,
                "built": True,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = GraphBuildRequest(
            graph_name="test",
            nodes=[GraphNode(node_id="n1", label="N1", node_type="entity")],
            edges=[GraphEdge(edge_id="e1", source_id="n1", target_id="n2", relation="CONNECTS_TO")],
        )
        response = client.post("/graph/build", json=request.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "test_graph"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_build_graph_exception(self, mock_get_orch, client):
        """Test build graph endpoint with exception."""
        mock_orch = MagicMock()
        mock_orch.build_graph = AsyncMock(side_effect=Exception("Test error"))
        mock_get_orch.return_value = mock_orch

        request = GraphBuildRequest(graph_name="test")
        response = client.post("/graph/build", json=request.model_dump())
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_query_graph_endpoint(self, mock_get_orch, client):
        """Test query graph endpoint."""
        mock_orch = MagicMock()
        mock_orch.query_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "nodes": [],
                "edges": [],
                "total": 0,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = GraphQueryRequest(graph_id="test_graph")
        response = client.post("/graph/query", json=request.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "test_graph"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_query_graph_key_error(self, mock_get_orch, client):
        """Test query graph endpoint with KeyError."""
        mock_orch = MagicMock()
        mock_orch.query_graph = AsyncMock(side_effect=KeyError("Graph not found"))
        mock_get_orch.return_value = mock_orch

        request = GraphQueryRequest(graph_id="nonexistent")
        response = client.post("/graph/query", json=request.model_dump())
        assert response.status_code == 404

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_query_graph_exception(self, mock_get_orch, client):
        """Test query graph endpoint with exception."""
        mock_orch = MagicMock()
        mock_orch.query_graph = AsyncMock(side_effect=Exception("Test error"))
        mock_get_orch.return_value = mock_orch

        request = GraphQueryRequest(graph_id="test_graph")
        response = client.post("/graph/query", json=request.model_dump())
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_reason_graph_endpoint(self, mock_get_orch, client):
        """Test reason graph endpoint."""
        mock_orch = MagicMock()
        mock_orch.infer_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "node_id": "node1",
                "reason_type": "neighbors",
                "results": [],
                "total": 0,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = GraphReasonRequest(graph_id="test_graph", node_id="node1")
        response = client.post("/graph/reason", json=request.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "test_graph"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_reason_graph_key_error(self, mock_get_orch, client):
        """Test reason graph endpoint with KeyError."""
        mock_orch = MagicMock()
        mock_orch.infer_graph = AsyncMock(side_effect=KeyError("Graph not found"))
        mock_get_orch.return_value = mock_orch

        request = GraphReasonRequest(graph_id="nonexistent", node_id="node1")
        response = client.post("/graph/reason", json=request.model_dump())
        assert response.status_code == 404

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_reason_graph_exception(self, mock_get_orch, client):
        """Test reason graph endpoint with exception."""
        mock_orch = MagicMock()
        mock_orch.infer_graph = AsyncMock(side_effect=Exception("Test error"))
        mock_get_orch.return_value = mock_orch

        request = GraphReasonRequest(graph_id="test_graph", node_id="node1")
        response = client.post("/graph/reason", json=request.model_dump())
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_visualize_graph_endpoint(self, mock_get_orch, client):
        """Test visualize graph endpoint."""
        mock_orch = MagicMock()
        mock_orch.visualize_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "nodes": [],
                "edges": [],
            }
        )
        mock_get_orch.return_value = mock_orch

        request = GraphVisualizationRequest(graph_id="test_graph")
        response = client.post("/graph/visualize", json=request.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "test_graph"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_visualize_graph_key_error(self, mock_get_orch, client):
        """Test visualize graph endpoint with KeyError."""
        mock_orch = MagicMock()
        mock_orch.visualize_graph = AsyncMock(side_effect=KeyError("Graph not found"))
        mock_get_orch.return_value = mock_orch

        request = GraphVisualizationRequest(graph_id="nonexistent")
        response = client.post("/graph/visualize", json=request.model_dump())
        assert response.status_code == 404

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_visualize_graph_exception(self, mock_get_orch, client):
        """Test visualize graph endpoint with exception."""
        mock_orch = MagicMock()
        mock_orch.visualize_graph = AsyncMock(side_effect=Exception("Test error"))
        mock_get_orch.return_value = mock_orch

        request = GraphVisualizationRequest(graph_id="test_graph")
        response = client.post("/graph/visualize", json=request.model_dump())
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_build_service_dependency_graph_endpoint(self, mock_get_orch, client):
        """Test build service dependency graph endpoint."""
        mock_orch = MagicMock()
        mock_orch.build_service_dependency_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "services_count": 2,
                "dependencies_count": 1,
                "built": True,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = ServiceDependencyGraphRequest(
            services=[
                ServiceDependency(service="Service A", depends_on=["Service B"]),
                ServiceDependency(service="Service B", depends_on=[]),
            ]
        )
        response = client.post("/service-dependency/build", json=request.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "test_graph"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_build_service_dependency_graph_exception(self, mock_get_orch, client):
        """Test build service dependency graph endpoint with exception."""
        mock_orch = MagicMock()
        mock_orch.build_service_dependency_graph = AsyncMock(
            side_effect=Exception("Test error")
        )
        mock_get_orch.return_value = mock_orch

        request = ServiceDependencyGraphRequest(services=[])
        response = client.post("/service-dependency/build", json=request.model_dump())
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_build_infrastructure_graph_endpoint(self, mock_get_orch, client):
        """Test build infrastructure graph endpoint."""
        mock_orch = MagicMock()
        mock_orch.build_infrastructure_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "components_count": 2,
                "connections_count": 1,
                "built": True,
            }
        )
        mock_get_orch.return_value = mock_orch

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
        response = client.post("/infrastructure/build", json=request.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "test_graph"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_build_infrastructure_graph_exception(self, mock_get_orch, client):
        """Test build infrastructure graph endpoint with exception."""
        mock_orch = MagicMock()
        mock_orch.build_infrastructure_graph = AsyncMock(
            side_effect=Exception("Test error")
        )
        mock_get_orch.return_value = mock_orch

        request = InfrastructureGraphRequest(components=[])
        response = client.post("/infrastructure/build", json=request.model_dump())
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_build_fault_propagation_graph_endpoint(self, mock_get_orch, client):
        """Test build fault propagation graph endpoint."""
        mock_orch = MagicMock()
        mock_orch.build_fault_propagation_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "states_count": 1,
                "rules_count": 1,
                "impacted_count": 1,
                "built": True,
            }
        )
        mock_get_orch.return_value = mock_orch

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
        response = client.post("/fault-propagation/build", json=request.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["graph_id"] == "test_graph"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_build_fault_propagation_graph_exception(self, mock_get_orch, client):
        """Test build fault propagation graph endpoint with exception."""
        mock_orch = MagicMock()
        mock_orch.build_fault_propagation_graph = AsyncMock(
            side_effect=Exception("Test error")
        )
        mock_get_orch.return_value = mock_orch

        request = FaultPropagationGraphRequest(states=[], rules=[])
        response = client.post("/fault-propagation/build", json=request.model_dump())
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_rpc_list_methods(self, mock_get_orch, client):
        """Test RPC list_methods."""
        mock_orch = MagicMock()
        mock_orch.list_methods = MagicMock(
            return_value=[
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
        )
        mock_get_orch.return_value = mock_orch

        response = client.post("/rpc/list_methods")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert "model_entity" in data

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_rpc_stats(self, mock_get_orch, client):
        """Test RPC stats."""
        mock_orch = MagicMock()
        mock_orch.get_stats = AsyncMock(
            return_value={
                "service": "test",
                "request_counts": {},
                "graph_entries": {},
                "cache_size": 0,
                "retry_policies": [],
            }
        )
        mock_get_orch.return_value = mock_orch

        response = client.post("/rpc/stats")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_rpc_unknown_method(self, mock_get_orch, client):
        """Test RPC with unknown method."""
        mock_orch = MagicMock()
        mock_orch.list_methods = MagicMock(return_value=["model_entity"])
        mock_get_orch.return_value = mock_orch

        response = client.post("/rpc/unknown_method")
        assert response.status_code == 404

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_rpc_with_payload(self, mock_get_orch, client):
        """Test RPC with payload."""
        mock_orch = MagicMock()
        mock_orch.model_entity = AsyncMock(
            return_value={
                "node_id": "test_node",
                "entity_name": "Test",
                "entity_type": "generic",
                "modeled": True,
            }
        )
        mock_orch.list_methods = MagicMock(return_value=["model_entity"])
        mock_get_orch.return_value = mock_orch

        payload = {"entity_name": "Test", "entity_type": "generic"}
        response = client.post("/rpc/model_entity", json=payload)
        assert response.status_code == 200

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_rpc_key_error(self, mock_get_orch, client):
        """Test RPC with KeyError."""
        mock_orch = MagicMock()
        mock_orch.model_entity = AsyncMock(side_effect=KeyError("Not found"))
        mock_orch.list_methods = MagicMock(return_value=["model_entity"])
        mock_get_orch.return_value = mock_orch

        payload = {"entity_name": "Test", "entity_type": "generic"}
        response = client.post("/rpc/model_entity", json=payload)
        assert response.status_code == 404

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_rpc_exception(self, mock_get_orch, client):
        """Test RPC with exception."""
        mock_orch = MagicMock()
        mock_orch.model_entity = AsyncMock(side_effect=Exception("Test error"))
        mock_orch.list_methods = MagicMock(return_value=["model_entity"])
        mock_get_orch.return_value = mock_orch

        payload = {"entity_name": "Test", "entity_type": "generic"}
        response = client.post("/rpc/model_entity", json=payload)
        assert response.status_code == 500

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_rpc_without_payload(self, mock_get_orch, client):
        """Test RPC without payload."""
        mock_orch = MagicMock()
        mock_orch.get_stats = AsyncMock(
            return_value={
                "service": "test",
                "request_counts": {},
                "graph_entries": {},
                "cache_size": 0,
                "retry_policies": [],
            }
        )
        mock_orch.list_methods = MagicMock(return_value=["get_stats"])
        mock_get_orch.return_value = mock_orch

        response = client.post("/rpc/get_stats")
        assert response.status_code == 200

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_rpc_with_none_payload(self, mock_get_orch, client):
        """Test RPC with None payload."""
        mock_orch = MagicMock()
        mock_orch.get_stats = AsyncMock(
            return_value={
                "service": "test",
                "request_counts": {},
                "graph_entries": {},
                "cache_size": 0,
                "retry_policies": [],
            }
        )
        mock_orch.list_methods = MagicMock(return_value=["get_stats"])
        mock_get_orch.return_value = mock_orch

        response = client.post("/rpc/get_stats", json=None)
        assert response.status_code == 200

    def test_app_creation(self):
        """Test that app is created successfully."""
        assert app is not None
        assert app.title == "knowledge-graph-service"

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_model_entity_with_properties(self, mock_get_orch, client):
        """Test model entity with properties."""
        mock_orch = MagicMock()
        mock_orch.model_entity = AsyncMock(
            return_value={
                "node_id": "test_node",
                "entity_name": "Test Entity",
                "entity_type": "custom",
                "modeled": True,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = EntityModelingRequest(
            entity_name="Test Entity",
            entity_type="custom",
            properties={"key": "value"},
        )
        response = client.post("/entity/model", json=request.model_dump())
        assert response.status_code == 200

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_model_relation_with_properties(self, mock_get_orch, client):
        """Test model relation with properties."""
        mock_orch = MagicMock()
        mock_orch.model_relation = AsyncMock(
            return_value={
                "edge_id": "test_edge",
                "source_id": "source",
                "target_id": "target",
                "relation_type": "CONNECTS_TO",
                "modeled": True,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = RelationModelingRequest(
            source_name="Source",
            target_name="Target",
            relation_type="CONNECTS_TO",
            properties={"weight": 1.0},
        )
        response = client.post("/relation/model", json=request.model_dump())
        assert response.status_code == 200

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_build_graph_with_metadata(self, mock_get_orch, client):
        """Test build graph with metadata."""
        mock_orch = MagicMock()
        mock_orch.build_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "nodes_count": 0,
                "edges_count": 0,
                "built": True,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = GraphBuildRequest(
            graph_name="test",
            metadata={"custom": "value"},
        )
        response = client.post("/graph/build", json=request.model_dump())
        assert response.status_code == 200

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_query_graph_with_parameters(self, mock_get_orch, client):
        """Test query graph with parameters."""
        mock_orch = MagicMock()
        mock_orch.query_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "nodes": [],
                "edges": [],
                "total": 0,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = GraphQueryRequest(
            graph_id="test_graph", entity_id="node1", depth=3, top_k=20
        )
        response = client.post("/graph/query", json=request.model_dump())
        assert response.status_code == 200

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_reason_graph_with_parameters(self, mock_get_orch, client):
        """Test reason graph with parameters."""
        mock_orch = MagicMock()
        mock_orch.infer_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "node_id": "node1",
                "reason_type": "transitive",
                "results": [],
                "total": 0,
            }
        )
        mock_get_orch.return_value = mock_orch

        request = GraphReasonRequest(
            graph_id="test_graph",
            node_id="node1",
            reason_type="transitive",
            max_depth=5,
        )
        response = client.post("/graph/reason", json=request.model_dump())
        assert response.status_code == 200

    @patch("extensions.addons.ai_plus.knowledge_graph_service.main_app.get_orchestrator")
    def test_visualize_graph_with_dimensions(self, mock_get_orch, client):
        """Test visualize graph with custom dimensions."""
        mock_orch = MagicMock()
        mock_orch.visualize_graph = AsyncMock(
            return_value={
                "graph_id": "test_graph",
                "nodes": [],
                "edges": [],
            }
        )
        mock_get_orch.return_value = mock_orch

        request = GraphVisualizationRequest(graph_id="test_graph", width=1200, height=800)
        response = client.post("/graph/visualize", json=request.model_dump())
        assert response.status_code == 200
