# -*- coding: utf-8 -*-
"""
Test cases for Plugin Development Router
Comprehensive test coverage for plugin development SDK API endpoints
"""

from datetime import datetime
from unittest.mock import MagicMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.plugin_development_router import router


# Test fixtures
@pytest.fixture
def client():
    """Create a test client for the router"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock user for authentication"""
    user = Mock()
    user.id = uuid4()
    user.username = "test_user"
    user.role = "operator"
    return user


# ============================================================================
# Get SDK Status Endpoint Tests
# ============================================================================


class TestGetSDKStatus:
    """Test cases for get_sdk_status endpoint"""

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_get_sdk_status_success(self, mock_get_sdk, client):
        """Test successful SDK status retrieval"""
        mock_sdk = MagicMock()
        mock_sdk.get_sdk_summary.return_value = {
            "sdk_version": "1.0.0",
            "available": True,
            "templates": ["collector", "analyzer", "notifier"],
        }
        mock_get_sdk.return_value = mock_sdk

        response = client.get("/api/plugin-sdk/status")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["sdk_version"] == "1.0.0"
        assert "timestamp" in data

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_get_sdk_status_exception(self, mock_get_sdk, client):
        """Test SDK status retrieval with exception"""
        mock_get_sdk.side_effect = Exception("SDK error")

        response = client.get("/api/plugin-sdk/status")
        assert response.status_code == 500
        assert "SDK error" in response.json()["detail"]


# ============================================================================
# Get Available Templates Endpoint Tests
# ============================================================================


class TestGetAvailableTemplates:
    """Test cases for get_available_templates endpoint"""

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_get_available_templates_success(self, mock_get_sdk, client):
        """Test successful templates retrieval"""
        mock_sdk = MagicMock()
        mock_sdk.get_available_templates.return_value = ["collector", "analyzer", "notifier", "action"]
        mock_get_sdk.return_value = mock_sdk

        response = client.get("/api/plugin-sdk/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["count"] == 4
        assert "collector" in data["data"]["templates"]
        assert "timestamp" in data

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_get_available_templates_empty(self, mock_get_sdk, client):
        """Test templates retrieval when no templates available"""
        mock_sdk = MagicMock()
        mock_sdk.get_available_templates.return_value = []
        mock_get_sdk.return_value = mock_sdk

        response = client.get("/api/plugin-sdk/templates")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["count"] == 0

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_get_available_templates_exception(self, mock_get_sdk, client):
        """Test templates retrieval with exception"""
        mock_get_sdk.side_effect = Exception("Templates error")

        response = client.get("/api/plugin-sdk/templates")
        assert response.status_code == 500
        assert "Templates error" in response.json()["detail"]


# ============================================================================
# Generate Plugin Package Endpoint Tests
# ============================================================================


class TestGeneratePluginPackage:
    """Test cases for generate_plugin_package endpoint"""

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_package_success(self, mock_get_sdk, client):
        """Test successful plugin package generation"""
        mock_sdk = MagicMock()
        mock_sdk.create_plugin_package.return_value = {
            "plugin_name": "test_plugin",
            "version": "1.0.0",
            "template_type": "collector",
        }
        mock_get_sdk.return_value = mock_sdk

        request_data = {
            "template_type": "collector",
            "plugin_name": "test_plugin",
            "class_name": "TestPlugin",
            "version": "1.0.0",
            "author": "Test Author",
        }

        response = client.post("/api/plugin-sdk/generate", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert data["data"]["plugin_name"] == "test_plugin"
        assert "timestamp" in data

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_package_with_custom_config(self, mock_get_sdk, client):
        """Test plugin package generation with custom config"""
        mock_sdk = MagicMock()
        mock_sdk.create_plugin_package.return_value = {
            "plugin_name": "test_plugin",
            "version": "1.0.0",
            "template_type": "analyzer",
        }
        mock_get_sdk.return_value = mock_sdk

        request_data = {
            "template_type": "analyzer",
            "plugin_name": "test_plugin",
            "class_name": "TestPlugin",
            "version": "1.0.0",
            "author": "Test Author",
            "custom_config": {"enabled": True, "interval": 60},
        }

        response = client.post("/api/plugin-sdk/generate", json=request_data)
        assert response.status_code == 200

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_package_all_templates(self, mock_get_sdk, client):
        """Test plugin package generation for all template types"""
        mock_sdk = MagicMock()
        mock_sdk.create_plugin_package.return_value = {
            "plugin_name": "test_plugin",
            "version": "1.0.0",
            "template_type": "collector",
        }
        mock_get_sdk.return_value = mock_sdk

        template_types = ["collector", "analyzer", "notifier", "action"]
        for template_type in template_types:
            request_data = {
                "template_type": template_type,
                "plugin_name": f"test_{template_type}",
                "class_name": "TestPlugin",
                "version": "1.0.0",
            }
            response = client.post("/api/plugin-sdk/generate", json=request_data)
            assert response.status_code == 200

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_package_exception(self, mock_get_sdk, client):
        """Test plugin package generation with exception"""
        mock_get_sdk.side_effect = Exception("Package generation error")

        request_data = {
            "template_type": "collector",
            "plugin_name": "test_plugin",
            "class_name": "TestPlugin",
        }

        response = client.post("/api/plugin-sdk/generate", json=request_data)
        assert response.status_code == 500
        assert "Package generation error" in response.json()["detail"]


# ============================================================================
# Generate Plugin Code Endpoint Tests
# ============================================================================


class TestGeneratePluginCode:
    """Test cases for generate_plugin_code endpoint"""

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_code_success(self, mock_get_sdk, client):
        """Test successful plugin code generation"""
        mock_sdk = MagicMock()
        mock_sdk.generate_plugin_code.return_value = "# Plugin code here"
        mock_get_sdk.return_value = mock_sdk

        request_data = {
            "template_type": "collector",
            "plugin_name": "test_plugin",
            "class_name": "TestPlugin",
            "version": "1.0.0",
            "author": "Test Author",
        }

        response = client.get("/api/plugin-sdk/generate/code", params=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "code" in data["data"]
        assert "line_count" in data["data"]
        assert "timestamp" in data

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_code_all_types(self, mock_get_sdk, client):
        """Test plugin code generation for all template types"""
        mock_sdk = MagicMock()
        mock_sdk.generate_plugin_code.return_value = "# Plugin code"
        mock_get_sdk.return_value = mock_sdk

        template_types = ["collector", "analyzer", "notifier", "action"]
        for template_type in template_types:
            request_data = {
                "template_type": template_type,
                "plugin_name": f"test_{template_type}",
                "class_name": "TestPlugin",
            }
            response = client.get("/api/plugin-sdk/generate/code", params=request_data)
            assert response.status_code == 200

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_code_with_version(self, mock_get_sdk, client):
        """Test plugin code generation with version"""
        mock_sdk = MagicMock()
        mock_sdk.generate_plugin_code.return_value = "# Plugin code"
        mock_get_sdk.return_value = mock_sdk

        request_data = {
            "template_type": "collector",
            "plugin_name": "test_plugin",
            "class_name": "TestPlugin",
            "version": "2.0.0",
            "author": "Test Author",
        }

        response = client.get("/api/plugin-sdk/generate/code", params=request_data)
        assert response.status_code == 200

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_code_exception(self, mock_get_sdk, client):
        """Test plugin code generation with exception"""
        mock_get_sdk.side_effect = Exception("Code generation error")

        request_data = {
            "template_type": "collector",
            "plugin_name": "test_plugin",
            "class_name": "TestPlugin",
        }

        response = client.get("/api/plugin-sdk/generate/code", params=request_data)
        assert response.status_code == 500
        assert "Code generation error" in response.json()["detail"]


# ============================================================================
# Generate Plugin Config Endpoint Tests
# ============================================================================


class TestGeneratePluginConfig:
    """Test cases for generate_plugin_config endpoint"""

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_config_success(self, mock_get_sdk, client):
        """Test successful plugin config generation"""
        mock_sdk = MagicMock()
        mock_sdk.generate_plugin_config.return_value = {
            "enabled": True,
            "interval": 60,
            "log_level": "INFO",
        }
        mock_get_sdk.return_value = mock_sdk

        request_data = {"template_type": "collector"}

        response = client.get("/api/plugin-sdk/generate/config", params=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "data" in data
        assert "timestamp" in data

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_config_with_custom_config(self, mock_get_sdk, client):
        """Test plugin config generation with custom config"""
        mock_sdk = MagicMock()
        mock_sdk.generate_plugin_config.return_value = {
            "enabled": True,
            "custom_field": "custom_value",
        }
        mock_get_sdk.return_value = mock_sdk

        request_data = {
            "template_type": "analyzer",
            "custom_config": {"custom_field": "custom_value"},
        }

        response = client.get("/api/plugin-sdk/generate/config", params=request_data)
        assert response.status_code == 200

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_config_all_types(self, mock_get_sdk, client):
        """Test plugin config generation for all template types"""
        mock_sdk = MagicMock()
        mock_sdk.generate_plugin_config.return_value = {"enabled": True}
        mock_get_sdk.return_value = mock_sdk

        template_types = ["collector", "analyzer", "notifier", "action"]
        for template_type in template_types:
            request_data = {"template_type": template_type}
            response = client.get("/api/plugin-sdk/generate/config", params=request_data)
            assert response.status_code == 200

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_generate_plugin_config_exception(self, mock_get_sdk, client):
        """Test plugin config generation with exception"""
        mock_get_sdk.side_effect = Exception("Config generation error")

        request_data = {"template_type": "collector"}

        response = client.get("/api/plugin-sdk/generate/config", params=request_data)
        assert response.status_code == 500
        assert "Config generation error" in response.json()["detail"]


# ============================================================================
# Integration Tests
# ============================================================================


class TestPluginDevelopmentIntegration:
    """Integration tests for plugin development workflow"""

    @patch("api.plugin_development_router.get_plugin_sdk")
    def test_full_development_workflow(self, mock_get_sdk, client):
        """Test complete plugin development workflow"""
        mock_sdk = MagicMock()
        mock_sdk.get_sdk_summary.return_value = {"sdk_version": "1.0.0", "available": True}
        mock_sdk.get_available_templates.return_value = ["collector", "analyzer"]
        mock_sdk.generate_plugin_code.return_value = "# Plugin code"
        mock_sdk.generate_plugin_config.return_value = {"enabled": True}
        mock_sdk.create_plugin_package.return_value = {
            "plugin_name": "test_plugin",
            "version": "1.0.0",
            "template_type": "collector",
        }
        mock_get_sdk.return_value = mock_sdk

        # Step 1: Check SDK status
        response = client.get("/api/plugin-sdk/status")
        assert response.status_code == 200

        # Step 2: Get available templates
        response = client.get("/api/plugin-sdk/templates")
        assert response.status_code == 200

        # Step 3: Generate plugin code
        response = client.get(
            "/api/plugin-sdk/generate/code",
            params={
                "template_type": "collector",
                "plugin_name": "test_plugin",
                "class_name": "TestPlugin",
            },
        )
        assert response.status_code == 200

        # Step 4: Generate plugin config
        response = client.get("/api/plugin-sdk/generate/config", params={"template_type": "collector"})
        assert response.status_code == 200

        # Step 5: Generate plugin package
        response = client.post(
            "/api/plugin-sdk/generate",
            json={
                "template_type": "collector",
                "plugin_name": "test_plugin",
                "class_name": "TestPlugin",
                "version": "1.0.0",
            },
        )
        assert response.status_code == 200
