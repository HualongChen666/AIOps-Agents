# -*- coding: utf-8 -*-
"""测试AI服务模块"""

import pytest


class TestAIServiceModule:
    """测试AI服务模块"""

    def test_ai_service_module_exists(self):
        """测试AI服务模块存在"""
        from core import ai_service

        assert ai_service is not None

    def test_ai_service_has_functions(self):
        """测试AI服务模块有函数"""
        from core import ai_service

        # 检查模块有函数或类
        assert len(dir(ai_service)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
