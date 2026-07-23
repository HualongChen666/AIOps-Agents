# -*- coding: utf-8 -*-
"""测试增强认证集成模块"""

import hashlib

import pytest

from core.enhanced_auth_integration import (
    AccessPolicy,
    AuthMethod,
    AuthToken,
    EnhancedAuthIntegration,
    Permission,
    Role,
    User,
    get_enhanced_auth_integration,
)


def _hash_password(username: str, password: str) -> str:
    return hashlib.sha256(f"{username}:{password}".encode()).hexdigest()


@pytest.fixture
def auth():
    return EnhancedAuthIntegration(
        config={
            "jwt_secret": "test-secret",
            "jwt_access_token_expire": 30,
            "auth_methods": ["jwt", "api_key"],
        }
    )


@pytest.fixture
def sample_user():
    return User(
        user_id="u1",
        username="alice",
        email="alice@example.com",
        roles={Role.OPERATOR},
        metadata={"password_hash": _hash_password("alice", "password123")},
    )


class TestEnhancedAuthIntegration:
    """测试 EnhancedAuthIntegration 核心方法"""

    def test_init_default_config(self):
        auth = EnhancedAuthIntegration()
        assert auth.jwt_algorithm == "HS256"
        assert AuthMethod.JWT in auth.auth_methods

    def test_register_user(self, auth):
        user = User(user_id="u2", username="bob", email="bob@example.com")
        auth.register_user(user)
        assert auth.users["u2"] is user

    def test_authenticate_user_success(self, auth, sample_user):
        auth.register_user(sample_user)
        token = auth.authenticate_user("alice", "password123")
        assert token is not None
        assert isinstance(token, AuthToken)

    def test_authenticate_user_wrong_password(self, auth, sample_user):
        auth.register_user(sample_user)
        assert auth.authenticate_user("alice", "wrong") is None

    def test_authenticate_user_not_found(self, auth):
        assert auth.authenticate_user("missing", "pw") is None

    def test_authenticate_inactive_user(self, auth, sample_user):
        sample_user.is_active = False
        auth.register_user(sample_user)
        assert auth.authenticate_user("alice", "password123") is None

    def test_verify_token(self, auth, sample_user):
        auth.register_user(sample_user)
        token = auth.authenticate_user("alice", "password123")
        user = auth.verify_token(token.token)
        assert user is not None
        assert user.user_id == "u1"

    def test_verify_invalid_token(self, auth):
        assert auth.verify_token("not.a.token") is None

    def test_refresh_token(self, auth, sample_user):
        auth.register_user(sample_user)
        token = auth.authenticate_user("alice", "password123")
        new_token = auth.refresh_token(token.refresh_token)
        assert new_token is not None

    def test_refresh_token_with_access_token_fails(self, auth, sample_user):
        auth.register_user(sample_user)
        token = auth.authenticate_user("alice", "password123")
        assert auth.refresh_token(token.token) is None

    def test_revoke_token(self, auth, sample_user):
        auth.register_user(sample_user)
        token = auth.authenticate_user("alice", "password123")
        assert auth.revoke_token(token.token) is True
        assert auth.revoke_token(token.token) is False

    def test_check_permission_direct(self, auth):
        user = User(
            user_id="u3",
            username="carol",
            email="carol@example.com",
            permissions={Permission.READ},
        )
        assert auth.check_permission(user, Permission.READ, "metrics") is True
        assert auth.check_permission(user, Permission.WRITE, "metrics") is False

    def test_check_permission_role_based(self, auth):
        user = User(user_id="u4", username="dave", email="dave@example.com", roles={Role.ADMIN})
        auth.register_user(user)
        # Admin role mapping includes READ permission
        assert auth.check_permission(user, Permission.READ, "metrics") is True

    def test_check_permission_policy_match(self, auth):
        user = User(
            user_id="u5",
            username="eve",
            email="eve@example.com",
            roles={Role.VIEWER},
        )
        policy = AccessPolicy(
            policy_id="custom",
            name="Custom",
            resource="metrics",
            required_permissions={Permission.READ},
            required_roles={Role.VIEWER},
        )
        auth.register_access_policy(policy)
        assert auth.check_permission(user, Permission.READ, "metrics") is True

    def test_assign_and_revoke_role(self, auth, sample_user):
        auth.register_user(sample_user)
        assert auth.assign_role("u1", Role.ANALYST) is True
        assert Role.ANALYST in auth.users["u1"].roles
        assert auth.revoke_role("u1", Role.ANALYST) is True
        assert Role.ANALYST not in auth.users["u1"].roles

    def test_assign_role_missing_user(self, auth):
        assert auth.assign_role("missing", Role.ADMIN) is False

    def test_get_auth_statistics(self, auth, sample_user):
        auth.register_user(sample_user)
        auth.authenticate_user("alice", "password123")
        stats = auth.get_auth_statistics()
        assert stats["registered_users"] == 1
        assert stats["successful_authentications"] == 1

    def test_unsupported_auth_method(self, auth, sample_user):
        auth.register_user(sample_user)
        assert auth.authenticate_user("alice", "password123", AuthMethod.API_KEY) is None

    def test_require_permission_decorator_sync(self, auth):
        @auth.require_permission(Permission.READ, "resource")
        def protected_func():
            return "called"

        assert protected_func() == "called"

    @pytest.mark.asyncio
    async def test_require_permission_decorator_async(self, auth):
        @auth.require_permission(Permission.READ, "resource")
        async def protected_async():
            return "async-called"

        assert await protected_async() == "async-called"


class TestEnumsAndFactory:
    """测试枚举和工厂函数"""

    def test_auth_method_values(self):
        assert AuthMethod.JWT.value == "jwt"
        assert AuthMethod.API_KEY.value == "api_key"

    def test_role_and_permission_values(self):
        assert Role.ADMIN.value == "admin"
        assert Permission.READ.value == "read"

    def test_get_enhanced_auth_integration(self):
        auth1 = get_enhanced_auth_integration()
        auth2 = get_enhanced_auth_integration()
        assert auth1 is not auth2  # factory creates new instances


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
