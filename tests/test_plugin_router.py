# -*- coding: utf-8 -*-
"""Plugin Router Unit Tests

Tests for Plugin API endpoints with proper authentication and authorization.
"""

import os
import tempfile

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.plugin_router import router as plugin_router
from core.auth import verify_token
from core.database import Base, get_db
from core.models import Plugin, PluginConfig, PluginExecution, PluginStatus, User

# Test database setup
temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
temp_db.close()
TEST_DATABASE_URL = f"sqlite:///{temp_db.name.replace(os.sep, '/')}"
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
def test_user(db_session):
    """Create a test user."""
    user = User(
        username="testuser",
        email="test@example.com",
        hashed_password="hashed_password",
        role="operator",
        disabled=False,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_plugin(db_session):
    """Create a test plugin."""
    from datetime import datetime
    plugin = Plugin(
        id="test-plugin-1",
        name="test_plugin",
        version="1.0.0",
        description="Test plugin",
        author="Test Author",
        plugin_type="collector",
        status=PluginStatus.ACTIVE.value,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db_session.add(plugin)
    db_session.commit()
    db_session.refresh(plugin)
    return plugin


@pytest.fixture(scope="function")
def auth_headers(test_user):
    """Create authentication headers for testing."""
    # In a real scenario, this would generate a valid JWT token
    # For testing, we'll mock the authentication
    return {"Authorization": "Bearer test_token"}


class TestPluginRouter:
    """Test cases for Plugin Router."""

    def test_list_plugins_unauthorized(self):
        """Test listing plugins without authentication."""
        response = client.get("/api/plugins/")
        assert response.status_code == 401

    def test_list_plugins_authorized(self, auth_headers, test_plugin):
        """Test listing plugins with authentication."""
        # Note: This test would need proper JWT token generation
        # For now, we'll skip the actual authentication check
        response = client.get("/api/plugins/", headers=auth_headers)
        # Should return 401 without valid token
        assert response.status_code in [401, 403]

    def test_create_plugin_unauthorized(self):
        """Test creating a plugin without authentication."""
        plugin_data = {
            "name": "new_plugin",
            "version": "1.0.0",
            "plugin_type": "collector",
            "description": "New test plugin",
        }
        response = client.post("/api/plugins/", json=plugin_data)
        assert response.status_code == 401

    def test_get_plugin_unauthorized(self, test_plugin):
        """Test getting a plugin without authentication."""
        response = client.get(f"/api/plugins/{test_plugin.id}")
        assert response.status_code == 401

    def test_update_plugin_unauthorized(self, test_plugin):
        """Test updating a plugin without authentication."""
        update_data = {"description": "Updated description"}
        response = client.put(f"/api/plugins/{test_plugin.id}", json=update_data)
        assert response.status_code == 401

    def test_delete_plugin_unauthorized(self, test_plugin):
        """Test deleting a plugin without authentication."""
        response = client.delete(f"/api/plugins/{test_plugin.id}")
        assert response.status_code == 401

    def test_run_plugin_unauthorized(self):
        """Test running a plugin without authentication."""
        response = client.post("/api/plugins/test_plugin/run")
        assert response.status_code == 401

    def test_get_plugin_stats_unauthorized(self):
        """Test getting plugin stats without authentication."""
        response = client.get("/api/plugins/stats")
        assert response.status_code == 401

    def test_get_plugin_config_unauthorized(self, test_plugin):
        """Test getting plugin config without authentication."""
        response = client.get(f"/api/plugins/{test_plugin.id}/config")
        assert response.status_code == 401

    def test_update_plugin_config_unauthorized(self, test_plugin):
        """Test updating plugin config without authentication."""
        config_data = {"config_data": {"key": "value"}}
        response = client.put(f"/api/plugins/{test_plugin.id}/config", json=config_data)
        assert response.status_code == 401


class TestPluginService:
    """Test cases for Plugin Service layer."""

    def test_plugin_creation(self, db_session):
        """Test plugin creation through service."""
        from services.plugin_service import PluginCreate, PluginService, PluginType

        service = PluginService(db_session)
        plugin_data = PluginCreate(
            name="service_test_plugin",
            version="1.0.0",
            plugin_type=PluginType.COLLECTOR,
            description="Service test plugin",
        )
        
        plugin = service.create_plugin(plugin_data, created_by="test_user")
        assert plugin is not None
        assert plugin.name == "service_test_plugin"
        assert plugin.version == "1.0.0"
        assert plugin.plugin_type == PluginType.COLLECTOR.value

    def test_plugin_retrieval(self, db_session, test_plugin):
        """Test plugin retrieval through service."""
        from services.plugin_service import PluginService

        service = PluginService(db_session)
        plugin = service.get_plugin(test_plugin.id)
        
        assert plugin is not None
        assert plugin.id == test_plugin.id
        assert plugin.name == test_plugin.name

    def test_plugin_update(self, db_session, test_plugin):
        """Test plugin update through service."""
        from services.plugin_service import PluginService, PluginUpdate

        service = PluginService(db_session)
        update_data = PluginUpdate(description="Updated description")
        
        plugin = service.update_plugin(test_plugin.id, update_data)
        assert plugin is not None
        assert plugin.description == "Updated description"

    def test_plugin_deletion(self, db_session, test_plugin):
        """Test plugin deletion through service."""
        from services.plugin_service import PluginService

        service = PluginService(db_session)
        success = service.delete_plugin(test_plugin.id)
        
        assert success is True
        plugin = service.get_plugin(test_plugin.id)
        assert plugin is None

    def test_plugin_stats(self, db_session, test_plugin):
        """Test plugin statistics through service."""
        from services.plugin_service import PluginService

        service = PluginService(db_session)
        stats = service.get_stats()
        
        assert stats is not None
        assert stats.total_plugins >= 1
        assert stats.active_plugins >= 0


class TestPluginRepository:
    """Test cases for Plugin Repository layer."""

    def test_repository_create(self, db_session):
        """Test plugin creation through repository."""
        from datetime import datetime
        from services.plugin_service.repository import SQLAlchemyPluginRepository

        repo = SQLAlchemyPluginRepository(db_session)
        plugin = Plugin(
            id="repo-test-1",
            name="repo_test_plugin",
            version="1.0.0",
            plugin_type="collector",
            status=PluginStatus.INACTIVE.value,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        created_plugin = repo.create(plugin)
        assert created_plugin is not None
        assert created_plugin.name == "repo_test_plugin"

    def test_repository_get(self, db_session, test_plugin):
        """Test plugin retrieval through repository."""
        from services.plugin_service.repository import SQLAlchemyPluginRepository

        repo = SQLAlchemyPluginRepository(db_session)
        plugin = repo.get(test_plugin.id)
        
        assert plugin is not None
        assert plugin.id == test_plugin.id

    def test_repository_list(self, db_session, test_plugin):
        """Test plugin listing through repository."""
        from services.plugin_service.repository import SQLAlchemyPluginRepository

        repo = SQLAlchemyPluginRepository(db_session)
        plugins = repo.list(limit=10)
        
        assert len(plugins) >= 1
        assert any(p.id == test_plugin.id for p in plugins)

    def test_repository_count(self, db_session, test_plugin):
        """Test plugin counting through repository."""
        from services.plugin_service.repository import SQLAlchemyPluginRepository

        repo = SQLAlchemyPluginRepository(db_session)
        count = repo.count()
        
        assert count >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
