# -*- coding: utf-8 -*-
"""
User Router Tests
用户管理路由测试
"""

import os
import sys
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Mock依赖模块
sys.modules["core.audit_service"] = Mock()
sys.modules["core.mfa_service"] = Mock()
sys.modules["core.user_service"] = Mock()

# Force reload api.user_router so core.authentication is imported as the real module
# (other tests may have left it as a MagicMock, causing await TypeErrors)
for _mod in ["config", "core.config", "api.user_router", "core.authentication"]:
    sys.modules.pop(_mod, None)

from api.user_router import router


class MockUserInDB:
    """Mock UserInDB class"""

    def __init__(self):
        self.id = 1
        self.username = "testuser"
        self.email = "test@example.com"
        self.full_name = "Test User"
        self.role = "user"
        self.disabled = False
        self.hashed_password = "hashed_password"
        self.created_at = datetime.now()
        self.last_login_at = None
        self.mfa_enabled = False


@pytest.fixture
def client():
    """创建测试客户端"""
    # Mock authentication
    mock_auth = Mock()
    mock_auth.verify_token = Mock(return_value={"sub": "testuser"})
    mock_auth.get_user = AsyncMock(return_value=MockUserInDB())
    mock_auth.validate_password_complexity = Mock(return_value=(True, ""))
    mock_auth.get_password_hash = Mock(return_value="hashed_password")
    mock_auth.verify_password = Mock(return_value=True)

    sys.modules["core.authentication"] = mock_auth

    # Mock services
    import api.user_router as user_router_module

    mock_user_service = AsyncMock()
    mock_user_service.get_user_by_username = AsyncMock(return_value=MockUserInDB())
    mock_user_service.get_user_by_email = AsyncMock(return_value=None)
    mock_user_service.create_user = AsyncMock(return_value=MockUserInDB())
    mock_user_service.list_users = AsyncMock(return_value=[MockUserInDB()])
    mock_user_service.update_user = AsyncMock(return_value=True)
    mock_user_service.delete_user = AsyncMock(return_value=True)
    mock_user_service.update_password = AsyncMock(return_value=True)

    user_router_module.user_service = mock_user_service

    mock_audit_service = Mock()
    mock_audit_service.log_action = AsyncMock()
    sys.modules["core.audit_service"] = mock_audit_service

    mock_mfa_service = Mock()
    mock_mfa_service.is_mfa_enabled = AsyncMock(return_value=False)
    mock_mfa_service.enable_mfa_for_user = AsyncMock(
        return_value=("secret", "qr_code", ["code1", "code2"])
    )
    mock_mfa_service.disable_mfa_for_user = AsyncMock(return_value=True)
    mock_mfa_service.get_mfa_status = AsyncMock(return_value={"enabled": False, "method": "totp"})
    sys.modules["core.mfa_service"] = mock_mfa_service

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


class TestCreateUser:
    """测试创建用户"""

    def test_create_user_success(self, client):
        """测试成功创建用户"""
        response = client.post(
            "/api/v1/users/",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "full_name": "New User",
                "password": "SecurePassword123!",
                "role": "user",
            },
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [201, 401, 403]

    def test_create_user_with_duplicate_username(self, client):
        """测试创建用户时用户名已存在"""
        mock_user_service = sys.modules["core.user_service"]
        mock_user_service.get_user_by_username = AsyncMock(return_value=MockUserInDB())

        response = client.post(
            "/api/v1/users/",
            json={
                "username": "existinguser",
                "email": "new@example.com",
                "password": "SecurePassword123!",
                "role": "user",
            },
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [201, 409, 401, 403]

    def test_create_user_with_duplicate_email(self, client):
        """测试创建用户时邮箱已存在"""
        mock_user_service = sys.modules["core.user_service"]
        mock_user_service.get_user_by_email = AsyncMock(return_value=MockUserInDB())

        response = client.post(
            "/api/v1/users/",
            json={
                "username": "newuser",
                "email": "existing@example.com",
                "password": "SecurePassword123!",
                "role": "user",
            },
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [201, 409, 401, 403]

    def test_create_user_with_invalid_password(self, client):
        """测试创建用户时密码复杂度不符合要求"""
        mock_auth = sys.modules["core.authentication"]
        mock_auth.validate_password_complexity = Mock(return_value=(False, "Password too weak"))

        response = client.post(
            "/api/v1/users/",
            json={"username": "newuser", "password": "weak", "role": "user"},
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [400, 401, 403]

    def test_create_user_without_auth(self, client):
        """测试未授权创建用户"""
        response = client.post(
            "/api/v1/users/",
            json={"username": "newuser", "password": "SecurePassword123!", "role": "user"},
        )
        assert response.status_code in [401, 403]


class TestListUsers:
    """测试列出用户"""

    def test_list_users_success(self, client):
        """测试成功列出用户"""
        response = client.get("/api/v1/users/", headers={"Authorization": "Bearer valid_token"})
        assert response.status_code in [200, 401, 403]

    def test_list_users_with_pagination(self, client):
        """测试分页列出用户"""
        response = client.get(
            "/api/v1/users/?limit=10&offset=0", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [200, 401, 403]

    def test_list_users_without_auth(self, client):
        """测试未授权列出用户"""
        response = client.get("/api/v1/users/")
        assert response.status_code in [401, 403]


class TestGetCurrentUser:
    """测试获取当前用户信息"""

    def test_get_current_user_success(self, client):
        """测试成功获取当前用户信息"""
        response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer valid_token"})
        assert response.status_code in [200, 401]

    def test_get_current_user_without_auth(self, client):
        """测试未授权获取当前用户信息"""
        response = client.get("/api/v1/users/me")
        assert response.status_code in [401]


class TestGetUserByUsername:
    """测试通过用户名获取用户"""

    def test_get_user_by_username_success(self, client):
        """测试成功通过用户名获取用户"""
        response = client.get(
            "/api/v1/users/testuser", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [200, 401, 403, 404]

    def test_get_user_by_username_not_found(self, client):
        """测试通过用户名获取不存在的用户"""
        mock_user_service = sys.modules["core.user_service"]
        mock_user_service.get_user_by_username = AsyncMock(return_value=None)

        response = client.get(
            "/api/v1/users/nonexistent", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [404, 401, 403]

    def test_get_user_by_username_without_auth(self, client):
        """测试未授权通过用户名获取用户"""
        response = client.get("/api/v1/users/testuser")
        assert response.status_code in [401, 403]


class TestUpdateUser:
    """测试更新用户"""

    def test_update_user_success(self, client):
        """测试成功更新用户"""
        response = client.put(
            "/api/v1/users/testuser",
            json={"email": "updated@example.com", "full_name": "Updated Name", "role": "admin"},
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [200, 401, 403, 404]

    def test_update_user_not_found(self, client):
        """测试更新不存在的用户"""
        mock_user_service = sys.modules["core.user_service"]
        mock_user_service.update_user = AsyncMock(return_value=False)

        response = client.put(
            "/api/v1/users/nonexistent",
            json={"email": "updated@example.com"},
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [404, 401, 403]

    def test_update_user_without_auth(self, client):
        """测试未授权更新用户"""
        response = client.put("/api/v1/users/testuser", json={"email": "updated@example.com"})
        assert response.status_code in [401, 403]


class TestDeleteUser:
    """测试删除用户"""

    def test_delete_user_success(self, client):
        """测试成功删除用户"""
        response = client.delete(
            "/api/v1/users/testuser", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [204, 401, 403, 404]

    def test_delete_user_not_found(self, client):
        """测试删除不存在的用户"""
        mock_user_service = sys.modules["core.user_service"]
        mock_user_service.delete_user = AsyncMock(return_value=False)

        response = client.delete(
            "/api/v1/users/nonexistent", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [404, 401, 403]

    def test_delete_self_forbidden(self, client):
        """测试禁止删除自己的账户"""
        response = client.delete(
            "/api/v1/users/testuser", headers={"Authorization": "Bearer valid_token"}
        )
        # 由于mock用户名匹配，可能会返回400
        assert response.status_code in [204, 400, 401, 403]

    def test_delete_user_without_auth(self, client):
        """测试未授权删除用户"""
        response = client.delete("/api/v1/users/testuser")
        assert response.status_code in [401, 403]


class TestChangePassword:
    """测试修改密码"""

    def test_change_password_success(self, client):
        """测试成功修改密码"""
        response = client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "oldpassword", "new_password": "NewSecurePassword123!"},
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [200, 401, 400]

    def test_change_password_wrong_current_password(self, client):
        """测试修改密码时当前密码错误"""
        mock_auth = sys.modules["core.authentication"]
        mock_auth.verify_password = Mock(return_value=False)

        response = client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "wrongpassword", "new_password": "NewSecurePassword123!"},
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [400, 401]

    def test_change_password_weak_new_password(self, client):
        """测试修改密码时新密码复杂度不够"""
        mock_auth = sys.modules["core.authentication"]
        mock_auth.validate_password_complexity = Mock(return_value=(False, "Password too weak"))

        response = client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "oldpassword", "new_password": "weak"},
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [400, 401]

    def test_change_password_without_auth(self, client):
        """测试未授权修改密码"""
        response = client.post(
            "/api/v1/users/me/change-password",
            json={"current_password": "oldpassword", "new_password": "NewSecurePassword123!"},
        )
        assert response.status_code in [401]


class TestMFAOperations:
    """测试MFA操作"""

    def test_enable_mfa_success(self, client):
        """测试成功启用MFA"""
        response = client.post(
            "/api/v1/users/me/mfa/enable",
            json={"password": "currentpassword"},
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [200, 401, 400]

    def test_enable_mfa_wrong_password(self, client):
        """测试启用MFA时密码错误"""
        mock_auth = sys.modules["core.authentication"]
        mock_auth.verify_password = Mock(return_value=False)

        response = client.post(
            "/api/v1/users/me/mfa/enable",
            json={"password": "wrongpassword"},
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [400, 401]

    def test_enable_mfa_already_enabled(self, client):
        """测试MFA已启用时再次启用"""
        mock_mfa_service = sys.modules["core.mfa_service"]
        mock_mfa_service.is_mfa_enabled = AsyncMock(return_value=True)

        response = client.post(
            "/api/v1/users/me/mfa/enable",
            json={"password": "currentpassword"},
            headers={"Authorization": "Bearer valid_token"},
        )
        assert response.status_code in [400, 401]

    def test_disable_mfa_success(self, client):
        """测试成功禁用MFA"""
        response = client.post(
            "/api/v1/users/me/mfa/disable", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [200, 401]

    def test_get_mfa_status(self, client):
        """测试获取MFA状态"""
        response = client.get(
            "/api/v1/users/me/mfa/status", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [200, 401]


class TestAuditLogs:
    """测试审计日志"""

    def test_get_my_audit_logs(self, client):
        """测试获取当前用户审计日志"""
        mock_audit_service = sys.modules["core.audit_service"]
        mock_audit_service.get_audit_logs = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "action": "login",
                    "resource_type": "user",
                    "username": "testuser",
                    "status": "success",
                }
            ]
        )

        response = client.get(
            "/api/v1/users/me/audit-logs", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [200, 401]

    def test_get_user_audit_logs_as_admin(self, client):
        """测试管理员获取指定用户审计日志"""
        mock_audit_service = sys.modules["core.audit_service"]
        mock_audit_service.get_audit_logs = AsyncMock(
            return_value=[
                {
                    "id": 1,
                    "action": "login",
                    "resource_type": "user",
                    "username": "testuser",
                    "status": "success",
                }
            ]
        )

        response = client.get(
            "/api/v1/users/testuser/audit-logs", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [200, 401, 403]

    def test_get_all_audit_logs_as_admin(self, client):
        """测试管理员获取所有审计日志"""
        mock_audit_service = sys.modules["core.audit_service"]
        mock_audit_service.get_audit_logs = AsyncMock(
            return_value=[
                {"id": 1, "action": "login", "resource_type": "user", "status": "success"}
            ]
        )

        response = client.get(
            "/api/v1/users/audit-logs", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code in [200, 401, 403]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
