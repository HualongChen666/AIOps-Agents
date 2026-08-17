# -*- coding: utf-8 -*-
"""
Real branch tests for api.frontend_enhancement_router.

Uses a real FastAPI TestClient and the real FrontendEnhancementManager.
No external mocks: branches are exercised by controlling the module-level
feature flag and by supplying real request data.
"""

import pytest
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
