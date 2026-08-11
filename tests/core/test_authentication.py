# -*- coding: utf-8 -*-
"""Unit tests for core/authentication.py."""

from datetime import timedelta

import pytest

from core.authentication import (
    JWTAuthService,
    create_access_token,
    create_refresh_token,
    hash_password,
    is_ip_allowed,
    validate_password_complexity,
    verify_password,
    verify_token,
)


def test_password_hash_and_verify():
    plain = "admin123"
    hashed = hash_password(plain)
    assert verify_password(plain, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_validate_password_complexity():
    ok, _ = validate_password_complexity("Strong1!")
    assert isinstance(ok, bool)


def test_access_token_round_trip():
    token = create_access_token({"sub": "admin"}, expires_delta=timedelta(minutes=5))
    assert isinstance(token, str)
    payload = verify_token(token)
    assert payload is not None
    assert payload.get("sub") == "admin"


def test_refresh_token_creation():
    token = create_refresh_token({"sub": "admin"})
    assert isinstance(token, str)


def test_is_ip_allowed():
    assert isinstance(is_ip_allowed("127.0.0.1"), bool)


@pytest.mark.asyncio
async def test_jwt_auth_service(client):
    service = JWTAuthService()
    token = service.create_access_token({"sub": "admin"})
    assert token is not None
    user = await service.authenticate_user("admin", "admin123")
    if user is not None:
        assert service.verify_role(user, "admin") is True
