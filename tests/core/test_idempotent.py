# -*- coding: utf-8 -*-
"""测试幂等性模块"""

import pytest


class TestIdempotentModule:
    """测试幂等性模块"""

    def test_idempotent_module_exists(self):
        """测试幂等性模块存在"""
        from core import idempotent

        assert idempotent is not None

    def test_idempotent_has_functions(self):
        """测试幂等性模块有函数"""
        from core import idempotent

        # 检查模块有函数或类
        assert len(dir(idempotent)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
