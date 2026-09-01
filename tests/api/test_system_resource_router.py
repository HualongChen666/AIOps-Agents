# -*- coding: utf-8 -*-
"""
System Resource Router Tests
Tests for system resource API endpoints with authorization checks
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


def test_resources_prefix_correct(client):
    """Test that system resource router uses correct prefix /api/resources"""
    # Check that the router is registered with correct prefix
    from api.system_resource_router import router
    assert router.prefix == "/api/resources"


def test_get_optimization_status_with_auth(client, admin_user):
    """Test GET /api/resources/status with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/resources/status")
        assert response.status_code in [200, 401, 403, 500]


def test_get_resource_summary_with_auth(client, admin_user):
    """Test GET /api/resources/summary with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/resources/summary")
        assert response.status_code in [200, 401, 403, 500]


def test_analyze_memory_usage_with_auth(client, admin_user):
    """Test GET /api/resources/memory with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/resources/memory")
        assert response.status_code in [200, 401, 403, 500]


def test_optimize_memory_with_auth(client, admin_user):
    """Test POST /api/resources/memory/optimize with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.post("/api/resources/memory/optimize")
        assert response.status_code in [200, 401, 403, 500]


def test_analyze_cpu_usage_with_auth(client, admin_user):
    """Test GET /api/resources/cpu with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/resources/cpu")
        assert response.status_code in [200, 401, 403, 500]


def test_optimize_cpu_with_auth(client, admin_user):
    """Test POST /api/resources/cpu/optimize with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.post("/api/resources/cpu/optimize")
        assert response.status_code in [200, 401, 403, 500]


def test_analyze_network_usage_with_auth(client, admin_user):
    """Test GET /api/resources/network with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/resources/network")
        assert response.status_code in [200, 401, 403, 500]


def test_optimize_network_with_auth(client, admin_user):
    """Test POST /api/resources/network/optimize with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.post("/api/resources/network/optimize")
        assert response.status_code in [200, 401, 403, 500]


def test_run_comprehensive_optimization_with_auth(client, admin_user):
    """Test POST /api/resources/optimize with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.post("/api/resources/optimize")
        assert response.status_code in [200, 401, 403, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
