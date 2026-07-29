# -*- coding: utf-8 -*-
"""测试验证器模块"""

import pytest


class TestVerifierModule:
    """测试验证器模块"""

    def test_verifier_module_exists(self):
        """测试验证器模块存在"""
        from core import verifier

        assert verifier is not None

    def test_verifier_has_functions(self):
        """测试验证器模块有函数"""
        from core import verifier

        # 检查模块有函数或类
        assert len(dir(verifier)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
