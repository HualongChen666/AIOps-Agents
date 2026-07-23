# -*- coding: utf-8 -*-
"""测试SSO认证模块"""

import pytest


class TestSSOAuthModule:
    """测试SSO认证模块"""

    @pytest.mark.skip(reason="Redis connection timeout")
    def test_sso_auth_module_exists(self):
        """测试SSO认证模块存在"""
        from core import sso_auth

        assert sso_auth is not None

    @pytest.mark.skip(reason="Redis connection timeout")
    def test_sso_auth_has_functions(self):
        """测试SSO认证模块有函数"""
        from core import sso_auth

        # 检查模块有函数或类
        assert len(dir(sso_auth)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
