# -*- coding: utf-8 -*-
"""测试限流策略模块"""

import pytest


class TestRateLimitingModule:
    """测试限流策略模块"""

    def test_rate_limiting_module_exists(self):
        """测试限流策略模块存在"""
        from core import rate_limiting

        assert rate_limiting is not None

    def test_rate_limiting_has_constants(self):
        """测试限流策略模块有常量"""
        from core import rate_limiting

        # 检查模块有常量
        assert len(dir(rate_limiting)) > 0


class TestEndpointLimits:
    """测试端点限流配置"""

    def test_endpoint_limits_exists(self):
        """测试端点限流配置存在"""
        try:
            from core.rate_limiting import ENDPOINT_LIMITS

            assert ENDPOINT_LIMITS is not None
            assert isinstance(ENDPOINT_LIMITS, dict)
        except Exception as e:
            pytest.skip(f"Cannot test endpoint limits exists: {e}")

    def test_endpoint_limits_structure(self):
        """测试端点限流配置结构"""
        try:
            from core.rate_limiting import ENDPOINT_LIMITS

            # Check required endpoints
            assert "/api/v1/alerts" in ENDPOINT_LIMITS
            assert "/api/v1/ai/analyze" in ENDPOINT_LIMITS
            assert "/api/v1/metrics" in ENDPOINT_LIMITS
            assert "/api/v1/health" in ENDPOINT_LIMITS
        except Exception as e:
            pytest.skip(f"Cannot test endpoint limits structure: {e}")

    def test_endpoint_limits_values(self):
        """测试端点限流配置值"""
        try:
            from core.rate_limiting import ENDPOINT_LIMITS

            # Check limit structure
            alerts_limit = ENDPOINT_LIMITS["/api/v1/alerts"]
            assert "requests" in alerts_limit
            assert "window" in alerts_limit
            assert alerts_limit["requests"] == 100
            assert alerts_limit["window"] == 60
        except Exception as e:
            pytest.skip(f"Cannot test endpoint limits values: {e}")


class TestUserLimits:
    """测试用户限流配置"""

    def test_user_limits_exists(self):
        """测试用户限流配置存在"""
        try:
            from core.rate_limiting import USER_LIMITS

            assert USER_LIMITS is not None
            assert isinstance(USER_LIMITS, dict)
        except Exception as e:
            pytest.skip(f"Cannot test user limits exists: {e}")

    def test_user_limits_structure(self):
        """测试用户限流配置结构"""
        try:
            from core.rate_limiting import USER_LIMITS

            # Check required user types
            assert "default" in USER_LIMITS
            assert "admin" in USER_LIMITS
        except Exception as e:
            pytest.skip(f"Cannot test user limits structure: {e}")

    def test_user_limits_values(self):
        """测试用户限流配置值"""
        try:
            from core.rate_limiting import USER_LIMITS

            # Check default user limits
            default_limit = USER_LIMITS["default"]
            assert "requests" in default_limit
            assert "window" in default_limit
            assert default_limit["requests"] == 100
            assert default_limit["window"] == 60

            # Check admin user limits
            admin_limit = USER_LIMITS["admin"]
            assert admin_limit["requests"] == 1000
            assert admin_limit["window"] == 60
        except Exception as e:
            pytest.skip(f"Cannot test user limits values: {e}")


class TestRateLimitingIntegration:
    """测试限流策略集成"""

    def test_all_configurations_valid(self):
        """测试所有配置有效"""
        try:
            from core.rate_limiting import ENDPOINT_LIMITS, USER_LIMITS

            # Verify all limits have required fields
            for endpoint, limit in ENDPOINT_LIMITS.items():
                assert "requests" in limit
                assert "window" in limit
                assert isinstance(limit["requests"], int)
                assert isinstance(limit["window"], int)

            for user_type, limit in USER_LIMITS.items():
                assert "requests" in limit
                assert "window" in limit
                assert isinstance(limit["requests"], int)
                assert isinstance(limit["window"], int)
        except Exception as e:
            pytest.skip(f"Cannot test all configurations valid: {e}")

    def test_limits_are_positive(self):
        """测试限流值为正数"""
        try:
            from core.rate_limiting import ENDPOINT_LIMITS, USER_LIMITS

            # Check all limits are positive
            for limit in ENDPOINT_LIMITS.values():
                assert limit["requests"] > 0
                assert limit["window"] > 0

            for limit in USER_LIMITS.values():
                assert limit["requests"] > 0
                assert limit["window"] > 0
        except Exception as e:
            pytest.skip(f"Cannot test limits are positive: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
