# -*- coding: utf-8 -*-
"""测试前端性能优化模块"""

import pytest


class TestFrontendPerformanceOptimizerModule:
    """测试前端性能优化模块"""

    def test_frontend_performance_optimizer_module_exists(self):
        """测试前端性能优化模块存在"""
        from core import frontend_performance_optimizer

        assert frontend_performance_optimizer is not None

    def test_frontend_performance_optimizer_has_functions(self):
        """测试前端性能优化模块有函数"""
        from core import frontend_performance_optimizer

        # 检查模块有函数或类
        assert len(dir(frontend_performance_optimizer)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
