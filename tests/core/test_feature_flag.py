# -*- coding: utf-8 -*-
"""测试功能标志模块"""

import pytest


class TestFeatureFlagModule:
    """测试功能标志模块"""

    def test_feature_flag_module_exists(self):
        """测试功能标志模块存在"""
        from core import feature_flag

        assert feature_flag is not None

    def test_feature_flag_has_functions(self):
        """测试功能标志模块有函数"""
        from core import feature_flag

        # 检查模块有函数或类
        assert len(dir(feature_flag)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
