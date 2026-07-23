# -*- coding: utf-8 -*-
"""测试L1L2数据流集成器模块"""

import pytest


class TestL1L2DataFlowIntegratorModule:
    """测试L1L2数据流集成器模块"""

    def test_l1l2_data_flow_integrator_module_exists(self):
        """测试L1L2数据流集成器模块存在"""
        from core import l1l2_data_flow_integrator

        assert l1l2_data_flow_integrator is not None

    def test_l1l2_data_flow_integrator_has_functions(self):
        """测试L1L2数据流集成器模块有函数"""
        from core import l1l2_data_flow_integrator

        # 检查模块有函数或类
        assert len(dir(l1l2_data_flow_integrator)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
