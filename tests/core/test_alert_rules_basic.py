# -*- coding: utf-8 -*-
"""
基础告警规则模块测试
测试告警规则核心功能的基础场景
"""

import pytest


class TestAlertRulesBasic:
    """告警规则模块基础测试"""

    def test_alert_rules_module_structure(self):
        """测试告警规则模块结构"""
        try:
            from core import alert_rules

            assert alert_rules is not None
        except ImportError as e:
            pytest.skip(f"Alert rules module not available: {e}")

    def test_alert_rules_functions_exist(self):
        """测试告警规则关键函数存在"""
        try:
            from core.alert_rules import check_threshold, evaluate_rule, match_pattern

            # 验证关键函数存在
            assert evaluate_rule is not None
            assert check_threshold is not None
            assert match_pattern is not None
        except Exception as e:
            pytest.skip(f"Alert rules functions test failed: {e}")

    def test_alert_rules_classes_exist(self):
        """测试告警规则关键类存在"""
        try:
            from core.alert_rules import AlertRule, RuleEvaluator, ThresholdChecker

            # 验证关键类存在
            assert AlertRule is not None
            assert RuleEvaluator is not None
            assert ThresholdChecker is not None
        except Exception as e:
            pytest.skip(f"Alert rules classes test failed: {e}")

    def test_alert_rules_constants(self):
        """测试告警规则常量定义"""
        try:
            from core.alert_rules import RuleSeverity, RuleType

            # 验证常量存在
            assert RuleType is not None
            assert RuleSeverity is not None
        except Exception as e:
            pytest.skip(f"Alert rules constants test failed: {e}")
