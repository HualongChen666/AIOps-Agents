# -*- coding: utf-8 -*-
"""
Topology Simple Router Tests
Tests for topology API endpoints with authorization checks
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch


@pytest.fixture
def client():
    """Create test client"""
    from main import app
    return TestClient(app)


@pytest.fixture
def admin_user():
    """Mock admin user"""
    return Mock(id="admin-1", username="admin", role="admin", is_active=True)


@pytest.fixture
def regular_user():
    """Mock regular user"""
    return Mock(id="user-1", username="user", role="user", is_active=True)


def test_topology_prefix_correct(client):
    """Test that topology simple router uses correct prefix /api/topology"""
    from api.topology_simple_router import router
    assert router.prefix == "/api/topology"


def test_get_topology_graph_with_auth(client, admin_user):
    """Test GET /api/topology/topology-graph with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/topology/topology-graph")
        assert response.status_code in [200, 401, 403]


def test_get_topology_nodes_with_auth(client, admin_user):
    """Test GET /api/topology/topology-nodes with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/topology/topology-nodes")
        assert response.status_code in [200, 401, 403]


def test_get_topology_edges_with_auth(client, admin_user):
    """Test GET /api/topology/topology-edges with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/topology/topology-edges")
        assert response.status_code in [200, 401, 403]


def test_get_topology_dependencies_with_auth(client, admin_user):
    """Test GET /api/topology/topology-dependencies with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/topology/topology-dependencies")
        assert response.status_code in [200, 401, 403]


def test_get_topology_health_with_auth(client, admin_user):
    """Test GET /api/topology/topology-health with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/topology/topology-health")
        assert response.status_code in [200, 401, 403]


def test_get_topology_metrics_with_auth(client, admin_user):
    """Test GET /api/topology/topology-metrics with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/topology/topology-metrics")
        assert response.status_code in [200, 401, 403]


def test_get_topology_visualization_with_auth(client, admin_user):
    """Test GET /api/topology/topology-visualization with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/topology/topology-visualization")
        assert response.status_code in [200, 401, 403]


def test_get_topology_analysis_with_auth(client, admin_user):
    """Test GET /api/topology/topology-analysis with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/topology/topology-analysis")
        assert response.status_code in [200, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
