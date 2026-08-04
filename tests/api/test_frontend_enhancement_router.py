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

from api.frontend_enhancement_router import (
    add_dashboard_widget,
    create_custom_theme,
    create_report_template,
    export_user_preferences,
    generate_report,
    get_accessibility_settings,
    get_available_themes,
    get_dashboard_config,
    get_frontend_summary,
    get_report_templates,
    get_responsive_breakpoints,
    get_responsive_config,
    get_user_preferences,
    get_view_modes,
    import_user_preferences,
    remove_dashboard_widget,
    update_accessibility_settings,
    update_dashboard_widget,
    update_user_preferences,
)

# Mock problematic imports before importing router
sys.modules["core.frontend_enhancement"] = MagicMock()
sys.modules["core.frontend_enhancement"].FRONTEND_AVAILABLE = True
sys.modules["core.frontend_enhancement"].ThemeType = MagicMock()
sys.modules["core.frontend_enhancement"].ViewMode = MagicMock()
sys.modules["core.frontend_enhancement"].frontend_enhancement_manager = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/v1/frontend", tags=["前端增强"])
    test_router.add_api_route("/preferences/{user_id}", get_user_preferences, methods=["GET"])
    test_router.add_api_route("/preferences/{user_id}", update_user_preferences, methods=["PUT"])
    test_router.add_api_route("/preferences/{user_id}/export", export_user_preferences, methods=["GET"])
    test_router.add_api_route("/preferences/{user_id}/import", import_user_preferences, methods=["POST"])
    test_router.add_api_route("/themes", get_available_themes, methods=["GET"])
    test_router.add_api_route("/themes/custom", create_custom_theme, methods=["POST"])
    test_router.add_api_route("/dashboard/{dashboard_id}", get_dashboard_config, methods=["GET"])
    test_router.add_api_route("/dashboard/widget", add_dashboard_widget, methods=["POST"])
    test_router.add_api_route("/dashboard/{dashboard_id}/widget/{widget_id}", remove_dashboard_widget, methods=["DELETE"])
    test_router.add_api_route("/dashboard/{dashboard_id}/widget/{widget_id}", update_dashboard_widget, methods=["PUT"])
    test_router.add_api_route("/reports/templates", create_report_template, methods=["POST"])
    test_router.add_api_route("/reports/templates", get_report_templates, methods=["GET"])
    test_router.add_api_route("/reports/generate", generate_report, methods=["POST"])
    test_router.add_api_route("/responsive/{viewport_width}", get_responsive_config, methods=["GET"])
    test_router.add_api_route("/accessibility/{user_id}", get_accessibility_settings, methods=["GET"])
    test_router.add_api_route("/accessibility/{user_id}", update_accessibility_settings, methods=["PUT"])
    test_router.add_api_route("/summary", get_frontend_summary, methods=["GET"])
    test_router.add_api_route("/view-modes", get_view_modes, methods=["GET"])
    test_router.add_api_route("/breakpoints", get_responsive_breakpoints, methods=["GET"])
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

    def test_export_user_preferences(self, client):
        """测试导出用户偏好"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.export_user_preferences.return_value = {"theme": "light", "language": "zh-CN"}

            response = client.get("/api/v1/frontend/preferences/user-123/export")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_import_user_preferences(self, client):
        """测试导入用户偏好"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_pref = Mock()
            mock_pref.user_id = "user-123"
            mock_pref.theme.value = "dark"
            mock_pref.language = "en-US"
            mock_pref.timezone = "UTC"
            mock_pref.last_updated.isoformat.return_value = "2026-07-03T10:00:00Z"
            mock_manager.import_user_preferences.return_value = mock_pref

            response = client.post(
                "/api/v1/frontend/preferences/user-123/import",
                json={"theme": "dark", "language": "en-US"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_create_custom_theme(self, client):
        """测试创建自定义主题"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.ThemeType") as mock_theme_type,
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_theme_type.return_value = Mock()
            mock_manager.create_custom_theme.return_value = {
                "theme_id": "custom-001",
                "name": "Custom Dark",
                "colors": {"primary": "#000000"},
            }

            response = client.post(
                "/api/v1/frontend/themes/custom",
                json={
                    "theme_id": "custom-001",
                    "name": "Custom Dark",
                    "colors": {"primary": "#000000"},
                    "base_theme": "light",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_create_custom_theme_invalid_base(self, client):
        """测试创建自定义主题（无效基础主题）"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.ThemeType") as mock_theme_type,
        ):
            mock_theme_type.side_effect = ValueError("Invalid theme")

            response = client.post(
                "/api/v1/frontend/themes/custom",
                json={
                    "theme_id": "custom-001",
                    "name": "Custom Dark",
                    "colors": {"primary": "#000000"},
                    "base_theme": "invalid",
                },
            )
            assert response.status_code == 400

    def test_get_dashboard_config(self, client):
        """测试获取仪表板配置"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_widget = Mock()
            mock_widget.widget_id = "widget-001"
            mock_widget.widget_type = "chart"
            mock_widget.title = "CPU Usage"
            mock_widget.position = {"x": 0, "y": 0}
            mock_widget.config = {}
            mock_widget.data_source = "metrics"
            mock_widget.refresh_interval = 30
            mock_widget.enabled = True
            mock_manager.get_dashboard_config.return_value = [mock_widget]

            response = client.get("/api/v1/frontend/dashboard/dashboard-001")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_remove_dashboard_widget(self, client):
        """测试删除仪表板小部件"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.remove_dashboard_widget.return_value = True

            response = client.delete("/api/v1/frontend/dashboard/dashboard-001/widget/widget-001")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_remove_dashboard_widget_not_found(self, client):
        """测试删除仪表板小部件（未找到）"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.remove_dashboard_widget.return_value = False

            response = client.delete("/api/v1/frontend/dashboard/dashboard-001/widget/widget-001")
            assert response.status_code == 404

    def test_update_dashboard_widget(self, client):
        """测试更新仪表板小部件"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_widget = Mock()
            mock_widget.widget_id = "widget-001"
            mock_widget.widget_type = "chart"
            mock_widget.title = "Updated Title"
            mock_widget.position = {"x": 1, "y": 1}
            mock_widget.config = {"new_config": True}
            mock_widget.refresh_interval = 60
            mock_widget.enabled = True
            mock_manager.update_dashboard_widget.return_value = mock_widget

            response = client.put(
                "/api/v1/frontend/dashboard/dashboard-001/widget/widget-001",
                json={"title": "Updated Title", "position": {"x": 1, "y": 1}},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_update_dashboard_widget_not_found(self, client):
        """测试更新仪表板小部件（未找到）"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.update_dashboard_widget.return_value = None

            response = client.put(
                "/api/v1/frontend/dashboard/dashboard-001/widget/widget-001",
                json={"title": "Updated Title"},
            )
            assert response.status_code == 404

    def test_create_report_template(self, client):
        """测试创建报告模板"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_template = Mock()
            mock_template.template_id = "template-001"
            mock_template.name = "Monthly Report"
            mock_template.description = "Monthly system report"
            mock_template.data_sources = ["metrics", "logs"]
            mock_template.visualization_config = {"type": "line"}
            mock_template.format = "pdf"
            mock_template.schedule = "monthly"
            mock_template.created_by = "admin"
            mock_template.created_at.isoformat.return_value = "2026-07-03T10:00:00Z"
            mock_manager.create_report_template.return_value = mock_template

            response = client.post(
                "/api/v1/frontend/reports/templates",
                json={
                    "template_id": "template-001",
                    "name": "Monthly Report",
                    "description": "Monthly system report",
                    "data_sources": ["metrics", "logs"],
                    "visualization_config": {"type": "line"},
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_report_templates(self, client):
        """测试获取报告模板列表"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_template = Mock()
            mock_template.template_id = "template-001"
            mock_template.name = "Monthly Report"
            mock_template.description = "Monthly system report"
            mock_template.data_sources = ["metrics"]
            mock_template.format = "pdf"
            mock_template.schedule = "monthly"
            mock_template.created_by = "admin"
            mock_template.created_at.isoformat.return_value = "2026-07-03T10:00:00Z"
            mock_manager.report_templates.values.return_value = [mock_template]

            response = client.get("/api/v1/frontend/reports/templates")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_generate_report(self, client):
        """测试生成报告"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.generate_report.return_value = {
                "report_id": "report-001",
                "status": "completed",
                "url": "/reports/report-001.pdf",
            }

            response = client.post(
                "/api/v1/frontend/reports/generate",
                json={"template_id": "template-001"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_generate_report_error(self, client):
        """测试生成报告（错误）"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.generate_report.return_value = {"error": "Template not found"}

            response = client.post(
                "/api/v1/frontend/reports/generate",
                json={"template_id": "invalid-template"},
            )
            assert response.status_code == 400

    def test_get_responsive_config(self, client):
        """测试获取响应式配置"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.get_responsive_config.return_value = {
                "layout": "grid",
                "columns": 3,
                "widget_size": "medium",
            }

            response = client.get("/api/v1/frontend/responsive/1024")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_accessibility_settings(self, client):
        """测试获取无障碍设置"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.get_accessibility_settings.return_value = {
                "high_contrast": True,
                "font_size": "large",
                "screen_reader": False,
            }

            response = client.get("/api/v1/frontend/accessibility/user-123")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_update_accessibility_settings(self, client):
        """测试更新无障碍设置"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.update_accessibility_settings.return_value = {
                "high_contrast": False,
                "font_size": "medium",
                "screen_reader": True,
            }

            response = client.put(
                "/api/v1/frontend/accessibility/user-123",
                json={"high_contrast": False, "font_size": "medium"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_view_modes(self, client):
        """测试获取支持的视图模式"""
        with patch("api.frontend_enhancement_router.ViewMode") as mock_view_mode:
            mock_view_mode.__iter__ = Mock(
                return_value=iter([Mock(value="default"), Mock(value="compact")])
            )

            response = client.get("/api/v1/frontend/view-modes")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_responsive_breakpoints(self, client):
        """测试获取响应式断点"""
        with (
            patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", True),
            patch("api.frontend_enhancement_router.frontend_enhancement_manager") as mock_manager,
        ):
            mock_manager.responsive_breakpoints = {
                "mobile": 768,
                "tablet": 1024,
                "desktop": 1440,
            }

            response = client.get("/api/v1/frontend/breakpoints")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_user_preferences_unavailable(self, client):
        """测试获取用户偏好（不可用）"""
        with patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", False):
            response = client.get("/api/v1/frontend/preferences/user-123")
            assert response.status_code == 503

    def test_update_user_preferences_unavailable(self, client):
        """测试更新用户偏好（不可用）"""
        with patch("api.frontend_enhancement_router.FRONTEND_AVAILABLE", False):
            response = client.put(
                "/api/v1/frontend/preferences/user-123", json={"theme": "dark"}
            )
            assert response.status_code == 503


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
