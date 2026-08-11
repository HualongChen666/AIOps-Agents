# -*- coding: utf-8 -*-
"""Tests for core/feature_flag.py."""

from core.feature_flag import (
    FeatureFlagManager,
    FlagRule,
    FlagStatus,
    FlagType,
    create_feature_flag_manager,
)


def test_factory_and_create():
    mgr = create_feature_flag_manager()
    assert isinstance(mgr, FeatureFlagManager)
    flag = mgr.create_flag(
        key="new_feature",
        name="New Feature",
        description="desc",
        flag_type=FlagType.BOOLEAN,
        fallback_value=True,
    )
    assert flag is not None


def test_evaluate_boolean_and_rules():
    mgr = FeatureFlagManager()
    mgr.initialize()
    mgr.create_flag("flag1", "flag1", "", FlagType.BOOLEAN, fallback_value=True)
    assert mgr.evaluate("flag1") is True

    mgr.update_flag("flag1", status=FlagStatus.DISABLED)
    assert mgr.evaluate("flag1") is False

    mgr.create_flag("rule_flag", "", "", FlagType.BOOLEAN, fallback_value=False)
    rule = FlagRule(name="env", conditions={"env": "test"})
    mgr.add_rule("rule_flag", rule)
    assert mgr.evaluate("rule_flag", context={"env": "test"}) is True


def test_percentage_and_multivariate():
    mgr = FeatureFlagManager()
    mgr.initialize()
    mgr.create_flag("pct", "", "", FlagType.PERCENTAGE, fallback_value=100)
    assert mgr.evaluate("pct", user_id="u1") is True

    mgr.create_flag(
        "mv",
        "",
        "",
        FlagType.MULTIVARIATE,
        fallback_value="default",
        metadata={"variants": [{"value": "a", "percentage": 100}]},
    )
    assert mgr.get_variant("mv", user_id="u1") == "a"


def test_lifecycle_and_list():
    mgr = FeatureFlagManager()
    mgr.initialize()
    mgr.create_flag("x", "X", "", FlagType.BOOLEAN, fallback_value=False)
    assert mgr.get_flag("x")["key"] == "x"
    assert len(mgr.list_flags()) >= 1
    assert mgr.is_enabled("x") is False
    assert mgr.delete_flag("x") is True
    assert mgr.get_flag("x") is None
