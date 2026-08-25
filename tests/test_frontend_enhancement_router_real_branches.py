# -*- coding: utf-8 -*-
"""
Real branch tests for api.frontend_enhancement_router.

Uses a real FastAPI TestClient and the real FrontendEnhancementManager.
No external mocks: branches are exercised by controlling the module-level
feature flag and by supplying real request data.
"""

import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.frontend_enhancement_router as fem
from api.frontend_enhancement_router import router

app = FastAPI()
app.include_router(router)


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _restore_frontend_flag():
    """Restore FRONTEND_AVAILABLE after each test so state does not leak."""
    original = fem.FRONTEND_AVAILABLE
    yield
    fem.FRONTEND_AVAILABLE = original


# ---------------------------------------------------------------------------
# Success / feature toggle branches (FRONTEND_AVAILABLE = True by default)
# ---------------------------------------------------------------------------
def test_preferences_feature_toggles_and_config(client):
    # Get preferences
    r = client.get("/api/v1/frontend/preferences/user-br")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["preferences"]["user_id"] == "user-br"

    # Update with a mix of provided and defaulted (None) fields
    r = client.put(
        "/api/v1/frontend/preferences/user-br",
        json={
            "theme": "dark",
            "language": "en-US",
            "view_mode": "list",
        },
    )
    assert r.status_code == 200
    assert r.json()["preferences"]["theme"] == "dark"
    assert r.json()["preferences"]["view_mode"] == "list"

    # Export
    r = client.get("/api/v1/frontend/preferences/user-br/export")
    assert r.status_code == 200
    assert r.json()["preferences"]["user_id"] == "user-br"

    # Import
    r = client.post(
        "/api/v1/frontend/preferences/user-br/import",
        json={"theme": "light", "view_mode": "grid"},
    )
    assert r.status_code == 200
    assert r.json()["preferences"]["theme"] == "light"


def test_themes_and_dashboard_widgets(client):
    # Available themes including fallback/custom handling
    r = client.get("/api/v1/frontend/themes")
    assert r.status_code == 200
    assert any(t["type"] == "dark" for t in r.json()["themes"])

    # Custom theme
    r = client.post(
        "/api/v1/frontend/themes/custom",
        json={
            "theme_id": "ct-br",
            "name": "Branch Theme",
            "colors": {"primary": "#111111"},
            "base_theme": "dark",
        },
    )
    assert r.status_code == 200
    assert r.json()["custom_theme"]["theme_id"] == "ct-br"

    # Dashboard config
    r = client.get("/api/v1/frontend/dashboard/dash-br")
    assert r.status_code == 200
    assert "widgets" in r.json()

    # Add widget with config and data_source to exercise `or` default branch
    r = client.post(
        "/api/v1/frontend/dashboard/widget",
        json={
            "dashboard_id": "dash-br",
            "widget_id": "w-br",
            "widget_type": "metrics",
            "title": "CPU Branch",
            "position": {"x": 0, "y": 0, "width": 6, "height": 4},
            "config": {"metrics": ["cpu"]},
            "data_source": "metrics",
            "refresh_interval": 60,
        },
    )
    assert r.status_code == 200
    assert r.json()["widget"]["widget_id"] == "w-br"

    # Update existing widget
    r = client.put(
        "/api/v1/frontend/dashboard/dash-br/widget/w-br",
        json={"title": "CPU Updated"},
    )
    assert r.status_code == 200
    assert r.json()["widget"]["title"] == "CPU Updated"

    # Delete existing widget
    r = client.delete("/api/v1/frontend/dashboard/dash-br/widget/w-br")
    assert r.status_code == 200


def test_reports_responsive_accessibility_summary_and_view_modes(client):
    # Create report template
    r = client.post(
        "/api/v1/frontend/reports/templates",
        json={
            "template_id": "tmpl-br",
            "name": "Branch Report",
            "description": "Coverage report",
            "data_sources": ["metrics", "alerts"],
            "visualization_config": {"type": "bar"},
        },
    )
    assert r.status_code == 200
    assert r.json()["template"]["template_id"] == "tmpl-br"

    # List templates
    r = client.get("/api/v1/frontend/reports/templates")
    assert r.status_code == 200
    assert any(t["template_id"] == "tmpl-br" for t in r.json()["templates"])

    # Generate with filters
    r = client.post(
        "/api/v1/frontend/reports/generate",
        json={"template_id": "tmpl-br", "filters": {"start": "2026-01-01"}},
    )
    assert r.status_code == 200
    assert r.json()["report"]["template_id"] == "tmpl-br"

    # Responsive config
    r = client.get("/api/v1/frontend/responsive/1024")
    assert r.status_code == 200
    assert r.json()["viewport_width"] == 1024

    # Accessibility
    r = client.get("/api/v1/frontend/accessibility/user-br")
    assert r.status_code == 200

    r = client.put(
        "/api/v1/frontend/accessibility/user-br",
        json={"high_contrast": True},
    )
    assert r.status_code == 200
    assert r.json()["accessibility_settings"]["high_contrast"] is True

    # Summary
    r = client.get("/api/v1/frontend/summary")
    assert r.status_code == 200
    assert "frontend_summary" in r.json()

    # View modes (no FRONTEND_AVAILABLE guard)
    r = client.get("/api/v1/frontend/view-modes")
    assert r.status_code == 200
    assert "grid" in r.json()["view_modes"]

    # Breakpoints
    r = client.get("/api/v1/frontend/breakpoints")
    assert r.status_code == 200
    assert "lg" in r.json()["breakpoints"]


# ---------------------------------------------------------------------------
# Validation / fallback / error branches
# ---------------------------------------------------------------------------
def test_custom_theme_validation_branch(client):
    # Invalid base_theme triggers ValueError -> 400
    r = client.post(
        "/api/v1/frontend/themes/custom",
        json={
            "theme_id": "bad",
            "name": "Bad",
            "colors": {},
            "base_theme": "not-a-theme",
        },
    )
    assert r.status_code == 400
    assert "无效的基础主题" in r.json()["detail"]


def test_dashboard_widget_and_report_error_branches(client):
    # Remove widget from unknown dashboard -> fallback 404
    r = client.delete("/api/v1/frontend/dashboard/no-such-dash/widget/any")
    assert r.status_code == 404
    assert "未找到" in r.json()["detail"]

    # Update widget from unknown dashboard -> fallback 404
    r = client.put(
        "/api/v1/frontend/dashboard/no-such-dash/widget/any",
        json={},
    )
    assert r.status_code == 404
    assert "未找到" in r.json()["detail"]

    # Generate report for missing template -> error branch 400
    r = client.post(
        "/api/v1/frontend/reports/generate",
        json={"template_id": "missing-template"},
    )
    assert r.status_code == 400
    assert "Template not found" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Feature toggle off branches (FRONTEND_AVAILABLE = False)
# ---------------------------------------------------------------------------
def test_frontend_unavailable_returns_503_for_all_guarded_endpoints(client):
    fem.FRONTEND_AVAILABLE = False

    endpoints = [
        ("get", "/api/v1/frontend/preferences/user-br"),
        ("put", "/api/v1/frontend/preferences/user-br", {"json": {"theme": "dark"}}),
        ("get", "/api/v1/frontend/preferences/user-br/export"),
        ("post", "/api/v1/frontend/preferences/user-br/import", {"json": {}}),
        ("get", "/api/v1/frontend/themes"),
        (
            "post",
            "/api/v1/frontend/themes/custom",
            {"json": {"theme_id": "x", "name": "x", "colors": {}}},
        ),
        ("get", "/api/v1/frontend/dashboard/dash-br"),
        (
            "post",
            "/api/v1/frontend/dashboard/widget",
            {
                "json": {
                    "dashboard_id": "dash-br",
                    "widget_id": "w-x",
                    "widget_type": "metrics",
                    "title": "X",
                    "position": {"x": 0, "y": 0, "width": 1, "height": 1},
                }
            },
        ),
        ("delete", "/api/v1/frontend/dashboard/dash-br/widget/w-x"),
        (
            "put",
            "/api/v1/frontend/dashboard/dash-br/widget/w-x",
            {"json": {}},
        ),
        (
            "post",
            "/api/v1/frontend/reports/templates",
            {
                "json": {
                    "template_id": "x",
                    "name": "x",
                    "description": "x",
                    "data_sources": [],
                    "visualization_config": {},
                }
            },
        ),
        ("get", "/api/v1/frontend/reports/templates"),
        ("post", "/api/v1/frontend/reports/generate", {"json": {"template_id": "x"}}),
        ("get", "/api/v1/frontend/responsive/1024"),
        ("get", "/api/v1/frontend/accessibility/user-br"),
        ("put", "/api/v1/frontend/accessibility/user-br", {"json": {}}),
        ("get", "/api/v1/frontend/summary"),
        ("get", "/api/v1/frontend/breakpoints"),
    ]

    for item in endpoints:
        method = item[0]
        path = item[1]
        kwargs = item[2] if len(item) > 2 else {}
        r = getattr(client, method)(path, **kwargs)
        assert (
            r.status_code == 503
        ), f"{method.upper()} {path} expected 503, got {r.status_code}: {r.text}"
        assert "前端增强管理器不可用" in r.json()["detail"]


# ---------------------------------------------------------------------------
# Additional edge case tests for missing coverage
# ---------------------------------------------------------------------------
def test_add_dashboard_widget_with_none_config_and_data_source(client):
    """Test add_dashboard_widget with config=None and data_source=None to cover 'or' default branch"""
    r = client.post(
        "/api/v1/frontend/dashboard/widget",
        json={
            "dashboard_id": "dash-none",
            "widget_id": "w-none",
            "widget_type": "metrics",
            "title": "None Config Test",
            "position": {"x": 0, "y": 0, "width": 6, "height": 4},
            # config and data_source omitted (None)
        },
    )
    assert r.status_code == 200
    assert r.json()["widget"]["widget_id"] == "w-none"


def test_update_dashboard_widget_nonexistent_widget(client):
    """Test update_dashboard_widget with a widget that doesn't exist in the dashboard"""
    # First create a dashboard
    r = client.get("/api/v1/frontend/dashboard/dash-update-test")
    assert r.status_code == 200

    # Try to update a widget that doesn't exist
    r = client.put(
        "/api/v1/frontend/dashboard/dash-update-test/widget/nonexistent-widget",
        json={"title": "Should Not Work"},
    )
    assert r.status_code == 404
    assert "未找到" in r.json()["detail"]


def test_remove_dashboard_widget_from_nonexistent_dashboard(client):
    """Test remove_dashboard_widget from a dashboard that doesn't exist"""
    r = client.delete("/api/v1/frontend/dashboard/nonexistent-dashboard/widget/any-widget")
    assert r.status_code == 404
    assert "未找到" in r.json()["detail"]


def test_remove_dashboard_widget_nonexistent_widget_in_existing_dashboard(client):
    """Test remove_dashboard_widget with a widget that doesn't exist in an existing dashboard"""
    # Create a dashboard
    r = client.get("/api/v1/frontend/dashboard/dash-remove-test")
    assert r.status_code == 200

    # Try to remove a widget that doesn't exist
    r = client.delete("/api/v1/frontend/dashboard/dash-remove-test/widget/nonexistent-widget")
    # This returns 200 even if widget doesn't exist (based on manager implementation)
    assert r.status_code == 200


def test_generate_report_without_filters(client):
    """Test generate_report with no filters parameter"""
    # First create a template
    r = client.post(
        "/api/v1/frontend/reports/templates",
        json={
            "template_id": "tmpl-no-filters",
            "name": "No Filters Report",
            "description": "Test report without filters",
            "data_sources": ["metrics"],
            "visualization_config": {"type": "line"},
        },
    )
    assert r.status_code == 200

    # Generate report without filters
    r = client.post(
        "/api/v1/frontend/reports/generate",
        json={"template_id": "tmpl-no-filters"},
    )
    assert r.status_code == 200
    assert r.json()["report"]["template_id"] == "tmpl-no-filters"


def test_update_user_preferences_with_all_fields(client):
    """Test update_user_preferences with all possible fields"""
    r = client.put(
        "/api/v1/frontend/preferences/user-all-fields",
        json={
            "theme": "dark",
            "language": "en-US",
            "timezone": "America/New_York",
            "date_format": "MM/DD/YYYY",
            "time_format": "hh:mm A",
            "view_mode": "list",
            "notifications_enabled": False,
            "notification_sound": True,
            "auto_refresh_interval": 60,
            "dashboard_layout": {"columns": 3},
            "custom_colors": {"primary": "#ff0000"},
            "accessibility_settings": {"high_contrast": True},
        },
    )
    assert r.status_code == 200
    prefs = r.json()["preferences"]
    assert prefs["theme"] == "dark"
    assert prefs["language"] == "en-US"
    assert prefs["timezone"] == "America/New_York"
    assert prefs["date_format"] == "MM/DD/YYYY"
    assert prefs["time_format"] == "hh:mm A"
    assert prefs["view_mode"] == "list"
    assert prefs["notifications_enabled"] is False
    assert prefs["notification_sound"] is True
    assert prefs["auto_refresh_interval"] == 60


def test_import_user_preferences_with_all_fields(client):
    """Test import_user_preferences with comprehensive preference data"""
    r = client.post(
        "/api/v1/frontend/preferences/user-import-full/import",
        json={
            "theme": "light",
            "language": "zh-CN",
            "timezone": "Asia/Shanghai",
            "date_format": "YYYY-MM-DD",
            "time_format": "HH:mm:ss",
            "view_mode": "grid",
            "notifications_enabled": True,
            "notification_sound": False,
            "auto_refresh_interval": 30,
            "dashboard_layout": {"columns": 4},
            "custom_colors": {"secondary": "#00ff00"},
            "accessibility_settings": {"font_size": "large"},
        },
    )
    assert r.status_code == 200
    assert r.json()["preferences"]["theme"] == "light"
    assert r.json()["preferences"]["language"] == "zh-CN"


def test_create_custom_theme_with_different_base_themes(client):
    """Test create_custom_theme with different base_theme values"""
    # Test with light base theme
    r = client.post(
        "/api/v1/frontend/themes/custom",
        json={
            "theme_id": "custom-light",
            "name": "Custom Light",
            "colors": {"primary": "#123456"},
            "base_theme": "light",
        },
    )
    assert r.status_code == 200
    assert r.json()["custom_theme"]["base_theme"] == "light"

    # Test with dark base theme
    r = client.post(
        "/api/v1/frontend/themes/custom",
        json={
            "theme_id": "custom-dark",
            "name": "Custom Dark",
            "colors": {"primary": "#654321"},
            "base_theme": "dark",
        },
    )
    assert r.status_code == 200
    assert r.json()["custom_theme"]["base_theme"] == "dark"

    # Test with auto base theme
    r = client.post(
        "/api/v1/frontend/themes/custom",
        json={
            "theme_id": "custom-auto",
            "name": "Custom Auto",
            "colors": {"primary": "#abcdef"},
            "base_theme": "auto",
        },
    )
    assert r.status_code == 200
    assert r.json()["custom_theme"]["base_theme"] == "auto"


def test_get_responsive_config_with_different_viewports(client):
    """Test get_responsive_config with various viewport widths"""
    viewports = [320, 640, 768, 1024, 1280, 1600]
    for width in viewports:
        r = client.get(f"/api/v1/frontend/responsive/{width}")
        assert r.status_code == 200
        assert r.json()["viewport_width"] == width
        assert "responsive_config" in r.json()


def test_update_accessibility_settings_with_multiple_fields(client):
    """Test update_accessibility_settings with multiple accessibility settings"""
    r = client.put(
        "/api/v1/frontend/accessibility/user-a11y",
        json={
            "high_contrast": True,
            "font_size": "large",
            "screen_reader": True,
            "keyboard_navigation": True,
        },
    )
    assert r.status_code == 200
    settings = r.json()["accessibility_settings"]
    assert settings["high_contrast"] is True
    assert settings["font_size"] == "large"
    assert settings["screen_reader"] is True
    assert settings["keyboard_navigation"] is True


def test_create_report_template_with_schedule_and_creator(client):
    """Test create_report_template with schedule and created_by fields"""
    r = client.post(
        "/api/v1/frontend/reports/templates",
        json={
            "template_id": "tmpl-scheduled",
            "name": "Scheduled Report",
            "description": "Report with schedule",
            "data_sources": ["alerts", "topology"],
            "visualization_config": {"type": "table"},
            "format": "html",
            "schedule": "0 9 * * *",
            "created_by": "admin",
        },
    )
    assert r.status_code == 200
    template = r.json()["template"]
    assert template["schedule"] == "0 9 * * *"
    assert template["created_by"] == "admin"
    assert template["format"] == "html"


def test_get_dashboard_config_for_new_dashboard(client):
    """Test get_dashboard_config creates default dashboard for new dashboard_id"""
    r = client.get("/api/v1/frontend/dashboard/new-dashboard-xyz")
    assert r.status_code == 200
    widgets = r.json()["widgets"]
    assert len(widgets) > 0
    # Should have default widgets
    widget_ids = [w["widget_id"] for w in widgets]
    assert "metrics_overview" in widget_ids
    assert "alert_stream" in widget_ids


def test_update_user_preferences_with_partial_fields(client):
    """Test update_user_preferences with only some fields to test dict filtering"""
    r = client.put(
        "/api/v1/frontend/preferences/user-partial",
        json={
            "theme": "dark",
            # Other fields are None or omitted
        },
    )
    assert r.status_code == 200
    assert r.json()["preferences"]["theme"] == "dark"


def test_update_user_preferences_with_only_none_values(client):
    """Test update_user_preferences when all fields are None (edge case)"""
    r = client.put(
        "/api/v1/frontend/preferences/user-none",
        json={
            "theme": None,
            "language": None,
        },
    )
    assert r.status_code == 200
    # Should return existing preferences since no updates provided


def test_add_dashboard_widget_with_minimal_fields(client):
    """Test add_dashboard_widget with only required fields"""
    r = client.post(
        "/api/v1/frontend/dashboard/widget",
        json={
            "dashboard_id": "dash-minimal",
            "widget_id": "w-minimal",
            "widget_type": "text",
            "title": "Minimal Widget",
            "position": {"x": 0, "y": 0},
        },
    )
    assert r.status_code == 200
    assert r.json()["widget"]["widget_id"] == "w-minimal"


def test_update_dashboard_widget_with_multiple_fields(client):
    """Test update_dashboard_widget with multiple update fields"""
    # First add a widget
    r = client.post(
        "/api/v1/frontend/dashboard/widget",
        json={
            "dashboard_id": "dash-multi-update",
            "widget_id": "w-multi",
            "widget_type": "metrics",
            "title": "Original Title",
            "position": {"x": 0, "y": 0, "width": 6, "height": 4},
        },
    )
    assert r.status_code == 200

    # Update with multiple fields
    r = client.put(
        "/api/v1/frontend/dashboard/dash-multi-update/widget/w-multi",
        json={
            "title": "Updated Title",
            "position": {"x": 6, "y": 0, "width": 6, "height": 4},
            "refresh_interval": 120,
        },
    )
    assert r.status_code == 200
    widget = r.json()["widget"]
    assert widget["title"] == "Updated Title"
    assert widget["refresh_interval"] == 120


def test_generate_report_with_complex_filters(client):
    """Test generate_report with complex filter structure"""
    # Create template
    r = client.post(
        "/api/v1/frontend/reports/templates",
        json={
            "template_id": "tmpl-complex",
            "name": "Complex Report",
            "description": "Report with complex filters",
            "data_sources": ["metrics", "alerts", "topology"],
            "visualization_config": {"type": "multi"},
        },
    )
    assert r.status_code == 200

    # Generate with complex filters
    r = client.post(
        "/api/v1/frontend/reports/generate",
        json={
            "template_id": "tmpl-complex",
            "filters": {
                "start": "2026-01-01",
                "end": "2026-12-31",
                "severity": ["critical", "high"],
                "services": ["api", "database"],
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["report"]["template_id"] == "tmpl-complex"


def test_get_view_modes_endpoint(client):
    """Test get_view_modes endpoint (no FRONTEND_AVAILABLE guard)"""
    r = client.get("/api/v1/frontend/view-modes")
    assert r.status_code == 200
    view_modes = r.json()["view_modes"]
    assert isinstance(view_modes, list)
    assert "grid" in view_modes
    assert "list" in view_modes


def test_get_view_modes_when_frontend_unavailable(client):
    """Test get_view_modes still works when FRONTEND_AVAILABLE is False"""
    import api.frontend_enhancement_router as fem

    original = fem.FRONTEND_AVAILABLE
    fem.FRONTEND_AVAILABLE = False

    try:
        r = client.get("/api/v1/frontend/view-modes")
        assert r.status_code == 200
        assert "grid" in r.json()["view_modes"]
    finally:
        fem.FRONTEND_AVAILABLE = original


def test_export_user_preferences_for_new_user(client):
    """Test export_user_preferences for a user that doesn't exist yet"""
    r = client.get("/api/v1/frontend/preferences/user-new-export/export")
    assert r.status_code == 200
    assert r.json()["preferences"]["user_id"] == "user-new-export"


def test_import_user_preferences_with_minimal_data(client):
    """Test import_user_preferences with minimal preference data"""
    r = client.post(
        "/api/v1/frontend/preferences/user-minimal-import/import",
        json={
            "theme": "dark",
        },
    )
    assert r.status_code == 200
    assert r.json()["preferences"]["theme"] == "dark"


def test_get_accessibility_settings_for_new_user(client):
    """Test get_accessibility_settings for a new user"""
    r = client.get("/api/v1/frontend/accessibility/user-new-a11y")
    assert r.status_code == 200
    assert "accessibility_settings" in r.json()


def test_update_accessibility_settings_with_empty_dict(client):
    """Test update_accessibility_settings with empty settings dict"""
    r = client.put(
        "/api/v1/frontend/accessibility/user-empty-a11y",
        json={},
    )
    assert r.status_code == 200
    assert "accessibility_settings" in r.json()


def test_get_frontend_summary_endpoint(client):
    """Test get_frontend_summary endpoint"""
    r = client.get("/api/v1/frontend/summary")
    assert r.status_code == 200
    assert "frontend_summary" in r.json()


def test_get_responsive_breakpoints_endpoint(client):
    """Test get_responsive_breakpoints endpoint"""
    r = client.get("/api/v1/frontend/breakpoints")
    assert r.status_code == 200
    breakpoints = r.json()["breakpoints"]
    assert isinstance(breakpoints, dict)
    assert "lg" in breakpoints


def test_create_report_template_with_different_formats(client):
    """Test create_report_template with different format values"""
    formats = ["pdf", "html", "csv", "json"]
    for fmt in formats:
        r = client.post(
            "/api/v1/frontend/reports/templates",
            json={
                "template_id": f"tmpl-{fmt}",
                "name": f"{fmt.upper()} Report",
                "description": f"Report in {fmt} format",
                "data_sources": ["metrics"],
                "visualization_config": {"type": "table"},
                "format": fmt,
            },
        )
        assert r.status_code == 200
        assert r.json()["template"]["format"] == fmt


def test_add_dashboard_widget_with_zero_refresh_interval(client):
    """Test add_dashboard_widget with refresh_interval=0 (edge case)"""
    r = client.post(
        "/api/v1/frontend/dashboard/widget",
        json={
            "dashboard_id": "dash-zero-refresh",
            "widget_id": "w-zero",
            "widget_type": "static",
            "title": "Static Widget",
            "position": {"x": 0, "y": 0},
            "refresh_interval": 0,
        },
    )
    assert r.status_code == 200
    assert r.json()["widget"]["widget_id"] == "w-zero"


def test_add_dashboard_widget_with_large_refresh_interval(client):
    """Test add_dashboard_widget with large refresh_interval"""
    r = client.post(
        "/api/v1/frontend/dashboard/widget",
        json={
            "dashboard_id": "dash-large-refresh",
            "widget_id": "w-large",
            "widget_type": "slow-metrics",
            "title": "Slow Widget",
            "position": {"x": 0, "y": 0},
            "refresh_interval": 3600,  # 1 hour
        },
    )
    assert r.status_code == 200
    assert r.json()["widget"]["widget_id"] == "w-large"


def test_get_responsive_config_with_edge_viewports(client):
    """Test get_responsive_config with edge case viewport widths"""
    edge_cases = [0, 1, 9999, 10000]
    for width in edge_cases:
        r = client.get(f"/api/v1/frontend/responsive/{width}")
        assert r.status_code == 200
        assert r.json()["viewport_width"] == width
