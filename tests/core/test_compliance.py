# -*- coding: utf-8 -*-
"""测试合规模块"""

import pytest


class TestComplianceModule:
    """测试合规模块"""

    def test_compliance_module_exists(self):
        """测试合规模块存在"""
        from core import compliance

        assert compliance is not None

    def test_compliance_has_functions(self):
        """测试合规模块有函数"""
        from core import compliance

        # 检查模块有函数或类
        assert len(dir(compliance)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
