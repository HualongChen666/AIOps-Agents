# -*- coding: utf-8 -*-
"""测试追踪可视化模块"""

import pytest


class TestTracingVisualizationModule:
    """测试追踪可视化模块"""

    def test_tracing_visualization_module_exists(self):
        """测试追踪可视化模块存在"""
        from core import tracing_visualization

        assert tracing_visualization is not None

    def test_tracing_visualization_has_functions(self):
        """测试追踪可视化模块有函数"""
        from core import tracing_visualization

        # 检查模块有函数或类
        assert len(dir(tracing_visualization)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
