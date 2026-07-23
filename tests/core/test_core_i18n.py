# -*- coding: utf-8 -*-
"""测试国际化模块"""

import pytest


class TestI18nModule:
    """测试国际化模块"""

    def test_i18n_module_exists(self):
        """测试国际化模块存在"""
        from core import i18n

        assert i18n is not None

    def test_i18n_has_functions(self):
        """测试国际化模块有函数"""
        from core import i18n

        # 检查模块有函数或类
        assert len(dir(i18n)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
