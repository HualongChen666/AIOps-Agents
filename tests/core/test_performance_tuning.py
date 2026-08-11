# -*- coding: utf-8 -*-
"""Tests for core/performance_tuning.py."""

from core.performance_tuning import (
    apply_comprehensive_tuning,
    apply_environment_tuning,
    apply_python_optimizations,
    apply_system_limits,
    get_performance_recommendations,
    get_uvicorn_config,
    monitor_performance_metrics,
)


def test_system_limits():
    result = apply_system_limits()
    assert "max_open_files" in result


def test_python_optimizations():
    result = apply_python_optimizations()
    assert "gc_threshold" in result


def test_uvicorn_config():
    config = get_uvicorn_config()
    assert config["log_level"] == "info"


def test_environment_tuning():
    result = apply_environment_tuning()
    assert "python_optimize" in result


def test_recommendations():
    result = get_performance_recommendations()
    assert "recommendations" in result


def test_comprehensive_and_monitor():
    result = apply_comprehensive_tuning()
    assert "steps" in result
    assert "system_limits" in result["steps"]
    metrics = monitor_performance_metrics()
    assert "memory" in metrics
    assert "used_percent" in metrics["memory"]
