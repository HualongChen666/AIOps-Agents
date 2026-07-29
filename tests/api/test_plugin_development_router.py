# -*- coding: utf-8 -*-
"""Plugin Development Router Tests"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.plugin_development_router import (
    generate_plugin_code,
    generate_plugin_config,
    generate_plugin_package,
    get_available_templates,
    get_sdk_status,
)

sys.modules["core.plugin_development_sdk"] = MagicMock()


@pytest.fixture
def client():
    app = FastAPI()
    test_router = APIRouter(prefix="/api/plugin-sdk", tags=["Plugin SDK"])
    test_router.add_api_route("/status", get_sdk_status, methods=["GET"])
    test_router.add_api_route("/templates", get_available_templates, methods=["GET"])
    test_router.add_api_route("/generate", generate_plugin_package, methods=["POST"])
    test_router.add_api_route("/generate/code", generate_plugin_code, methods=["GET"])
    test_router.add_api_route("/generate/config", generate_plugin_config, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestPluginDevelopmentRouter:
    def test_get_sdk_status(self, client):
        with patch("core.plugin_development_sdk.get_plugin_sdk") as mock_sdk:
            mock_instance = Mock()
            mock_instance.get_sdk_summary.return_value = {"sdk_version": "1.0.0", "available": True}
            mock_sdk.return_value = mock_instance
            response = client.get("/api/plugin-sdk/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_sdk_status_error(self, client):
        with patch("core.plugin_development_sdk.get_plugin_sdk") as mock_sdk:
            mock_sdk.side_effect = Exception("plugin SDK error")
            response = client.get("/api/plugin-sdk/status")
            assert response.status_code == 500

    def test_get_available_templates(self, client):
        with patch("core.plugin_development_sdk.get_plugin_sdk") as mock_sdk:
            mock_instance = Mock()
            mock_instance.get_available_templates.return_value = [
                "collector",
                "analyzer",
                "notifier",
            ]
            mock_sdk.return_value = mock_instance
            response = client.get("/api/plugin-sdk/templates")
            assert response.status_code == 200

    def test_generate_plugin_package(self, client):
        with patch("core.plugin_development_sdk.get_plugin_sdk") as mock_sdk:
            mock_instance = Mock()
            mock_instance.create_plugin_package.return_value = {
                "plugin_name": "TestPlugin",
                "version": "1.0.0",
                "template_type": "collector",
            }
            mock_sdk.return_value = mock_instance
            response = client.post(
                "/api/plugin-sdk/generate",
                params={
                    "template_type": "collector",
                    "plugin_name": "TestPlugin",
                    "class_name": "TestClass",
                },
            )
            assert response.status_code == 200

    def test_generate_plugin_code(self, client):
        with patch("core.plugin_development_sdk.get_plugin_sdk") as mock_sdk:
            mock_instance = Mock()
            mock_instance.generate_plugin_code.return_value = "class TestPlugin:\n    pass"
            mock_sdk.return_value = mock_instance
            response = client.get(
                "/api/plugin-sdk/generate/code",
                params={
                    "template_type": "collector",
                    "plugin_name": "TestPlugin",
                    "class_name": "TestClass",
                },
            )
            assert response.status_code == 200

    def test_generate_plugin_config(self, client):
        with patch("core.plugin_development_sdk.get_plugin_sdk") as mock_sdk:
            mock_instance = Mock()
            mock_instance.generate_plugin_config.return_value = {"enabled": True, "config": {}}
            mock_sdk.return_value = mock_instance
            response = client.get("/api/plugin-sdk/generate/config?template_type=collector")
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
