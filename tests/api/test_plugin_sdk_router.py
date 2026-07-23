# -*- coding: utf-8 -*-
"""Plugin SDK Router Tests"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

sys.modules["core.plugin_system_manager"] = MagicMock()
from api.plugin_sdk_router import (
    define_plugin_interface,
    disable_plugin,
    enable_plugin,
    get_interface_spec,
    get_plugin_info,
    get_system_status,
    list_plugins,
    register_plugin,
)


@pytest.fixture
def client():
    app = FastAPI()
    test_router = APIRouter(prefix="/api/plugin-system", tags=["Plugin System"])
    test_router.add_api_route("/status", get_system_status, methods=["GET"])
    test_router.add_api_route("/interface/define", define_plugin_interface, methods=["POST"])
    test_router.add_api_route(
        "/interface/spec/{interface_type}", get_interface_spec, methods=["GET"]
    )
    test_router.add_api_route("/plugin/register", register_plugin, methods=["POST"])
    test_router.add_api_route("/plugin/{plugin_id}/enable", enable_plugin, methods=["POST"])
    test_router.add_api_route("/plugin/{plugin_id}/disable", disable_plugin, methods=["POST"])
    test_router.add_api_route("/plugins", list_plugins, methods=["GET"])
    test_router.add_api_route("/plugin/{plugin_id}", get_plugin_info, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestPluginSDKRouter:
    def test_get_system_status(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_system_summary.return_value = {
                "total_plugins": 10,
                "active_plugins": 8,
                "total_interfaces": 5,
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-system/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_system_status_error(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_manager.side_effect = Exception("plugin system error")
            response = client.get("/api/plugin-system/status")
            assert response.status_code == 500

    def test_define_plugin_interface(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_instance = Mock()
            mock_interface = Mock()
            mock_interface.interface_id = "data-collector"
            mock_interface.interface_name = "Data Collector"
            mock_interface.methods = ["collect"]
            mock_interface.events = ["on_data"]
            mock_instance.define_plugin_interface.return_value = mock_interface
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-system/interface/define",
                params={"interface_id": "data-collector", "interface_name": "Data Collector"},
                json={"methods": {}, "events": {}},
            )
            assert response.status_code == 200

    def test_get_interface_spec(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.generate_plugin_interface_spec.return_value = {
                "interface_type": "data-collector",
                "methods": [],
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-system/interface/spec/data-collector")
            assert response.status_code == 200

    def test_register_plugin(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.register_plugin.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-system/plugin/register",
                params={
                    "plugin_id": "plugin-123",
                    "name": "TestPlugin",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "TestAuthor",
                    "plugin_type": "collector",
                },
            )
            assert response.status_code == 200

    def test_enable_plugin(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.enable_plugin.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post("/api/plugin-system/plugin/plugin-123/enable")
            assert response.status_code == 200

    def test_disable_plugin(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.disable_plugin.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post("/api/plugin-system/plugin/plugin-123/disable")
            assert response.status_code == 200

    def test_list_plugins(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.list_plugins.return_value = [{"plugin_id": "plugin-123", "name": "Test"}]
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-system/plugins")
            assert response.status_code == 200

    def test_get_plugin_info(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_plugin_info.return_value = {"plugin_id": "plugin-123", "name": "Test"}
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-system/plugin/plugin-123")
            assert response.status_code == 200

    def test_get_plugin_info_not_found(self, client):
        with patch("core.plugin_system_manager.get_plugin_system_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_plugin_info.return_value = None
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-system/plugin/plugin-404")
            assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
