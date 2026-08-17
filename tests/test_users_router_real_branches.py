# -*- coding: utf-8 -*-
"""Real TestClient tests for api/users_router.py.

Uses a small FastAPI app with only auth + users routers so startup is fast
and deterministic.  Exercises CRUD, permissions, RBAC, 404/403/400 branches,
tenant header handling and edge payloads to drive branch coverage for
api/users_router.py.
"""

import uuid

import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient

from api.auth_router import router as _auth_router
from api.users_router import router as _users_router
from core.api_error import (
    api_error_handler,
    general_exception_handler,
    validation_error_handler,
)

_users_app = FastAPI()
_users_app.include_router(_auth_router)
_users_app.include_router(_users_router)
_users_app.add_exception_handler(HTTPException, api_error_handler)
_users_app.add_exception_handler(RequestValidationError, validation_error_handler)
_users_app.add_exception_handler(Exception, general_exception_handler)


@pytest.fixture(scope="module", autouse=True)
def client():
    with TestClient(_users_app, raise_server_exceptions=False) as c:
        yield c


def _rand(prefix: str = "u") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _token_for(client, username: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


def _err_msg(resp):
    """Return the human-readable error message from the unified error response."""
    return resp.json()["error"]["message"]


def _admin_id(client, admin_headers):
    resp = client.get("/api/v1/users/", headers=admin_headers)
    assert resp.status_code == 200
    for u in resp.json():
        if u["role"] == "admin":
            return u["id"]
    raise AssertionError("no admin found")


def _ensure_single_admin(client, admin_headers):
    """Delete any extra admin accounts (only the seeded 'admin' is kept)."""
    resp = client.get("/api/v1/users/", headers=admin_headers)
    assert resp.status_code == 200
    for u in resp.json():
        if u["role"] == "admin" and u["username"] != "admin":
            client.delete(f"/api/v1/users/{u['id']}", headers=admin_headers)


def test_list_users_and_auth(client, admin_headers):
    # admin list
    resp = client.get("/api/v1/users/", headers=admin_headers)
    assert resp.status_code == 200
    assert any(u["username"] == "admin" for u in resp.json())

    # missing token
    resp = client.get("/api/v1/users/")
    assert resp.status_code == 401

    # viewer cannot list
    uname = _rand("view")
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": uname, "password": "secret", "role": "viewer"},
    )
    assert resp.status_code == 201
    token = _token_for(client, uname, "secret")
    resp = client.get("/api/v1/users/", headers=_headers(token))
    assert resp.status_code == 403


def test_create_user_and_get_me(client, admin_headers):
    uname = _rand("bob")
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "username": uname,
            "password": "secret",
            "role": "viewer",
            "is_active": True,
            "permissions": [{"asset_id": 1, "permission": "view"}],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["username"] == uname
    assert data["role"] == "viewer"
    assert data["is_active"] is True
    uid = data["id"]

    # get me
    token = _token_for(client, uname, "secret")
    resp = client.get("/api/v1/users/me", headers=_headers(token))
    assert resp.status_code == 200
    assert resp.json()["id"] == uid

    # get by id as admin
    resp = client.get(f"/api/v1/users/{uid}", headers=admin_headers)
    assert resp.status_code == 200

    # get permissions as admin
    resp = client.get(f"/api/v1/users/{uid}/permissions", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # set permissions
    resp = client.put(
        f"/api/v1/users/{uid}/permissions",
        headers=admin_headers,
        json={"permissions": [{"asset_id": 2, "permission": "edit"}]},
    )
    assert resp.status_code == 200
    assert resp.json()[0]["permission"] == "edit"


def test_create_user_validation(client, admin_headers):
    # invalid role
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": _rand("x"), "password": "secret", "role": "superuser"},
    )
    assert resp.status_code == 400
    assert "Invalid role" in _err_msg(resp)

    # invalid permission
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={
            "username": _rand("x"),
            "password": "secret",
            "role": "viewer",
            "permissions": [{"asset_id": 1, "permission": "admin"}],
        },
    )
    assert resp.status_code == 400
    assert "Invalid permission" in _err_msg(resp)

    # missing required field
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": _rand("x"), "role": "viewer"},
    )
    assert resp.status_code == 422

    # duplicate username
    uname = _rand("dup")
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": uname, "password": "secret", "role": "viewer"},
    )
    assert resp.status_code == 201
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": uname, "password": "secret", "role": "viewer"},
    )
    assert resp.status_code == 400
    assert "already taken" in _err_msg(resp)


def test_create_admin_max(client, admin_headers):
    _ensure_single_admin(client, admin_headers)
    a2 = _rand("adm2")
    a3 = _rand("adm3")
    a4 = _rand("adm4")
    created_ids = []
    try:
        for uname in (a2, a3):
            resp = client.post(
                "/api/v1/users/",
                headers=admin_headers,
                json={"username": uname, "password": "secret", "role": "admin"},
            )
            assert resp.status_code == 201
            assert resp.json()["role"] == "admin"
            created_ids.append(resp.json()["id"])

        resp = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={"username": a4, "password": "secret", "role": "admin"},
        )
        assert resp.status_code == 400
        assert "Maximum number of admins" in _err_msg(resp)
    finally:
        for uid in created_ids:
            client.delete(f"/api/v1/users/{uid}", headers=admin_headers)


def test_get_user_rbac_and_not_found(client, admin_headers):
    uname = _rand("vget")
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": uname, "password": "secret", "role": "viewer"},
    )
    uid = resp.json()["id"]
    token = _token_for(client, uname, "secret")

    # self get
    resp = client.get(f"/api/v1/users/{uid}", headers=_headers(token))
    assert resp.status_code == 200

    # viewer get another user -> 403
    admin_id = _admin_id(client, admin_headers)
    resp = client.get(f"/api/v1/users/{admin_id}", headers=_headers(token))
    assert resp.status_code == 403

    # admin get non-existent
    resp = client.get("/api/v1/users/99999", headers=admin_headers)
    assert resp.status_code == 404

    # unauthenticated
    resp = client.get(f"/api/v1/users/{uid}")
    assert resp.status_code == 401


def test_update_user_self_password(client, admin_headers):
    uname = _rand("self")
    client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": uname, "password": "oldpass", "role": "viewer"},
    )
    token = _token_for(client, uname, "oldpass")
    me = client.get("/api/v1/users/me", headers=_headers(token)).json()
    uid = me["id"]

    resp = client.put(
        f"/api/v1/users/{uid}",
        headers=_headers(token),
        json={"new_password": "newpass"},
    )
    assert resp.status_code == 200

    # login with new password
    new_token = _token_for(client, uname, "newpass")
    resp = client.get("/api/v1/users/me", headers=_headers(new_token))
    assert resp.status_code == 200


def test_update_user_admin_fields_and_errors(client, admin_headers):
    uname = _rand("upd")
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": uname, "password": "secret", "role": "viewer"},
    )
    uid = resp.json()["id"]

    # change role
    resp = client.put(f"/api/v1/users/{uid}", headers=admin_headers, json={"role": "operator"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "operator"

    # deactivate
    resp = client.put(f"/api/v1/users/{uid}", headers=admin_headers, json={"is_active": False})
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # invalid role
    resp = client.put(f"/api/v1/users/{uid}", headers=admin_headers, json={"role": "hacker"})
    assert resp.status_code == 400
    assert "Invalid role" in _err_msg(resp)

    # 404
    resp = client.put("/api/v1/users/99999", headers=admin_headers, json={"role": "operator"})
    assert resp.status_code == 404

    # non-admin cannot update another user
    v1 = _rand("v1")
    client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": v1, "password": "secret", "role": "viewer"},
    )
    v1_token = _token_for(client, v1, "secret")
    v2 = _rand("v2")
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": v2, "password": "secret", "role": "viewer"},
    )
    v2_id = resp.json()["id"]
    resp = client.put(
        f"/api/v1/users/{v2_id}",
        headers=_headers(v1_token),
        json={"new_password": "xyz"},
    )
    assert resp.status_code == 403

    # self cannot set role / is_active
    v2_token = _token_for(client, v2, "secret")
    resp = client.put(
        f"/api/v1/users/{v2_id}",
        headers=_headers(v2_token),
        json={"role": "operator"},
    )
    assert resp.status_code == 403
    assert "Admin only" in _err_msg(resp)


def test_update_user_last_admin_and_promotion(client, admin_headers):
    _ensure_single_admin(client, admin_headers)
    created_ids = []
    try:
        # promote a viewer to admin
        v = _rand("promo")
        resp = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={"username": v, "password": "secret", "role": "viewer"},
        )
        vid = resp.json()["id"]
        created_ids.append(vid)
        resp = client.put(f"/api/v1/users/{vid}", headers=admin_headers, json={"role": "admin"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "admin"

        # change that admin back to viewer (not last admin)
        resp = client.put(f"/api/v1/users/{vid}", headers=admin_headers, json={"role": "viewer"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"

        # try to change the role of the last admin
        admin_id = _admin_id(client, admin_headers)
        resp = client.put(
            f"/api/v1/users/{admin_id}",
            headers=admin_headers,
            json={"role": "viewer"},
        )
        assert resp.status_code == 400
        assert "Cannot change role of the last admin" in _err_msg(resp)

        # try to deactivate the last admin
        resp = client.put(
            f"/api/v1/users/{admin_id}",
            headers=admin_headers,
            json={"is_active": False},
        )
        assert resp.status_code == 400
        assert "Cannot deactivate the last admin" in _err_msg(resp)

        # promotion blocked by max admins
        a1 = _rand("adm_a")
        a2 = _rand("adm_b")
        r1 = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={"username": a1, "password": "secret", "role": "admin"},
        )
        created_ids.append(r1.json()["id"])
        r2 = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={"username": a2, "password": "secret", "role": "admin"},
        )
        created_ids.append(r2.json()["id"])
        v2 = _rand("v2promo")
        r3 = client.post(
            "/api/v1/users/",
            headers=admin_headers,
            json={"username": v2, "password": "secret", "role": "viewer"},
        )
        v2_id = r3.json()["id"]
        created_ids.append(v2_id)
        resp = client.put(f"/api/v1/users/{v2_id}", headers=admin_headers, json={"role": "admin"})
        assert resp.status_code == 400
        assert "Maximum number of admins" in _err_msg(resp)
    finally:
        for uid in created_ids:
            client.delete(f"/api/v1/users/{uid}", headers=admin_headers)


def test_delete_user(client, admin_headers):
    _ensure_single_admin(client, admin_headers)
    # create and delete
    uname = _rand("delme")
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": uname, "password": "secret", "role": "viewer"},
    )
    uid = resp.json()["id"]
    resp = client.delete(f"/api/v1/users/{uid}", headers=admin_headers)
    assert resp.status_code == 200
    assert "deleted" in resp.json()["detail"]

    # 404 on second delete
    resp = client.delete(f"/api/v1/users/{uid}", headers=admin_headers)
    assert resp.status_code == 404

    # cannot delete last admin
    admin_id = _admin_id(client, admin_headers)
    resp = client.delete(f"/api/v1/users/{admin_id}", headers=admin_headers)
    assert resp.status_code == 400
    assert "Cannot delete the last admin" in _err_msg(resp)

    # non-admin cannot delete
    v = _rand("vdel")
    client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": v, "password": "secret", "role": "viewer"},
    )
    v_token = _token_for(client, v, "secret")
    resp = client.delete(f"/api/v1/users/{admin_id}", headers=_headers(v_token))
    assert resp.status_code == 403


def test_permissions_rbac_and_errors(client, admin_headers):
    v = _rand("vperm")
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": v, "password": "secret", "role": "viewer"},
    )
    vid = resp.json()["id"]
    v_token = _token_for(client, v, "secret")

    # self get permissions
    resp = client.get(f"/api/v1/users/{vid}/permissions", headers=_headers(v_token))
    assert resp.status_code == 200
    assert resp.json() == []

    # another viewer cannot get
    v2 = _rand("vperm2")
    resp2 = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": v2, "password": "secret", "role": "viewer"},
    )
    v2_id = resp2.json()["id"]
    resp = client.get(f"/api/v1/users/{v2_id}/permissions", headers=_headers(v_token))
    assert resp.status_code == 403

    # 404 get
    resp = client.get("/api/v1/users/99999/permissions", headers=admin_headers)
    assert resp.status_code == 404

    # set permissions invalid
    resp = client.put(
        f"/api/v1/users/{vid}/permissions",
        headers=admin_headers,
        json={"permissions": [{"asset_id": 1, "permission": "own"}]},
    )
    assert resp.status_code == 400
    assert "Invalid permission" in _err_msg(resp)

    # set permissions 404
    resp = client.put(
        "/api/v1/users/99999/permissions",
        headers=admin_headers,
        json={"permissions": []},
    )
    assert resp.status_code == 404

    # set empty permissions
    resp = client.put(
        f"/api/v1/users/{vid}/permissions",
        headers=admin_headers,
        json={"permissions": []},
    )
    assert resp.status_code == 200
    assert resp.json() == []


def test_tenant_header_does_not_break(client, admin_headers):
    # tenant middleware resolves the header; the user router should still work
    resp = client.get(
        "/api/v1/users/",
        headers={**admin_headers, "X-Tenant-ID": "tenant2"},
    )
    assert resp.status_code == 200
    assert any(u["username"] == "admin" for u in resp.json())


def test_edge_payloads(client, admin_headers):
    # empty password is accepted by the router
    uname = _rand("empty")
    resp = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": uname, "password": "", "role": "viewer"},
    )
    assert resp.status_code == 201
    uid = resp.json()["id"]

    # update with all admin fields including empty password and no real changes
    resp = client.put(
        f"/api/v1/users/{uid}",
        headers=admin_headers,
        json={"new_password": "", "is_active": True, "role": "viewer"},
    )
    assert resp.status_code == 200

    # empty update body
    resp = client.put(f"/api/v1/users/{uid}", headers=admin_headers, json={})
    assert resp.status_code == 200
