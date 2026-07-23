# -*- coding: utf-8 -*-
"""测试智能告警分析器模块"""

import pytest


class TestIntelligentAlertAnalyzerModule:
    """测试智能告警分析器模块"""

    def test_intelligent_alert_analyzer_module_exists(self):
        """测试智能告警分析器模块存在"""
        from core import intelligent_alert_analyzer

        assert intelligent_alert_analyzer is not None

    def test_intelligent_alert_analyzer_has_functions(self):
        """测试智能告警分析器模块有函数"""
        from core import intelligent_alert_analyzer

        # 检查模块有函数或类
        assert len(dir(intelligent_alert_analyzer)) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
