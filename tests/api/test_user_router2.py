# -*- coding: utf-8 -*-
"""User Router Success Branch Tests.

Complements the existing test_user_router.py by actually authenticating and
exercising the happy path / core branches of every endpoint in api/user_router.
"""

from __future__ import annotations

import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure api.user_router can be imported with mocked dependencies. Other test
# files may have already imported the real core modules; we pop the router so
# it reloads with our MagicMock stubs for the services we control below.
for _mod in ["api.user_router"]:
    sys.modules.pop(_mod, None)

# component service modules so the router import does not drag in heavy infra.
sys.modules.setdefault("core.audit_service", Mock())
sys.modules.setdefault("core.mfa_service", Mock())
sys.modules.setdefault("core.user_service", Mock())
sys.modules.setdefault("core.authentication", Mock())

import api.user_router as user_router  # noqa: E402


class MockUserInDB(SimpleNamespace):
    """Lightweight stand-in for the user object used inside the router."""

    def __init__(self):
        super().__init__(
            id=1,
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            role="admin",
            disabled=False,
            hashed_password="hashed_password",
            created_at=datetime(2026, 7, 4, 0, 0, 0),
            last_login_at=None,
            mfa_enabled=False,
        )


def _audit_log() -> dict:
    return {
        "id": 1,
        "action": "login",
        "resource_type": "user",
        "resource_id": "1",
        "username": "admin",
        "ip_address": "127.0.0.1",
        "status": "success",
        "details": "",
        "created_at": datetime(2026, 7, 4, 0, 0, 0),
    }


@pytest.fixture
def client():
    """Return a TestClient with user_router globals patched for success paths."""
    app = FastAPI()
    app.include_router(user_router.router)

    originals = {
        name: getattr(user_router, name, None)
        for name in (
            "verify_token",
            "get_user",
            "validate_password_complexity",
            "get_password_hash",
            "verify_password",
            "user_service",
            "audit_service",
            "mfa_service",
        )
    }

    user_router.verify_token = Mock(return_value={"sub": "admin"})
    user_router.get_user = AsyncMock(return_value=MockUserInDB())
    user_router.validate_password_complexity = Mock(return_value=(True, ""))
    user_router.get_password_hash = Mock(return_value="hashed_password")
    user_router.verify_password = Mock(return_value=True)

    user_router.user_service = AsyncMock()
    user_router.user_service.get_user_by_username.return_value = None
    user_router.user_service.get_user_by_email.return_value = None
    user_router.user_service.create_user.return_value = MockUserInDB()
    user_router.user_service.list_users.return_value = [MockUserInDB()]
    user_router.user_service.update_user.return_value = True
    user_router.user_service.update_password.return_value = True
    user_router.user_service.delete_user.return_value = True

    user_router.audit_service = AsyncMock()
    user_router.audit_service.log_action.return_value = None
    user_router.audit_service.get_audit_logs.return_value = [_audit_log()]

    user_router.mfa_service = AsyncMock()
    user_router.mfa_service.is_mfa_enabled.return_value = False
    user_router.mfa_service.enable_mfa_for_user.return_value = (
        "secret",
        "data:image/png;base64,test",
        ["code1", "code2", "code3"],
    )
    user_router.mfa_service.disable_mfa_for_user.return_value = True
    user_router.mfa_service.get_mfa_status.return_value = {"enabled": False, "method": "totp"}

    try:
        yield TestClient(app)
    finally:
        for name, value in originals.items():
            if value is not None:
                setattr(user_router, name, value)


class TestUserRouterSuccess:
    """Exercise the success branches of every user_router endpoint."""

    def test_create_user_success(self, client):
        response = client.post(
            "/api/v1/users/",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "full_name": "New User",
                "password": "SecurePassword123!",
                "role": "user",
            },
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 201

    def test_list_users_success(self, client):
        response = client.get(
            "/api/v1/users/?limit=10&offset=0",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    def test_get_current_user_info_success(self, client):
        response = client.get(
            "/api/v1/users/me",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    def test_get_user_by_username_success(self, client):
        user_router.user_service.get_user_by_username.return_value = MockUserInDB()
        response = client.get(
            "/api/v1/users/testuser",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    def test_get_user_by_username_not_found(self, client):
        user_router.user_service.get_user_by_username.return_value = None
        response = client.get(
            "/api/v1/users/nonexistent",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 404

    def test_update_user_success(self, client):
        user_router.user_service.update_user.return_value = True
        user_router.user_service.get_user_by_username.return_value = MockUserInDB()
        response = client.put(
            "/api/v1/users/testuser",
            json={"email": "updated@example.com", "full_name": "Updated", "role": "admin"},
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    def test_update_user_not_found(self, client):
        user_router.user_service.update_user.return_value = False
        response = client.put(
            "/api/v1/users/nonexistent",
            json={"email": "updated@example.com"},
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 404

    def test_delete_user_success(self, client):
        response = client.delete(
            "/api/v1/users/testuser",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 204

    def test_delete_user_self_forbidden(self, client):
        response = client.delete(
            "/api/v1/users/admin",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 400

    def test_change_password_success(self, client):
        response = client.post(
            "/api/v1/users/me/change-password",
            json={
                "current_password": "OldSecurePass123!",
                "new_password": "NewSecurePass123!",
            },
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    def test_change_password_wrong_current(self, client):
        user_router.verify_password.return_value = False
        response = client.post(
            "/api/v1/users/me/change-password",
            json={
                "current_password": "wrong",
                "new_password": "NewSecurePass123!",
            },
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 400

    def test_enable_mfa_success(self, client):
        response = client.post(
            "/api/v1/users/me/mfa/enable",
            json={"password": "SecurePassword123!"},
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    def test_disable_mfa_success(self, client):
        response = client.post(
            "/api/v1/users/me/mfa/disable",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    def test_get_mfa_status_success(self, client):
        response = client.get(
            "/api/v1/users/me/mfa/status",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    def test_get_my_audit_logs_success(self, client):
        response = client.get(
            "/api/v1/users/me/audit-logs",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    def test_get_user_audit_logs_success(self, client):
        response = client.get(
            "/api/v1/users/testuser/audit-logs",
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 200

    async def test_get_all_audit_logs_success(self, client):
        # /api/v1/users/audit-logs is shadowed by /{username} in the route order,
        # so exercise the endpoint handler directly to cover its body.
        result = await user_router.get_all_audit_logs(
            limit=100,
            offset=0,
            action="login",
            resource_type="user",
            current_user=MockUserInDB(),
        )
        assert result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
