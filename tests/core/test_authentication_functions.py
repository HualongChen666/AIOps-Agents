# -*- coding: utf-8 -*-
"""Targeted tests for core.authentication pure/helper functions and P2 classes."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

import core.authentication as auth


class _FakePwdContext:
    """Lightweight CryptContext stand-in for unit tests."""

    def hash(self, secret: str) -> str:
        return f"hashed:{secret[:72]}"

    def verify(self, secret: str, hash_value: str) -> bool:
        return hash_value == f"hashed:{secret[:72]}"


@pytest.fixture(autouse=True)
def _disable_redis(monkeypatch) -> None:
    """Keep Redis out of authentication tests by returning a None client."""
    monkeypatch.setattr(auth, "_get_redis_client", lambda: None)
    monkeypatch.setattr(auth, "redis_client", None)
    monkeypatch.setattr(auth, "_redis_available", False)
    monkeypatch.setattr(auth, "pwd_context", _FakePwdContext())


@pytest.fixture
def valid_password() -> str:
    return "StrongPass1!"


class TestEnvironmentHelpers:
    def test_parse_int_with_default(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_INT", "42")
        assert auth._parse_int_with_default("TEST_INT", 0) == 42
        assert auth._parse_int_with_default("MISSING_INT", 7) == 7
        monkeypatch.setenv("TEST_INT_BAD", "not-a-number")
        assert auth._parse_int_with_default("TEST_INT_BAD", 3) == 3

    def test_get_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("ENVIRONMENT", "PRODUCTION")
        assert auth._get_environment() == "production"


class TestPasswordHelpers:
    def test_validate_password_complexity(self) -> None:
        assert auth.validate_password_complexity("StrongPass1!") == (True, "")
        assert auth.validate_password_complexity("short1!")[0] is False
        assert auth.validate_password_complexity("nouppercase1!")[0] is False
        assert auth.validate_password_complexity("NOLOWERCASE1!")[0] is False
        assert auth.validate_password_complexity("NoDigits!aaa")[0] is False
        assert auth.validate_password_complexity("NoSpecial1aaa")[0] is False
        assert auth.validate_password_complexity("Password123!")[0] is False

    def test_hash_and_verify_password(self, valid_password: str) -> None:
        hashed = auth.hash_password(valid_password)
        assert auth.verify_password(valid_password, hashed) is True
        assert auth.verify_password("wrong", hashed) is False
        assert auth.get_password_hash(valid_password) == hashed


class TestIPWhitelist:
    def test_is_ip_allowed_empty(self, monkeypatch) -> None:
        monkeypatch.setattr(auth, "ALLOWED_LOCAL_IPS", [])
        assert auth.is_ip_allowed("127.0.0.1") is False

    def test_is_ip_allowed_wildcard(self, monkeypatch) -> None:
        monkeypatch.setattr(auth, "ALLOWED_LOCAL_IPS", ["*"])
        assert auth.is_ip_allowed("127.0.0.1") is True

    def test_is_ip_allowed_exact(self, monkeypatch) -> None:
        monkeypatch.setattr(auth, "ALLOWED_LOCAL_IPS", ["192.168.1.1"])
        assert auth.is_ip_allowed("192.168.1.1") is True
        assert auth.is_ip_allowed("192.168.1.2") is False

    def test_is_ip_allowed_cidr(self, monkeypatch) -> None:
        monkeypatch.setattr(auth, "ALLOWED_LOCAL_IPS", ["10.0.0.0/8"])
        assert auth.is_ip_allowed("10.0.0.5") is True
        assert auth.is_ip_allowed("192.168.1.1") is False

    def test_is_ip_allowed_empty_ip(self) -> None:
        assert auth.is_ip_allowed("") is False


class TestTokenLifecycle:
    def test_create_and_verify_access_token(self) -> None:
        token = auth.create_access_token({"sub": "user1", "role": "user"})
        payload = auth.verify_token(token)
        assert payload is not None
        assert payload["sub"] == "user1"
        assert payload["type"] == "access"
        assert payload["jti"] is not None

    def test_verify_invalid_token(self) -> None:
        assert auth.verify_token("not.a.token") is None

    def test_create_and_refresh_token(self) -> None:
        refresh = auth.create_refresh_token({"sub": "user1"})
        access = auth.refresh_access_token(refresh)
        assert access is not None
        assert auth.verify_token(access) is not None

    def test_refresh_access_token_with_access_token_fails(self) -> None:
        access = auth.create_access_token({"sub": "user1"})
        assert auth.refresh_access_token(access) is None

    def test_refresh_access_token_invalid(self) -> None:
        assert auth.refresh_access_token("bad.token") is None

    @pytest.mark.asyncio
    async def test_revoke_and_check_token(self) -> None:
        token = auth.create_access_token({"sub": "user1"})
        await auth.revoke_token(token)
        assert await auth.is_token_revoked(token) is True

    @pytest.mark.asyncio
    async def test_revoke_invalid_token(self) -> None:
        await auth.revoke_token("not.a.token")
        assert await auth.is_token_revoked("not.a.token") is False

    @pytest.mark.asyncio
    async def test_is_token_revoked_in_memory_expires(self, monkeypatch) -> None:
        monkeypatch.setattr(auth, "_token_blacklist", {})
        token = auth.create_access_token({"sub": "user1"})
        await auth.revoke_token(token)
        # Force the blacklist entry to be older than 1 hour
        auth._token_blacklist[token] = datetime.now(timezone.utc) - timedelta(hours=2)
        assert await auth.is_token_revoked(token) is False


class TestCurrentUser:
    @pytest.mark.asyncio
    async def test_get_current_user(self, monkeypatch) -> None:
        token = auth.create_access_token({"sub": "user1", "role": "user"})
        user = auth.UserInDB(
            id=1,
            username="user1",
            role="user",
            hashed_password="hashed",
            disabled=False,
        )
        monkeypatch.setattr(auth, "get_user", AsyncMock(return_value=user))
        result = await auth.get_current_user(token)
        assert result.username == "user1"

    @pytest.mark.asyncio
    async def test_get_current_user_revoked(self) -> None:
        token = auth.create_access_token({"sub": "user1", "role": "user"})
        with patch.object(auth, "is_token_revoked", AsyncMock(return_value=True)):
            with pytest.raises(auth.HTTPException) as exc:
                await auth.get_current_user(token)
            assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_invalid(self) -> None:
        with pytest.raises(auth.HTTPException):
            await auth.get_current_user("bad.token")

    @pytest.mark.asyncio
    async def test_get_current_active_user(self) -> None:
        user = auth.User(username="u", disabled=False, role="user")
        assert (await auth.get_current_active_user(user)).username == "u"

        disabled_user = auth.User(username="u", disabled=True, role="user")
        with pytest.raises(auth.HTTPException):
            await auth.get_current_active_user(disabled_user)

    def test_verify_ip_whitelist(self) -> None:
        request = MagicMock()
        request.client.host = "127.0.0.1"
        auth.verify_ip_whitelist(request)

    @pytest.mark.asyncio
    async def test_role_required(self) -> None:
        admin = auth.User(username="admin", disabled=False, role="admin")
        verifier = auth.role_required("admin")
        assert (await verifier(current_user=admin)).role == "admin"


class TestJWTAuthService:
    def test_create_access_token(self) -> None:
        token = auth.auth_service.create_access_token({"sub": "user1"}, expires_delta=300)
        payload = jwt.decode(
            token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM], audience=auth.JWT_AUDIENCE
        )
        assert payload["sub"] == "user1"

    @pytest.mark.asyncio
    async def test_get_current_user(self, monkeypatch) -> None:
        token = auth.auth_service.create_access_token({"sub": "user1"})
        monkeypatch.setattr(auth, "is_token_revoked", AsyncMock(return_value=False))
        user = auth.UserInDB(
            username="user1", role="user", hashed_password="hashed", disabled=False
        )
        monkeypatch.setattr(auth, "get_user", AsyncMock(return_value=user))
        result = await auth.auth_service.get_current_user(token)
        assert result is not None
        assert result["username"] == "user1"

    @pytest.mark.asyncio
    async def test_get_current_user_revoked(self, monkeypatch) -> None:
        token = auth.auth_service.create_access_token({"sub": "user1"})
        monkeypatch.setattr(auth, "is_token_revoked", AsyncMock(return_value=True))
        assert await auth.auth_service.get_current_user(token) is None

    @pytest.mark.asyncio
    async def test_get_current_user_invalid(self) -> None:
        assert await auth.auth_service.get_current_user("bad") is None

    @pytest.mark.asyncio
    async def test_verify_permission(self) -> None:
        assert await auth.auth_service.verify_permission({"role": "admin"}, auth.Permission.READ)
        assert (
            await auth.auth_service.verify_permission({"role": "user"}, auth.Permission.ADMIN)
            is False
        )

    @pytest.mark.asyncio
    async def test_verify_role(self) -> None:
        assert await auth.auth_service.verify_role({"role": "admin"}, "admin")
        assert await auth.auth_service.verify_role({"role": "user"}, "admin") is False

    @pytest.mark.asyncio
    async def test_authenticate_user(self, monkeypatch) -> None:
        user = auth.UserInDB(username="u", role="user", hashed_password="hashed", disabled=False)
        monkeypatch.setattr(auth, "authenticate_user", lambda u, p: user)
        result = await auth.auth_service.authenticate_user("u", "p")
        assert result is not None
        assert result["username"] == "u"


class TestPydanticModels:
    def test_token_model(self) -> None:
        t = auth.Token(access_token="abc")
        assert t.token_type == "bearer"

    def test_user_models(self) -> None:
        u = auth.User(username="u")
        udb = auth.UserInDB(**u.model_dump(), hashed_password="hp")
        assert udb.hashed_password == "hp"


class TestTenantContext:
    @pytest.mark.asyncio
    async def test_get_tenant_config(self) -> None:
        config = await auth.tenant_context.get_tenant_config("t1")
        assert config["tenant_id"] == "t1"
        # Cached on second call
        assert (await auth.tenant_context.get_tenant_config("t1"))["tenant_id"] == "t1"

    @pytest.mark.asyncio
    async def test_validate_tenant_access(self) -> None:
        assert await auth.tenant_context.validate_tenant_access("t1", "u1") is True


class TestABACPolicy:
    @pytest.mark.asyncio
    async def test_evaluate_access(self) -> None:
        assert await auth.abac_policy.evaluate_access({"role": "admin"}, "alerts", "read") is True
        assert await auth.abac_policy.evaluate_access({"role": "viewer"}, "alerts", "read") is True
        assert (
            await auth.abac_policy.evaluate_access({"role": "viewer"}, "alerts", "write") is False
        )
        assert (
            await auth.abac_policy.evaluate_access({"role": "operator"}, "metrics", "execute")
            is True
        )
        assert (
            await auth.abac_policy.evaluate_access({"role": "operator"}, "unknown", "execute")
            is False
        )

    def test_match_resource(self) -> None:
        assert auth.abac_policy._match_resource("alerts", ["alerts", "metrics"])
        assert auth.abac_policy._match_resource("alerts", "alerts")
        assert auth.abac_policy._match_resource("alerts", "metrics") is False
        assert auth.abac_policy._match_resource("alerts", "*")


class TestSSOProvider:
    @pytest.mark.asyncio
    async def test_authenticate_with_sso(self) -> None:
        result = await auth.sso_provider.authenticate_with_sso("oidc", "tok")
        assert result is not None
        assert result["provider"] == "oidc"
        assert await auth.sso_provider.authenticate_with_sso("saml", "tok") is None

    @pytest.mark.asyncio
    async def test_generate_sso_link(self) -> None:
        link = await auth.sso_provider.generate_sso_link("oidc", "http://app/cb")
        assert link is not None and "oidc" in link
        assert await auth.sso_provider.generate_sso_link("saml", "http://app/cb") is None


class TestComplianceManager:
    @pytest.mark.asyncio
    async def test_log_audit_event(self) -> None:
        await auth.compliance_manager.log_audit_event(
            "login", "u1", "alerts", "read", {"ip": "127.0.0.1"}
        )
        assert len(auth.compliance_manager.audit_logs) == 1

    @pytest.mark.asyncio
    async def test_run_compliance_check(self) -> None:
        result = await auth.compliance_manager.run_compliance_check(
            auth.ComplianceFramework.ISO27001
        )
        assert result["framework"] == "iso27001"
        assert result["overall_status"] == "pass"

    @pytest.mark.asyncio
    async def test_run_compliance_check_unsupported(self) -> None:
        result = await auth.compliance_manager.run_compliance_check(auth.ComplianceFramework.HIPAA)
        assert result["overall_status"] == "fail"

    @pytest.mark.asyncio
    async def test_get_audit_report(self) -> None:
        cm = auth.ComplianceManager()
        await cm.log_audit_event("login", "u1", "alerts", "read")
        await cm.log_audit_event("login", "u1", "alerts", "read")
        await cm.log_audit_event("logout", "u2", "metrics", "write")
        report = await cm.get_audit_report()
        assert report["total_events"] == 3
        assert report["summary"]["by_user"]["u1"] == 2
        assert report["summary"]["by_user"]["u2"] == 1
        assert report["summary"]["by_event_type"]["login"] == 2

    @pytest.mark.asyncio
    async def test_get_audit_report_with_dates(self) -> None:
        cm = auth.ComplianceManager()
        now = datetime.now(timezone.utc)
        await cm.log_audit_event("login", "u1", "alerts", "read")
        report = await cm.get_audit_report(now - timedelta(hours=1), now + timedelta(hours=1))
        assert report["total_events"] == 1

    def test_generate_audit_summary(self) -> None:
        logs = [
            {"event_type": "login", "user_id": "u1", "resource": "alerts"},
            {"event_type": "login", "user_id": "u1", "resource": "alerts"},
        ]
        summary = auth.compliance_manager._generate_audit_summary(logs)
        assert summary["by_event_type"]["login"] == 2

    @pytest.mark.asyncio
    async def test_audit_log_rotation(self, monkeypatch) -> None:
        cm = auth.ComplianceManager()
        monkeypatch.setattr(cm, "audit_logs", [])
        for i in range(10002):
            await cm.log_audit_event("e", f"u{i}", "r", "a")
        assert len(cm.audit_logs) == 10000
