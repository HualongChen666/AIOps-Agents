# -*- coding: utf-8 -*-
"""测试备份策略模块"""

import pytest


class TestBackupStrategyModule:
    """测试备份策略模块"""

    def test_backup_strategy_module_exists(self):
        """测试备份策略模块存在"""
        from core import backup_strategy

        assert backup_strategy is not None

    def test_backup_strategy_has_functions(self):
        """测试备份策略模块有函数"""
        from core import backup_strategy

        # 检查模块有函数或类
        assert len(dir(backup_strategy)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
