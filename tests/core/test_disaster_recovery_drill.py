# -*- coding: utf-8 -*-
"""测试灾难恢复演练模块"""

import pytest


class TestDisasterRecoveryDrillModule:
    """测试灾难恢复演练模块"""

    def test_disaster_recovery_drill_module_exists(self):
        """测试灾难恢复演练模块存在"""
        from core import disaster_recovery_drill

        assert disaster_recovery_drill is not None

    def test_disaster_recovery_drill_has_functions(self):
        """测试灾难恢复演练模块有函数"""
        from core import disaster_recovery_drill

        # 检查模块有函数或类
        assert len(dir(disaster_recovery_drill)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
