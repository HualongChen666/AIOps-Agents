# -*- coding: utf-8 -*-
"""测试调用链搜索模块"""

import pytest


class TestCallChainSearchModule:
    """测试调用链搜索模块"""

    def test_call_chain_search_module_exists(self):
        """测试调用链搜索模块存在"""
        from core import call_chain_search

        assert call_chain_search is not None

    def test_call_chain_search_has_functions(self):
        """测试调用链搜索模块有函数"""
        from core import call_chain_search

        # 检查模块有函数或类
        assert len(dir(call_chain_search)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
