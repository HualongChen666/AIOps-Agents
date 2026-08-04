# -*- coding: utf-8 -*-
"""Plugin Router Tests"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.modules["core.authentication"] = MagicMock()
sys.modules["core.authentication"].role_required = lambda role: lambda: {
    "username": "testuser",
    "role": "admin",
}
sys.modules["core.plugin_manager"] = MagicMock()

from api.plugin_router import router  # noqa: E402


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestPluginRouter:
    def test_list_plugins(self, client):
        with patch("api.plugin_router.list_plugins", return_value=["cpu_monitor", "disk_cleaner"]):
            response = client.get("/api/plugins/")
            assert response.status_code == 200
            assert "cpu_monitor" in response.json()

    def test_run_plugin_success(self, client):
        plugin_mock = MagicMock()
        plugin_mock.collect.return_value = {"cpu_usage": 45.2, "cores": 8}
        with (
            patch("api.plugin_router.list_plugins", return_value=["cpu_monitor"]),
            patch("api.plugin_router.get_plugin", return_value=plugin_mock),
        ):
            response = client.post("/api/plugins/cpu_monitor/run")
            assert response.status_code == 200
            assert response.json()["plugin"] == "cpu_monitor"

    def test_run_plugin_not_found(self, client):
        with patch("api.plugin_router.list_plugins", return_value=[]):
            response = client.post("/api/plugins/missing/run")
            assert response.status_code == 404

    def test_run_plugin_no_collect(self, client):
        plugin_mock = MagicMock()
        del plugin_mock.collect
        with (
            patch("api.plugin_router.list_plugins", return_value=["bad_plugin"]),
            patch("api.plugin_router.get_plugin", return_value=plugin_mock),
        ):
            response = client.post("/api/plugins/bad_plugin/run")
            assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
