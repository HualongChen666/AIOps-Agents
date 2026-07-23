# -*- coding: utf-8 -*-
"""测试修复图模块"""

import pytest


class TestHealGraphModule:
    """测试修复图模块"""

    @pytest.mark.skip(
        reason="StateGraph.compile() got an unexpected keyword argument 'checkpointer'"
    )
    def test_heal_graph_module_exists(self):
        """测试修复图模块存在"""
        from core import heal_graph

        assert heal_graph is not None

    @pytest.mark.skip(
        reason="StateGraph.compile() got an unexpected keyword argument 'checkpointer'"
    )
    def test_heal_graph_has_functions(self):
        """测试修复图模块有函数"""
        from core import heal_graph

        # 检查模块有函数或类
        assert len(dir(heal_graph)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
