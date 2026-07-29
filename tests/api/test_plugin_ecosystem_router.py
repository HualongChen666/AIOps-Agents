# -*- coding: utf-8 -*-
"""Plugin Ecosystem Router Tests"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.plugin_ecosystem_router import (
    get_developer_stats,
    get_ecosystem_status,
    get_plugin_activities,
    record_activity,
    register_developer,
)

sys.modules["core.plugin_ecosystem_manager"] = MagicMock()


@pytest.fixture
def client():
    app = FastAPI()
    test_router = APIRouter(prefix="/api/plugin-ecosystem", tags=["Plugin Ecosystem"])
    test_router.add_api_route("/status", get_ecosystem_status, methods=["GET"])
    test_router.add_api_route("/activity", record_activity, methods=["POST"])
    test_router.add_api_route("/activities/{plugin_id}", get_plugin_activities, methods=["GET"])
    test_router.add_api_route("/developer/register", register_developer, methods=["POST"])
    test_router.add_api_route("/developer/{developer_id}", get_developer_stats, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestPluginEcosystemRouter:
    def test_get_ecosystem_status(self, client):
        with patch("core.plugin_ecosystem_manager.get_ecosystem_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_ecosystem_summary.return_value = {
                "total_plugins": 10,
                "active_plugins": 8,
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-ecosystem/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data

    def test_get_ecosystem_status_error(self, client):
        with patch("core.plugin_ecosystem_manager.get_ecosystem_manager") as mock_manager:
            mock_manager.side_effect = Exception("plugin ecosystem error")
            response = client.get("/api/plugin-ecosystem/status")
            assert response.status_code == 500

    def test_record_activity(self, client):
        with patch("core.plugin_ecosystem_manager.get_ecosystem_manager") as mock_manager:
            mock_instance = Mock()
            mock_activity = Mock()
            mock_activity.activity_id = "act-123"
            mock_activity.activity_type.value = "install"
            mock_instance.record_activity.return_value = mock_activity
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-ecosystem/activity",
                params={
                    "plugin_id": "plugin-123",
                    "activity_type": "install",
                    "user_id": "user-123",
                },
            )
            assert response.status_code == 200

    def test_get_plugin_activities(self, client):
        with patch("core.plugin_ecosystem_manager.get_ecosystem_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_plugin_activities.return_value = [
                {"activity_id": "act-123", "activity_type": "install"}
            ]
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-ecosystem/activities/plugin-123?time_range_hours=24")
            assert response.status_code == 200

    def test_register_developer(self, client):
        with patch("core.plugin_ecosystem_manager.get_ecosystem_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.register_developer.return_value = True
            mock_manager.return_value = mock_instance
            response = client.post(
                "/api/plugin-ecosystem/developer/register",
                params={"developer_id": "dev-123", "name": "TestDev", "email": "test@example.com"},
            )
            assert response.status_code == 200

    def test_get_developer_stats(self, client):
        with patch("core.plugin_ecosystem_manager.get_ecosystem_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_developer_stats.return_value = {
                "total_plugins": 5,
                "total_downloads": 1000,
            }
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-ecosystem/developer/dev-123")
            assert response.status_code == 200

    def test_get_developer_stats_not_found(self, client):
        with patch("core.plugin_ecosystem_manager.get_ecosystem_manager") as mock_manager:
            mock_instance = Mock()
            mock_instance.get_developer_stats.return_value = None
            mock_manager.return_value = mock_instance
            response = client.get("/api/plugin-ecosystem/developer/dev-404")
            assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
