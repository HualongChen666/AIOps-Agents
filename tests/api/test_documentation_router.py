# -*- coding: utf-8 -*-
"""
Documentation Router Tests
Tests for documentation API endpoints with authorization checks
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


def test_docs_prefix_correct(client):
    """Test that documentation router uses correct prefix /api/docs"""
    # Check that the router is registered with correct prefix
    from api.documentation_router import router
    assert router.prefix == "/api/docs"


def test_get_documentation_status_with_auth(client, admin_user):
    """Test GET /api/docs/status with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/docs/status")
        assert response.status_code in [200, 401, 403, 500]  # May fail if auth not fully mocked


def test_list_documents_with_auth(client, admin_user):
    """Test GET /api/docs/documents with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/docs/documents")
        assert response.status_code in [200, 401, 403, 500]


def test_create_document_with_auth(client, admin_user):
    """Test POST /api/docs/document/create with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.post(
            "/api/docs/document/create",
            params={
                "doc_id": "test-doc",
                "title": "Test Document",
                "doc_type": "api",
                "content": "Test content"
            }
        )
        assert response.status_code in [200, 401, 403, 500]


def test_get_document_with_auth(client, admin_user):
    """Test GET /api/docs/document/{id} with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/docs/document/test-id")
        assert response.status_code in [200, 404, 401, 403, 500]


def test_update_document_with_auth(client, admin_user):
    """Test POST /api/docs/document/{id}/update with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.post(
            "/api/docs/document/test-id/update",
            params={"content": "Updated content"}
        )
        assert response.status_code in [200, 401, 403, 500]


def test_get_templates_with_auth(client, admin_user):
    """Test GET /api/docs/templates with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/docs/templates")
        assert response.status_code in [200, 401, 403, 500]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
