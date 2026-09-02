# -*- coding: utf-8 -*-
"""Plugin Integration Tests

Integration tests for Plugin API with full database and authentication setup.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.plugin_router import router as plugin_router
from core.auth import verify_token
from core.database import Base, get_db
from core.models import Plugin, PluginConfig, PluginExecution, PluginStatus, User
from jose import jwt

# Test database setup
TEST_DATABASE_URL = "sqlite:///./test_plugin_integration.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# Create test app
app = FastAPI()
app.include_router(plugin_router)
app.dependency_overrides[get_db] = override_get_db

# Create tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture(scope="function")
def admin_user(db_session):
    """Create an admin user for testing."""
    user = User(
        username="admin",
        email="admin@example.com",
        hashed_password="hashed_password",
        role="admin",
        disabled=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def operator_user(db_session):
    """Create an operator user for testing."""
    user = User(
        username="operator",
        email="operator@example.com",
        hashed_password="hashed_password",
        role="operator",
        disabled=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def regular_user(db_session):
    """Create a regular user for testing."""
    user = User(
        username="user",
        email="user@example.com",
        hashed_password="hashed_password",
        role="user",
        disabled=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_token(admin_user):
    """Create a valid JWT token for testing."""
    from config import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET_KEY
    
    payload = {
        "sub": str(admin_user.id),
        "username": admin_user.username,
        "role": admin_user.role,
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
    }
    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


@pytest.fixture(scope="function")
def auth_headers(auth_token):
    """Create authentication headers for testing."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="function")
def test_plugin(db_session):
    """Create a test plugin."""
    plugin = Plugin(
        id="integration-test-plugin-1",
        name="integration_test_plugin",
        version="1.0.0",
        description="Integration test plugin",
        author="Test Author",
        plugin_type="collector",
        status=PluginStatus.ACTIVE.value,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )
    db_session.add(plugin)
    db_session.commit()
    db_session.refresh(plugin)
    return plugin


@pytest.fixture(scope="function")
def test_plugin_config(db_session, test_plugin):
    """Create a test plugin config."""
    config = PluginConfig(
        id="integration-test-config-1",
        plugin_id=test_plugin.id,
        plugin_name=test_plugin.name,
        config_data={"key": "value"},
        config_version=1,
        is_active=True,
        created_at="2024-01-01T00:00:00",
        updated_at="2024-01-01T00:00:00",
    )
    db_session.add(config)
    db_session.commit()
    db_session.refresh(config)
    return config


class TestPluginIntegration:
    """Integration tests for Plugin API."""

    def test_list_plugins_with_auth(self, auth_headers, test_plugin):
        """Test listing plugins with valid authentication."""
        response = client.get("/api/plugins/", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "plugins" in data
        assert isinstance(data["plugins"], list)

    def test_create_plugin_with_auth(self, auth_headers):
        """Test creating a plugin with valid authentication."""
        plugin_data = {
            "name": "new_integration_plugin",
            "version": "1.0.0",
            "plugin_type": "collector",
            "description": "New integration test plugin",
        }
        response = client.post("/api/plugins/", json=plugin_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["name"] == "new_integration_plugin"
        assert data["version"] == "1.0.0"

    def test_get_plugin_with_auth(self, auth_headers, test_plugin):
        """Test getting a plugin with valid authentication."""
        response = client.get(f"/api/plugins/{test_plugin.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_plugin.id
        assert data["name"] == test_plugin.name

    def test_update_plugin_with_auth(self, auth_headers, test_plugin):
        """Test updating a plugin with valid authentication."""
        update_data = {"description": "Updated integration description"}
        response = client.put(f"/api/plugins/{test_plugin.id}", json=update_data, headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["description"] == "Updated integration description"

    def test_delete_plugin_with_auth(self, auth_headers, test_plugin):
        """Test deleting a plugin with valid authentication."""
        response = client.delete(f"/api/plugins/{test_plugin.id}", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data

    def test_get_plugin_stats_with_auth(self, auth_headers):
        """Test getting plugin stats with valid authentication."""
        response = client.get("/api/plugins/stats", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total_plugins" in data
        assert "active_plugins" in data
        assert "total_executions" in data

    def test_get_plugin_config_with_auth(self, auth_headers, test_plugin_config):
        """Test getting plugin config with valid authentication."""
        response = client.get(f"/api/plugins/{test_plugin_config.plugin_id}/config", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["plugin_id"] == test_plugin_config.plugin_id
        assert "config_data" in data

    def test_update_plugin_config_with_auth(self, auth_headers, test_plugin_config):
        """Test updating plugin config with valid authentication."""
        config_data = {"config_data": {"new_key": "new_value"}}
        response = client.put(
            f"/api/plugins/{test_plugin_config.plugin_id}/config",
            json=config_data,
            headers=auth_headers,
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["config_data"]["new_key"] == "new_value"

    def test_list_plugin_executions_with_auth(self, auth_headers, test_plugin):
        """Test listing plugin executions with valid authentication."""
        response = client.get(f"/api/plugins/{test_plugin.id}/executions", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "executions" in data


class TestPluginRBAC:
    """Test RBAC permissions for Plugin API."""

    def test_user_cannot_create_plugin(self, db_session, regular_user):
        """Test that regular users cannot create plugins."""
        from config import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET_KEY
        from jose import jwt
        
        payload = {
            "sub": str(regular_user.id),
            "username": regular_user.username,
            "role": regular_user.role,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        
        plugin_data = {
            "name": "unauthorized_plugin",
            "version": "1.0.0",
            "plugin_type": "collector",
        }
        response = client.post("/api/plugins/", json=plugin_data, headers=headers)
        assert response.status_code == 403

    def test_operator_can_create_plugin(self, db_session, operator_user):
        """Test that operators can create plugins."""
        from config import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET_KEY
        from jose import jwt
        
        payload = {
            "sub": str(operator_user.id),
            "username": operator_user.username,
            "role": operator_user.role,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        
        plugin_data = {
            "name": "operator_plugin",
            "version": "1.0.0",
            "plugin_type": "collector",
        }
        response = client.post("/api/plugins/", json=plugin_data, headers=headers)
        assert response.status_code == 200

    def test_admin_can_delete_plugin(self, db_session, admin_user):
        """Test that admins can delete plugins."""
        from config import JWT_ALGORITHM, JWT_AUDIENCE, JWT_ISSUER, JWT_SECRET_KEY
        from jose import jwt
        
        # Create a test plugin
        plugin = Plugin(
            id="admin-delete-test",
            name="admin_delete_test",
            version="1.0.0",
            plugin_type="collector",
            status=PluginStatus.ACTIVE.value,
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        db_session.add(plugin)
        db_session.commit()
        
        payload = {
            "sub": str(admin_user.id),
            "username": admin_user.username,
            "role": admin_user.role,
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        }
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        headers = {"Authorization": f"Bearer {token}"}
        
        response = client.delete(f"/api/plugins/{plugin.id}", headers=headers)
        assert response.status_code == 200


class TestPluginRateLimiting:
    """Test rate limiting for Plugin API."""

    def test_rate_limiting_on_create(self, auth_headers):
        """Test that rate limiting works on plugin creation."""
        plugin_data = {
            "name": "rate_limit_test",
            "version": "1.0.0",
            "plugin_type": "collector",
        }
        
        # Make multiple requests to trigger rate limit
        responses = []
        for _ in range(35):  # Exceed the 30 requests per minute limit
            response = client.post("/api/plugins/", json=plugin_data, headers=auth_headers)
            responses.append(response.status_code)
        
        # At least one should be rate limited (429)
        assert 429 in responses


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-n", "auto", "--tb=short"])
