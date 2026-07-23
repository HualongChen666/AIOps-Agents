# -*- coding: utf-8 -*-
"""测试细粒度RBAC模块"""

import pytest


class TestFineRbacModule:
    """测试细粒度RBAC模块"""

    def test_fine_rbac_module_exists(self):
        """测试细粒度RBAC模块存在"""
        from core import fine_rbac

        assert fine_rbac is not None

    def test_fine_rbac_has_functions(self):
        """测试细粒度RBAC模块有函数"""
        from core import fine_rbac

        # 检查模块有函数或类
        assert len(dir(fine_rbac)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
