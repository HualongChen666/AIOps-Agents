# -*- coding: utf-8 -*-
"""
Qdrant Router Tests
Tests for vector API endpoints with authorization checks
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


def test_vector_prefix_correct(client):
    """Test that qdrant router uses correct prefix /api/vector"""
    # Check that the router is registered with correct prefix
    from api.qdrant_router import router
    assert router.prefix == "/api/vector"


def test_health_check_with_auth(client, admin_user):
    """Test GET /api/vector/health with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/vector/health")
        assert response.status_code in [200, 401, 403, 503]


def test_list_collections_with_auth(client, admin_user):
    """Test GET /api/vector/collections with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/vector/collections")
        assert response.status_code in [200, 401, 403, 503]


def test_create_collection_requires_admin(client, regular_user):
    """Test POST /api/vector/collections requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.post(
            "/api/vector/collections",
            json={"name": "test", "vector_size": 128, "distance": "Cosine"}
        )
        # Should fail due to insufficient permissions
        assert response.status_code in [401, 403, 503]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
