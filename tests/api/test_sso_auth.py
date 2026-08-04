# -*- coding: utf-8 -*-
"""Real endpoint tests for core/sso_auth.py APIRouter (counted under api coverage)."""

import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.modules["core.authentication"] = MagicMock()

from core import sso_auth  # noqa: E402
from core.sso_auth import router  # noqa: E402


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestSSOAuthRouter:
    """Tests for the three SSO auth endpoints."""

    def test_login_when_sso_disabled(self, client, monkeypatch):
        monkeypatch.setattr(sso_auth, "SSO_ENABLED", False, raising=False)
        response = client.get("/auth/login")
        assert response.status_code == 400
        assert "SSO not configured" in response.json()["detail"]

    def test_login_when_sso_enabled(self, client, monkeypatch):
        monkeypatch.setattr(sso_auth, "SSO_ENABLED", True, raising=False)
        fake_oidc = SimpleNamespace(
            authorize_redirect=AsyncMock(
                return_value=__import__(
                    "fastapi.responses", fromlist=["RedirectResponse"]
                ).RedirectResponse(url="https://idp.example/authorize")
            )
        )
        monkeypatch.setattr(sso_auth.oauth, "oidc", fake_oidc, raising=False)
        response = client.get("/auth/login", follow_redirects=False)
        assert response.status_code == 307
        assert "https://idp.example/authorize" in response.headers["location"]

    def test_callback_invalid_state(self, client, monkeypatch):
        monkeypatch.setattr(sso_auth, "SSO_ENABLED", True, raising=False)
        response = client.get("/auth/callback?state=invalid")
        assert response.status_code == 400
        assert "Invalid state parameter" in response.json()["detail"]

    def test_callback_success(self, client, monkeypatch):
        monkeypatch.setattr(sso_auth, "SSO_ENABLED", True, raising=False)
        monkeypatch.setattr(
            sso_auth,
            "_state_store",
            {"valid-state": datetime.now(timezone.utc) - timedelta(minutes=1)},
            raising=False,
        )
        fake_oidc = SimpleNamespace(
            authorize_access_token=AsyncMock(
                return_value={
                    "userinfo": {
                        "preferred_username": "sso_user",
                        "email": "sso@example.com",
                        "name": "SSO User",
                    }
                }
            )
        )
        monkeypatch.setattr(sso_auth.oauth, "oidc", fake_oidc, raising=False)
        monkeypatch.setattr(
            sso_auth, "create_access_token", lambda data, expires_delta=None: "test-token"
        )
        response = client.get("/auth/callback?state=valid-state", follow_redirects=False)
        assert response.status_code == 307
        assert "/login_success?token=test-token" in response.headers["location"]

    def test_callback_expired_state(self, client, monkeypatch):
        monkeypatch.setattr(sso_auth, "SSO_ENABLED", True, raising=False)
        monkeypatch.setattr(
            sso_auth,
            "_state_store",
            {"old-state": datetime.now(timezone.utc) - timedelta(minutes=10)},
            raising=False,
        )
        response = client.get("/auth/callback?state=old-state")
        assert response.status_code == 400
        assert "expired" in response.json()["detail"]

    def test_callback_oauth_error(self, client, monkeypatch):
        monkeypatch.setattr(sso_auth, "SSO_ENABLED", True, raising=False)
        monkeypatch.setattr(
            sso_auth,
            "_state_store",
            {"err-state": datetime.now(timezone.utc) - timedelta(minutes=1)},
            raising=False,
        )

        class FakeOAuthError(Exception):
            def __init__(self):
                self.error = "invalid_grant"

        monkeypatch.setattr(sso_auth, "OAuthError", FakeOAuthError, raising=False)
        fake_oidc = SimpleNamespace(
            authorize_access_token=AsyncMock(side_effect=FakeOAuthError())
        )
        monkeypatch.setattr(sso_auth.oauth, "oidc", fake_oidc, raising=False)
        response = client.get("/auth/callback?state=err-state")
        assert response.status_code == 400

    def test_callback_missing_userinfo(self, client, monkeypatch):
        monkeypatch.setattr(sso_auth, "SSO_ENABLED", True, raising=False)
        monkeypatch.setattr(
            sso_auth,
            "_state_store",
            {"no-userinfo-state": datetime.now(timezone.utc) - timedelta(minutes=1)},
            raising=False,
        )
        fake_oidc = SimpleNamespace(
            authorize_access_token=AsyncMock(return_value={"access_token": "abc"})
        )
        monkeypatch.setattr(sso_auth.oauth, "oidc", fake_oidc, raising=False)
        response = client.get("/auth/callback?state=no-userinfo-state")
        assert response.status_code == 400

    def test_login_success(self, client):
        response = client.get("/auth/login_success?token=abc123")
        assert response.status_code == 200
        assert "abc123" in response.text
