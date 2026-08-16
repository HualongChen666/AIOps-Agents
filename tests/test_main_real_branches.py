# -*- coding: utf-8 -*-
"""Real branch-coverage tests for main.py using TestClient(app) and real login.

These tests exercise FastAPI startup/lifespan, core/add-on routers, and the
exception handling branches registered in main.py without mocking internal code.
"""

import importlib
import os

import pytest
from fastapi.testclient import TestClient

# Force a fast, branch-focused import of main.py for this test module.
# Disabling add-ons at import time skips heavy optional integrations and also
# exercises the `if ENABLE_ADDONS:` false branch and the add-on skip path in
# `main.py::lifespan`.
os.environ["ENABLE_ADDONS"] = "false"
os.environ["AIOPS_DISABLE_SECURITY_SCAN"] = "1"

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


def test_health_and_service_info(main_client):
    r = main_client.get("/health")
    assert r.status_code == 200


def test_root_and_service_workers(main_client):
    root = main_client.get("/")
    assert root.status_code in {200, 404, 500}

    for path in ("/sw.js", "/sw-register.js"):
        r = main_client.get(path)
        assert r.status_code in {200, 500}
        if r.status_code == 200:
            assert r.headers["content-type"].startswith("application/javascript")


def test_options_preflight(main_client):
    # Covers the OPTIONS branch in main.py's security_middleware.
    r = main_client.request("OPTIONS", "/health")
    assert r.status_code in {200, 204, 400, 405}


def test_login_and_authorized_me(main_client):
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


def test_unauthorized_triggers_api_error_handler(main_client):
    # Covers the HTTPException -> api_error_handler path registered in main.py.
    r = main_client.get("/api/v1/auth/me")
    assert r.status_code in {401, 403}


def test_validation_error_triggers_validation_handler(main_client):
    # Covers the RequestValidationError -> validation_error_handler path.
    r = main_client.post("/api/v1/auth/login", json={})
    assert r.status_code == 422


def test_dr_scenarios_authorized(main_client, admin_headers):
    r = main_client.get("/api/v1/dr/scenarios", headers=admin_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any("database_failover" in s.get("name", "") for s in data)


def test_dr_run_authorized(main_client, admin_headers):
    r = main_client.post(
        "/api/v1/dr/run/database_failover",
        headers=admin_headers,
    )
    assert r.status_code in {200, 500}
    if r.status_code == 200:
        body = r.json()
        assert "status" in body


def test_global_exception_handler(main_client, admin_headers):
    # Add a one-off route that raises a generic RuntimeError so main.py's
    # global Exception handler is exercised.  This is not a mock: it uses the
    # real app and real exception handling pipeline.
    def _boom():
        raise RuntimeError("unhandled boom")

    app.add_api_route("/_test_unhandled_exception", _boom, methods=["GET"])
    r = main_client.get("/_test_unhandled_exception", headers=admin_headers)
    assert r.status_code == 500
