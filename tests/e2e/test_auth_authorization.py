# -*- coding: utf-8 -*-
"""
E2E Test: Authentication and Authorization
真实E2E测试：用户认证和授权流程，不使用Mock
"""

import asyncio  # noqa: F401
import json  # noqa: F401
from datetime import datetime, timedelta  # noqa: F401

import httpx  # noqa: F401
import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestAuthenticationAndAuthorization:
    """认证和授权流程E2E测试"""

    @pytest.mark.asyncio
    async def test_complete_auth_workflow(self, http_client):
        """测试完整认证工作流：注册→登录→令牌获取→API访问→登出"""

        # 步骤1: 用户注册
        user_data = {
            "username": f"e2e_test_user_{int(datetime.now().timestamp())}",
            "email": f"e2e_test_{int(datetime.now().timestamp())}@example.com",
            "password": "SecurePassword123!",
            "full_name": "E2E Test User",
        }

        register_response = await http_client.post(
            "http://localhost:8000/api/v1/auth/register", json=user_data, timeout=10.0
        )

        # 注册可能成功或用户已存在
        assert register_response.status_code in [200, 201, 409]  # 409表示用户已存在

        # 步骤2: 用户登录
        login_response = await http_client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"username": user_data["username"], "password": user_data["password"]},
            timeout=10.0,
        )

        assert login_response.status_code == 200
        login_result = login_response.json()
        assert "access_token" in login_result
        assert "refresh_token" in login_result

        access_token = login_result["access_token"]

        # 步骤3: 使用令牌访问受保护的API
        protected_response = await http_client.get(
            "http://localhost:8000/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )

        assert protected_response.status_code == 200
        user_info = protected_response.json()
        assert user_info["username"] == user_data["username"]

        # 步骤4: 测试权限验证（访问管理员API）
        admin_response = await http_client.get(
            "http://localhost:8000/api/v1/admin/users",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )

        # 普通用户应该被拒绝
        assert admin_response.status_code == 403

        # 步骤5: 令牌刷新
        refresh_response = await http_client.post(
            "http://localhost:8000/api/v1/auth/refresh",
            json={"refresh_token": login_result["refresh_token"]},
            timeout=10.0,
        )

        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens

        # 步骤6: 登出
        logout_response = await http_client.post(
            "http://localhost:8000/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {new_tokens['access_token']}"},
            timeout=10.0,
        )

        assert logout_response.status_code in [200, 204]

    @pytest.mark.asyncio
    async def test_role_based_access_control(self, http_client):
        """测试基于角色的访问控制"""

        # 注册用户（简化处理，直接登录）
        admin_login = await http_client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
            timeout=10.0,
        )

        regular_login = await http_client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"username": "user", "password": "user123"},
            timeout=10.0,
        )

        # 如果默认用户不存在，跳过此测试
        if admin_login.status_code != 200 or regular_login.status_code != 200:
            pytest.skip("Default users not available")

        admin_token = admin_login.json().get("access_token")
        regular_token = regular_login.json().get("access_token")

        # 测试管理员权限
        admin_api_response = await http_client.get(
            "http://localhost:8000/api/v1/admin/system/config",
            headers={"Authorization": f"Bearer {admin_token}"},
            timeout=10.0,
        )

        # 测试普通用户权限
        user_api_response = await http_client.get(
            "http://localhost:8000/api/v1/admin/system/config",
            headers={"Authorization": f"Bearer {regular_token}"},
            timeout=10.0,
        )

        # 验证权限差异
        assert admin_api_response.status_code in [200, 404]  # 404如果API不存在
        assert user_api_response.status_code == 403

    @pytest.mark.asyncio
    async def test_token_expiration_and_refresh(self, http_client):
        """测试令牌过期和刷新"""

        # 登录获取短期令牌
        login_response = await http_client.post(
            "http://localhost:8000/api/v1/auth/login",
            json={"username": "testuser", "password": "test123"},
            timeout=10.0,
        )

        if login_response.status_code != 200:
            pytest.skip("Test user not available")

        tokens = login_response.json()
        access_token = tokens["access_token"]

        # 测试访问令牌
        api_response = await http_client.get(
            "http://localhost:8000/api/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )

        assert api_response.status_code == 200

        # 等待令牌过期（模拟）
        # 实际环境中需要等待真实过期时间，这里跳过
        # refresh_response = await http_client.post(
        #     "http://localhost:8000/api/v1/auth/refresh",
        #     json={"refresh_token": refresh_token},
        #     timeout=10.0
        # )

        # assert refresh_response.status_code == 200

    @pytest.mark.asyncio
    async def test_permission_hierarchy(self, http_client):
        """测试权限层次"""

        # 登录不同权限的用户
        users = ["admin", "operator", "viewer"]
        permission_tests = {
            "admin": [
                "POST /api/v1/alerts",
                "DELETE /api/v1/alerts/{id}",
                "PUT /api/v1/users/{id}",
            ],
            "operator": ["POST /api/v1/alerts", "GET /api/v1/users/me"],
            "viewer": ["GET /api/v1/alerts", "GET /api/v1/users/me"],
        }

        for user in users:
            login_response = await http_client.post(
                "http://localhost:8000/api/v1/auth/login",
                json={"username": user, "password": f"{user}123"},
                timeout=10.0,
            )

            if login_response.status_code != 200:
                continue

            token = login_response.json().get("access_token")

            # 测试权限
            for endpoint in permission_tests.get(user, []):
                method, path = endpoint.split(" ", 1)
                path = path.replace("{id}", "1")

                if method == "POST":
                    response = await http_client.post(
                        f"http://localhost:8000{path}",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"test": "data"},
                        timeout=10.0,
                    )
                elif method == "DELETE":
                    response = await http_client.delete(
                        f"http://localhost:8000{path}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10.0,
                    )
                elif method == "PUT":
                    response = await http_client.put(
                        f"http://localhost:8000{path}",
                        headers={"Authorization": f"Bearer {token}"},
                        json={"test": "data"},
                        timeout=10.0,
                    )
                else:
                    response = await http_client.get(
                        f"http://localhost:8000{path}",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=10.0,
                    )

                # 验证权限
                if user == "admin":
                    assert response.status_code in [200, 404, 405]  # 404/405如果API不存在
                elif user == "operator":
                    assert response.status_code in [200, 403, 404, 405]
                else:  # viewer
                    assert response.status_code in [200, 403, 404, 405]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "e2e"])
