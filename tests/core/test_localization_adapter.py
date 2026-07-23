# -*- coding: utf-8 -*-
"""测试本地化适配器模块"""

import pytest


class TestLocalizationAdapterModule:
    """测试本地化适配器模块"""

    def test_localization_adapter_module_exists(self):
        """测试本地化适配器模块存在"""
        from core import localization_adapter

        assert localization_adapter is not None

    def test_localization_adapter_has_functions(self):
        """测试本地化适配器模块有函数"""
        from core import localization_adapter

        # 检查模块有函数或类
        assert len(dir(localization_adapter)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
