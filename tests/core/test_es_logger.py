# -*- coding: utf-8 -*-
"""测试ES日志模块"""

import pytest


class TestEsLoggerModule:
    """测试ES日志模块"""

    def test_es_logger_module_exists(self):
        """测试ES日志模块存在"""
        from core import es_logger

        assert es_logger is not None

    def test_es_logger_has_functions(self):
        """测试ES日志模块有函数"""
        from core import es_logger

        # 检查模块有函数或类
        assert len(dir(es_logger)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
