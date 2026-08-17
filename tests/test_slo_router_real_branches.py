# -*- coding: utf-8 -*-
"""Real branch-coverage tests for api/slo_router.py using TestClient.

These tests exercise the SLO/SLA FastAPI router without mocks or stubs.
A small FastAPI app that mounts only the SLO router is used to cover the
internal-api-key authentication branches, while the real main.app is used
for role-based and CRUD branches.
"""

import uuid

import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.assets_router import router as _assets_router
from api.auth_router import router as _auth_router
from api.slo_router import router as _slo_router
from api.users_router import router as _users_router
from config import INTERNAL_API_KEY

_slo_only_app = FastAPI()
_slo_only_app.include_router(_slo_router)

_slo_app = FastAPI()
_slo_app.include_router(_auth_router)
_slo_app.include_router(_assets_router)
_slo_app.include_router(_slo_router)
_slo_app.include_router(_users_router)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def slo_client():
    with TestClient(_slo_app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="module")
def internal_client():
    with TestClient(_slo_only_app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="module")
def admin_headers(slo_client):
    r = slo_client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert r.status_code == 200, f"admin login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module", autouse=True)
def _clean_slo_state(slo_client, admin_headers):
    """Remove stale SLOs/reports from earlier test runs."""
    r = slo_client.get("/api/v1/slo/", headers=admin_headers)
    if r.status_code == 200:
        for s in r.json().get("slos", []):
            slo_client.delete(f"/api/v1/slo/{s['id']}", headers=admin_headers)
    r = slo_client.get("/api/v1/slo/reports", headers=admin_headers)
    if r.status_code == 200:
        for rep in r.json().get("reports", []):
            slo_client.delete(f"/api/v1/slo/reports/{rep['id']}", headers=admin_headers)
    yield


@pytest.fixture(scope="module")
def slo_asset(slo_client, admin_headers):
    service = f"slo-svc-{uuid.uuid4().hex[:8]}"
    r = slo_client.post(
        "/api/v1/assets/",
        headers=admin_headers,
        json={"name": "SLO test asset", "service": service},
    )
    assert r.status_code == 201, f"asset create failed: {r.text}"
    return r.json()


def _make_business_user(client, admin_headers, username, permissions):
    r = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": username, "password": "Pass1234!", "role": "business"},
    )
    assert r.status_code == 201, f"user create failed: {r.text}"
    uid = r.json()["id"]
    if permissions:
        r = client.put(
            f"/api/v1/users/{uid}/permissions",
            headers=admin_headers,
            json={"permissions": permissions},
        )
        assert r.status_code == 200, f"permissions set failed: {r.text}"
    r = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "Pass1234!"},
    )
    assert r.status_code == 200, f"business login failed: {r.text}"
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def biz_edit_headers(slo_client, admin_headers, slo_asset):
    return _make_business_user(
        slo_client,
        admin_headers,
        f"slo_biz_edit_{uuid.uuid4().hex[:6]}",
        [{"asset_id": slo_asset["id"], "permission": "edit"}],
    )


@pytest.fixture(scope="module")
def biz_view_headers(slo_client, admin_headers, slo_asset):
    return _make_business_user(
        slo_client,
        admin_headers,
        f"slo_biz_view_{uuid.uuid4().hex[:6]}",
        [{"asset_id": slo_asset["id"], "permission": "view"}],
    )


@pytest.fixture(scope="module")
def biz_none_headers(slo_client, admin_headers):
    return _make_business_user(
        slo_client,
        admin_headers,
        f"slo_biz_none_{uuid.uuid4().hex[:6]}",
        [],
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _create_slo(client, headers, service, name=None, **extra):
    payload = {
        "name": name or f"slo-{uuid.uuid4().hex[:6]}",
        "service": service,
        "metric": "availability",
        "target": 99.9,
        "window": "1h",
        "alert_threshold": 95.0,
        "aggregation": "good_ratio",
    }
    payload.update(extra)
    r = client.post("/api/v1/slo/", headers=headers, json=payload)
    assert r.status_code == 200, f"create SLO failed: {r.text}"
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def test_internal_auth_branches(internal_client):
    """Cover _get_current_user_or_internal internal-key branches."""
    # No internal key, no token -> 401 from _get_current_user_or_internal
    r = internal_client.get("/api/v1/slo/")
    assert r.status_code == 401

    # Valid internal key -> 200
    r = internal_client.get("/api/v1/slo/", headers={"X-Internal-Key": INTERNAL_API_KEY})
    assert r.status_code == 200

    # Invalid internal key, no token -> 401
    r = internal_client.get("/api/v1/slo/", headers={"X-Internal-Key": "wrong-key"})
    assert r.status_code == 401


def test_create_slo_business_editor(slo_client, biz_edit_headers, slo_asset):
    """Business user with edit permission can create an SLO."""
    slo_id = _create_slo(slo_client, biz_edit_headers, slo_asset["service"], name="biz-ok")
    r = slo_client.get(f"/api/v1/slo/{slo_id}", headers=biz_edit_headers)
    assert r.status_code == 200
    assert r.json()["name"] == "biz-ok"


def test_create_slo_business_permission_denied(
    slo_client, biz_view_headers, biz_edit_headers, slo_asset
):
    """Business user cannot create for a service without edit permission."""
    # View-only user cannot create even for the known service.
    r = slo_client.post(
        "/api/v1/slo/",
        headers=biz_view_headers,
        json={
            "name": "denied",
            "service": slo_asset["service"],
            "metric": "availability",
            "target": 99.9,
            "window": "1h",
        },
    )
    assert r.status_code == 403

    # Editor cannot create for an unknown service (asset_id is None).
    r = slo_client.post(
        "/api/v1/slo/",
        headers=biz_edit_headers,
        json={
            "name": "denied",
            "service": "nonexistent-service",
            "metric": "availability",
            "target": 99.9,
            "window": "1h",
        },
    )
    assert r.status_code == 403


def test_list_and_get_slo_business(
    slo_client, admin_headers, biz_edit_headers, biz_view_headers, biz_none_headers, slo_asset
):
    """List and GET filter SLOs by business user view permission."""
    visible_id = _create_slo(slo_client, biz_edit_headers, slo_asset["service"], name="visible")
    hidden_id = _create_slo(slo_client, admin_headers, "unknown-service", name="hidden")

    # Business viewer sees only the SLO for the allowed service.
    r = slo_client.get("/api/v1/slo/", headers=biz_view_headers)
    assert r.status_code == 200
    ids = {s["id"] for s in r.json()["slos"]}
    assert visible_id in ids
    assert hidden_id not in ids

    # Admin sees all.
    r = slo_client.get("/api/v1/slo/", headers=admin_headers)
    assert r.status_code == 200
    assert hidden_id in {s["id"] for s in r.json()["slos"]}

    # Business viewer can GET the visible SLO.
    r = slo_client.get(f"/api/v1/slo/{visible_id}", headers=biz_view_headers)
    assert r.status_code == 200

    # Business user with no permission cannot GET the visible SLO.
    r = slo_client.get(f"/api/v1/slo/{visible_id}", headers=biz_none_headers)
    assert r.status_code == 403

    # Not found is still 404.
    r = slo_client.get("/api/v1/slo/NOSUCH", headers=biz_view_headers)
    assert r.status_code == 404


def test_update_slo_business(
    slo_client, admin_headers, biz_edit_headers, biz_view_headers, slo_asset
):
    """Business permission and conversion branches in PUT /{slo_id}."""
    # Create a second asset and grant editor permission for both services.
    r = slo_client.post(
        "/api/v1/assets/",
        headers=admin_headers,
        json={"name": "Other asset", "service": "other-svc"},
    )
    assert r.status_code == 201
    other_asset = r.json()

    me = slo_client.get("/api/v1/users/me", headers=biz_edit_headers).json()
    editor_id = me["id"]
    slo_client.put(
        f"/api/v1/users/{editor_id}/permissions",
        headers=admin_headers,
        json={
            "permissions": [
                {"asset_id": slo_asset["id"], "permission": "edit"},
                {"asset_id": other_asset["id"], "permission": "edit"},
            ]
        },
    )

    slo_id = _create_slo(slo_client, biz_edit_headers, slo_asset["service"], name="to-update")

    # Update with target/window/alert_threshold present to cover conversion branches.
    r = slo_client.put(
        f"/api/v1/slo/{slo_id}",
        headers=biz_edit_headers,
        json={
            "name": "updated",
            "target": 99.5,
            "window": "24h",
            "alert_threshold": 98.0,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "updated"

    # Change to another editable service (covers new-service permission true).
    r = slo_client.put(
        f"/api/v1/slo/{slo_id}",
        headers=biz_edit_headers,
        json={"service": other_asset["service"]},
    )
    assert r.status_code == 200
    assert r.json()["service"] == other_asset["service"]

    # Change back to the original service.
    r = slo_client.put(
        f"/api/v1/slo/{slo_id}",
        headers=biz_edit_headers,
        json={"service": slo_asset["service"]},
    )
    assert r.status_code == 200

    # Revoke edit on the other service and try to change there -> 403.
    slo_client.put(
        f"/api/v1/users/{editor_id}/permissions",
        headers=admin_headers,
        json={
            "permissions": [
                {"asset_id": slo_asset["id"], "permission": "edit"},
            ]
        },
    )
    r = slo_client.put(
        f"/api/v1/slo/{slo_id}",
        headers=biz_edit_headers,
        json={"service": other_asset["service"]},
    )
    assert r.status_code == 403

    # Viewer cannot edit the existing service.
    r = slo_client.put(
        f"/api/v1/slo/{slo_id}",
        headers=biz_view_headers,
        json={"name": "viewer-update"},
    )
    assert r.status_code == 403


def test_sla_report_branches(
    slo_client, admin_headers, biz_edit_headers, biz_view_headers, biz_none_headers, slo_asset
):
    """Cover report generation/listing/GET/delete business branches."""
    _create_slo(slo_client, biz_edit_headers, slo_asset["service"], name="reported")

    # Editor can generate reports.
    r = slo_client.post(
        "/api/v1/slo/reports",
        headers=biz_edit_headers,
        params={"period": "30d"},
    )
    assert r.status_code == 200
    assert r.json()["generated_ids"]
    report_id = r.json()["generated_ids"][0]  # noqa: F841  # Variable for test verification

    # Viewer cannot generate reports (no editable SLO).
    r = slo_client.post(
        "/api/v1/slo/reports",
        headers=biz_view_headers,
        params={"period": "30d"},
    )
    assert r.status_code == 403

    # Viewer can list reports for the viewable service; none-user cannot.
    r = slo_client.get("/api/v1/slo/reports", headers=biz_view_headers, params={"period": "30d"})
    assert r.status_code == 200
    assert any(rep.get("service") == slo_asset["service"] for rep in r.json()["reports"])

    r = slo_client.get("/api/v1/slo/reports", headers=biz_none_headers)
    assert r.status_code == 200
    assert all(rep.get("service") != slo_asset["service"] for rep in r.json()["reports"])

    # Viewer can GET the report; none-user cannot.
    r = slo_client.get(f"/api/v1/slo/reports/{report_id}", headers=biz_view_headers)
    assert r.status_code == 200

    r = slo_client.get(f"/api/v1/slo/reports/{report_id}", headers=biz_none_headers)
    assert r.status_code == 403

    # Admin creates another report so we can test viewer delete permission.
    r = slo_client.post(
        "/api/v1/slo/reports",
        headers=admin_headers,
        params={"period": "30d"},
    )
    assert r.status_code == 200
    report_id2 = r.json()["generated_ids"][0]  # noqa: F841  # Variable for test verification

    # Viewer cannot delete an editable report.
    r = slo_client.delete(f"/api/v1/slo/reports/{report_id2}", headers=biz_view_headers)
    assert r.status_code == 403

    # Editor can delete the original report.
    r = slo_client.delete(f"/api/v1/slo/reports/{report_id}", headers=biz_edit_headers)
    assert r.status_code == 200


def test_delete_slo_business(
    slo_client, admin_headers, biz_edit_headers, biz_view_headers, slo_asset
):
    """Cover delete SLO business permission branches."""
    slo_id = _create_slo(slo_client, biz_edit_headers, slo_asset["service"], name="to-del")

    # Editor can delete.
    r = slo_client.delete(f"/api/v1/slo/{slo_id}", headers=biz_edit_headers)
    assert r.status_code == 200

    # Create another SLO as admin so viewer can attempt delete without permission.
    slo_id2 = _create_slo(slo_client, admin_headers, slo_asset["service"], name="admin-slo")
    r = slo_client.delete(f"/api/v1/slo/{slo_id2}", headers=biz_view_headers)
    assert r.status_code == 403
