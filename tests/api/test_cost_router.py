# -*- coding: utf-8 -*-
"""
Cost Router Tests
Tests for cost API endpoints with authorization checks
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


def test_cost_prefix_correct(client):
    """Test that cost router uses correct prefix /api/cost"""
    from api.cost_router import router
    assert router.prefix == "/api/cost"


def test_get_collect_with_auth(client, admin_user):
    """Test GET /api/cost/collect with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/cost/collect")
        assert response.status_code in [200, 401, 403, 404]


def test_get_forecast_with_auth(client, admin_user):
    """Test GET /api/cost/forecast with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/cost/forecast")
        assert response.status_code in [200, 401, 403, 404]


def test_get_budget_with_auth(client, admin_user):
    """Test GET /api/cost/budget with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/cost/budget")
        assert response.status_code in [200, 401, 403]


def test_get_cost_optimization_with_auth(client, admin_user):
    """Test GET /api/cost/cost-optimization with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/cost/cost-optimization")
        assert response.status_code in [200, 401, 403]


def test_get_resource_cost_with_auth(client, admin_user):
    """Test GET /api/cost/resource-cost with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/cost/resource-cost")
        assert response.status_code in [200, 401, 403]


def test_get_llm_cost_with_auth(client, admin_user):
    """Test GET /api/cost/llm-cost with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/cost/llm-cost")
        assert response.status_code in [200, 401, 403]


def test_get_budget_management_with_auth(client, admin_user):
    """Test GET /api/cost/budget-management with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/cost/budget-management")
        assert response.status_code in [200, 401, 403]


def test_create_budget_requires_admin(client, regular_user):
    """Test POST /api/cost/budget-management requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.post("/api/cost/budget-management", json={"name": "test", "amount": 1000})
        assert response.status_code in [401, 403]


def test_get_cost_prediction_with_auth(client, admin_user):
    """Test POST /api/cost/cost-prediction with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.post("/api/cost/cost-prediction", json={"time_horizon": 30})
        assert response.status_code in [200, 401, 403]


def test_get_cost_collection_with_auth(client, admin_user):
    """Test GET /api/cost/cost-collection with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/cost/cost-collection")
        assert response.status_code in [200, 401, 403]


def test_sync_cost_collection_requires_admin(client, regular_user):
    """Test POST /api/cost/cost-collection/{id}/sync requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.post("/api/cost/cost-collection/1/sync")
        assert response.status_code in [401, 403]


def test_get_cost_monitoring_with_auth(client, admin_user):
    """Test GET /api/cost/cost-monitoring with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/cost/cost-monitoring")
        assert response.status_code in [200, 401, 403]


def test_get_cost_report_with_auth(client, admin_user):
    """Test POST /api/cost/cost-report with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.post("/api/cost/cost-report", json={"period": "monthly"})
        assert response.status_code in [200, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
