# -*- coding: utf-8 -*-
"""Real branch-coverage tests for api/user_router.py."""

import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.user_router import router as _user_router
from core.authentication import create_access_token, get_password_hash
from core.mfa_service import mfa_service
from core.user_service import user_service

_users_app = FastAPI()
_users_app.include_router(_user_router)


def _rand(prefix: str = "u") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _headers(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    with TestClient(_users_app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="module")
def admin_token():
    return create_access_token({"sub": "admin"})


@pytest.fixture(autouse=True)
def _patch_audit_log(monkeypatch):
    from core.audit_service import audit_service

    monkeypatch.setattr(audit_service, "log_action", AsyncMock(return_value=None))


def test_get_current_user_fallbacks(client):
    # missing token -> FAKE_ADMIN -> admin endpoint 200
    r = client.get("/api/v1/users/")
    assert r.status_code == 200

    # invalid token -> verify_token returns None -> FAKE_ADMIN -> 200
    r = client.get("/api/v1/users/", headers=_headers("not-a-jwt"))
    assert r.status_code == 200

    # valid token but empty sub -> FAKE_ADMIN -> 200
    r = client.get("/api/v1/users/", headers=_headers(create_access_token({"sub": ""})))
    assert r.status_code == 200

    # valid token, unknown user -> FAKE_ADMIN -> 200
    r = client.get("/api/v1/users/", headers=_headers(create_access_token({"sub": "nobody"})))
    assert r.status_code == 200


def test_get_current_user_disabled_and_require_admin(client):
    disabled = _rand("disabled")
    asyncio.run(
        user_service.create_user(
            username=disabled,
            hashed_password=get_password_hash("SecurePass123!"),
            role="user",
            disabled=True,
        )
    )
    r = client.get("/api/v1/users/me", headers=_headers(create_access_token({"sub": disabled})))
    assert r.status_code == 403

    viewer = _rand("viewer")
    asyncio.run(
        user_service.create_user(
            username=viewer,
            hashed_password=get_password_hash("SecurePass123!"),
            role="user",
        )
    )
    r = client.get("/api/v1/users/", headers=_headers(create_access_token({"sub": viewer})))
    assert r.status_code == 403


def test_get_client_ip_x_forwarded_for(client, admin_headers):
    r = client.post(
        "/api/v1/users/",
        headers={**admin_headers, "X-Forwarded-For": "1.2.3.4, 5.6.7.8"},
        json={
            "username": _rand("fwd"),
            "password": "SecurePass123!",
            "role": "user",
            "email": f"{_rand('fwd')}@example.com",
        },
    )
    assert r.status_code == 201


def test_create_user_validation(client, admin_headers):
    # invalid password
    r = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": _rand("bad"), "password": "aaaaaaaaaaaa", "role": "user"},
    )
    assert r.status_code == 400

    # duplicate username
    uname = _rand("dup")
    payload = {"username": uname, "password": "SecurePass123!", "role": "user"}
    r = client.post("/api/v1/users/", headers=admin_headers, json=payload)
    assert r.status_code == 201
    r = client.post("/api/v1/users/", headers=admin_headers, json=payload)
    assert r.status_code == 409

    # duplicate email
    email = f"{_rand('em')}@example.com"
    u1 = _rand("em1")
    u2 = _rand("em2")
    r = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": u1, "password": "SecurePass123!", "role": "user", "email": email},
    )
    assert r.status_code == 201
    r = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": u2, "password": "SecurePass123!", "role": "user", "email": email},
    )
    assert r.status_code == 409


def test_create_user_internal_error(client, admin_headers, monkeypatch):
    monkeypatch.setattr(user_service, "create_user", AsyncMock(return_value=None))
    r = client.post(
        "/api/v1/users/",
        headers=admin_headers,
        json={"username": _rand("fail"), "password": "SecurePass123!", "role": "user"},
    )
    assert r.status_code == 500


def test_get_user_not_found(client, admin_headers):
    r = client.get("/api/v1/users/nobody", headers=admin_headers)
    assert r.status_code == 404


def test_update_user_failures(client, admin_headers, monkeypatch):
    monkeypatch.setattr(user_service, "update_user", AsyncMock(return_value=False))
    r = client.put(
        "/api/v1/users/nobody",
        headers=admin_headers,
        json={"full_name": "x"},
    )
    assert r.status_code == 404

    monkeypatch.setattr(user_service, "update_user", AsyncMock(return_value=True))
    monkeypatch.setattr(user_service, "get_user_by_username", AsyncMock(return_value=None))
    r = client.put(
        "/api/v1/users/nobody2",
        headers=admin_headers,
        json={"full_name": "y"},
    )
    assert r.status_code == 404


def test_delete_user_branches(client, admin_headers):
    # cannot delete own account
    r = client.delete("/api/v1/users/admin", headers=admin_headers)
    assert r.status_code == 400

    # user not found
    r = client.delete("/api/v1/users/nobody", headers=admin_headers)
    assert r.status_code == 404


def test_change_password_branches(client, admin_headers, monkeypatch):
    # wrong current password
    r = client.post(
        "/api/v1/users/me/change-password",
        headers=admin_headers,
        json={"current_password": "wrong", "new_password": "NewSecurePass123!"},
    )
    assert r.status_code == 400

    # invalid new password
    r = client.post(
        "/api/v1/users/me/change-password",
        headers=admin_headers,
        json={"current_password": "admin123", "new_password": "bbbbbbbbbbbb"},
    )
    assert r.status_code == 400

    # update_password failure
    monkeypatch.setattr(user_service, "update_password", AsyncMock(return_value=False))
    r = client.post(
        "/api/v1/users/me/change-password",
        headers=admin_headers,
        json={"current_password": "admin123", "new_password": "NewSecurePass123!"},
    )
    assert r.status_code == 500


def test_mfa_branches(client, admin_headers, monkeypatch):
    # wrong password
    r = client.post(
        "/api/v1/users/me/mfa/enable",
        headers=admin_headers,
        json={"password": "wrong"},
    )
    assert r.status_code == 400

    # already enabled
    monkeypatch.setattr(mfa_service, "is_mfa_enabled", AsyncMock(return_value=True))
    r = client.post(
        "/api/v1/users/me/mfa/enable",
        headers=admin_headers,
        json={"password": "admin123"},
    )
    assert r.status_code == 400

    # disable mfa failure
    monkeypatch.setattr(mfa_service, "disable_mfa_for_user", AsyncMock(return_value=False))
    r = client.post("/api/v1/users/me/mfa/disable", headers=admin_headers)
    assert r.status_code == 500


def test_get_audit_logs(client, admin_headers, monkeypatch):
    from core.audit_service import audit_service

    monkeypatch.setattr(
        audit_service,
        "get_audit_logs",
        AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "action": "login",
                    "resource_type": "user",
                    "resource_id": "1",
                    "username": "admin",
                    "ip_address": "127.0.0.1",
                    "status": "success",
                    "details": "",
                    "created_at": None,
                }
            ]
        ),
    )
    r = client.get("/api/v1/users/audit-logs", headers=admin_headers)
    assert r.status_code == 200
