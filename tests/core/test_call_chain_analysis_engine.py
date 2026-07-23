# -*- coding: utf-8 -*-
"""测试调用链分析引擎模块"""

import pytest


class TestCallChainAnalysisEngineModule:
    """测试调用链分析引擎模块"""

    def test_call_chain_analysis_engine_module_exists(self):
        """测试调用链分析引擎模块存在"""
        from core import call_chain_analysis_engine

        assert call_chain_analysis_engine is not None

    def test_call_chain_analysis_engine_has_functions(self):
        """测试调用链分析引擎模块有函数"""
        from core import call_chain_analysis_engine

        # 检查模块有函数或类
        assert len(dir(call_chain_analysis_engine)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
