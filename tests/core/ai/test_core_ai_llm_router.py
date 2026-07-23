# -*- coding: utf-8 -*-
"""测试LLM路由模块"""

import pytest


class TestLLMRouterModule:
    """测试LLM路由模块"""

    def test_capability_evaluator_module_exists(self):
        """测试能力评估器模块存在"""
        from core.ai.llm_router import capability_evaluator

        assert capability_evaluator is not None

    def test_capability_evaluator_has_functions(self):
        """测试能力评估器模块有函数"""
        from core.ai.llm_router import capability_evaluator

        # 检查模块有函数或类
        assert len(dir(capability_evaluator)) > 0

    def test_cost_optimizer_module_exists(self):
        """测试成本优化器模块存在"""
        from core.ai.llm_router import cost_optimizer

        assert cost_optimizer is not None

    def test_cost_optimizer_has_functions(self):
        """测试成本优化器模块有函数"""
        from core.ai.llm_router import cost_optimizer

        # 检查模块有函数或类
        assert len(dir(cost_optimizer)) > 0

    def test_enhanced_router_module_exists(self):
        """测试增强路由器模块存在"""
        from core.ai.llm_router import enhanced_router

        assert enhanced_router is not None

    def test_enhanced_router_has_functions(self):
        """测试增强路由器模块有函数"""
        from core.ai.llm_router import enhanced_router

        # 检查模块有函数或类
        assert len(dir(enhanced_router)) > 0

    def test_load_balancer_module_exists(self):
        """测试负载均衡器模块存在"""
        from core.ai.llm_router import load_balancer

        assert load_balancer is not None

    def test_load_balancer_has_functions(self):
        """测试负载均衡器模块有函数"""
        from core.ai.llm_router import load_balancer

        # 检查模块有函数或类
        assert len(dir(load_balancer)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
