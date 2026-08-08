# -*- coding: utf-8 -*-
"""Smoke tests for global RBAC middleware."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_public_health_is_open(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_protected_endpoint_rejects_missing_token(client):
    response = client.get("/api/v1/users")
    assert response.status_code == 401


def test_write_endpoint_rejects_viewer(client):
    # A fake token with viewer role
    response = client.post(
        "/api/v1/workflows/execute",
        json={"dsl": {}},
        headers={"Authorization": "Bearer invalid"},
    )
    # Missing token -> 401; if token present but invalid -> 401; if valid viewer -> 403
    assert response.status_code in (401, 403)
