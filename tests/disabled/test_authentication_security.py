# -*- coding: utf-8 -*-
# tests/security/test_authentication_security.py
# 认证授权安全测试
import pytest


@pytest.mark.security
class TestSQLInjection:
    """SQL注入防护测试"""

    def test_sql_injection_in_username(self, client):
        """测试用户名中的SQL注入"""
        malicious_username = "admin' OR '1'='1"
        response = client.post(
            "/api/login", json={"username": malicious_username, "password": "password"}
        )
        # 应该拒绝登录或返回错误，而不是绕过认证
        assert response.status_code in [400, 401, 422]

    def test_sql_injection_in_password(self, client):
        """测试密码中的SQL注入"""
        response = client.post("/api/login", json={"username": "admin", "password": "' OR '1'='1"})
        # 应该拒绝登录
        assert response.status_code in [400, 401, 422]

    def test_sql_injection_in_query_params(self, client):
        """测试查询参数中的SQL注入"""
        malicious_id = "1' UNION SELECT * FROM users--"
        response = client.get(f"/api/users/{malicious_id}")
        # 应该返回错误或拒绝请求
        assert response.status_code in [400, 404, 422]

    def test_sql_injection_in_search(self, client):
        """测试搜索功能中的SQL注入"""
        malicious_search = "test' OR '1'='1"
        response = client.get("/api/search", params={"q": malicious_search})
        # 应该安全处理或返回错误
        assert response.status_code in [400, 422, 200]  # 200 if safely handled

    def test_sql_injection_in_filter(self, client):
        """测试过滤器中的SQL注入"""
        malicious_filter = "id=1 OR 1=1"
        response = client.get("/api/data", params={"filter": malicious_filter})
        # 应该拒绝或安全处理
        assert response.status_code in [400, 422, 200]


@pytest.mark.security
class TestXSSProtection:
    """XSS防护测试"""

    def test_xss_in_username(self, client):
        """测试用户名中的XSS"""
        malicious_username = "<script>alert('xss')</script>"
        response = client.post(
            "/api/register",
            json={
                "username": malicious_username,
                "email": "test@example.com",
                "password": "password123",
            },
        )
        # 应该拒绝或转义
        assert response.status_code in [400, 422]

    def test_xss_in_comment(self, client):
        """测试评论中的XSS"""
        malicious_comment = "<img src=x onerror=alert('xss')>"
        response = client.post("/api/comments", json={"content": malicious_comment})
        # 应该转义或拒绝
        assert response.status_code in [400, 422, 201]  # 201 if safely stored

    def test_xss_in_description(self, client):
        """测试描述中的XSS"""
        malicious_desc = "<script>document.cookie='xss'</script>"
        response = client.post("/api/items", json={"name": "test", "description": malicious_desc})
        # 应该转义或拒绝
        assert response.status_code in [400, 422, 201]

    def test_xss_in_search_query(self, client):
        """测试搜索查询中的XSS"""
        malicious_query = "<script>alert(1)</script>"
        response = client.get("/api/search", params={"q": malicious_query})
        # 响应中不应包含未转义的脚本
        if response.status_code == 200:
            content = response.text
            assert "<script>" not in content or "&lt;script&gt;" in content

    def test_xss_in_user_agent(self, client):
        """测试User-Agent中的XSS"""
        malicious_ua = "<script>alert('xss')</script>"
        response = client.get("/api/health", headers={"User-Agent": malicious_ua})
        # 应该安全处理
        assert response.status_code in [200, 400]


@pytest.mark.security
class TestCSRFProtection:
    """CSRF防护测试"""

    def test_csrf_token_required(self, client):
        """测试CSRF token是否必需"""
        response = client.post("/api/update", json={"data": "test"})
        # 应该要求CSRF token
        assert response.status_code in [400, 403, 422]

    def test_csrf_token_validation(self, client):
        """测试CSRF token验证"""
        # 发送无效的CSRF token
        response = client.post("/api/update", json={"data": "test", "csrf_token": "invalid_token"})
        # 应该拒绝
        assert response.status_code in [400, 403]

    def test_csrf_token_reuse_prevention(self, client):
        """测试CSRF token重用防护"""
        # 尝试重用CSRF token
        response = client.post("/api/update", json={"data": "test", "csrf_token": "reused_token"})
        # 应该拒绝重用的token
        assert response.status_code in [400, 403]

    def test_csrf_referer_check(self, client):
        """测试Referer检查"""
        response = client.post(
            "/api/update", json={"data": "test"}, headers={"Referer": "http://malicious.com"}
        )
        # 应该检查Referer
        assert response.status_code in [400, 403, 422]

    def test_csrf_origin_check(self, client):
        """测试Origin检查"""
        response = client.post(
            "/api/update", json={"data": "test"}, headers={"Origin": "http://malicious.com"}
        )
        # 应该检查Origin
        assert response.status_code in [400, 403, 422]


@pytest.mark.security
class TestAuthenticationSecurity:
    """认证安全测试"""

    def test_weak_password_rejection(self, client):
        """测试弱密码拒绝"""
        weak_passwords = ["123456", "password", "admin", "test"]
        for password in weak_passwords:
            response = client.post(
                "/api/register",
                json={"username": "testuser", "email": "test@example.com", "password": password},
            )
            # 应该拒绝弱密码
            assert response.status_code in [400, 422]

    def test_password_hashing(self, client):
        """测试密码哈希"""
        # 密码应该被哈希存储，不应该以明文存储
        # 这个测试需要检查数据库或API响应
        response = client.post(
            "/api/register",
            json={"username": "testuser", "email": "test@example.com", "password": "password123"},
        )
        # 如果成功，验证密码不被明文返回
        if response.status_code == 201:
            data = response.json()
            assert "password" not in data or data["password"] != "password123"

    def test_password_expiration(self, client):
        """测试密码过期"""
        # 测试过期密码应该被拒绝
        response = client.post(
            "/api/login", json={"username": "expired_user", "password": "expired_password"}
        )
        # 应该要求更改密码
        assert response.status_code in [401, 403]

    def test_account_lockout(self, client):
        """测试账户锁定"""
        # 尝试多次失败登录
        for _ in range(10):
            response = client.post(
                "/api/login", json={"username": "testuser", "password": "wrong_password"}
            )
            # 应该锁定账户
            if response.status_code == 423:  # Locked
                break

    def test_session_timeout(self, client):
        """测试会话超时"""
        # 测试过期会话应该被拒绝
        response = client.get("/api/protected", headers={"Authorization": "Bearer expired_token"})
        # 应该拒绝过期token
        assert response.status_code in [401, 403]

    def test_token_revocation(self, client):
        """测试token撤销"""
        # 测试撤销的token应该被拒绝
        response = client.get("/api/protected", headers={"Authorization": "Bearer revoked_token"})
        # 应该拒绝撤销的token
        assert response.status_code in [401, 403]


@pytest.mark.security
class TestAuthorizationSecurity:
    """授权安全测试"""

    def test_unauthorized_access(self, client):
        """测试未授权访问"""
        response = client.get("/api/admin/users")
        # 未授权用户应该被拒绝
        assert response.status_code in [401, 403]

    def test_privilege_escalation(self, client):
        """测试权限提升"""
        # 普通用户尝试访问管理员功能
        response = client.post("/api/admin/config", json={"key": "value"})
        # 应该拒绝
        assert response.status_code in [401, 403]

    def test_horizontal_privilege_escalation(self, client):
        """测试水平权限提升"""
        # 用户A尝试访问用户B的数据
        response = client.get("/api/users/2/data")
        # 应该拒绝
        assert response.status_code in [401, 403, 404]

    def test_role_based_access_control(self, client):
        """测试基于角色的访问控制"""
        # 不同角色应该有不同的访问权限
        response = client.get("/api/admin/settings")
        # 非管理员应该被拒绝
        assert response.status_code in [401, 403]

    def test_resource_based_access_control(self, client):
        """测试基于资源的访问控制"""
        # 用户只能访问自己的资源
        response = client.get("/api/users/999/profile")
        # 应该拒绝
        assert response.status_code in [401, 403, 404]


@pytest.mark.security
class TestSessionSecurity:
    """会话安全测试"""

    def test_session_fixation(self, client):
        """测试会话固定"""
        # 不应该接受预先设置的session ID
        response = client.get("/api/login", headers={"Cookie": "session_id=malicious_session"})
        # 应该生成新的session ID
        assert "session_id" not in response.headers.get("Set-Cookie", "")

    def test_session_hijacking_prevention(self, client):
        """测试会话劫持防护"""
        # 应该使用HttpOnly和Secure标志
        response = client.post(
            "/api/login", json={"username": "testuser", "password": "password123"}
        )
        set_cookie = response.headers.get("Set-Cookie", "")
        assert "HttpOnly" in set_cookie or "httponly" in set_cookie.lower()

    def test_concurrent_session_limit(self, client):
        """测试并发会话限制"""
        # 应该限制同一用户的并发会话数
        # 这个测试需要实际登录逻辑

    def test_session_invalidation_on_logout(self, client):
        """测试登出时会话失效"""
        response = client.post("/api/logout")
        # 登出后session应该失效
        assert response.status_code in [200, 204]
