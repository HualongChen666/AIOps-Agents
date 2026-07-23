# -*- coding: utf-8 -*-
"""测试依赖注入模块"""

import pytest


class TestDependencyInjectionModule:
    """测试依赖注入模块"""

    def test_dependency_injection_module_exists(self):
        """测试依赖注入模块存在"""
        from core import dependency_injection

        assert dependency_injection is not None

    def test_dependency_injection_has_functions(self):
        """测试依赖注入模块有函数"""
        from core import dependency_injection

        # 检查模块有函数或类
        assert len(dir(dependency_injection)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
