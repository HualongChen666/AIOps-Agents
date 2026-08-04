# -*- coding: utf-8 -*-
"""Real endpoint tests for core/authentication.py APIRouter."""

from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.authentication import create_access_token, router, UserInDB


@pytest.fixture
def auth_globals(monkeypatch):
    """Pin JWT settings so tests can create/verify tokens deterministically."""
    monkeypatch.setattr("core.authentication.SECRET_KEY", "test-secret-key", raising=False)
    monkeypatch.setattr("core.authentication.JWT_ISSUER", "test-issuer", raising=False)
    monkeypatch.setattr("core.authentication.JWT_AUDIENCE", "test-audience", raising=False)
    monkeypatch.setattr("core.authentication.ALGORITHM", "HS256", raising=False)
    monkeypatch.setattr("core.authentication.ACCESS_TOKEN_EXPIRE_MINUTES", 30, raising=False)
    monkeypatch.setattr("core.authentication._get_redis_client", lambda: None, raising=False)
    monkeypatch.setattr("core.authentication.verify_password", lambda _plain, _hashed: True)


@pytest.fixture
def client(auth_globals):
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


def _make_user(role: str = "user"):
    return UserInDB(
        username="testuser",
        hashed_password="fakehashed",
        role=role,
        disabled=False,
    )


class TestAuthenticationRouter:
    """Tests for /auth/token and /auth/revoke."""

    def test_login_success(self, client, monkeypatch):
        user = _make_user()
        monkeypatch.setattr("core.authentication.get_user_by_username", lambda _username: user)
        response = client.post("/auth/token", data={"username": "testuser", "password": "pass"})
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_failure(self, client, monkeypatch):
        monkeypatch.setattr("core.authentication.get_user_by_username", lambda _username: None)
        monkeypatch.setattr("core.authentication.get_user", lambda _username: None)
        response = client.post("/auth/token", data={"username": "bad", "password": "pass"})
        assert response.status_code == 401
        assert "Incorrect username or password" in response.json()["detail"]

    def test_revoke_token(self, client, monkeypatch):
        user = _make_user()
        monkeypatch.setattr("core.authentication.get_user_by_username", lambda _username: user)
        monkeypatch.setattr("core.authentication.get_user", AsyncMock(return_value=user))
        monkeypatch.setattr("core.authentication.is_token_revoked", AsyncMock(return_value=False))
        token = create_access_token(data={"sub": "testuser", "role": "user"})
        response = client.post(
            "/auth/revoke", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert "revoked successfully" in response.json()["detail"]
