# -*- coding: utf-8 -*-
"""Tests for core/authentication.py helper functions and classes."""

from core.authentication import (
    ABACPolicy,
    ComplianceFramework,
    ComplianceManager,
    SSOProvider,
    TenantContext,
    create_access_token,
    create_refresh_token,
    hash_password,
    is_ip_allowed,
    refresh_access_token,
    validate_password_complexity,
    verify_password,
    verify_token,
)


def test_is_ip_allowed(monkeypatch):
    monkeypatch.setenv("IP_WHITELIST", "127.0.0.1,192.168.1.0/24")
    assert is_ip_allowed("127.0.0.1") is True
    assert is_ip_allowed("192.168.1.55") is True
    assert is_ip_allowed("10.0.0.1") is False
    assert is_ip_allowed("") is False


def test_validate_password_complexity():
    assert validate_password_complexity("Short1!")[0] is False
    assert validate_password_complexity("ValidPassword123![39;49;00m")[0] is True
    assert validate_password_complexity("password")[0] is False


def test_hash_and_verify_password():
    hashed = hash_password("ValidPassword123![39;49;00m")
    assert hashed
    assert verify_password("ValidPassword123![39;49;00m", hashed) is True
    assert verify_password("wrong", hashed) is False
    assert verify_password("", "") is False


def test_create_and_verify_access_token():
    token = create_access_token({"sub": "admin"})
    assert token
    payload = verify_token(token)
    assert payload is not None
    assert payload["sub"] == "admin"
    assert payload["type"] == "access"


def test_verify_invalid_token():
    assert verify_token("") is None
    assert verify_token("not.a.token") is None


def test_refresh_access_token():
    refresh = create_refresh_token({"sub": "admin"})
    new_access = refresh_access_token(refresh)
    assert new_access
    assert verify_token(new_access) is not None
    assert refresh_access_token("invalid") is None


async def test_tenant_context():
    ctx = TenantContext()
    config = await ctx.get_tenant_config("t1")
    assert config["tenant_id"] == "t1"
    assert await ctx.validate_tenant_access("t1", "u1") is True


async def test_abac_policy():
    policy = ABACPolicy()
    assert await policy.evaluate_access({"role": "admin"}, "alerts", "delete") is True
    assert await policy.evaluate_access({"role": "viewer"}, "alerts", "read") is True
    assert await policy.evaluate_access({"role": "viewer"}, "alerts", "delete") is False
    assert await policy.evaluate_access({"role": "operator"}, "repairs", "execute") is True


async def test_sso_provider():
    sso = SSOProvider()
    assert await sso.authenticate_with_sso("oidc", "tok") is not None
    assert await sso.authenticate_with_sso("saml", "tok") is None
    link = await sso.generate_sso_link("oidc", "http://app/cb")
    assert link and "oidc" in link


async def test_compliance_manager():
    mgr = ComplianceManager()
    await mgr.log_audit_event("login", "u1", "auth", "read")
    assert len(mgr.audit_logs) == 1
    result = await mgr.run_compliance_check(ComplianceFramework.ISO27001)  # noqa: F841  # Variable for test verification
    assert result["framework"] == "iso27001"
    assert result["overall_status"] == "pass"
