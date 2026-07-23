# -*- coding: utf-8 -*-
"""
Frontend Enhancement Router Tests
前端增强路由API基础测试
"""

import sys
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["core.frontend_enhancement"] = MagicMock()
sys.modules["core.frontend_enhancement"].FRONTEND_AVAILABLE = True
sys.modules["core.frontend_enhancement"].ThemeType = MagicMock()
sys.modules["core.frontend_enhancement"].ViewMode = MagicMock()
sys.modules["core.frontend_enhancement"].frontend_enhancement_manager = MagicMock()

from api.frontend_enhancement_router import (
    add_dashboard_widget,
    get_available_themes,
    get_frontend_summary,
    get_user_preferences,
    update_user_preferences,
)


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/frontend", tags=["前端增强"])
    test_router.add_api_route("/preferences/{user_id}", get_user_preferences, methods=["GET"])
    test_router.add_api_route("/preferences/{user_id}", update_user_preferences, methods=["PUT"])
    test_router.add_api_route("/themes", get_available_themes, methods=["GET"])
    test_router.add_api_route("/dashboard/widget", add_dashboard_widget, methods=["POST"])
    test_router.add_api_route("/summary", get_frontend_summary, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestFrontendEnhancementRouter:
    """测试前端增强路由"""

    def test_get_user_preferences(self, client):
        """测试获取用户偏好"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_pref = Mock()
            mock_pref.user_id = "user-123"
            mock_pref.theme.value = "light"
            mock_pref.language = "zh-CN"
            mock_pref.timezone = "Asia/Shanghai"
            mock_pref.date_format = "YYYY-MM-DD"
            mock_pref.time_format = "HH:mm:ss"
            mock_pref.view_mode.value = "default"
            mock_pref.notifications_enabled = True
            mock_pref.notification_sound = True
            mock_pref.auto_refresh_interval = 30
            mock_pref.dashboard_layout = {}
            mock_pref.custom_colors = {}
            mock_pref.accessibility_settings = {}
            mock_pref.last_updated.isoformat.return_value = "2026-07-03T10:00:00Z"
            mock_manager.get_user_preferences.return_value = mock_pref

            response = client.get("/api/v1/frontend/preferences/user-123")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_update_user_preferences(self, client):
        """测试更新用户偏好"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_pref = Mock()
            mock_pref.user_id = "user-123"
            mock_pref.theme.value = "dark"
            mock_pref.language = "en-US"
            mock_pref.timezone = "UTC"
            mock_pref.date_format = "MM/DD/YYYY"
            mock_pref.time_format = "hh:mm A"
            mock_pref.view_mode.value = "compact"
            mock_pref.notifications_enabled = False
            mock_pref.notification_sound = False
            mock_pref.auto_refresh_interval = 60
            mock_pref.dashboard_layout = {}
            mock_pref.custom_colors = {}
            mock_pref.accessibility_settings = {}
            mock_pref.last_updated.isoformat.return_value = "2026-07-03T10:00:00Z"
            mock_manager.update_user_preferences.return_value = mock_pref

            response = client.put(
                "/api/v1/frontend/preferences/user-123", json={"theme": "dark", "language": "en-US"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_available_themes(self, client):
        """测试获取可用主题"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.ThemeType") as mock_theme_type,
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_theme_type.__iter__ = Mock(
                return_value=iter([Mock(value="light"), Mock(value="dark")])
            )
            mock_manager.get_theme_config.return_value = {"primary": "#007bff"}
            mock_manager.custom_themes = []

            response = client.get("/api/v1/frontend/themes")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_add_dashboard_widget(self, client):
        """测试添加仪表板小部件"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
            patch("core.frontend_enhancement.DashboardWidget") as mock_widget_class,
        ):
            mock_widget = Mock()
            mock_widget.widget_id = "widget-001"
            mock_widget.widget_type = "chart"
            mock_widget.title = "CPU Usage"
            mock_widget.position = {"x": 0, "y": 0}
            mock_manager.add_dashboard_widget.return_value = mock_widget
            mock_widget_class.return_value = mock_widget

            response = client.post(
                "/api/v1/frontend/dashboard/widget",
                json={
                    "dashboard_id": "dashboard-001",
                    "widget_id": "widget-001",
                    "widget_type": "chart",
                    "title": "CPU Usage",
                    "position": {"x": 0, "y": 0},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_frontend_summary(self, client):
        """测试获取前端增强摘要"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.get_frontend_summary.return_value = {
                "total_users": 100,
                "active_themes": 5,
                "custom_themes_count": 2,
            }

            response = client.get("/api/v1/frontend/summary")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
