# -*- coding: utf-8 -*-
"""Real branch-coverage tests for main.py with ENABLE_ADDONS=true but all
individual feature-pack flags set to false. This exercises the `if flag:` false
branches inside the `if ENABLE_ADDONS:` block.
"""

import importlib
import os

import pytest
from fastapi.testclient import TestClient

# Add-ons on, but every pack flag off to cover the false branches.
for _key in [
    "ENABLE_ADDONS",
    "LLM_ROUTER_ENABLED",
    "RAG_ENABLED",
    "METRICS_ENABLED",
    "TOPOLOGY_ENABLED",
    "TRACING_ENABLED",
    "LOG_AGGREGATION_ENABLED",
    "INCIDENT_RESPONSE_ENABLED",
    "WORKFLOW_ENABLED",
    "INTEGRATIONS_ENABLED",
    "SECURITY_SCANNING_ENABLED",
    "PLUGINS_ENABLED",
    "MCP_ENABLED",
    "GRAPHQL_ENABLED",
    "I18N_ENABLED",
    "DOC_GENERATION_ENABLED",
]:
    os.environ[_key] = "true" if _key == "ENABLE_ADDONS" else "false"

os.environ["AIOPS_DISABLE_SECURITY_SCAN"] = "1"
os.environ["CONFIG_VALIDATION_ENABLED"] = "false"
os.environ["LOKI_ENABLED"] = "false"
os.environ["TEMPO_ENABLED"] = "false"
os.environ["VICTORIAMETRICS_ENABLED"] = "false"

import config

importlib.reload(config)
import main

importlib.reload(main)
from main import app


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


def test_health_flags_false(main_client):
    r = main_client.get("/health")
    assert r.status_code == 200


def test_options_preflight_flags_false(main_client):
    r = main_client.request("OPTIONS", "/health")
    assert r.status_code in {200, 204, 400, 405}


def test_login_and_me_flags_false(main_client):
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


def test_core_routers_flags_false(main_client, admin_headers):
    r = main_client.get("/api/v1/dr/scenarios", headers=admin_headers)
    assert r.status_code in {200, 401, 403}


def test_addon_routers_not_mounted_flags_false(main_client, admin_headers):
    # With all pack flags false, add-on endpoints should not be mounted.
    addon_paths = [
        "/api/v1/ai/models",
        "/api/v1/rag/search",
        "/api/v1/topology/nodes",
        "/api/v1/metrics/health",
        "/api/v1/workflow/templates",
        "/api/v1/integrations",
        "/api/v1/plugins",
        "/api/v1/i18n/locales",
        "/api/v1/docs/list",
    ]
    for path in addon_paths:
        r = main_client.get(path, headers=admin_headers)
        assert r.status_code in {401, 403, 404, 405}


def test_global_exception_handler_flags_false(main_client, admin_headers):
    def _boom():
        raise RuntimeError("unhandled boom")

    app.add_api_route("/_test_unhandled_exception_flags_false", _boom, methods=["GET"])
    r = main_client.get("/_test_unhandled_exception_flags_false", headers=admin_headers)
    assert r.status_code == 500
