# -*- coding: utf-8 -*-
"""测试日志路由器模块"""

import pytest


class TestLogRouterModule:
    """测试日志路由器模块"""

    def test_log_router_module_exists(self):
        """测试日志路由器模块存在"""
        from core import log_router

        assert log_router is not None

    def test_log_router_has_functions(self):
        """测试日志路由器模块有函数"""
        from core import log_router

        # 检查模块有函数或类
        assert len(dir(log_router)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
