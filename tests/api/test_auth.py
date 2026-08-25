# -*- coding: utf-8 -*-
"""Real end-to-end tests for the auth and user management APIs.

These tests exercise the actual FastAPI application, real SQLite database,
and real JWT tokens. Fixtures are provided by tests/conftest.py.
"""

import uuid
from unittest.mock import Mock, patch

import pytest  # noqa: F401  # Imported for test setup
from sqlalchemy.orm import Session

from core.auth_db import Base, SessionLocal, User, engine


def test_login_success(client):
    """A valid admin login returns a bearer token."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["user"]["username"] == "admin"


def test_login_invalid_credentials(client):
    """Invalid credentials must return 401."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


def test_me_requires_token(client):
    """Calling /me without a token must be rejected."""
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_me_returns_current_user(client, admin_token):
    """A valid token returns the current user's profile."""
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"
    assert resp.json()["role"] == "admin"


@pytest.fixture
def test_user(client, admin_headers):
    """Create a unique operator user and clean it up after the test."""
    username = f"operator_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "password": "testpass",
            "role": "operator",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    user = resp.json()
    yield user
    # Cleanup is best-effort; ignore 404 if already deleted.
    client.delete(f"/api/v1/users/{user['id']}", headers=admin_headers)


def test_change_password(client, test_user):
    """A user can change its own password and log in with the new one."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": test_user["username"], "password": "testpass"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "testpass", "new_password": "newpass123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/auth/login",
        json={"username": test_user["username"], "password": "newpass123"},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_logout_revokes_token(client, test_user):
    """After logout the token can no longer be used."""
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": test_user["username"], "password": "testpass"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 401


def test_list_users_requires_admin(client):
    """Listing users without authentication must be rejected."""
    resp = client.get("/api/v1/users/")
    assert resp.status_code == 401


def test_list_users(client, admin_headers):
    """Admin can list users and the known admin is present."""
    resp = client.get("/api/v1/users/", headers=admin_headers)
    assert resp.status_code == 200
    usernames = {u["username"] for u in resp.json()}
    assert "admin" in usernames


def test_create_user_invalid_role(client, admin_headers):
    """Creating a user with an invalid role returns 400."""
    username = f"bad_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "password": "testpass",
            "role": "superuser",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400


def test_get_user(client, admin_headers, test_user):
    """A user can be retrieved by id with an admin token."""
    resp = client.get(f"/api/v1/users/{test_user['id']}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == test_user["username"]


def test_update_user_role(client, admin_headers, test_user):
    """An admin can update a user's role."""
    resp = client.put(
        f"/api/v1/users/{test_user['id']}",
        json={"role": "viewer"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "viewer"


def test_delete_user(client, admin_headers):
    """An admin can delete a user."""
    username = f"del_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "password": "testpass",
            "role": "viewer",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    resp = client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert resp.status_code == 200

    resp = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert resp.status_code == 404


def test_register_admin_fails_when_users_exist(client):
    """Bootstrap admin registration fails when users already exist (lines 74-78)."""
    # The database already has an admin user from conftest
    resp = client.post(
        "/api/v1/auth/register-admin",
        json={"username": "newadmin", "password": "admin123"},
    )
    assert resp.status_code == 400
    resp_data = resp.json()
    # Check for error message in nested structure
    error_msg = (
        resp_data.get("detail")
        or resp_data.get("message")
        or resp_data.get("error", {}).get("message", "")
    )
    assert "Bootstrap registration only allowed when no users exist" in error_msg


def test_change_password_wrong_old_password(client, admin_token):
    """Changing password with wrong old password returns 401 (line 104)."""
    resp = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "wrongpassword", "new_password": "newpass123"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code == 401
    resp_data = resp.json()
    error_msg = (
        resp_data.get("detail")
        or resp_data.get("message")
        or resp_data.get("error", {}).get("message", "")
    )
    assert "Old password is incorrect" in error_msg


def test_logout_without_jti_in_token(client, test_user):
    """Logout handles tokens without jti gracefully (lines 123-128)."""
    # First, login to get a normal token
    resp = client.post(
        "/api/v1/auth/login",
        json={"username": test_user["username"], "password": "testpass"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]

    # Create a malformed token without jti by manually crafting a JWT
    from datetime import datetime, timedelta, timezone

    import jwt

    import config

    # Create a token payload without jti but with required fields
    payload = {
        "sub": test_user["username"],
        "role": "operator",
        "exp": (datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp(),
        "iat": datetime.now(timezone.utc).timestamp(),
        "iss": "aiops-agent",
        "aud": "aiops-api",
        "tenant_id": "default",
        # Note: no "jti" field
    }
    malformed_token = jwt.encode(
        payload,
        config.JWT_SECRET_KEY,
        algorithm=config.JWT_ALGORITHM,
    )

    # Logout should still succeed even without jti
    resp = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {malformed_token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["detail"] == "Logged out"
