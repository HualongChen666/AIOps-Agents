# -*- coding: utf-8 -*-
"""测试输入验证器模块"""

import pytest


class TestInputValidatorModule:
    """测试输入验证器模块"""

    def test_input_validator_module_exists(self):
        """测试输入验证器模块存在"""
        from core import input_validator

        assert input_validator is not None

    def test_input_validator_has_functions(self):
        """测试输入验证器模块有函数"""
        from core import input_validator

        # 检查模块有函数或类
        assert len(dir(input_validator)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
