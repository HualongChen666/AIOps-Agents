# -*- coding: utf-8 -*-
"""Real-branch coverage tests for core/authentication.py.

These tests exercise the actual authentication helpers and JWTAuthService
against the real in-memory SQLite test database and real environment state.
No mocks or stubs are used.
"""

import asyncio
import importlib
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import HTTPException

import core.authentication as auth
from core.user_service import user_service


def test_pwd_context_schemes_and_default_scheme():
    """Exercise the bcrypt compatibility wrapper's reporting methods."""
    assert auth.pwd_context.schemes() == ["bcrypt"]
    assert auth.pwd_context.default_scheme() == "bcrypt"


def test_hash_and_verify_password_edge_cases():
    """Real bcrypt hashing and edge cases for verify_password."""
    assert auth.hash_password("") == ""
    assert auth.verify_password("x", "") is False
    assert auth.verify_password("", "irrelevant") is False

    hashed = auth.hash_password("StrongPass123!")
    assert hashed
    assert auth.verify_password("StrongPass123!", hashed) is True
    assert auth.verify_password("wrong", hashed) is False
    assert auth.verify_password("x", "not-a-valid-hash") is False


def test_validate_password_complexity_branches():
    """Cover every password-complexity failure branch."""
    assert auth.validate_password_complexity("short1!") == (
        False,
        "密码长度至少需要12个字符",
    )
    assert auth.validate_password_complexity("lowercase123!") == (
        False,
        "密码必须包含至少1个大写字母",
    )
    assert auth.validate_password_complexity("UPPERCASE123!") == (
        False,
        "密码必须包含至少1个小写字母",
    )
    assert auth.validate_password_complexity("Uppercase!!!") == (
        False,
        "密码必须包含至少1个数字",
    )
    assert auth.validate_password_complexity("Password123!") == (
        False,
        "密码过于简单，请使用更复杂的密码",
    )
    assert auth.validate_password_complexity("StrongPass123!")[0] is True


def test_is_ip_allowed_wildcard_and_empty(monkeypatch):
    """Wildcard allows any IP; empty client IP is rejected."""
    monkeypatch.setenv("IP_WHITELIST", "*")
    assert auth.is_ip_allowed("anything") is True
    assert auth.is_ip_allowed("") is False


def test_is_ip_allowed_invalid_network(monkeypatch):
    """Invalid client IP / malformed CIDR exercise the ipaddress exception path."""
    monkeypatch.setenv("IP_WHITELIST", "bad/24")
    assert auth.is_ip_allowed("not-an-ip") is False


def test_module_secret_initialization_branches(monkeypatch):
    """Reload the module with various secret env combos to cover top-level branches."""
    original_secret = auth.SECRET_KEY

    try:
        # insecure default in production -> first-try ValueError
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.setenv("JWT_SECRET_KEY", "default-secret-key")
        with pytest.raises(ValueError):
            importlib.reload(auth)

        # no secret in development -> fallback generation (except-block path)
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
        importlib.reload(auth)
        assert auth.SECRET_KEY
        generated_key = auth.SECRET_KEY

        # real secret in development -> uses it, covers the empty-secret false branch
        monkeypatch.setenv("JWT_SECRET_KEY", "real-test-secret-key-for-tests")
        importlib.reload(auth)
        assert auth.SECRET_KEY == "real-test-secret-key-for-tests"

        # insecure default in development -> log warning, set secret
        monkeypatch.setenv("JWT_SECRET_KEY", "default-secret-key")
        importlib.reload(auth)
        assert auth.SECRET_KEY == "default-secret-key"
    finally:
        # Restore the test environment and module state.
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.setenv("JWT_SECRET_KEY", "test-secret-key")
        importlib.reload(auth)
        assert auth.SECRET_KEY == "test-secret-key"


def test_create_access_token_empty_data():
    """Empty payload returns an empty string instead of encoding."""
    assert auth.create_access_token({}) == ""


def test_verify_token_edge_cases():
    """Cover type validation, empty jti, expired and malformed tokens."""
    assert auth.verify_token("") is None
    assert auth.verify_token("not.a.token") is None

    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=5)
    iat = now

    def _make(overrides):
        payload = {
            "sub": "admin",
            "exp": exp,
            "iat": iat,
            "iss": auth.JWT_ISSUER,
            "aud": auth.JWT_AUDIENCE,
            "type": "access",
            "jti": "unique-jti",
        }
        payload.update(overrides)
        return jwt.encode(payload, auth.SECRET_KEY, algorithm=auth.ALGORITHM)

    # wrong type
    assert auth.verify_token(_make({"type": "other"})) is None
    # empty jti present but falsy
    assert auth.verify_token(_make({"jti": ""})) is None
    # valid token
    assert auth.verify_token(_make({})) is not None
    # expired token
    assert auth.verify_token(_make({"exp": now - timedelta(minutes=1)})) is None


def test_create_refresh_token_with_expires_delta():
    """Refresh token accepts a custom timedelta."""
    token = auth.create_refresh_token(
        {"sub": "admin"}, expires_delta=timedelta(days=1)
    )
    assert token
    payload = auth.verify_token(token)
    assert payload and payload["type"] == "refresh"


def test_refresh_access_token_round_trip_and_invalid():
    """Refresh an access token; non-refresh tokens are rejected."""
    refresh = auth.create_refresh_token({"sub": "admin"})
    new_access = auth.refresh_access_token(refresh)
    assert isinstance(new_access, str)
    assert auth.verify_token(new_access) is not None

    access = auth.create_access_token({"sub": "admin"})
    assert auth.refresh_access_token(access) is None
    assert auth.refresh_access_token("invalid") is None


def test_get_user_and_authenticate_real_db():
    """Real DB-backed user lookup and authentication."""
    admin = asyncio.run(auth.get_user("admin"))
    assert admin is not None
    assert admin.username == "admin"

    by_name = auth.get_user_by_username("admin")
    assert by_name is not None
    assert by_name.username == "admin"
    assert auth.get_user_by_username("does-not-exist") is None

    assert auth.authenticate_user("admin", "admin123") is not None
    assert auth.authenticate_user("admin", "wrong") is None
    assert auth.authenticate_user("does-not-exist", "x") is None


def test_authenticate_user_disabled():
    """Create a disabled user and ensure authentication rejects them."""
    existing = asyncio.run(user_service.get_user_by_username("disabled_user"))
    if not existing:
        asyncio.run(
            user_service.create_user(
                username="disabled_user",
                hashed_password=auth.hash_password("ValidPass123!"),
                role="user",
                disabled=True,
            )
        )

    assert auth.authenticate_user("disabled_user", "ValidPass123!") is None


async def test_get_current_user_valid_expired_and_unknown():
    """Exercise get_current_user success, expiry and missing-user branches."""
    auth._token_blacklist.clear()

    token = auth.create_access_token({"sub": "admin", "role": "admin"})
    user = await auth.get_current_user(token=token)
    assert user.username == "admin"

    expired = auth.create_access_token(
        {"sub": "admin"}, expires_delta=timedelta(seconds=-1)
    )
    with pytest.raises(HTTPException):
        await auth.get_current_user(token=expired)

    unknown = auth.create_access_token({"sub": "nobody"})
    with pytest.raises(HTTPException):
        await auth.get_current_user(token=unknown)


async def test_get_current_user_revoked():
    """A revoked token causes get_current_user to raise."""
    auth._token_blacklist.clear()
    token = auth.create_access_token({"sub": "admin"})
    await auth.revoke_token(token)

    with pytest.raises(HTTPException) as exc:
        await auth.get_current_user(token=token)
    assert "revoked" in exc.value.detail.lower()


async def test_get_current_active_user_branches():
    """Current-user path raises for disabled users and returns active users."""
    active = await auth.get_current_active_user(
        current_user=auth.User(username="active", disabled=False)
    )
    assert active.username == "active"

    with pytest.raises(HTTPException) as exc:
        await auth.get_current_active_user(
            current_user=auth.User(username="inactive", disabled=True)
        )
    assert "Inactive user" in exc.value.detail


async def test_get_current_active_user_token_branch_returns_none():
    """Token path returns None when get_user_by_username is unavailable."""
    token = auth.create_access_token({"sub": "admin", "role": "admin"})
    result = await auth.get_current_active_user(token=token)
    assert result is None


async def test_revoke_and_check_token_lifecycle():
    """Revoke a real token and verify it is blacklisted in memory."""
    auth._token_blacklist.clear()
    token = auth.create_access_token({"sub": "admin"})
    assert await auth.is_token_revoked(token) is False

    await auth.revoke_token(token)
    assert token in auth._token_blacklist
    assert await auth.is_token_revoked(token) is True


async def test_revoke_token_without_expiry():
    """Tokens without an expiration are not added to the blacklist."""
    auth._token_blacklist.clear()
    no_exp = jwt.encode(
        {
            "sub": "admin",
            "iat": datetime.now(timezone.utc),
            "iss": auth.JWT_ISSUER,
            "aud": auth.JWT_AUDIENCE,
            "type": "access",
            "jti": "jti-no-exp",
        },
        auth.SECRET_KEY,
        algorithm=auth.ALGORITHM,
    )
    await auth.revoke_token(no_exp)
    assert no_exp not in auth._token_blacklist


async def test_is_token_revoked_stale_entries():
    """Stale token and jti entries are pruned from the in-memory blacklist."""
    auth._token_blacklist.clear()
    token = auth.create_access_token({"sub": "admin"})
    payload = auth._decode_for_revocation(token)
    jti = payload["jti"]

    # Stale token entry
    auth._token_blacklist[token] = datetime.now(timezone.utc) - timedelta(hours=2)
    assert await auth.is_token_revoked(token) is False
    assert token not in auth._token_blacklist

    # Stale jti entry
    auth._token_blacklist[f"jti:{jti}"] = datetime.now(timezone.utc) - timedelta(
        hours=2
    )
    assert await auth.is_token_revoked(token) is False
    assert f"jti:{jti}" not in auth._token_blacklist


async def test_jwt_auth_service():
    """Real DB-backed JWTAuthService token and permission checks."""
    service = auth.JWTAuthService()
    token = service.create_access_token({"sub": "admin", "role": "admin"})
    assert token

    user = await service.get_current_user(token)
    assert user is not None
    assert user["username"] == "admin"

    assert await service.verify_role(user, "admin") is True
    assert await service.verify_role(user, "user") is False
    assert await service.verify_permission(user, auth.Permission.ADMIN) is True
    assert await service.verify_permission(user, auth.Permission.WRITE) is True

    user_user = {"role": "user"}
    assert await service.verify_permission(user_user, auth.Permission.READ) is True
    assert await service.verify_permission(user_user, auth.Permission.ADMIN) is False


async def test_abac_policy_remaining_branches():
    """ABAC loop continuation and non-list/non-wildcard resource matching."""
    policy = auth.ABACPolicy()
    # operator attributes match but resource doesn't -> loop continues
    assert await policy.evaluate_access({"role": "operator"}, "dashboards", "read") is False

    assert policy._match_resource("x", "*") is True
    assert policy._match_resource("alerts", ["alerts", "metrics"]) is True
    assert policy._match_resource("alerts", "metrics") is False
    assert policy._match_resource("alerts", "alerts") is True


async def test_tenant_context_validate_access():
    """Tenant access returns True for a real cached tenant config."""
    ctx = auth.TenantContext()
    assert await ctx.validate_tenant_access("t1", "u1") is True


async def test_compliance_manager_audit_overflow():
    """Audit log is truncated to 10,000 entries."""
    mgr = auth.ComplianceManager()
    for i in range(10001):
        await mgr.log_audit_event("login", f"user_{i}", "auth", "read")
    assert len(mgr.audit_logs) == 10000
    assert mgr.audit_logs[0]["user_id"] != "user_0"
