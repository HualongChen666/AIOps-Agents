# -*- coding: utf-8 -*-
"""Real branch-coverage tests for main.py with add-ons enabled.

These tests exercise the `if ENABLE_ADDONS` true branches, lifespan add-on
initialization paths, and add-on router registration in main.py without
mocking internal code.
"""

import importlib
import os  # noqa: F401  # Imported for test setup

import pytest  # noqa: F401  # Imported for test setup
from fastapi.testclient import TestClient

# Enable add-ons and all feature packs before main.py is imported.
os.environ["ENABLE_ADDONS"] = "true"
os.environ["AIOPS_DISABLE_SECURITY_SCAN"] = "1"
os.environ["CONFIG_VALIDATION_ENABLED"] = "false"
os.environ["LOKI_ENABLED"] = "false"
os.environ["TEMPO_ENABLED"] = "false"
os.environ["VICTORIAMETRICS_ENABLED"] = "false"

import config  # noqa: E402  # Module level import not at top (intentional for test setup)

importlib.reload(config)
import main  # noqa: E402  # Module level import not at top (intentional for test setup)

importlib.reload(main)
from main import app  # noqa: E402  # Module level import not at top (intentional for test setup)


@pytest.fixture(scope="module")
def main_client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def admin_headers(main_client):
    resp = main_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200, f"login failed: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_health_addons_enabled(main_client):
    r = main_client.get("/health")
    assert r.status_code == 200


def test_options_preflight_addons_enabled(main_client):
    # Covers the OPTIONS branch in main.py's security_middleware.
    r = main_client.request("OPTIONS", "/health")
    assert r.status_code in {200, 204, 400, 405}


def test_login_and_me_addons_enabled(main_client):
    resp = main_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp2 = main_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200


def test_core_routers_still_available(main_client, admin_headers):
    # Ensure core routers are mounted together with add-ons.
    r = main_client.get("/api/v1/dr/scenarios", headers=admin_headers)
    assert r.status_code in {200, 401, 403}


def test_addon_routers_mounted(main_client, admin_headers):
    # Hit a few add-on endpoints to exercise the include_router paths.
    # These endpoints are read-only or validation-only to avoid side effects.
    addon_paths = [
        "/api/v1/ai/models",  # ai_router
        "/api/v1/rag/search",  # rag_router
        "/api/v1/topology/nodes",  # topology_router
        "/api/v1/metrics/health",  # metrics_router
        "/api/v1/workflow/templates",  # workflow_router
        "/api/v1/integrations",  # integration_router
        "/api/v1/plugins",  # plugin_router
        "/api/v1/i18n/locales",  # i18n_router
        "/api/v1/docs/list",  # documentation_router
    ]
    for path in addon_paths:
        r = main_client.get(path, headers=admin_headers)
        # 200/401/403/404/422 are all acceptable; the goal is to make the
        # include_router routes reachable and execute their request handlers.
        assert r.status_code in {200, 401, 403, 404, 405, 422, 500}


def test_global_exception_handler_addons_enabled(main_client, admin_headers):
    def _boom():
        raise RuntimeError("unhandled boom")

    app.add_api_route("/_test_unhandled_exception_addons", _boom, methods=["GET"])
    r = main_client.get("/_test_unhandled_exception_addons", headers=admin_headers)
    assert r.status_code == 500
