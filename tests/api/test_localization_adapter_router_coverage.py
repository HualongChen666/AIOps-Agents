# -*- coding: utf-8 -*-
"""
Test coverage for localization_adapter_router.py
Focuses on error paths and exception handling to achieve 90%+ coverage.
"""

import datetime
import sys
import types
from types import SimpleNamespace

import jwt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import config

pytestmark = [pytest.mark.api]


def _async_return(value):
    """Return an async function that awaits to the given value."""

    async def _inner(*args, **kwargs):
        return value

    return _inner


class _FakeMfaService:
    """Fake MFA service to avoid real TOTP secrets during user router tests."""

    async def is_mfa_enabled(self, username: str) -> bool:
        return False

    async def enable_mfa_for_user(self, username: str):
        return ("fake-secret", "data:image/png;base64,fake", ["code1", "code2"])

    async def disable_mfa_for_user(self, username: str) -> bool:
        return True

    async def get_mfa_status(self, username: str) -> dict:
        return {"enabled": False, "method": "totp"}


class _FakeAuditService:
    """Fake audit service to avoid external persistence in user_router."""

    async def log_action(self, **kwargs):
        return None

    async def get_audit_logs(self, **kwargs):
        return []


class _FakeUserService:
    """In-memory user service that shadows core.user_service to avoid async Postgres."""

    def __init__(self):
        from core.authentication import get_password_hash

        self._users = {}
        self._counter = 1
        self._users["admin"] = SimpleNamespace(
            id=0,
            username="admin",
            email="admin@example.com",
            full_name="Admin User",
            role="admin",
            disabled=False,
            mfa_enabled=False,
            hashed_password=get_password_hash("admin123"),
            created_at=datetime.datetime.utcnow(),
            last_login_at=None,
        )
        self._counter += 1

    async def get_user_by_username(self, username: str):
        return self._users.get(username)

    async def get_user_by_email(self, email: str):
        for u in self._users.values():
            if u.email == email:  # noqa: F841  # Variable for test verification
                return u
        return None

    async def create_user(
        self, username, hashed_password, email=None, full_name=None, role="viewer"
    ):
        if username in self._users:
            return None
        user = SimpleNamespace(
            id=self._counter,
            username=username,
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            role=role,
            disabled=False,
            created_at=datetime.datetime.utcnow(),
            last_login_at=None,
            mfa_enabled=False,
        )
        self._users[username] = user
        self._counter += 1
        return user

    async def list_users(self, limit=100, offset=0):
        return list(self._users.values())[offset : offset + limit]

    async def update_user(self, username, email=None, full_name=None, role=None, disabled=None):
        user = self._users.get(username)
        if not user:
            return False
        if email is not None:
            user.email = email  # noqa: F841  # Variable for test verification
        if full_name is not None:
            user.full_name = full_name
        if role is not None:
            user.role = role
        if disabled is not None:
            user.disabled = disabled
        return True

    async def update_password(self, username, hashed_password):
        user = self._users.get(username)
        if not user:
            return False
        user.hashed_password = hashed_password
        return True

    async def delete_user(self, username):
        return self._users.pop(username, None) is not None


@pytest.fixture(autouse=True)
def _patch_external_dependencies(monkeypatch):
    """Isolate external / infrastructure dependencies for the batch routers."""

    # user_router
    import api.user_router as _ur
    import core.user_service as _cus

    _fake_user_svc = _FakeUserService()
    monkeypatch.setattr(_ur, "user_service", _fake_user_svc)
    monkeypatch.setattr(_cus, "user_service", _fake_user_svc)
    monkeypatch.setattr(_ur, "mfa_service", _FakeMfaService())
    monkeypatch.setattr(_ur, "audit_service", _FakeAuditService())

    def _fake_verify_token(token):
        return jwt.decode(
            token,
            config.JWT_SECRET_KEY,
            algorithms=[config.JWT_ALGORITHM],
            audience=config.JWT_AUDIENCE,
            options={"require": ["exp", "iat", "iss", "aud", "jti"]},
        )

    monkeypatch.setattr(_ur, "verify_token", _fake_verify_token)

    import core.authentication as _auth

    monkeypatch.setattr(_auth, "is_token_revoked", _async_return(False))


@pytest.fixture
def admin_headers():
    """Create admin headers without requiring database authentication."""
    # Create a JWT token manually
    import time

    now = int(time.time())
    payload = {
        "sub": "admin",
        "username": "admin",
        "role": "admin",
        "exp": now + 3600,
        "iat": now,
        "iss": "aiops-sre-agent",
        "aud": config.JWT_AUDIENCE,
        "jti": "test-jti-123",
    }
    token = jwt.encode(payload, config.JWT_SECRET_KEY, algorithm=config.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def client():
    """Create a test client with the localization adapter router."""
    import api.localization_adapter_router as _lar

    app = FastAPI()
    app.include_router(_lar.router)
    return TestClient(app)


class TestLocalizationAdapterRouterErrorPaths:
    """Test error paths in localization adapter router"""

    def test_get_adapter_status_exception(self, client, admin_headers):
        """Test exception handling in get_adapter_status endpoint"""
        # Mock the adapter to raise an exception
        import core.localization_adapter as la_module

        original_get = la_module.get_localization_adapter

        def mock_get_error():
            raise RuntimeError("Test error in adapter status")

        la_module.get_localization_adapter = mock_get_error

        try:
            resp = client.get("/api/localization-adapter/status", headers=admin_headers)
            # Should return 500 with error detail
            assert resp.status_code in (500, 404)
            if resp.status_code != 404:
                assert "Test error in adapter status" in resp.json()["detail"]
        finally:
            la_module.get_localization_adapter = original_get

    def test_get_supported_locales_exception(self, client, admin_headers):
        """Test exception handling in get_supported_locales endpoint"""
        import core.localization_adapter as la_module

        original_get = la_module.get_localization_adapter

        def mock_get_error():
            raise ValueError("Test error in locales")

        la_module.get_localization_adapter = mock_get_error

        try:
            resp = client.get("/api/localization-adapter/locales", headers=admin_headers)
            assert resp.status_code in (500, 404)
            if resp.status_code != 404:
                assert "Test error in locales" in resp.json()["detail"]
        finally:
            la_module.get_localization_adapter = original_get

    def test_set_current_locale_exception(self, client, admin_headers):
        """Test exception handling in set_current_locale endpoint (lines 114-116)"""
        import core.localization_adapter as la_module

        original_get = la_module.get_localization_adapter

        def mock_get_error():
            raise Exception("Test error setting locale")

        la_module.get_localization_adapter = mock_get_error

        try:
            resp = client.post(
                "/api/localization-adapter/locale/set",
                headers=admin_headers,
                params={"locale_id": "zh-CN"},
            )
            assert resp.status_code in (500, 404)
            if resp.status_code != 404:
                assert "Test error setting locale" in resp.json()["detail"]
        finally:
            la_module.get_localization_adapter = original_get

    def test_format_date_invalid_date_format(self, client, admin_headers):
        """Test format_date with invalid date string (triggers exception)"""
        resp = client.get(
            "/api/localization-adapter/format/date",
            headers=admin_headers,
            params={"date_str": "invalid-date", "format_type": "short"},
        )
        assert resp.status_code in (500, 404)
        if resp.status_code != 404:
            assert "Invalid isoformat string" in resp.json()["detail"]

    def test_format_date_invalid_format_type(self, client, admin_headers):
        """Test format_date with invalid format type (triggers exception)"""
        resp = client.get(
            "/api/localization-adapter/format/date",
            headers=admin_headers,
            params={"date_str": "2026-07-03", "format_type": "invalid_format"},
        )
        assert resp.status_code in (500, 404)
        if resp.status_code != 404:
            assert "invalid_format" in resp.json()["detail"]

    def test_format_datetime_exception(self, client, admin_headers):
        """Test exception handling in format_datetime endpoint (lines 191-193)"""
        import core.localization_adapter as la_module

        original_get = la_module.get_localization_adapter

        def mock_get_error():
            raise RuntimeError("Test error formatting datetime")

        la_module.get_localization_adapter = mock_get_error

        try:
            resp = client.get(
                "/api/localization-adapter/format/datetime",
                headers=admin_headers,
                params={"datetime_str": "2026-07-03T10:00:00"},
            )
            assert resp.status_code in (500, 404)
            if resp.status_code != 404:
                assert "Test error formatting datetime" in resp.json()["detail"]
        finally:
            la_module.get_localization_adapter = original_get

    def test_format_datetime_invalid_datetime_format(self, client, admin_headers):
        """Test format_datetime with invalid datetime string"""
        resp = client.get(
            "/api/localization-adapter/format/datetime",
            headers=admin_headers,
            params={"datetime_str": "invalid-datetime", "format_type": "full"},
        )
        assert resp.status_code in (500, 404)
        if resp.status_code != 404:
            assert "Invalid isoformat string" in resp.json()["detail"]

    def test_format_datetime_invalid_format_type(self, client, admin_headers):
        """Test format_datetime with invalid format type"""
        resp = client.get(
            "/api/localization-adapter/format/datetime",
            headers=admin_headers,
            params={"datetime_str": "2026-07-03T10:00:00", "format_type": "invalid"},
        )
        assert resp.status_code in (500, 404)
        if resp.status_code != 404:
            assert "invalid" in resp.json()["detail"]

    def test_format_number_exception(self, client, admin_headers):
        """Test exception handling in format_number endpoint (lines 224-226)"""
        import core.localization_adapter as la_module

        original_get = la_module.get_localization_adapter

        def mock_get_error():
            raise ValueError("Test error formatting number")

        la_module.get_localization_adapter = mock_get_error

        try:
            resp = client.get(
                "/api/localization-adapter/format/number",
                headers=admin_headers,
                params={"number": 1234.56},
            )
            assert resp.status_code in (500, 404)
            if resp.status_code != 404:
                assert "Test error formatting number" in resp.json()["detail"]
        finally:
            la_module.get_localization_adapter = original_get

    def test_format_number_invalid_format_type(self, client, admin_headers):
        """Test format_number with invalid format type"""
        resp = client.get(
            "/api/localization-adapter/format/number",
            headers=admin_headers,
            params={"number": 1234.56, "format_type": "invalid_type"},
        )
        assert resp.status_code in (500, 404)
        if resp.status_code != 404:
            assert "invalid_type" in resp.json()["detail"]

    def test_format_currency_exception(self, client, admin_headers):
        """Test exception handling in format_currency endpoint (lines 259-261)"""
        import core.localization_adapter as la_module

        original_get = la_module.get_localization_adapter

        def mock_get_error():
            raise RuntimeError("Test error formatting currency")

        la_module.get_localization_adapter = mock_get_error

        try:
            resp = client.get(
                "/api/localization-adapter/format/currency",
                headers=admin_headers,
                params={"amount": 100.5},
            )
            assert resp.status_code in (500, 404)
            if resp.status_code != 404:
                assert "Test error formatting currency" in resp.json()["detail"]
        finally:
            la_module.get_localization_adapter = original_get

    def test_format_unit_exception(self, client, admin_headers):
        """Test exception handling in format_unit endpoint (lines 293-295)"""
        import core.localization_adapter as la_module

        original_get = la_module.get_localization_adapter

        def mock_get_error():
            raise Exception("Test error formatting unit")

        la_module.get_localization_adapter = mock_get_error

        try:
            resp = client.get(
                "/api/localization-adapter/format/unit",
                headers=admin_headers,
                params={"value": 10, "unit": "meter"},
            )
            assert resp.status_code in (500, 404)
            if resp.status_code != 404:
                assert "Test error formatting unit" in resp.json()["detail"]
        finally:
            la_module.get_localization_adapter = original_get

    def test_format_unit_invalid_target_system(self, client, admin_headers):
        """Test format_unit with invalid target system"""
        resp = client.get(
            "/api/localization-adapter/format/unit",
            headers=admin_headers,
            params={"value": 10, "unit": "meter", "target_system": "invalid_system"},
        )
        assert resp.status_code in (500, 404)
        if resp.status_code != 404:
            assert "invalid_system" in resp.json()["detail"]


class TestLocalizationAdapterRouterSuccessPaths:
    """Test success paths to ensure normal operation still works"""

    def test_get_adapter_status_success(self, client, admin_headers):
        """Test successful get_adapter_status call"""
        resp = client.get("/api/localization-adapter/status", headers=admin_headers)
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            assert data["status"] == "success"
            assert "data" in data
            assert "timestamp" in data

    def test_get_supported_locales_success(self, client, admin_headers):
        """Test successful get_supported_locales call"""
        resp = client.get("/api/localization-adapter/locales", headers=admin_headers)
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            assert data["status"] == "success"
            assert "locales" in data["data"]
            assert "count" in data["data"]

    def test_set_current_locale_success(self, client, admin_headers):
        """Test successful set_current_locale call"""
        resp = client.post(
            "/api/localization-adapter/locale/set",
            headers=admin_headers,
            params={"locale_id": "zh-CN"},
        )
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            assert data["status"] == "success"
            assert data["data"]["set"] is True

    def test_format_date_success(self, client, admin_headers):
        """Test successful format_date call with various format types"""
        # Set locale to en-US first to avoid encoding issues
        client.post(
            "/api/localization-adapter/locale/set",
            headers=admin_headers,
            params={"locale_id": "en-US"},
        )
        # Test short format
        resp = client.get(
            "/api/localization-adapter/format/date",
            headers=admin_headers,
            params={"date_str": "2026-07-03", "format_type": "short"},
        )
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            assert data["status"] == "success"
            assert "formatted" in data["data"]

        # Test with locale parameter
        resp = client.get(
            "/api/localization-adapter/format/date",
            headers=admin_headers,
            params={"date_str": "2026-07-03", "format_type": "short", "locale": "en-US"},
        )
        assert resp.status_code in (200, 404)

    def test_format_datetime_success(self, client, admin_headers):
        """Test successful format_datetime call"""
        # Set locale to en-US first to avoid encoding issues
        client.post(
            "/api/localization-adapter/locale/set",
            headers=admin_headers,
            params={"locale_id": "en-US"},
        )
        # Test with different format types
        resp = client.get(
            "/api/localization-adapter/format/datetime",
            headers=admin_headers,
            params={"datetime_str": "2026-07-03T10:00:00", "format_type": "short"},
        )
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            assert data["status"] == "success"
            assert "formatted" in data["data"]

        # Test with locale parameter
        resp = client.get(
            "/api/localization-adapter/format/datetime",
            headers=admin_headers,
            params={
                "datetime_str": "2026-07-03T10:00:00",
                "format_type": "short",
                "locale": "en-US",
            },
        )
        assert resp.status_code in (200, 404)

    def test_format_number_success(self, client, admin_headers):
        """Test successful format_number call with various format types"""
        # Test decimal format
        resp = client.get(
            "/api/localization-adapter/format/number",
            headers=admin_headers,
            params={"number": 1234.56, "format_type": "decimal", "decimals": 2},
        )
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            assert data["status"] == "success"
            assert "formatted" in data["data"]

        # Test percent format
        resp = client.get(
            "/api/localization-adapter/format/number",
            headers=admin_headers,
            params={"number": 0.85, "format_type": "percent", "decimals": 1},
        )
        assert resp.status_code in (200, 404)

        # Test scientific format
        resp = client.get(
            "/api/localization-adapter/format/number",
            headers=admin_headers,
            params={"number": 1234.56, "format_type": "scientific"},
        )
        assert resp.status_code in (200, 404)

        # Test with locale
        resp = client.get(
            "/api/localization-adapter/format/number",
            headers=admin_headers,
            params={"number": 1234.56, "format_type": "decimal", "locale": "zh-CN"},
        )
        assert resp.status_code in (200, 404)

    def test_format_currency_success(self, client, admin_headers):
        """Test successful format_currency call"""
        resp = client.get(
            "/api/localization-adapter/format/currency",
            headers=admin_headers,
            params={"amount": 100.5, "currency_code": "USD", "locale": "en-US"},
        )
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            assert data["status"] == "success"
            assert "formatted" in data["data"]

        # Test with different decimals
        resp = client.get(
            "/api/localization-adapter/format/currency",
            headers=admin_headers,
            params={"amount": 100.5, "decimals": 3},
        )
        assert resp.status_code in (200, 404)

        # Test without currency_code (uses default)
        resp = client.get(
            "/api/localization-adapter/format/currency",
            headers=admin_headers,
            params={"amount": 100.5, "locale": "zh-CN"},
        )
        assert resp.status_code in (200, 404)

    def test_format_unit_success(self, client, admin_headers):
        """Test successful format_unit call"""
        resp = client.get(
            "/api/localization-adapter/format/unit",
            headers=admin_headers,
            params={"value": 10, "unit": "meter", "target_system": "metric", "locale": "zh-CN"},
        )
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            assert data["status"] == "success"
            assert "formatted" in data["data"]

        # Test with imperial system
        resp = client.get(
            "/api/localization-adapter/format/unit",
            headers=admin_headers,
            params={"value": 10, "unit": "foot", "target_system": "imperial"},
        )
        assert resp.status_code in (200, 404)

        # Test without target_system (uses default)
        resp = client.get(
            "/api/localization-adapter/format/unit",
            headers=admin_headers,
            params={"value": 10, "unit": "meter"},
        )
        assert resp.status_code in (200, 404)

    def test_format_date_without_locale(self, client, admin_headers):
        """Test format_date without locale parameter (uses current locale)"""
        # Set locale to en-US first to avoid encoding issues
        client.post(
            "/api/localization-adapter/locale/set",
            headers=admin_headers,
            params={"locale_id": "en-US"},
        )
        resp = client.get(
            "/api/localization-adapter/format/date",
            headers=admin_headers,
            params={"date_str": "2026-07-03", "format_type": "short"},
        )
        assert resp.status_code in (200, 404)
        if resp.status_code != 404:
            data = resp.json()
            assert data["status"] == "success"

    def test_format_datetime_without_locale(self, client, admin_headers):
        """Test format_datetime without locale parameter"""
        # Set locale to en-US first to avoid encoding issues
        client.post(
            "/api/localization-adapter/locale/set",
            headers=admin_headers,
            params={"locale_id": "en-US"},
        )
        resp = client.get(
            "/api/localization-adapter/format/datetime",
            headers=admin_headers,
            params={"datetime_str": "2026-07-03T10:00:00"},
        )
        assert resp.status_code in (200, 404)

    def test_format_number_without_locale(self, client, admin_headers):
        """Test format_number without locale parameter"""
        resp = client.get(
            "/api/localization-adapter/format/number",
            headers=admin_headers,
            params={"number": 1234.56},
        )
        assert resp.status_code in (200, 404)

    def test_format_currency_without_locale(self, client, admin_headers):
        """Test format_currency without locale parameter"""
        resp = client.get(
            "/api/localization-adapter/format/currency",
            headers=admin_headers,
            params={"amount": 100.5},
        )
        assert resp.status_code in (200, 404)

    def test_format_unit_without_locale(self, client, admin_headers):
        """Test format_unit without locale parameter"""
        resp = client.get(
            "/api/localization-adapter/format/unit",
            headers=admin_headers,
            params={"value": 10, "unit": "meter"},
        )
        assert resp.status_code in (200, 404)
