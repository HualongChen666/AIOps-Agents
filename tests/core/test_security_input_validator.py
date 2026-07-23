# -*- coding: utf-8 -*-
"""
Security Input Validator Tests
测试安全输入验证中间件
"""

from unittest.mock import Mock  # noqa: F401

import pytest
from fastapi import FastAPI, Request  # noqa: F401
from fastapi.testclient import TestClient

from core.security_input_validator import (
    SecurityInputValidator,
    SecurityInputValidatorMiddleware,
    get_security_validator,
)


class TestSecurityInputValidator:
    """测试安全输入验证器"""

    @pytest.fixture
    def validator(self):
        """创建验证器实例"""
        return SecurityInputValidator()

    def test_validate_string_with_xss_attack(self, validator):
        """测试XSS攻击检测"""
        xss_payload = "<script>alert('xss')</script>"
        is_valid, error = validator.validate_string(xss_payload)

        assert not is_valid
        assert "XSS" in error

    def test_validate_string_with_sql_injection(self, validator):
        """测试SQL注入检测"""
        sql_payload = "1' OR '1'='1"
        is_valid, error = validator.validate_string(sql_payload)

        assert not is_valid
        assert "SQL injection" in error

    def test_validate_string_with_path_traversal(self, validator):
        """测试路径遍历检测"""
        path_payload = "../../../etc/passwd"
        is_valid, error = validator.validate_string(path_payload, "filename")

        assert not is_valid
        assert "path traversal" in error

    def test_validate_string_with_command_injection(self, validator):
        """测试命令注入检测"""
        cmd_payload = "file.txt; rm -rf /"
        is_valid, error = validator.validate_string(cmd_payload, "command")

        assert not is_valid
        assert "command injection" in error

    def test_validate_string_with_safe_input(self, validator):
        """测试安全输入验证通过"""
        safe_input = "normal_string_123"
        is_valid, error = validator.validate_string(safe_input)

        assert is_valid
        assert error is None

    def test_sanitize_string(self, validator):
        """测试字符串清理"""
        malicious = "<script>alert('xss')</script>"
        sanitized = validator.sanitize_string(malicious)

        assert "<script>" not in sanitized
        assert "alert" not in sanitized

    def test_validate_dict_with_nested_data(self, validator):
        """测试嵌套字典验证"""
        data = {"user": "safe_user", "nested": {"data": "<script>alert('xss')</script>"}}
        is_valid, error = validator.validate_dict(data)

        assert not is_valid
        assert "XSS" in error

    def test_validate_list_with_mixed_data(self, validator):
        """测试混合类型列表验证"""
        data = ["safe", 123, {"key": "<script>alert('xss')</script>"}]
        is_valid, error = validator.validate_list(data)

        assert not is_valid
        assert "XSS" in error

    def test_validate_any_with_various_types(self, validator):
        """测试各种数据类型验证"""
        # 字符串
        assert validator.validate_any("safe_string")[0]

        # 字典
        assert validator.validate_any({"key": "value"})[0]

        # 列表
        assert validator.validate_any([1, 2, 3])[0]

        # 数字
        assert validator.validate_any(123)[0]

        # 带XSS的字符串
        assert not validator.validate_any("<script>alert('xss')</script>")[0]


class TestSecurityInputValidatorMiddleware:
    """测试安全输入验证中间件"""

    @pytest.fixture
    def app_with_middleware(self):
        """创建带中间件的应用"""
        app = FastAPI()
        app.add_middleware(SecurityInputValidatorMiddleware)

        @app.post("/test")
        async def test_endpoint(data: dict):
            return {"received": data}

        @app.get("/test")
        async def test_get_endpoint():
            return {"status": "ok"}

        return app

    @pytest.fixture
    def client(self, app_with_middleware):
        """创建测试客户端"""
        return TestClient(app_with_middleware)

    def test_middleware_allows_safe_requests(self, client):
        """测试中间件允许安全请求"""
        response = client.post("/test", json={"data": "safe_string"})
        assert response.status_code == 200
        assert response.json()["received"]["data"] == "safe_string"

    def test_middleware_blocks_xss_requests(self, client):
        """测试中间件阻止XSS请求"""
        response = client.post("/test", json={"data": "<script>alert('xss')</script>"})
        assert response.status_code == 400
        assert "XSS" in response.json()["detail"]

    def test_middleware_blocks_sql_injection_requests(self, client):
        """测试中间件阻止SQL注入请求"""
        response = client.post("/test", json={"query": "1' OR '1'='1"})
        assert response.status_code == 400
        assert "SQL injection" in response.json()["detail"]

    def test_middleware_allows_safe_get_requests(self, client):
        """测试中间件允许安全GET请求"""
        response = client.get("/test?param=safe_value")
        assert response.status_code == 200

    def test_middleware_blocks_xss_in_query_params(self, client):
        """测试中间件阻止查询参数中的XSS"""
        response = client.get("/test?param=<script>alert('xss')</script>")
        assert response.status_code == 400
        assert "XSS" in response.json()["detail"]

    def test_middleware_skips_health_check_paths(self):
        """测试中间件跳过健康检查路径"""
        app = FastAPI()
        app.add_middleware(SecurityInputValidatorMiddleware)

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200


class TestSecurityValidatorGlobal:
    """测试全局安全验证器"""

    def test_get_security_validator_returns_singleton(self):
        """测试全局验证器返回单例"""
        validator1 = get_security_validator()
        validator2 = get_security_validator()

        # 应该是同一个实例
        assert validator1 is validator2

    def test_global_validator_functionality(self):
        """测试全局验证器功能"""
        validator = get_security_validator()

        # 测试基本功能
        is_valid, error = validator.validate_string("safe_string")
        assert is_valid

        is_valid, error = validator.validate_string("<script>alert('xss')</script>")
        assert not is_valid
        assert "XSS" in error
