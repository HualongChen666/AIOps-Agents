# -*- coding: utf-8 -*-
# tests/test_alert_rules.py
# 告警规则单元测试
import pytest

from core.alert_rules import (  # noqa: F401
    add_alert_rule,
    disable_rule,
    enable_rule,
    evaluate_alert_rule,
    evaluate_all_rules,
    get_alert_rule,
    get_all_alert_rules,
    get_enabled_rules,
    load_alert_rules,
    remove_alert_rule,
    reset_alert_rules,
)


class TestAlertRulesBasic:
    """告警规则基础测试"""

    def test_get_alert_rule(self):
        """测试获取告警规则"""
        rule = get_alert_rule("cpu_high")
        assert rule is not None
        assert rule["enabled"] is True
        assert "threshold" in rule

    def test_get_alert_rule_nonexistent(self):
        """测试获取不存在的告警规则"""
        rule = get_alert_rule("nonexistent_rule")
        assert rule is None

    def test_get_all_alert_rules(self):
        """测试获取所有告警规则"""
        rules = get_all_alert_rules()
        assert isinstance(rules, dict)
        assert len(rules) > 0
        assert "cpu_high" in rules

    def test_add_alert_rule(self):
        """测试添加告警规则"""
        new_rule = {
            "enabled": True,
            "threshold": 80.0,
            "severity": "warning",
            "description": "Test rule",
        }
        add_alert_rule("test_rule", new_rule)

        rule = get_alert_rule("test_rule")
        assert rule is not None
        assert rule["threshold"] == 80.0

    def test_remove_alert_rule(self):
        """测试删除告警规则"""
        add_alert_rule("temp_rule", {"enabled": True, "threshold": 50.0})
        result = remove_alert_rule("temp_rule")

        assert result is True
        assert get_alert_rule("temp_rule") is None

    def test_remove_alert_rule_nonexistent(self):
        """测试删除不存在的告警规则"""
        result = remove_alert_rule("nonexistent_rule")
        assert result is False


class TestAlertRuleEvaluation:
    """告警规则评估测试"""

    def test_evaluate_alert_rule_triggered(self):
        """测试告警规则触发"""
        alert = evaluate_alert_rule("cpu_high", 95.0)

        assert alert is not None
        assert alert["rule_name"] == "cpu_high"
        assert alert["severity"] == "warning"
        assert alert["current_value"] == 95.0

    def test_evaluate_alert_rule_not_triggered(self):
        """测试告警规则未触发"""
        alert = evaluate_alert_rule("cpu_high", 50.0)

        assert alert is None

    def test_evaluate_alert_rule_disabled(self):
        """测试禁用的告警规则"""
        disable_rule("cpu_high")
        alert = evaluate_alert_rule("cpu_high", 95.0)

        assert alert is None
        # Re-enable for other tests
        enable_rule("cpu_high")

    def test_evaluate_all_rules(self):
        """测试评估所有告警规则"""
        metrics = {
            "cpu": 95.0,
            "memory": 90.0,
            "disk": 85.0,
        }

        alerts = evaluate_all_rules(metrics)

        assert isinstance(alerts, list)
        # CPU should trigger both high and critical
        cpu_alerts = [a for a in alerts if "cpu" in a["rule_name"]]
        assert len(cpu_alerts) >= 1


class TestAlertRuleManagement:
    """告警规则管理测试"""

    def test_get_enabled_rules(self):
        """测试获取启用的告警规则"""
        enabled_rules = get_enabled_rules()

        assert isinstance(enabled_rules, list)
        assert len(enabled_rules) > 0
        assert "cpu_high" in enabled_rules

    def test_disable_rule(self):
        """测试禁用告警规则"""
        result = disable_rule("cpu_high")

        assert result is True
        assert "cpu_high" not in get_enabled_rules()
        # Re-enable for other tests
        enable_rule("cpu_high")

    def test_disable_rule_nonexistent(self):
        """测试禁用不存在的告警规则"""
        result = disable_rule("nonexistent_rule")
        assert result is False

    def test_enable_rule(self):
        """测试启用告警规则"""
        disable_rule("cpu_high")
        result = enable_rule("cpu_high")

        assert result is True
        assert "cpu_high" in get_enabled_rules()

    def test_enable_rule_nonexistent(self):
        """测试启用不存在的告警规则"""
        result = enable_rule("nonexistent_rule")
        assert result is False


class TestAlertRulesReset:
    """告警规则重置测试"""

    def test_reset_alert_rules(self):
        """测试重置告警规则"""
        # Add a custom rule
        add_alert_rule("custom_rule", {"enabled": True, "threshold": 100.0})

        # Reset
        reset_alert_rules()

        # Custom rule should be gone
        assert get_alert_rule("custom_rule") is None
        # Default rules should be present
        assert get_alert_rule("cpu_high") is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
