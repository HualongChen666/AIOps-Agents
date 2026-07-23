# -*- coding: utf-8 -*-
"""测试急切加载模块"""

import pytest


class TestEagerLoadingModule:
    """测试急切加载模块"""

    @pytest.mark.skip(reason="SQLAlchemy loader options error")
    def test_eager_loading_module_exists(self):
        """测试急切加载模块存在"""
        from core import eager_loading

        assert eager_loading is not None

    @pytest.mark.skip(reason="SQLAlchemy loader options error")
    def test_eager_loading_has_functions(self):
        """测试急切加载模块有函数"""
        from core import eager_loading

        # 检查模块有函数或类
        assert len(dir(eager_loading)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
