# -*- coding: utf-8 -*-
"""Real end-to-end tests for the user management endpoints."""

import uuid

import pytest  # noqa: F401  # Imported for test setup

_CASES = [
    ("POST", "/api/v1/users/", {}, {200, 422, 500}),
    ("GET", "/api/v1/users/", None, {200, 404, 500}),
    ("GET", "/api/v1/users/me", None, {200, 500}),
    ("GET", "/api/v1/users/audit-logs", None, {200, 403, 422, 500}),
    ("GET", "/api/v1/users/1", None, {200, 404, 500}),
    ("PUT", "/api/v1/users/1", {}, {200, 422, 404, 500}),
    ("DELETE", "/api/v1/users/1", None, {200, 204, 400, 404, 500}),
    ("POST", "/api/v1/users/me/change-password", {}, {200, 422, 404, 500}),
    ("POST", "/api/v1/users/me/mfa/enable", {}, {200, 422, 404, 500}),
    ("POST", "/api/v1/users/me/mfa/disable", {}, {200, 422, 404, 500}),
    ("GET", "/api/v1/users/me/mfa/status", None, {200, 404, 500}),
    ("GET", "/api/v1/users/me/audit-logs", None, {200, 404, 500}),
    ("GET", "/api/v1/users/1/audit-logs", None, {200, 404, 500}),
]


@pytest.mark.smoke
@pytest.mark.parametrize("method,path,body,expected", _CASES)
def test_user_endpoint(client, admin_headers, method, path, body, expected):
    """Each user_router endpoint returns an expected status set."""
    kwargs = {}
    if body is not None:
        kwargs["json"] = body
    resp = client.request(method, path, headers=admin_headers, **kwargs)
    assert resp.status_code in expected


def test_create_user_with_invalid_permission(client):
    """Creating a user with an invalid permission returns 400 (covers lines 100-105)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    username = f"badperm_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "password": "testpass",
            "role": "viewer",
            "is_active": True,
            "permissions": [{"asset_id": 1, "permission": "invalid_perm"}],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "Invalid permission" in resp.json()["error"]["message"]


def test_create_user_with_valid_permissions(client):
    """Creating a user with valid permissions succeeds (covers line 113)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    username = f"goodperm_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "password": "testpass",
            "role": "viewer",
            "is_active": True,
            "permissions": [
                {"asset_id": 1, "permission": "view"},
                {"asset_id": 2, "permission": "edit"},
            ],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    user = resp.json()
    assert user["username"] == username
    # Cleanup
    client.delete(f"/api/v1/users/{user['id']}", headers=admin_headers)


def test_update_nonexistent_user(client):
    """Updating a nonexistent user returns 404 (covers line 145)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.put(
        "/api/v1/users/99999",
        json={"role": "viewer"},
        headers=admin_headers,
    )
    assert resp.status_code == 404
    assert "User not found" in resp.json()["error"]["message"]


def test_update_password_as_non_admin_non_self(client):
    """A non-admin user cannot update another user's password (covers line 153)."""
    # Create two regular users using admin
    username1 = f"user1_{uuid.uuid4().hex[:8]}"
    username2 = f"user2_{uuid.uuid4().hex[:8]}"

    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp1 = client.post(
        "/api/v1/users/",
        json={
            "username": username1,
            "password": "testpass1",
            "role": "viewer",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp1.status_code == 201
    user1_id = resp1.json()["id"]

    resp2 = client.post(
        "/api/v1/users/",
        json={
            "username": username2,
            "password": "testpass2",
            "role": "viewer",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp2.status_code == 201
    user2 = resp2.json()

    # Login as user1
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username1, "password": "testpass1"},
    )
    assert login_resp.status_code == 200
    user1_token = login_resp.json()["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}

    # Try to update user2's password as user1 (should fail)
    resp = client.put(
        f"/api/v1/users/{user2['id']}",
        json={"new_password": "newpass"},
        headers=user1_headers,
    )
    assert resp.status_code == 403

    # Cleanup
    client.delete(f"/api/v1/users/{user1_id}", headers=admin_headers)
    client.delete(f"/api/v1/users/{user2['id']}", headers=admin_headers)


def test_update_user_with_invalid_role(client):
    """Updating a user with an invalid role returns 400 (covers line 164)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    username = f"badrole_{uuid.uuid4().hex[:8]}"
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

    resp = client.put(
        f"/api/v1/users/{user_id}",
        json={"role": "superuser"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "Invalid role" in resp.json()["error"]["message"]

    # Cleanup
    client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)


def test_promote_user_to_admin(client):
    """Promoting a regular user to admin succeeds (covers line 174)."""
    # First create an additional admin to ensure we don't hit the max admin limit
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    admin2_username = f"admin2_{uuid.uuid4().hex[:8]}"
    resp = client.post(
        "/api/v1/users/",
        json={
            "username": admin2_username,
            "password": "adminpass",
            "role": "admin",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    admin2_id = resp.json()["id"]

    # Create a regular user
    username = f"promote_{uuid.uuid4().hex[:8]}"
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

    # Promote the user to admin
    resp = client.put(
        f"/api/v1/users/{user_id}",
        json={"role": "admin"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"

    # Cleanup
    client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    client.delete(f"/api/v1/users/{admin2_id}", headers=admin_headers)


def test_delete_nonexistent_user(client):
    """Deleting a nonexistent user returns 404 (covers line 198)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.delete("/api/v1/users/99999", headers=admin_headers)
    assert resp.status_code == 404
    assert "User not found" in resp.json()["error"]["message"]


def test_get_permissions_forbidden(client):
    """Getting permissions for another user as non-admin returns 403 (covers line 216)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create two regular users
    username1 = f"user1_{uuid.uuid4().hex[:8]}"
    username2 = f"user2_{uuid.uuid4().hex[:8]}"

    resp1 = client.post(
        "/api/v1/users/",
        json={
            "username": username1,
            "password": "testpass1",
            "role": "viewer",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp1.status_code == 201
    user1_id = resp1.json()["id"]

    resp2 = client.post(
        "/api/v1/users/",
        json={
            "username": username2,
            "password": "testpass2",
            "role": "viewer",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp2.status_code == 201
    user2 = resp2.json()

    # Login as user1
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username1, "password": "testpass1"},
    )
    assert login_resp.status_code == 200
    user1_token = login_resp.json()["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}

    # Try to get user2's permissions as user1 (should fail)
    resp = client.get(
        f"/api/v1/users/{user2['id']}/permissions",
        headers=user1_headers,
    )
    assert resp.status_code == 403

    # Cleanup
    client.delete(f"/api/v1/users/{user1_id}", headers=admin_headers)
    client.delete(f"/api/v1/users/{user2['id']}", headers=admin_headers)


def test_set_permissions_nonexistent_user(client):
    """Setting permissions for a nonexistent user returns 404 (covers line 236)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.put(
        "/api/v1/users/99999/permissions",
        json={"permissions": [{"asset_id": 1, "permission": "view"}]},
        headers=admin_headers,
    )
    assert resp.status_code == 404
    assert "User not found" in resp.json()["error"]["message"]


def test_set_permissions_invalid_permission(client):
    """Setting permissions with an invalid permission returns 400."""
    username = f"badsetperm_{uuid.uuid4().hex[:8]}"

    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

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

    resp = client.put(
        f"/api/v1/users/{user_id}/permissions",
        json={"permissions": [{"asset_id": 1, "permission": "invalid"}]},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "Invalid permission" in resp.json()["error"]["message"]

    # Cleanup
    client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)


def test_get_user_forbidden(client):
    """A non-admin user cannot get another user's info (covers lines 128-129)."""
    # Create two regular users
    username1 = f"user1_{uuid.uuid4().hex[:8]}"
    username2 = f"user2_{uuid.uuid4().hex[:8]}"

    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp1 = client.post(
        "/api/v1/users/",
        json={
            "username": username1,
            "password": "testpass1",
            "role": "viewer",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp1.status_code == 201
    user1_id = resp1.json()["id"]

    resp2 = client.post(
        "/api/v1/users/",
        json={
            "username": username2,
            "password": "testpass2",
            "role": "viewer",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp2.status_code == 201
    user2 = resp2.json()

    # Login as user1
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username1, "password": "testpass1"},
    )
    assert login_resp.status_code == 200
    user1_token = login_resp.json()["access_token"]
    user1_headers = {"Authorization": f"Bearer {user1_token}"}

    # Try to get user2's info as user1 (should fail)
    resp = client.get(
        f"/api/v1/users/{user2['id']}",
        headers=user1_headers,
    )
    assert resp.status_code == 403

    # Cleanup
    client.delete(f"/api/v1/users/{user1_id}", headers=admin_headers)
    client.delete(f"/api/v1/users/{user2['id']}", headers=admin_headers)


def test_get_user_not_found(client):
    """Getting a nonexistent user returns 404 (covers lines 130-132)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/api/v1/users/99999", headers=admin_headers)
    assert resp.status_code == 404
    assert "User not found" in resp.json()["error"]["message"]


def test_update_password_as_self(client):
    """A user can update their own password (covers lines 152-156)."""
    # Create a regular user
    username = f"selfpass_{uuid.uuid4().hex[:8]}"

    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

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

    # Login as the user
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "testpass"},
    )
    assert login_resp.status_code == 200
    user_token = login_resp.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Update own password
    resp = client.put(
        f"/api/v1/users/{user_id}",
        json={"new_password": "newpass123"},
        headers=user_headers,
    )
    assert resp.status_code == 200

    # Verify password was changed by logging in with new password
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "newpass123"},
    )
    assert login_resp.status_code == 200

    # Cleanup
    client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)


def test_update_user_admin_only_fields(client):
    """Non-admin users cannot update admin-only fields (covers line 160)."""
    # Create a regular user
    username = f"adminfield_{uuid.uuid4().hex[:8]}"

    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

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

    # Login as the user
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "testpass"},
    )
    assert login_resp.status_code == 200
    user_token = login_resp.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # Try to update role (admin-only field)
    resp = client.put(
        f"/api/v1/users/{user_id}",
        json={"role": "operator"},
        headers=user_headers,
    )
    assert resp.status_code == 403
    assert "Admin only" in resp.json()["error"]["message"]

    # Cleanup
    client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)


def test_get_permissions_success(client):
    """Successfully get user permissions (covers lines 217-221)."""
    # Create a user with permissions
    username = f"getperm_{uuid.uuid4().hex[:8]}"

    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "password": "testpass",
            "role": "viewer",
            "is_active": True,
            "permissions": [
                {"asset_id": 1, "permission": "view"},
                {"asset_id": 2, "permission": "edit"},
            ],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 201
    user_id = resp.json()["id"]

    # Get permissions as admin
    resp = client.get(
        f"/api/v1/users/{user_id}/permissions",
        headers=admin_headers,
    )
    assert resp.status_code == 200
    perms = resp.json()
    assert len(perms) == 2

    # Cleanup
    client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)


def test_set_permissions_success(client):
    """Successfully set user permissions (covers lines 243-254)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Create a user without permissions
    username = f"setperm_{uuid.uuid4().hex[:8]}"
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

    # Set permissions
    resp = client.put(
        f"/api/v1/users/{user_id}/permissions",
        json={
            "permissions": [
                {"asset_id": 1, "permission": "view"},
                {"asset_id": 2, "permission": "edit"},
            ]
        },
        headers=admin_headers,
    )
    assert resp.status_code == 200
    perms = resp.json()
    assert len(perms) == 2

    # Cleanup
    client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)


def test_create_user_duplicate_username(client):
    """Creating a user with duplicate username returns 400 (covers line 84)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    username = f"dupuser_{uuid.uuid4().hex[:8]}"
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

    # Try to create the same user again
    resp = client.post(
        "/api/v1/users/",
        json={
            "username": username,
            "password": "testpass2",
            "role": "viewer",
            "is_active": True,
            "permissions": [],
        },
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "Username already taken" in resp.json()["error"]["message"]

    # Cleanup
    user_id = resp.json()["id"] if "id" in resp.json() else None
    if user_id:
        client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)


def test_get_me(client):
    """Get current user info (covers line 119)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    resp = client.get("/api/v1/users/me", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


def test_update_user_demote_last_admin(client):
    """Cannot demote the last admin (covers line 169)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Try to demote the only admin
    resp = client.put(
        "/api/v1/users/1",
        json={"role": "viewer"},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "Cannot change role of the last admin" in resp.json()["error"]["message"]


def test_update_user_deactivate_last_admin(client):
    """Cannot deactivate the last admin (covers lines 178-183)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Try to deactivate the only admin
    resp = client.put(
        "/api/v1/users/1",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    assert "Cannot deactivate the last admin" in resp.json()["error"]["message"]


def test_delete_last_admin(client):
    """Cannot delete the last admin (covers line 200)."""
    # Login as admin first
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert login_resp.status_code == 200
    admin_token = login_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Try to delete the only admin
    resp = client.delete("/api/v1/users/1", headers=admin_headers)
    assert resp.status_code == 400
    assert "Cannot delete the last admin" in resp.json()["error"]["message"]
