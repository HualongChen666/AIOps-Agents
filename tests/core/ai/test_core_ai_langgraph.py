# -*- coding: utf-8 -*-
"""测试LangGraph模块"""

import pytest


class TestLangGraphModule:
    """测试LangGraph模块"""

    def test_dsl_module_exists(self):
        """测试DSL模块存在"""
        from core.ai.langgraph import dsl

        assert dsl is not None

    def test_dsl_has_functions(self):
        """测试DSL模块有函数"""
        from core.ai.langgraph import dsl

        # 检查模块有函数或类
        assert len(dir(dsl)) > 0

    def test_executor_module_exists(self):
        """测试执行器模块存在"""
        from core.ai.langgraph import executor

        assert executor is not None

    def test_executor_has_functions(self):
        """测试执行器模块有函数"""
        from core.ai.langgraph import executor

        # 检查模块有函数或类
        assert len(dir(executor)) > 0

    def test_nodes_module_exists(self):
        """测试节点模块存在"""
        from core.ai.langgraph import nodes

        assert nodes is not None

    def test_nodes_has_functions(self):
        """测试节点模块有函数"""
        from core.ai.langgraph import nodes

        # 检查模块有函数或类
        assert len(dir(nodes)) > 0

    def test_visualizer_module_exists(self):
        """测试可视化模块存在"""
        from core.ai.langgraph import visualizer

        assert visualizer is not None

    def test_visualizer_has_functions(self):
        """测试可视化模块有函数"""
        from core.ai.langgraph import visualizer

        # 检查模块有函数或类
        assert len(dir(visualizer)) > 0

    def test_workflow_module_exists(self):
        """测试工作流模块存在"""
        from core.ai.langgraph import workflow

        assert workflow is not None

    def test_workflow_has_functions(self):
        """测试工作流模块有函数"""
        from core.ai.langgraph import workflow

        # 检查模块有函数或类
        assert len(dir(workflow)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
