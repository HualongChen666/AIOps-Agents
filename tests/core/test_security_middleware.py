# -*- coding: utf-8 -*-
"""Tests for core/security_middleware.py."""

from unittest.mock import MagicMock

import pytest  # noqa: F401  # Imported for test setup
from starlette.responses import Response

from core.security_middleware import (
    MFAManager,
    PasswordPolicy,
    RateLimiter,
    SecurityHeaders,
    TLSEnforcer,
)


def test_password_policy():
    valid, _ = PasswordPolicy.validate_password("MyStrongP@ss1")
    assert valid is True
    invalid, msg = PasswordPolicy.validate_password("weak")
    assert invalid is False
    assert "at least" in msg or "12" in msg


def test_password_hash_and_verify():
    hashed = PasswordPolicy.hash_password("MyStrongP@ss1!")
    assert PasswordPolicy.verify_password("MyStrongP@ss1!", hashed) is True
    assert PasswordPolicy.verify_password("wrong", hashed) is False


def test_mfa_manager():
    mfa = MFAManager()
    mfa.enable_mfa()
    assert mfa._mfa_enabled is True
    mfa.disable_mfa()
    assert mfa._mfa_enabled is False
    assert mfa.verify_totp("user", "123456") is True  # MFA disabled


def test_totp_secret():
    pytest.importorskip("pyotp")
    mfa = MFAManager()
    secret = mfa.generate_totp_secret("user")
    assert len(secret) > 0
    assert mfa._totp_secret_cache["user"] == secret


def test_rate_limiter():
    limiter = RateLimiter()
    limiter._max_requests = 1
    allowed, _ = limiter.check_rate_limit("client1")
    assert allowed is True
    allowed, retry = limiter.check_rate_limit("client1")
    assert allowed is False
    assert isinstance(retry, int)


def test_security_headers():
    response = Response()
    updated = SecurityHeaders.add_security_headers(response)
    assert updated.headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in updated.headers


def test_tls_enforcer():
    enforcer = TLSEnforcer(enforce_tls=True)
    secure_request = MagicMock()
    secure_request.url.scheme = "https"
    assert enforcer.check_tls(secure_request) is True
    insecure_request = MagicMock()
    insecure_request.url.scheme = "http"
    assert enforcer.check_tls(insecure_request) is False
