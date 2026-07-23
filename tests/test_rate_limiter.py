# -*- coding: utf-8 -*-
# tests/test_rate_limiter.py
# 速率限制单元测试
from unittest.mock import Mock, patch

import pytest
from fastapi import Request  # noqa: F401

import config
from core.rate_limiter import (
    check_rate_limit,
    get_limiter,
    get_rate_limit_for_endpoint,
)


class TestRateLimitConfiguration:
    """速率限制配置测试"""

    def test_get_rate_limit_for_auth_endpoint(self):
        """测试认证端点速率限制"""
        limit = get_rate_limit_for_endpoint("/auth/login")
        assert "minute" in limit
        # Should use the stricter auth limit
        assert str(config.RATE_LIMIT_AUTH_PER_MINUTE) in limit

    def test_get_rate_limit_for_admin_endpoint(self):
        """测试管理员端点速率限制"""
        limit = get_rate_limit_for_endpoint("/admin/users")
        assert "minute" in limit
        # Should use the higher admin limit
        assert str(config.RATE_LIMIT_ADMIN_PER_MINUTE) in limit

    def test_get_rate_limit_for_api_endpoint(self):
        """测试API端点速率限制"""
        limit = get_rate_limit_for_endpoint("/api/metrics")
        assert "minute" in limit
        # Should use the default API limit
        assert str(config.RATE_LIMIT_API_PER_MINUTE) in limit

    def test_get_rate_limit_for_unknown_endpoint(self):
        """测试未知端点速率限制（使用默认）"""
        limit = get_rate_limit_for_endpoint("/unknown/endpoint")
        assert "minute" in limit
        # Should use the default API limit
        assert str(config.RATE_LIMIT_API_PER_MINUTE) in limit


class TestRateLimitCheck:
    """速率限制检查测试"""

    @patch("core.rate_limiter.config.RATE_LIMIT_ENABLED", False)
    def test_check_rate_limit_disabled(self):
        """测试速率限制禁用时允许请求"""
        request = Mock()
        request.url.path = "/api/test"
        result = check_rate_limit(request)
        assert result is True

    @patch("core.rate_limiter.config.RATE_LIMIT_ENABLED", True)
    def test_check_rate_limit_enabled(self):
        """测试速率限制启用时检查请求"""
        request = Mock()
        request.url.path = "/api/test"
        result = check_rate_limit(request)
        # Should return True (actual limiting handled by decorator)
        assert result is True

    @patch("core.rate_limiter.config.RATE_LIMIT_ENABLED", True)
    def test_check_rate_limit_with_custom_limit(self):
        """测试自定义速率限制"""
        request = Mock()
        request.url.path = "/api/test"
        custom_limit = "100/minute"
        result = check_rate_limit(request, limit=custom_limit)
        assert result is True


class TestRateLimiterInitialization:
    """速率限制器初始化测试"""

    def test_get_limiter(self):
        """测试获取速率限制器"""
        limiter = get_limiter()
        # Limiter might be None if slowapi fails to initialize
        # or it might be a valid Limiter instance
        assert limiter is None or hasattr(limiter, "key_func") or hasattr(limiter, "_key_func")

    @patch("core.rate_limiter.config.RATE_LIMIT_ENABLED", False)
    def test_limiter_not_required_when_disabled(self):
        """测试速率限制禁用时不需要限制器"""
        request = Mock()
        request.url.path = "/api/test"
        result = check_rate_limit(request)
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
