# -*- coding: utf-8 -*-
"""Real endpoint tests for core/authentication.py APIRouter (api coverage)."""

import sys
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 如果其他测试已经把 core.authentication 替换成 Mock，先删掉强制重新加载真实模块
if isinstance(sys.modules.get("core.authentication"), Mock):
    del sys.modules["core.authentication"]

import core.authentication as _auth  # noqa: E402


@pytest.fixture
def auth_globals(monkeypatch):
    """Pin JWT settings so tests can create/verify tokens deterministically."""
    monkeypatch.setattr(_auth, "SECRET_KEY", "test-secret-key", raising=False)
    monkeypatch.setattr(_auth, "JWT_ISSUER", "test-issuer", raising=False)
    monkeypatch.setattr(_auth, "JWT_AUDIENCE", "test-audience", raising=False)
    monkeypatch.setattr(_auth, "ALGORITHM", "HS256", raising=False)
    monkeypatch.setattr(_auth, "ACCESS_TOKEN_EXPIRE_MINUTES", 30, raising=False)
    monkeypatch.setattr(_auth, "_get_redis_client", lambda: None, raising=False)
    monkeypatch.setattr(_auth, "verify_password", lambda _plain, _hashed: True)


@pytest.fixture
def client(auth_globals):
    app = FastAPI()
    app.include_router(_auth.router)
    return TestClient(app)


def _make_user(role: str = "user"):
    return _auth.UserInDB(
        username="testuser",
        hashed_password="fakehashed",
        role=role,
        disabled=False,
    )


class TestAuthenticationRouter:
    """Tests for /auth/token and /auth/revoke."""

    def test_login_success(self, client, monkeypatch):
        user = _make_user()
        monkeypatch.setattr(_auth, "get_user_by_username", lambda _username: user)
        response = client.post("/auth/token", data={"username": "testuser", "password": "pass"})
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_failure(self, client, monkeypatch):
        monkeypatch.setattr(_auth, "get_user_by_username", lambda _username: None)
        monkeypatch.setattr(_auth, "get_user", lambda _username: None)
        response = client.post("/auth/token", data={"username": "bad", "password": "pass"})
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_revoke_token(self, client, monkeypatch):
        user = _make_user()
        monkeypatch.setattr(_auth, "get_user_by_username", lambda _username: user)
        monkeypatch.setattr(_auth, "get_user", AsyncMock(return_value=user))
        monkeypatch.setattr(_auth, "is_token_revoked", AsyncMock(return_value=False))
        token = _auth.create_access_token(data={"sub": "testuser", "role": "user"})
        response = client.post(
            "/auth/revoke", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert "revoked successfully" in response.json()["detail"]

    def test_is_ip_allowed(self, monkeypatch):
        monkeypatch.setattr(_auth, "ALLOWED_LOCAL_IPS", ["127.0.0.1"])
        assert _auth.is_ip_allowed("127.0.0.1") is True
        assert _auth.is_ip_allowed("10.0.0.1") is False

    def test_password_hash_and_verify(self):
        hashed = _auth.pwd_context.hash("secret")
        assert _auth.pwd_context.verify("secret", hashed) is True
        assert _auth.pwd_context.verify("wrong", hashed) is False
