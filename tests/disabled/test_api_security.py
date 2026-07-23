# -*- coding: utf-8 -*-
# tests/security/test_api_security.py
# API安全测试
import pytest


@pytest.mark.security
class TestInputValidation:
    """输入验证测试"""

    def test_missing_required_parameters(self, client):
        """测试缺少必需参数"""
        response = client.post("/api/users", json={})
        # 应该返回验证错误
        assert response.status_code in [400, 422]

    def test_invalid_parameter_types(self, client):
        """测试无效参数类型"""
        response = client.post(
            "/api/users",
            json={"username": 123, "email": "invalid", "age": "not_a_number"},  # 应该是字符串
        )
        # 应该返回验证错误
        assert response.status_code in [400, 422]

    def test_parameter_length_limits(self, client):
        """测试参数长度限制"""
        long_string = "x" * 10000
        response = client.post("/api/users", json={"username": long_string})
        # 应该拒绝过长的输入
        assert response.status_code in [400, 422]

    def test_special_characters_in_input(self, client):
        """测试输入中的特殊字符"""
        special_chars = "<>\"'&;"
        response = client.post("/api/search", params={"q": special_chars})
        # 应该安全处理或拒绝
        assert response.status_code in [200, 400, 422]

    def test_null_byte_injection(self, client):
        """测试空字节注入"""
        malicious_input = "test\x00user"
        response = client.post("/api/users", json={"username": malicious_input})
        # 应该拒绝或安全处理
        assert response.status_code in [400, 422]

    def test_unicode_normalization(self, client):
        """测试Unicode规范化"""
        # 测试Unicode规范化攻击
        malicious_unicode = "\u0000\u0001\u0002"
        response = client.post("/api/users", json={"username": malicious_unicode})
        # 应该拒绝或安全处理
        assert response.status_code in [400, 422]


@pytest.mark.security
class TestRateLimiting:
    """速率限制测试"""

    def test_rate_limiting_on_api(self, client):
        """测试API速率限制"""
        # 快速发送多个请求
        responses = []
        for _ in range(100):
            response = client.get("/api/health")
            responses.append(response.status_code)
            if response.status_code == 429:  # Too Many Requests
                break

        # 应该触发速率限制
        assert 429 in responses or len(responses) < 100

    def test_rate_limiting_per_user(self, client):
        """测试每用户速率限制"""
        # 同一用户快速发送多个请求
        responses = []
        for _ in range(50):
            response = client.get("/api/users", headers={"Authorization": "Bearer test_token"})
            responses.append(response.status_code)
            if response.status_code == 429:
                break

        # 应该触发速率限制
        assert 429 in responses or len(responses) < 50

    def test_rate_limiting_per_ip(self, client):
        """测试每IP速率限制"""
        # 从同一IP快速发送多个请求
        responses = []
        for _ in range(50):
            response = client.get("/api/health")
            responses.append(response.status_code)
            if response.status_code == 429:
                break

        # 应该触发速率限制
        assert 429 in responses or len(responses) < 50

    def test_rate_limit_recovery(self, client):
        """测试速率限制恢复"""
        # 触发速率限制
        for _ in range(100):
            client.get("/api/health")

        # 等待一段时间后应该恢复
        import time

        time.sleep(1)

        response = client.get("/api/health")
        # 应该允许请求
        assert response.status_code in [200, 404]


@pytest.mark.security
class TestHTTPSecurityHeaders:
    """HTTP安全头测试"""

    def test_x_frame_options_header(self, client):
        """测试X-Frame-Options头"""
        response = client.get("/api/health")
        headers = response.headers
        # 应该设置X-Frame-Options
        assert "X-Frame-Options" in headers or "x-frame-options" in headers

    def test_x_content_type_options_header(self, client):
        """测试X-Content-Type-Options头"""
        response = client.get("/api/health")
        headers = response.headers
        # 应该设置X-Content-Type-Options
        assert "X-Content-Type-Options" in headers or "x-content-type-options" in headers

    def test_x_xss_protection_header(self, client):
        """测试X-XSS-Protection头"""
        response = client.get("/api/health")
        headers = response.headers
        # 应该设置X-XSS-Protection
        assert "X-XSS-Protection" in headers or "x-xss-protection" in headers

    def test_content_security_policy_header(self, client):
        """测试Content-Security-Policy头"""
        response = client.get("/api/health")
        headers = response.headers
        # 应该设置Content-Security-Policy
        assert "Content-Security-Policy" in headers or "content-security-policy" in headers

    def test_strict_transport_security_header(self, client):
        """测试Strict-Transport-Security头"""
        response = client.get("/api/health")
        headers = response.headers
        # HTTPS应该设置HSTS
        assert "Strict-Transport-Security" in headers or "strict-transport-security" in headers

    def test_referrer_policy_header(self, client):
        """测试Referrer-Policy头"""
        response = client.get("/api/health")
        headers = response.headers
        # 应该设置Referrer-Policy
        assert "Referrer-Policy" in headers or "referrer-policy" in headers


@pytest.mark.security
class TestAPISecurity:
    """API安全测试"""

    def test_sensitive_data_in_url(self, client):
        """测试URL中的敏感数据"""
        # 不应该在URL中传递敏感数据
        response = client.get("/api/users?password=secret")
        # 应该拒绝或警告
        assert response.status_code in [400, 422]

    def test_sensitive_data_in_logs(self, client):
        """测试日志中的敏感数据"""
        # 敏感数据不应该出现在日志中
        response = client.post("/api/login", json={"username": "test", "password": "secret123"})
        # 响应中不应该包含明文密码
        if response.status_code == 200:
            data = response.json()
            assert "password" not in data or data["password"] != "secret123"

    def test_api_versioning(self, client):
        """测试API版本控制"""
        # 应该支持API版本控制
        response = client.get("/api/v1/health")
        # 应该返回响应或404（如果版本不存在）
        assert response.status_code in [200, 404]

    def test_api_deprecation(self, client):
        """测试API弃用"""
        # 弃用的API应该返回警告头
        response = client.get("/api/v0/legacy")
        headers = response.headers
        # 应该返回弃用警告
        if response.status_code == 200:
            assert "Deprecation" in headers or "deprecation" in headers

    def test_api_error_messages(self, client):
        """测试API错误消息"""
        # 错误消息不应该泄露敏感信息
        response = client.get("/api/nonexistent")
        # 应该返回通用错误消息
        if response.status_code == 404:
            data = response.json()
            assert "password" not in str(data).lower()
            assert "secret" not in str(data).lower()


@pytest.mark.security
class TestFileUploadSecurity:
    """文件上传安全测试"""

    def test_file_type_validation(self, client):
        """测试文件类型验证"""
        # 尝试上传恶意文件类型
        response = client.post(
            "/api/upload",
            files={"file": ("malicious.exe", b"malicious content", "application/x-msdownload")},
        )
        # 应该拒绝
        assert response.status_code in [400, 422]

    def test_file_size_limit(self, client):
        """测试文件大小限制"""
        # 尝试上传过大文件
        large_file = b"x" * (100 * 1024 * 1024)  # 100MB
        response = client.post(
            "/api/upload", files={"file": ("large.txt", large_file, "text/plain")}
        )
        # 应该拒绝
        assert response.status_code in [400, 413]

    def test_file_content_validation(self, client):
        """测试文件内容验证"""
        # 尝试上传包含恶意内容的文件
        malicious_content = b"<script>alert('xss')</script>"
        response = client.post(
            "/api/upload", files={"file": ("malicious.html", malicious_content, "text/html")}
        )
        # 应该拒绝或安全处理
        assert response.status_code in [400, 422]

    def test_file_name_validation(self, client):
        """测试文件名验证"""
        # 尝试上传包含路径遍历的文件名
        malicious_filename = "../../../etc/passwd"
        response = client.post(
            "/api/upload", files={"file": (malicious_filename, b"content", "text/plain")}
        )
        # 应该拒绝
        assert response.status_code in [400, 422]

    def test_file_extension_validation(self, client):
        """测试文件扩展名验证"""
        # 尝试上传双扩展名文件
        malicious_filename = "file.txt.exe"
        response = client.post(
            "/api/upload", files={"file": (malicious_filename, b"content", "text/plain")}
        )
        # 应该拒绝或验证
        assert response.status_code in [400, 422]


@pytest.mark.security
class TestIDORProtection:
    """IDOR防护测试"""

    def test_idor_in_user_profile(self, client):
        """测试用户资料中的IDOR"""
        # 尝试访问其他用户的资料
        response = client.get("/api/users/999/profile")
        # 应该拒绝
        assert response.status_code in [401, 403, 404]

    def test_idor_in_order_access(self, client):
        """测试订单访问中的IDOR"""
        # 尝试访问其他用户的订单
        response = client.get("/api/orders/999")
        # 应该拒绝
        assert response.status_code in [401, 403, 404]

    def test_idor_in_document_access(self, client):
        """测试文档访问中的IDOR"""
        # 尝试访问其他用户的文档
        response = client.get("/api/documents/999")
        # 应该拒绝
        assert response.status_code in [401, 403, 404]

    def test_idor_in_message_access(self, client):
        """测试消息访问中的IDOR"""
        # 尝试访问其他用户的消息
        response = client.get("/api/messages/999")
        # 应该拒绝
        assert response.status_code in [401, 403, 404]

    def test_idor_prevention_with_uuid(self, client):
        """测试使用UUID防止IDOR"""
        # 使用UUID而不是自增ID
        response = client.get("/api/users/550e8400-e29b-41d4-a716-446655440000")
        # 应该安全处理
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.security
class TestMassAssignment:
    """批量赋值测试"""

    def test_mass_assignment_prevention(self, client):
        """测试批量赋值防护"""
        # 尝试通过批量赋值修改敏感字段
        response = client.put(
            "/api/users/1",
            json={"username": "admin", "is_admin": True, "role": "admin"},  # 不应该允许直接设置
        )
        # 应该拒绝或忽略敏感字段
        assert response.status_code in [400, 403, 422]

    def test_field_filtering(self, client):
        """测试字段过滤"""
        # 只允许更新特定字段
        response = client.patch("/api/users/1", json={"email": "new@example.com"})
        # 应该允许
        assert response.status_code in [200, 401, 403, 404]

    def test_hidden_field_protection(self, client):
        """测试隐藏字段保护"""
        # 尝试修改隐藏字段
        response = client.put(
            "/api/users/1", json={"created_at": "2024-01-01", "updated_at": "2024-01-01"}
        )
        # 应该拒绝
        assert response.status_code in [400, 403, 422]


@pytest.mark.security
class TestPathTraversal:
    """路径遍历测试"""

    def test_path_traversal_in_filename(self, client):
        """测试文件名中的路径遍历"""
        malicious_filename = "../../../etc/passwd"
        response = client.get(f"/api/files/{malicious_filename}")
        # 应该拒绝
        assert response.status_code in [400, 404]

    def test_path_traversal_in_url(self, client):
        """测试URL中的路径遍历"""
        malicious_url = "/api/files/../../../etc/passwd"
        response = client.get(malicious_url)
        # 应该拒绝
        assert response.status_code in [400, 404]

    def test_path_traversal_with_encoding(self, client):
        """测试编码的路径遍历"""
        malicious_filename = "%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        response = client.get(f"/api/files/{malicious_filename}")
        # 应该拒绝
        assert response.status_code in [400, 404]

    def test_path_traversal_with_unicode(self, client):
        """测试Unicode路径遍历"""
        malicious_filename = "..%c0%af..%c0%afetc%2fpasswd"
        response = client.get(f"/api/files/{malicious_filename}")
        # 应该拒绝
        assert response.status_code in [400, 404]

    def test_path_traversal_in_parameter(self, client):
        """测试参数中的路径遍历"""
        response = client.get("/api/files", params={"path": "../../../etc/passwd"})
        # 应该拒绝
        assert response.status_code in [400, 422]


@pytest.mark.security
class TestSSRFProtection:
    """SSRF防护测试"""

    def test_ssrf_with_internal_ip(self, client):
        """测试内部IP的SSRF"""
        malicious_url = "http://127.0.0.1/admin"
        response = client.post("/api/fetch", json={"url": malicious_url})
        # 应该拒绝
        assert response.status_code in [400, 422]

    def test_ssrf_with_localhost(self, client):
        """测试localhost的SSRF"""
        malicious_url = "http://localhost:8080"
        response = client.post("/api/fetch", json={"url": malicious_url})
        # 应该拒绝
        assert response.status_code in [400, 422]

    def test_ssrf_with_private_ip(self, client):
        """测试私有IP的SSRF"""
        malicious_url = "http://192.168.1.1"
        response = client.post("/api/fetch", json={"url": malicious_url})
        # 应该拒绝
        assert response.status_code in [400, 422]

    def test_ssrf_with_metadata_endpoint(self, client):
        """测试元数据端点的SSRF"""
        malicious_url = "http://169.254.169.254/latest/meta-data/"
        response = client.post("/api/fetch", json={"url": malicious_url})
        # 应该拒绝
        assert response.status_code in [400, 422]

    def test_ssrf_with_file_protocol(self, client):
        """测试file://协议的SSRF"""
        malicious_url = "file:///etc/passwd"
        response = client.post("/api/fetch", json={"url": malicious_url})
        # 应该拒绝
        assert response.status_code in [400, 422]
