# -*- coding: utf-8 -*-
"""API tests for topology microservice."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def orchestrator_client():
    from services.topology_service.orchestrator import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def analyzer_client():
    from services.topology_service.analyzer import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def visualizer_client():
    from services.topology_service.visualizer_app import app

    with TestClient(app) as client:
        yield client


class TestOrchestratorAPI:
    def test_health(self, orchestrator_client):
        response = orchestrator_client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "topology-orchestrator"

    def test_create_and_get_topology(self, orchestrator_client):
        response = orchestrator_client.post(
            "/topologies", json={"source": "config", "scope": "core"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "discovered"

        get_response = orchestrator_client.get(f"/topologies/{data['topology_id']}")
        assert get_response.status_code == 200
        assert get_response.json()["topology_id"] == data["topology_id"]

    def test_list_topologies(self, orchestrator_client):
        response = orchestrator_client.get("/topologies")
        assert response.status_code == 200
        assert "items" in response.json()

    def test_impact_analysis(self, orchestrator_client):
        create = orchestrator_client.post("/topologies", json={"source": "config", "scope": "core"})
        topology_id = create.json()["topology_id"]
        response = orchestrator_client.post(
            f"/topologies/{topology_id}/impact",
            json={"changed_nodes": ["agent"], "direction": "outbound", "max_depth": 3},
        )
        assert response.status_code == 200
        assert "impacted_nodes" in response.json()

    def test_visualize(self, orchestrator_client):
        create = orchestrator_client.post("/topologies", json={"source": "config", "scope": "core"})
        topology_id = create.json()["topology_id"]
        response = orchestrator_client.post(f"/topologies/{topology_id}/visualize")
        assert response.status_code == 200
        assert "nodes" in response.json()

    def test_version_commit(self, orchestrator_client):
        create = orchestrator_client.post("/topologies", json={"source": "config", "scope": "core"})
        topology_id = create.json()["topology_id"]
        response = orchestrator_client.post(f"/topologies/{topology_id}/version")
        assert response.status_code == 200
        assert response.json()["topology_id"] == topology_id

    def test_metrics(self, orchestrator_client):
        response = orchestrator_client.get("/metrics")
        assert response.status_code == 200


class TestAnalyzerAPI:
    def test_health(self, analyzer_client):
        response = analyzer_client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "topology-analyzer"

    def test_dependencies(self, analyzer_client):
        response = analyzer_client.post(
            "/topologies/t/dependencies", json={"service_name": "agent"}
        )
        assert response.status_code == 200

    def test_impact(self, analyzer_client):
        response = analyzer_client.post(
            "/topologies/t/impact",
            json={"changed_nodes": ["agent"], "direction": "outbound", "max_depth": 3},
        )
        assert response.status_code == 200


class TestVisualizerAPI:
    def test_health(self, visualizer_client):
        response = visualizer_client.get("/health")
        assert response.status_code == 200
        assert response.json()["service"] == "topology-visualizer"

    def test_visualize(self, visualizer_client):
        response = visualizer_client.post("/topologies/t/visualize")
        assert response.status_code == 200
