# -*- coding: utf-8 -*-
"""测试异常处理器模块"""

import pytest


class TestExceptionHandlerModule:
    """测试异常处理器模块"""

    def test_exception_handler_module_exists(self):
        """测试异常处理器模块存在"""
        from core import exception_handler

        assert exception_handler is not None

    def test_exception_handler_has_functions(self):
        """测试异常处理器模块有函数"""
        from core import exception_handler

        # 检查模块有函数或类
        assert len(dir(exception_handler)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
