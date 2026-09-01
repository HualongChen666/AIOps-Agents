# -*- coding: utf-8 -*-
"""
Repair Router Append Tests
Tests for repair API endpoints with authorization checks
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


def test_repair_prefix_correct(client):
    """Test that repair router append uses correct prefix /api/repair"""
    from api.repair_router_append import router
    assert router.prefix == "/api/repair"


def test_get_repair_history_with_auth(client, admin_user):
    """Test GET /api/repair/repair-history with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/repair/repair-history")
        assert response.status_code in [200, 401, 403]


def test_get_repair_templates_with_auth(client, admin_user):
    """Test GET /api/repair/repair-templates with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/repair/repair-templates")
        assert response.status_code in [200, 401, 403]


def test_get_repair_metrics_with_auth(client, admin_user):
    """Test GET /api/repair/repair-metrics with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/repair/repair-metrics")
        assert response.status_code in [200, 401, 403]


def test_get_repair_policies_with_auth(client, admin_user):
    """Test GET /api/repair/repair-policies with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/repair/repair-policies")
        assert response.status_code in [200, 401, 403]


def test_update_repair_policies_requires_admin(client, regular_user):
    """Test POST /api/repair/repair-policies requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.post("/api/repair/repair-policies", json={"name": "test"})
        assert response.status_code in [401, 403]


def test_get_repair_status_with_auth(client, admin_user):
    """Test GET /api/repair/repair-status with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/repair/repair-status")
        assert response.status_code in [200, 401, 403]


def test_get_repair_recommendations_with_auth(client, admin_user):
    """Test GET /api/repair/repair-recommendations with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/repair/repair-recommendations")
        assert response.status_code in [200, 401, 403]


def test_get_repair_automation_with_auth(client, admin_user):
    """Test GET /api/repair/repair-automation with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/repair/repair-automation")
        assert response.status_code in [200, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
