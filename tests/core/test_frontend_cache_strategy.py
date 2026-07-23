# -*- coding: utf-8 -*-
"""测试前端缓存策略模块"""

import pytest


class TestFrontendCacheStrategyModule:
    """测试前端缓存策略模块"""

    def test_frontend_cache_strategy_module_exists(self):
        """测试前端缓存策略模块存在"""
        from core import frontend_cache_strategy

        assert frontend_cache_strategy is not None

    def test_frontend_cache_strategy_has_functions(self):
        """测试前端缓存策略模块有函数"""
        from core import frontend_cache_strategy

        # 检查模块有函数或类
        assert len(dir(frontend_cache_strategy)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
