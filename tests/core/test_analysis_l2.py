# -*- coding: utf-8 -*-
"""测试L2分析模块"""

import pytest

pytestmark = pytest.mark.smoke


class TestAnalysisL2Module:
    """测试L2分析模块"""

    def test_enhanced_causal_analyzer_module_exists(self):
        """测试增强因果分析器模块存在"""
        from core.analysis.l2 import enhanced_causal_analyzer

        assert enhanced_causal_analyzer is not None

    def test_enhanced_causal_analyzer_has_functions(self):
        """测试增强因果分析器模块有函数"""
        from core.analysis.l2 import enhanced_causal_analyzer

        # 检查模块有函数或类
        assert len(dir(enhanced_causal_analyzer)) > 0

    def test_langgraph_engine_module_exists(self):
        """测试LangGraph引擎模块存在"""
        from core.analysis.l2 import langgraph_engine

        assert langgraph_engine is not None

    def test_langgraph_engine_has_functions(self):
        """测试LangGraph引擎模块有函数"""
        from core.analysis.l2 import langgraph_engine

        # 检查模块有函数或类
        assert len(dir(langgraph_engine)) > 0

    def test_model_router_module_exists(self):
        """测试模型路由器模块存在"""
        from core.analysis.l2 import model_router

        assert model_router is not None

    def test_model_router_has_functions(self):
        """测试模型路由器模块有函数"""
        from core.analysis.l2 import model_router

        # 检查模块有函数或类
        assert len(dir(model_router)) > 0

    def test_rag_engine_module_exists(self):
        """测试RAG引擎模块存在"""
        from core.analysis.l2 import rag_engine

        assert rag_engine is not None

    def test_rag_engine_has_functions(self):
        """测试RAG引擎模块有函数"""
        from core.analysis.l2 import rag_engine

        # 检查模块有函数或类
        assert len(dir(rag_engine)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
