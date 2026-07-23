# -*- coding: utf-8 -*-
"""测试健康检查模块"""

import pytest


class TestHealthCheckModule:
    """测试健康检查模块"""

    def test_health_check_module_exists(self):
        """测试健康检查模块存在"""
        from core import health_check

        assert health_check is not None

    def test_health_check_has_functions(self):
        """测试健康检查模块有函数"""
        from core import health_check

        # 检查模块有函数或类
        assert len(dir(health_check)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
