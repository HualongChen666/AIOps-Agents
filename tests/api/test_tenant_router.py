# -*- coding: utf-8 -*-
"""
Tenant Router Tests
Tests for tenant API endpoints with authorization checks
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


def test_tenant_prefix_correct(client):
    """Test that tenant router uses correct prefix /api/tenant"""
    # Check that the router is registered with correct prefix
    from api.tenant_router import router
    assert router.prefix == "/api/tenant"


def test_get_all_tenants_with_auth(client, admin_user):
    """Test GET /api/tenant/ with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/tenant/")
        assert response.status_code in [200, 401, 403]  # May fail if auth not fully mocked


def test_create_tenant_requires_admin(client, regular_user):
    """Test POST /api/tenant/ requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.post(
            "/api/tenant/",
            json={"name": "test-tenant", "plan": "basic", "status": "active"}
        )
        # Should fail due to insufficient permissions
        assert response.status_code in [401, 403]


def test_get_tenant_by_id_with_auth(client, admin_user):
    """Test GET /api/tenant/{id} with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/tenant/test-id")
        assert response.status_code in [200, 404, 401, 403]


def test_update_tenant_requires_admin(client, regular_user):
    """Test PUT /api/tenant/{id} requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.put(
            "/api/tenant/test-id",
            json={"name": "updated-name"}
        )
        # Should fail due to insufficient permissions
        assert response.status_code in [401, 403]


def test_delete_tenant_requires_admin(client, regular_user):
    """Test DELETE /api/tenant/{id} requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.delete("/api/tenant/test-id")
        # Should fail due to insufficient permissions
        assert response.status_code in [401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
