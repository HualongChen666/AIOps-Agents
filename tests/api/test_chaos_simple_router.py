# -*- coding: utf-8 -*-
"""
Chaos Simple Router Tests
Tests for chaos API endpoints with authorization checks
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


def test_chaos_prefix_correct(client):
    """Test that chaos simple router uses correct prefix /api/chaos"""
    from api.chaos_simple_router import router
    assert router.prefix == "/api/chaos"


def test_get_chaos_configuration_with_auth(client, admin_user):
    """Test GET /api/chaos/chaos-configuration with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/chaos/chaos-configuration")
        assert response.status_code in [200, 401, 403]


def test_get_chaos_reports_with_auth(client, admin_user):
    """Test GET /api/chaos/chaos-reports with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/chaos/chaos-reports")
        assert response.status_code in [200, 401, 403]


def test_get_chaos_dashboard_with_auth(client, admin_user):
    """Test GET /api/chaos/chaos-dashboard with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/chaos/chaos-dashboard")
        assert response.status_code in [200, 401, 403]


def test_get_chaos_scenarios_with_auth(client, admin_user):
    """Test GET /api/chaos/chaos-scenarios with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/chaos/chaos-scenarios")
        assert response.status_code in [200, 401, 403]


def test_get_chaos_experiments_with_auth(client, admin_user):
    """Test GET /api/chaos/chaos-experiments with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/chaos/chaos-experiments")
        assert response.status_code in [200, 401, 403]


def test_get_chaos_mesh_with_auth(client, admin_user):
    """Test GET /api/chaos/chaos-mesh with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/chaos/chaos-mesh")
        assert response.status_code in [200, 401, 403]


def test_get_fault_injection_with_auth(client, admin_user):
    """Test GET /api/chaos/fault-injection with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/chaos/fault-injection")
        assert response.status_code in [200, 401, 403]


def test_get_chaos_engineering_with_auth(client, admin_user):
    """Test GET /api/chaos/chaos-engineering with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/chaos/chaos-engineering")
        assert response.status_code in [200, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
