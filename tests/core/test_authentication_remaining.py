# -*- coding: utf-8 -*-
"""Additional tests for core/authentication.py remaining components."""

import pytest  # noqa: F401  # Imported for test setup

from core.authentication import (
    ABACPolicy,
    ComplianceFramework,
    ComplianceManager,
    JWTAuthService,
    SSOProvider,
    TenantContext,
    create_access_token,
    create_refresh_token,
    refresh_access_token,
)


def test_refresh_access_token_round_trip():
    refresh = create_refresh_token({"sub": "admin"})
    new_access = refresh_access_token(refresh)
    assert isinstance(new_access, str)
    assert refresh_access_token("invalid") is None
    assert refresh_access_token(create_access_token({"sub": "admin"})) is None


@pytest.mark.asyncio
async def test_jwt_auth_service_token_and_role():
    service = JWTAuthService()
    token = service.create_access_token({"sub": "admin"})
    assert isinstance(token, str)
    assert await service.verify_role({"role": "admin"}, "admin") is True
    assert await service.verify_role({"role": "user"}, "admin") is False


@pytest.mark.asyncio
async def test_tenant_context():
    ctx = TenantContext()
    config = await ctx.get_tenant_config("t1")
    assert config["tenant_id"] == "t1"
    assert await ctx.validate_tenant_access("t1", "u1") is True


@pytest.mark.asyncio
async def test_abac_policy_evaluate_access():
    policy = ABACPolicy()
    assert await policy.evaluate_access({"role": "admin"}, "metrics", "read") is True
    assert await policy.evaluate_access({"role": "viewer"}, "alerts", "read") is True
    assert await policy.evaluate_access({"role": "viewer"}, "alerts", "delete") is False
    assert await policy.evaluate_access({"role": "unknown"}, "alerts", "read") is False


@pytest.mark.asyncio
async def test_sso_provider():
    provider = SSOProvider()
    user = await provider.authenticate_with_sso("oidc", "token")
    assert user is not None
    assert user["provider"] == "oidc"
    assert await provider.authenticate_with_sso("saml", "token") is None
    link = await provider.generate_sso_link("oidc", "https://app/callback")
    assert link is not None
    assert "https://oidc.example.com" in link


@pytest.mark.asyncio
async def test_compliance_manager():
    manager = ComplianceManager()
    await manager.log_audit_event("login", "admin", "auth", "read")
    result = await manager.run_compliance_check(
        ComplianceFramework.ISO27001
    )  # noqa: F841  # Variable for test verification
    assert result["overall_status"] == "pass"
    report = await manager.get_audit_report()
    assert report["total_events"] == 1
    assert report["summary"]["by_user"]["admin"] == 1
