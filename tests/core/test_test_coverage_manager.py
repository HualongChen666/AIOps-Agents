# -*- coding: utf-8 -*-
"""Tests for core/test_coverage_manager.py."""

from core.test_coverage_manager import (
    CoverageLevel,
    TestCoverageManager,
    get_coverage_manager,
)


def test_get_coverage_manager():
    mgr = get_coverage_manager()
    assert isinstance(mgr, TestCoverageManager)


def test_add_and_get_module_coverage():
    mgr = TestCoverageManager()
    assert mgr.add_module_coverage("mod1", "Module 1", 100, 85) is True
    assert mgr.add_module_coverage("mod1", "Module 1", 0, 0) is False
    coverage = mgr.get_module_coverage("mod1")
    assert coverage.coverage_percentage == 85.0
    assert coverage.coverage_level == CoverageLevel.GOOD


def test_threshold_and_summary():
    mgr = TestCoverageManager()
    mgr.add_module_coverage("mod1", "Module 1", 100, 75)
    result = mgr.check_coverage_threshold("mod1", "default")
    assert "meets_minimum" in result
    summary = mgr.get_coverage_summary()
    assert "average_coverage" in summary
    report = mgr.get_coverage_report()
    assert "summary" in report
    assert "modules_below_threshold" in report
    assert "recommendations" in report
