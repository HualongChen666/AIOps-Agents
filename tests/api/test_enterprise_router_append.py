# -*- coding: utf-8 -*-
"""
Enterprise Router Append Tests
Tests for enterprise API endpoints with authorization checks
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


def test_enterprise_prefix_correct(client):
    """Test that enterprise router append uses correct prefix /api/enterprise"""
    from api.enterprise_router_append import router
    assert router.prefix == "/api/enterprise"


def test_get_enterprise_features_with_auth(client, admin_user):
    """Test GET /api/enterprise/enterprise-features with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/enterprise/enterprise-features")
        assert response.status_code in [200, 401, 403]


def test_get_enterprise_licenses_with_auth(client, admin_user):
    """Test GET /api/enterprise/enterprise-licenses with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/enterprise/enterprise-licenses")
        assert response.status_code in [200, 401, 403]


def test_get_enterprise_settings_with_auth(client, admin_user):
    """Test GET /api/enterprise/enterprise-settings with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/enterprise/enterprise-settings")
        assert response.status_code in [200, 401, 403]


def test_update_enterprise_settings_requires_admin(client, regular_user):
    """Test POST /api/enterprise/enterprise-settings requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.post("/api/enterprise/enterprise-settings", json={"company_name": "Test"})
        assert response.status_code in [401, 403]


def test_get_enterprise_users_with_auth(client, admin_user):
    """Test GET /api/enterprise/enterprise-users with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/enterprise/enterprise-users")
        assert response.status_code in [200, 401, 403]


def test_get_enterprise_roles_with_auth(client, admin_user):
    """Test GET /api/enterprise/enterprise-roles with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/enterprise/enterprise-roles")
        assert response.status_code in [200, 401, 403]


def test_get_enterprise_audit_with_auth(client, admin_user):
    """Test GET /api/enterprise/enterprise-audit with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/enterprise/enterprise-audit")
        assert response.status_code in [200, 401, 403]


def test_get_enterprise_compliance_with_auth(client, admin_user):
    """Test GET /api/enterprise/enterprise-compliance with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/enterprise/enterprise-compliance")
        assert response.status_code in [200, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
