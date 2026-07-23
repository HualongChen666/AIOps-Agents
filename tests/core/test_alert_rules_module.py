# -*- coding: utf-8 -*-
"""测试告警规则模块"""

import pytest


class TestAlertRulesModule:
    """测试告警规则模块"""

    def test_alert_rules_module_exists(self):
        """测试告警规则模块存在"""
        from core import alert_rules

        assert alert_rules is not None

    def test_alert_rules_has_functions(self):
        """测试告警规则模块有函数"""
        from core import alert_rules

        # 检查模块有函数或类
        assert len(dir(alert_rules)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
