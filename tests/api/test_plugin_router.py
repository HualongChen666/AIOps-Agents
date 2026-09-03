# -*- coding: utf-8 -*-
"""
Test cases for Plugin Router
Comprehensive test coverage for plugin management API endpoints
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.plugin_router import router


# Test fixtures
@pytest.fixture
def client():
    """Create a test client for the router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def sample_plugin():
    """Create a sample plugin for testing"""
    return {
        "id": str(uuid4()),
        "name": "test_plugin",
        "version": "1.0.0",
        "description": "Test plugin description",
        "author": "Test Author",
        "plugin_type": "collector",
        "status": "active",
        "config_schema": {"type": "object"},
        "default_config": {"enabled": True},
        "dependencies": [],
        "file_path": "/plugins/test_plugin.py",
        "entry_point": "TestPlugin",
        "plugin_metadata": {"category": "monitoring"},
        "created_by": "test_user",
    }


@pytest.fixture
def sample_plugin_config():
    """Create a sample plugin config for testing"""
    return {
        "id": str(uuid4()),
        "plugin_id": str(uuid4()),
        "plugin_name": "test_plugin",
        "config_data": {"enabled": True, "interval": 60},
        "config_version": 1,
        "is_active": True,
        "description": "Test configuration",
        "updated_by": "test_user",
    }


# ============================================================================
# List Plugins Endpoint Tests
# ============================================================================


class TestListPluginsEndpoint:
    """Test cases for list plugins endpoint"""

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_list_plugins_success(
        self, mock_get_service, mock_rate_limit, mock_permission, client, sample_plugin
    ):
        """Test successful plugin listing"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_user.username = "test_user"
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.list_plugins.return_value = [sample_plugin]
        mock_service.count_plugins.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "plugins" in data
        assert data["total"] == 1

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_list_plugins_empty(
        self, mock_get_service, mock_rate_limit, mock_permission, client
    ):
        """Test plugin listing when no plugins exist"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.list_plugins.return_value = []
        mock_service.count_plugins.return_value = 0
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert data["total"] == 0

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_list_plugins_with_status_filter(
        self, mock_get_service, mock_rate_limit, mock_permission, client, sample_plugin
    ):
        """Test plugin listing with status filter"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.list_plugins.return_value = [sample_plugin]
        mock_service.count_plugins.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/?status=active")
        assert response.status_code == 200

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_list_plugins_with_type_filter(
        self, mock_get_service, mock_rate_limit, mock_permission, client, sample_plugin
    ):
        """Test plugin listing with type filter"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.list_plugins.return_value = [sample_plugin]
        mock_service.count_plugins.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/?plugin_type=collector")
        assert response.status_code == 200

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_list_plugins_with_pagination(
        self, mock_get_service, mock_rate_limit, mock_permission, client, sample_plugin
    ):
        """Test plugin listing with pagination"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.list_plugins.return_value = [sample_plugin]
        mock_service.count_plugins.return_value = 1
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/?limit=10&offset=0")
        assert response.status_code == 200

    @patch("api.plugin_router.require_permission")
    def test_list_plugins_unauthorized(self, mock_permission, client):
        """Test plugin listing without authentication"""
        from fastapi import HTTPException
        mock_permission.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        response = client.get("/api/plugins/")
        assert response.status_code == 401

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    def test_list_plugins_rate_limit_exceeded(
        self, mock_rate_limit, mock_permission, client
    ):
        """Test plugin listing when rate limit is exceeded"""
        from fastapi import HTTPException
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user
        mock_rate_limit.side_effect = HTTPException(status_code=429, detail="Rate limit exceeded")

        response = client.get("/api/plugins/")
        assert response.status_code == 429


# ============================================================================
# Create Plugin Endpoint Tests
# ============================================================================


class TestCreatePluginEndpoint:
    """Test cases for create plugin endpoint"""

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_create_plugin_success(
        self, mock_get_service, mock_rate_limit, mock_permission, client, sample_plugin
    ):
        """Test successful plugin creation"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.create_plugin.return_value = sample_plugin
        mock_get_service.return_value = mock_service

        plugin_data = {
            "name": "test_plugin",
            "version": "1.0.0",
            "description": "Test plugin",
            "author": "Test Author",
            "plugin_type": "collector",
        }

        response = client.post("/api/plugins/", json=plugin_data)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_plugin"

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_create_plugin_invalid_data(
        self, mock_get_service, mock_rate_limit, mock_permission, client
    ):
        """Test plugin creation with invalid data"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.create_plugin.side_effect = ValueError("Invalid plugin data")
        mock_get_service.return_value = mock_service

        plugin_data = {"name": "", "version": "1.0.0"}
        response = client.post("/api/plugins/", json=plugin_data)
        assert response.status_code == 400

    @patch("api.plugin_router.require_permission")
    def test_create_plugin_unauthorized(self, mock_permission, client):
        """Test plugin creation without authentication"""
        from fastapi import HTTPException
        mock_permission.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        response = client.post("/api/plugins/", json={"name": "test"})
        assert response.status_code == 401

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    def test_create_plugin_rate_limit_exceeded(
        self, mock_rate_limit, mock_permission, client
    ):
        """Test plugin creation when rate limit is exceeded"""
        from fastapi import HTTPException
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user
        mock_rate_limit.side_effect = HTTPException(status_code=429, detail="Rate limit exceeded")

        response = client.post("/api/plugins/", json={"name": "test"})
        assert response.status_code == 429


# ============================================================================
# Get Plugin Endpoint Tests
# ============================================================================


class TestGetPluginEndpoint:
    """Test cases for get plugin endpoint"""

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.get_plugin_service")
    def test_get_plugin_success(
        self, mock_get_service, mock_permission, client, sample_plugin
    ):
        """Test successful plugin retrieval"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.get_plugin.return_value = sample_plugin
        mock_get_service.return_value = mock_service

        response = client.get(f"/api/plugins/{sample_plugin['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_plugin["id"]

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.get_plugin_service")
    def test_get_plugin_not_found(self, mock_get_service, mock_permission, client):
        """Test getting a non-existent plugin"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.get_plugin.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/nonexistent")
        assert response.status_code == 404

    @patch("api.plugin_router.require_permission")
    def test_get_plugin_unauthorized(self, mock_permission, client):
        """Test getting plugin without authentication"""
        from fastapi import HTTPException
        mock_permission.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        response = client.get("/api/plugins/test-id")
        assert response.status_code == 401


# ============================================================================
# Update Plugin Endpoint Tests
# ============================================================================


class TestUpdatePluginEndpoint:
    """Test cases for update plugin endpoint"""

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_update_plugin_success(
        self, mock_get_service, mock_rate_limit, mock_permission, client, sample_plugin
    ):
        """Test successful plugin update"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.update_plugin.return_value = sample_plugin
        mock_get_service.return_value = mock_service

        update_data = {"description": "Updated description"}
        response = client.put(f"/api/plugins/{sample_plugin['id']}", json=update_data)
        assert response.status_code == 200

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_update_plugin_not_found(
        self, mock_get_service, mock_rate_limit, mock_permission, client
    ):
        """Test updating a non-existent plugin"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.update_plugin.return_value = None
        mock_get_service.return_value = mock_service

        response = client.put("/api/plugins/nonexistent", json={"description": "test"})
        assert response.status_code == 404

    @patch("api.plugin_router.require_permission")
    def test_update_plugin_unauthorized(self, mock_permission, client):
        """Test updating plugin without authentication"""
        from fastapi import HTTPException
        mock_permission.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        response = client.put("/api/plugins/test-id", json={"description": "test"})
        assert response.status_code == 401


# ============================================================================
# Delete Plugin Endpoint Tests
# ============================================================================


class TestDeletePluginEndpoint:
    """Test cases for delete plugin endpoint"""

    @patch("api.plugin_router.require_role")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_delete_plugin_success(
        self, mock_get_service, mock_rate_limit, mock_permission, client
    ):
        """Test successful plugin deletion"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.delete_plugin.return_value = True
        mock_get_service.return_value = mock_service

        response = client.delete("/api/plugins/test-id")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    @patch("api.plugin_router.require_role")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_delete_plugin_not_found(
        self, mock_get_service, mock_rate_limit, mock_permission, client
    ):
        """Test deleting a non-existent plugin"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.delete_plugin.return_value = False
        mock_get_service.return_value = mock_service

        response = client.delete("/api/plugins/nonexistent")
        assert response.status_code == 404

    @patch("api.plugin_router.require_role")
    def test_delete_plugin_forbidden(self, mock_permission, client):
        """Test deleting plugin without admin role"""
        from fastapi import HTTPException
        mock_permission.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        response = client.delete("/api/plugins/test-id")
        assert response.status_code == 401


# ============================================================================
# Run Plugin Endpoint Tests
# ============================================================================


class TestRunPluginEndpoint:
    """Test cases for run plugin endpoint"""

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_run_plugin_success(
        self, mock_get_service, mock_rate_limit, mock_permission, client
    ):
        """Test successful plugin execution"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.run_plugin.return_value = {
            "plugin_id": "test",
            "success": True,
            "output": {"result": "test"},
        }
        mock_get_service.return_value = mock_service

        response = client.post("/api/plugins/test_plugin/run", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_run_plugin_not_found(
        self, mock_get_service, mock_rate_limit, mock_permission, client
    ):
        """Test running a non-existent plugin"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.run_plugin.side_effect = ValueError("Plugin not found")
        mock_get_service.return_value = mock_service

        response = client.post("/api/plugins/nonexistent/run", json={})
        assert response.status_code == 404

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_run_plugin_execution_error(
        self, mock_get_service, mock_rate_limit, mock_permission, client
    ):
        """Test plugin execution with error"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.run_plugin.side_effect = Exception("Execution failed")
        mock_get_service.return_value = mock_service

        response = client.post("/api/plugins/test_plugin/run", json={})
        assert response.status_code == 500


# ============================================================================
# Get Plugin Stats Endpoint Tests
# ============================================================================


class TestGetPluginStatsEndpoint:
    """Test cases for get plugin stats endpoint"""

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.get_plugin_service")
    def test_get_plugin_stats_success(
        self, mock_get_service, mock_permission, client
    ):
        """Test successful plugin stats retrieval"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.get_stats.return_value = {
            "total_plugins": 10,
            "active_plugins": 8,
            "inactive_plugins": 2,
        }
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_plugins" in data

    @patch("api.plugin_router.require_permission")
    def test_get_plugin_stats_unauthorized(self, mock_permission, client):
        """Test getting stats without authentication"""
        from fastapi import HTTPException
        mock_permission.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        response = client.get("/api/plugins/stats")
        assert response.status_code == 401


# ============================================================================
# Get Plugin Executions Endpoint Tests
# ============================================================================


class TestGetPluginExecutionsEndpoint:
    """Test cases for get plugin executions endpoint"""

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.get_plugin_service")
    def test_get_plugin_executions_success(
        self, mock_get_service, mock_permission, client
    ):
        """Test successful plugin executions retrieval"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.list_executions.return_value = []
        mock_service.count_executions.return_value = 0
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/test_id/executions")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "executions" in data

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.get_plugin_service")
    def test_get_plugin_executions_with_filter(
        self, mock_get_service, mock_permission, client
    ):
        """Test plugin executions with success filter"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.list_executions.return_value = []
        mock_service.count_executions.return_value = 0
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/test_id/executions?success=true")
        assert response.status_code == 200

    @patch("api.plugin_router.require_permission")
    def test_get_plugin_executions_unauthorized(self, mock_permission, client):
        """Test getting executions without authentication"""
        from fastapi import HTTPException
        mock_permission.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        response = client.get("/api/plugins/test_id/executions")
        assert response.status_code == 401


# ============================================================================
# Get Plugin Config Endpoint Tests
# ============================================================================


class TestGetPluginConfigEndpoint:
    """Test cases for get plugin config endpoint"""

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.get_plugin_service")
    def test_get_plugin_config_success(
        self, mock_get_service, mock_permission, client, sample_plugin_config
    ):
        """Test successful plugin config retrieval"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.get_config_by_plugin_id.return_value = sample_plugin_config
        mock_get_service.return_value = mock_service

        response = client.get(f"/api/plugins/{sample_plugin_config['plugin_id']}/config")
        assert response.status_code == 200
        data = response.json()
        assert data["plugin_id"] == sample_plugin_config["plugin_id"]

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.get_plugin_service")
    def test_get_plugin_config_not_found(
        self, mock_get_service, mock_permission, client
    ):
        """Test getting config for non-existent plugin"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.get_config_by_plugin_id.return_value = None
        mock_get_service.return_value = mock_service

        response = client.get("/api/plugins/nonexistent/config")
        assert response.status_code == 404

    @patch("api.plugin_router.require_permission")
    def test_get_plugin_config_unauthorized(self, mock_permission, client):
        """Test getting config without authentication"""
        from fastapi import HTTPException
        mock_permission.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        response = client.get("/api/plugins/test_id/config")
        assert response.status_code == 401


# ============================================================================
# Update Plugin Config Endpoint Tests
# ============================================================================


class TestUpdatePluginConfigEndpoint:
    """Test cases for update plugin config endpoint"""

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_update_plugin_config_success(
        self, mock_get_service, mock_rate_limit, mock_permission, client, sample_plugin_config
    ):
        """Test successful plugin config update"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.get_config_by_plugin_id.return_value = sample_plugin_config
        mock_service.update_config.return_value = sample_plugin_config
        mock_get_service.return_value = mock_service

        update_data = {"config_data": {"enabled": False}}
        response = client.put(
            f"/api/plugins/{sample_plugin_config['plugin_id']}/config", json=update_data
        )
        assert response.status_code == 200

    @patch("api.plugin_router.require_permission")
    @patch("api.plugin_router.check_rate_limit")
    @patch("api.plugin_router.get_plugin_service")
    def test_update_plugin_config_not_found(
        self, mock_get_service, mock_rate_limit, mock_permission, client
    ):
        """Test updating config for non-existent plugin"""
        mock_user = Mock()
        mock_user.id = uuid4()
        mock_permission.return_value = mock_user

        mock_service = MagicMock()
        mock_service.get_config_by_plugin_id.return_value = None
        mock_get_service.return_value = mock_service

        response = client.put("/api/plugins/nonexistent/config", json={"config_data": {}})
        assert response.status_code == 404

    @patch("api.plugin_router.require_permission")
    def test_update_plugin_config_unauthorized(self, mock_permission, client):
        """Test updating config without authentication"""
        from fastapi import HTTPException
        mock_permission.side_effect = HTTPException(status_code=401, detail="Unauthorized")

        response = client.put("/api/plugins/test_id/config", json={"config_data": {}})
        assert response.status_code == 401
