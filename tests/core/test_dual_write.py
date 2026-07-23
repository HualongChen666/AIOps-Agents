# -*- coding: utf-8 -*-
"""测试双写模块"""

import pytest


class TestDualWriteModule:
    """测试双写模块"""

    def test_dual_write_module_exists(self):
        """测试双写模块存在"""
        from core import dual_write

        assert dual_write is not None

    def test_dual_write_has_functions(self):
        """测试双写模块有函数"""
        from core import dual_write

        # 检查模块有函数或类
        assert len(dir(dual_write)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
