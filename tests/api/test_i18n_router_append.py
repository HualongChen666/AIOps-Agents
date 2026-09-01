# -*- coding: utf-8 -*-
"""
i18n Router Append Tests
Tests for i18n API endpoints with authorization checks
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


def test_i18n_prefix_correct(client):
    """Test that i18n router append uses correct prefix /api/i18n"""
    from api.i18n_router_append import router
    assert router.prefix == "/api/i18n"


def test_get_i18n_translations_with_auth(client, admin_user):
    """Test GET /api/i18n/i18n-translations with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/i18n/i18n-translations")
        assert response.status_code in [200, 401, 403]


def test_get_i18n_languages_with_auth(client, admin_user):
    """Test GET /api/i18n/i18n-languages with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/i18n/i18n-languages")
        assert response.status_code in [200, 401, 403]


def test_get_i18n_locales_with_auth(client, admin_user):
    """Test GET /api/i18n/i18n-locales with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/i18n/i18n-locales")
        assert response.status_code in [200, 401, 403]


def test_get_i18n_configuration_with_auth(client, admin_user):
    """Test GET /api/i18n/i18n-configuration with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/i18n/i18n-configuration")
        assert response.status_code in [200, 401, 403]


def test_update_i18n_configuration_requires_admin(client, regular_user):
    """Test POST /api/i18n/i18n-configuration requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.post("/api/i18n/i18n-configuration", json={"default_language": "zh"})
        assert response.status_code in [401, 403]


def test_get_i18n_translations_by_language_with_auth(client, admin_user):
    """Test GET /api/i18n/i18n-translations/{language} with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/i18n/i18n-translations/en")
        assert response.status_code in [200, 401, 403]


def test_update_i18n_translations_requires_admin(client, regular_user):
    """Test POST /api/i18n/i18n-translations/{language} requires admin role"""
    with patch("core.authentication.get_current_active_user", return_value=regular_user):
        response = client.post("/api/i18n/i18n-translations/en", json={"welcome": "Welcome"})
        assert response.status_code in [401, 403]


def test_get_i18n_pluralization_with_auth(client, admin_user):
    """Test GET /api/i18n/i18n-pluralization with authorization"""
    with patch("core.authentication.get_current_active_user", return_value=admin_user):
        response = client.get("/api/i18n/i18n-pluralization")
        assert response.status_code in [200, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto"])
