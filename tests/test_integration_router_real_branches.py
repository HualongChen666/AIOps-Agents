# -*- coding: utf-8 -*-
"""Real branch-coverage tests for api/integration_router.py.

A small FastAPI app mounts the integration router and the auth router with the
global RBAC middleware so that authentication/authorisation branches are
exercised.  No unittest.mock or monkeypatching is used; the only environment
tweak is a short microservice timeout so remote add-on calls fail fast.
"""

import hashlib  # noqa: F401  # Imported for test setup
import hmac  # noqa: F401  # Imported for test setup
import json  # noqa: F401  # Imported for test setup
import os  # noqa: F401  # Imported for test setup
import uuid

import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ["MICROSERVICE_TIMEOUT"] = "0.5"

from api.auth_router import router as _auth_router  # noqa: E402
from api.integration_router import router as _integration_router  # noqa: E402
from api.middleware.rbac_middleware import RBACMiddleware  # noqa: E402
from api.users_router import router as _users_router  # noqa: E402

_app = FastAPI()
_app.add_middleware(RBACMiddleware)
_app.include_router(_auth_router)
_app.include_router(_users_router)
_app.include_router(_integration_router)


@pytest.fixture(scope="module")
def client():
    with TestClient(_app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def admin_headers(client):
    r = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert r.status_code == 200, f"admin login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def viewer_headers(client, admin_headers):
    username = f"viewer_{uuid.uuid4().hex[:6]}"
    r = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "username": username,
            "password": "Pass1234!",
            "role": "viewer",
            "is_active": True,
            "permissions": [],
        },
    )
    assert r.status_code == 201, f"viewer create failed: {r.text}"
    r = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Pass1234!"},
    )
    assert r.status_code == 200, f"viewer login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def fresh_integration_id(client, admin_headers):
    """Create a throwaway custom integration and return its id."""
    payload = {
        "integration_type": "custom",
        "name": f"custom-{uuid.uuid4().hex[:8]}",
        "config": {"provider": "dummy"},
        "enabled": True,
    }
    r = client.post("/api/v1/integration/register", headers=admin_headers, json=payload)
    assert r.status_code == 200, f"register failed: {r.text}"
    return r.json()["integration"]["integration_id"]


# ---------------------------------------------------------------------------
# Authentication / authorization / validation error branches
# ---------------------------------------------------------------------------
def test_auth_missing(client):
    r = client.get("/api/v1/integration/list")
    assert r.status_code == 401


def test_auth_forbidden_write(client, viewer_headers):
    r = client.post(
        "/api/v1/integration/register",
        headers=viewer_headers,
        json={
            "integration_type": "custom",
            "name": "forbidden",
            "config": {},
        },
    )
    assert r.status_code == 403


def test_register_missing_payload(client, admin_headers):
    r = client.post("/api/v1/integration/register", headers=admin_headers, json={})
    assert r.status_code == 422


def test_query_missing_payload(client, admin_headers, fresh_integration_id):
    r = client.post(
        f"/api/v1/integration/{fresh_integration_id}/query",
        headers=admin_headers,
        data="",
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Registration, listing, filtering and type/status error branches
# ---------------------------------------------------------------------------
def test_register_invalid_type(client, admin_headers):
    r = client.post(
        "/api/v1/integration/register",
        headers=admin_headers,
        json={
            "integration_type": "not_a_real_type",
            "name": "bad",
            "config": {},
        },
    )
    assert r.status_code == 400
    assert "无效" in r.json()["detail"] or "invalid" in r.json()["detail"].lower()


def test_register_and_list(client, admin_headers):
    r = client.post(
        "/api/v1/integration/register",
        headers=admin_headers,
        json={
            "integration_type": "monitoring",
            "name": f"prometheus-{uuid.uuid4().hex[:6]}",
            "config": {"url": "http://localhost:1"},
            "enabled": True,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["integration"]["integration_type"] == "monitoring"

    # cover the response-formatting branches: last_tested may be None/isoformat,
    # list default, filter by valid type and by valid status
    r = client.get("/api/v1/integration/list", headers=admin_headers)
    assert r.status_code == 200
    assert "integrations" in r.json()

    r = client.get(
        "/api/v1/integration/list",
        headers=admin_headers,
        params={"integration_type": "monitoring"},
    )
    assert r.status_code == 200
    assert all(i["integration_type"] == "monitoring" for i in r.json()["integrations"])

    r = client.get(
        "/api/v1/integration/list",
        headers=admin_headers,
        params={"status": "configuring"},
    )
    assert r.status_code == 200


def test_list_invalid_filters(client, admin_headers):
    r = client.get(
        "/api/v1/integration/list",
        headers=admin_headers,
        params={"integration_type": "bad_type"},
    )
    assert r.status_code == 400

    r = client.get(
        "/api/v1/integration/list",
        headers=admin_headers,
        params={"status": "bad_status"},
    )
    assert r.status_code == 400


def test_get_integration_types(client, admin_headers):
    r = client.get("/api/v1/integration/types", headers=admin_headers)
    assert r.status_code == 200
    assert "monitoring" in r.json()["integration_types"]


def test_get_templates(client, admin_headers):
    r = client.get("/api/v1/integration/templates", headers=admin_headers)
    assert r.status_code == 200
    assert "prometheus" in r.json()["templates"]


def test_get_summary(client, admin_headers):
    r = client.get("/api/v1/integration/summary", headers=admin_headers)
    assert r.status_code == 200
    assert "integration_summary" in r.json()


# ---------------------------------------------------------------------------
# Test, update (re-register / status flip) and delete branches
# ---------------------------------------------------------------------------
def test_test_integration(client, admin_headers, fresh_integration_id):
    r = client.post(
        f"/api/v1/integration/test/{fresh_integration_id}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert "test_result" in r.json()

    # missing integration still returns 200 with a test_result describing the failure
    r = client.post(
        "/api/v1/integration/test/no-such-integration",
        headers=admin_headers,
    )
    assert r.status_code == 200


def test_delete_integration(client, admin_headers, fresh_integration_id):
    # successful delete
    r = client.delete(
        f"/api/v1/integration/{fresh_integration_id}",
        headers=admin_headers,
    )
    assert r.status_code == 200

    # missing delete -> 404
    r = client.delete(
        "/api/v1/integration/no-such-integration",
        headers=admin_headers,
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Notification and channel branches
# ---------------------------------------------------------------------------
def test_send_notification(client, admin_headers):
    r = client.post(
        "/api/v1/integration/notification/send",
        headers=admin_headers,
        json={
            "channel": "slack",
            "recipient": "#ops",
            "subject": "test",
            "body": "hello",
            "priority": "high",
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "success"
    assert "message" in r.json()


def test_get_notification_channels(client, admin_headers):
    r = client.get("/api/v1/integration/notification/channels", headers=admin_headers)
    assert r.status_code == 200
    assert "channels" in r.json()


# ---------------------------------------------------------------------------
# Webhook register, list, handle and event branches
# ---------------------------------------------------------------------------
def test_webhook_register_and_list(client, admin_headers):
    r = client.post(
        "/api/v1/integration/webhook/register",
        headers=admin_headers,
        json={
            "source": "github",
            "event_type": "push",
            "endpoint": "http://localhost:1/webhook",
            "secret": "shhh",
        },
    )
    assert r.status_code == 200
    webhook_id = r.json()["webhook_id"]

    r = client.get("/api/v1/integration/webhooks", headers=admin_headers)
    assert r.status_code == 200
    assert any(w["webhook_id"] == webhook_id for w in r.json()["webhooks"])

    # handle the webhook with no signature (success branch)
    r = client.post(
        "/api/v1/integration/webhook/handle",
        headers=admin_headers,
        params={"webhook_id": webhook_id},
        json={"ref": "refs/heads/main"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success" and "result" in data

    # handle with a wrong signature (signature validation failure branch)
    r = client.post(
        "/api/v1/integration/webhook/handle",
        headers=admin_headers,
        params={"webhook_id": webhook_id, "signature": "wrong"},
        json={"ref": "refs/heads/main"},
    )
    assert r.status_code == 200
    assert r.json()["result"]["success"] is False

    # handle a missing webhook_id
    r = client.post(
        "/api/v1/integration/webhook/handle",
        headers=admin_headers,
        params={"webhook_id": "no-such-webhook"},
        json={},
    )
    assert r.status_code == 200
    assert r.json()["result"]["success"] is False


def test_webhook_events(client, admin_headers):
    # default branch: processed=False
    r = client.get("/api/v1/integration/events", headers=admin_headers)
    assert r.status_code == 200
    assert "events" in r.json()

    # explicit processed=True / limit branches
    r = client.get(
        "/api/v1/integration/events",
        headers=admin_headers,
        params={"processed": "true", "limit": 10},
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# Provider-specific query / sync / callback branches
# ---------------------------------------------------------------------------
def _register_for_query(client, admin_headers, provider, extra_config=None, enabled=True):
    payload = {
        "integration_type": "custom",
        "name": f"{provider}-{uuid.uuid4().hex[:6]}",
        "config": {"provider": provider, **(extra_config or {})},
        "enabled": enabled,
    }
    r = client.post("/api/v1/integration/register", headers=admin_headers, json=payload)
    assert r.status_code == 200, f"register {provider} failed: {r.text}"
    return r.json()["integration"]["integration_id"]


def test_query_integration_not_found(client, admin_headers):
    r = client.post(
        "/api/v1/integration/missing-id/query",
        headers=admin_headers,
        json={"query": "up", "params": {}},
    )
    assert r.status_code == 404


def test_query_integration_disabled(client, admin_headers):
    iid = _register_for_query(client, admin_headers, "datadog", enabled=False)
    r = client.post(
        f"/api/v1/integration/{iid}/query",
        headers=admin_headers,
        json={"query": "avg:system.cpu.user{*}", "params": {}},
    )
    assert r.status_code == 400


def test_query_integration_unsupported_provider(client, admin_headers):
    iid = _register_for_query(client, admin_headers, "unknown")
    r = client.post(
        f"/api/v1/integration/{iid}/query",
        headers=admin_headers,
        json={"query": "foo", "params": {}},
    )
    assert r.status_code == 400


def test_query_integration_remote_providers_503(client, admin_headers):
    # These branches hit the remote add-on gateway; with a short timeout the
    # connection to the local add-on ports is refused and the endpoint returns 503.
    for provider in ("datadog", "grafana", "elk"):
        iid = _register_for_query(client, admin_headers, provider)
        r = client.post(
            f"/api/v1/integration/{iid}/query",
            headers=admin_headers,
            json={"query": "foo", "params": {}},
        )
        assert r.status_code in (503, 200), f"{provider} query: {r.status_code}"


def test_query_integration_cloudwatch_parse_error(client, admin_headers):
    iid = _register_for_query(
        client,
        admin_headers,
        "cloudwatch",
        extra_config={
            "aws_access_key_id": "fake",
            "aws_secret_access_key": "fake",
            "region": "us-east-1",
        },
    )
    r = client.post(
        f"/api/v1/integration/{iid}/query",
        headers=admin_headers,
        json={"query": "CPUUtilization", "params": {"time_range": "not-a-duration"}},
    )
    assert r.status_code == 200


def test_query_integration_pagerduty_key_error(client, admin_headers):
    iid = _register_for_query(client, admin_headers, "pagerduty")
    r = client.post(
        f"/api/v1/integration/{iid}/query",
        headers=admin_headers,
        json={"query": "incident", "params": {}},
    )
    assert r.status_code == 200


def test_prometheus_query(client, admin_headers):
    r = client.post(
        "/api/v1/integration/prometheus/query",
        headers=admin_headers,
        json={
            "integration_id": "no-such-prometheus",
            "query": "up",
            "time_range": "1h",
        },
    )
    assert r.status_code == 200
    assert "query_result" in r.json()


def test_jenkins_trigger(client, admin_headers):
    r = client.post(
        "/api/v1/integration/register",
        headers=admin_headers,
        json={
            "integration_type": "custom",
            "name": "jenkins",
            "config": {
                "url": "http://localhost:1",
                "username": "admin",
                "api_token": "fake",
            },
        },
    )
    assert r.status_code == 200, f"jenkins register failed: {r.text}"
    iid = r.json()["integration"]["integration_id"]
    r = client.post(
        "/api/v1/integration/jenkins/trigger",
        headers=admin_headers,
        json={
            "integration_id": iid,
            "job_name": "build",
            "parameters": {"branch": "main"},
        },
    )
    assert r.status_code == 200
    assert r.json()["trigger_result"]["success"] is True


def test_jira_issue_create(client, admin_headers):
    r = client.post(
        "/api/v1/integration/register",
        headers=admin_headers,
        json={
            "integration_type": "custom",
            "name": "jira",
            "config": {
                "url": "http://localhost:1",
                "username": "admin",
                "api_token": "fake",
            },
        },
    )
    assert r.status_code == 200, f"jira register failed: {r.text}"
    iid = r.json()["integration"]["integration_id"]
    r = client.post(
        "/api/v1/integration/jira/issue",
        headers=admin_headers,
        json={
            "integration_id": iid,
            "summary": "test",
            "description": "desc",
            "issue_type": "Bug",
            "priority": "Medium",
        },
    )
    assert r.status_code == 200
    assert r.json()["creation_result"]["success"] is True
