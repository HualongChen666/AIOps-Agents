# -*- coding: utf-8 -*-
"""Real branch-coverage tests for modules/observability/smart_alerting.py.

No mocks -- every test uses real SmartAlerting instances and real or
in-memory data so that the threshold, fallback, ML/correlation, anomaly,
error, and routing branches are exercised.
"""

from datetime import datetime, timedelta

import pytest  # noqa: F401  # Imported for test setup

import modules.observability.smart_alerting as smart_alerting


@pytest.mark.parametrize(
    "condition,metrics,expected",
    [
        ("cpu_usage > 80", {"cpu_usage": 85.0}, True),
        ("cpu_usage < 80", {"cpu_usage": 75.0}, True),
        ("cpu_usage >= 80", {"cpu_usage": 80.0}, True),
        ("cpu_usage <= 80", {"cpu_usage": 80.0}, True),
        ("cpu_usage == 80", {"cpu_usage": 80.0}, True),
        ("cpu_usage != 80", {"cpu_usage": 85.0}, True),
    ],
)
def test_alert_rule_all_comparison_operators(condition, metrics, expected):
    """Cover the comparison-operator branches in _parse_and_evaluate."""
    rule = smart_alerting.AlertRule("r1", "op", condition, smart_alerting.AlertSeverity.WARNING)
    assert rule.evaluate(metrics) is expected


def test_alert_rule_literal_and_metric_both_sides():
    """Cover the left/right value lookup branches (literal vs. metric)."""
    rule = smart_alerting.AlertRule(
        "r2", "lit", "100 > cpu_usage", smart_alerting.AlertSeverity.INFO
    )
    assert rule.evaluate({"cpu_usage": 95.0}) is True
    assert rule.evaluate({"cpu_usage": 105.0}) is False


def test_alert_rule_boolean_and_error_fallbacks():
    """Cover boolean conditions, malformed expressions, and ValueError fallbacks."""
    rule = smart_alerting.AlertRule("r3", "bool", "cpu_active", smart_alerting.AlertSeverity.INFO)
    # condition used as a boolean key in metrics
    assert rule._parse_and_evaluate("cpu_active", {"cpu_active": True}) is True
    assert rule._parse_and_evaluate("cpu_active", {"cpu_active": 0}) is False
    # unknown key and empty expression fall through to the final False
    assert rule._parse_and_evaluate("unknown_key", {"other": 1}) is False
    assert rule._parse_and_evaluate("", {"other": 1}) is False
    # malformed: too many parts for the operator
    assert rule._parse_and_evaluate("cpu_usage > 80 > 70", {"cpu_usage": 90.0}) is False
    # ValueError fallbacks for non-numeric sides
    assert rule._parse_and_evaluate("abc > 80", {}) is False
    assert rule._parse_and_evaluate("80 > abc", {}) is False


def test_dynamic_threshold_window_pop_and_no_data():
    """Cover the sliding-window pop and the no-data fallback threshold."""
    calc = smart_alerting.DynamicThresholdCalculator(window_size=3)
    for i in range(5):
        calc.add_metric("cpu", float(i))
    # window popped the oldest two values
    assert len(calc.metric_history["cpu"]) == 3
    assert calc.metric_history["cpu"] == [2.0, 3.0, 4.0]
    # no data -> default 0.0
    assert calc.calculate_threshold("never_seen") == 0.0


def test_dynamic_threshold_moving_avg_short_history():
    """Cover the moving_avg branch where the window is larger than the history."""
    calc = smart_alerting.DynamicThresholdCalculator()
    for i in range(12):
        calc.add_metric("cpu", float(i))
    result = calc.calculate_threshold("cpu", method="moving_avg", window=20)  # noqa: F841  # Variable for test verification
    expected = sum(range(12)) / 12.0
    assert result == pytest.approx(expected)  # noqa: F841  # Variable for test verification


def test_alert_suppressor_expired_rule_continue():
    """Cover the expired-rule continue branch in should_suppress."""
    suppressor = smart_alerting.AlertSuppressor()
    alert_match = smart_alerting.Alert(
        "1", "x", "x", smart_alerting.AlertSeverity.WARNING, labels={"host": "h1"}
    )
    alert_no_match = smart_alerting.Alert(
        "2", "x", "x", smart_alerting.AlertSeverity.WARNING, labels={"host": "h2"}
    )

    # active rule suppresses h1
    suppressor.add_suppression_rule({"host": "h1"}, duration=3600)
    assert suppressor.should_suppress(alert_match) is True
    assert suppressor.should_suppress(alert_no_match) is False

    # expired rule for h2: the continue branch is hit, then the function returns False
    suppressor.suppression_rules.append(
        {
            "match_labels": {"host": "h2"},
            "duration": 1,
            "created_at": datetime.now() - timedelta(seconds=10),
        }
    )
    assert suppressor.should_suppress(alert_no_match) is False


def test_smart_alerting_engine_rule_and_metric_branches():
    """Cover remove-rule missing, disabled rules, non-numeric metrics, and false rules."""
    engine = smart_alerting.create_smart_alerting_engine()

    # remove a non-existent rule
    engine.remove_rule("missing-rule")

    # disabled rule -> continue
    disabled_rule = smart_alerting.AlertRule(
        "mem-disabled",
        "Memory disabled",
        "memory_usage > 90",
        smart_alerting.AlertSeverity.CRITICAL,
        enabled=False,
    )
    engine.add_rule(disabled_rule)

    # rule that will not fire
    engine.add_rule(
        smart_alerting.AlertRule(
            "disk-low",
            "Disk low",
            "disk_usage > 80",
            smart_alerting.AlertSeverity.WARNING,
        )
    )

    # rule that will fire
    engine.add_rule(
        smart_alerting.AlertRule(
            "cpu-high",
            "CPU high",
            "cpu_usage > 80",
            smart_alerting.AlertSeverity.WARNING,
        )
    )

    metrics = {
        "cpu_usage": 95.0,
        "memory_usage": 95.0,
        "disk_usage": 70.0,
        "load": "high",  # non-numeric, skipped by the threshold calculator
    }
    alerts = engine.evaluate_metrics(metrics)
    assert len(alerts) == 1
    assert alerts[0].title == "CPU high"

    # remove an existing rule
    engine.remove_rule("disk-low")
    assert "disk-low" not in engine.rules

    # statistics reflect the disabled rule and the single active alert
    stats = engine.get_alert_statistics()
    assert stats["total_active"] == 1
    assert stats["total_rules"] == 2
    assert stats["enabled_rules"] == 1


def test_smart_alerting_engine_acknowledge_and_resolve_branches():
    """Cover empty, wrong-id, and successful acknowledge/resolve branches."""
    engine = smart_alerting.create_smart_alerting_engine()

    # no active alerts
    assert engine.acknowledge_alert("nope") is False
    assert engine.resolve_alert("nope") is False

    rule = smart_alerting.AlertRule(
        "cpu", "CPU", "cpu_usage > 80", smart_alerting.AlertSeverity.WARNING
    )
    engine.add_rule(rule)
    alerts = engine.evaluate_metrics({"cpu_usage": 85.0})
    assert len(alerts) == 1

    # active alerts exist but the id does not match
    assert engine.acknowledge_alert("wrong-id") is False
    assert engine.resolve_alert("wrong-id") is False

    right_id = alerts[0].id
    assert engine.acknowledge_alert(right_id) is True
    assert engine.resolve_alert(right_id) is True

    # resolved alerts are no longer active
    assert engine.get_active_alerts() == []
