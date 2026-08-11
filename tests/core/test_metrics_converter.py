# -*- coding: utf-8 -*-
"""Tests for core/metrics_converter.py."""

from core.metrics_converter import MetricsConverter


def test_sqlite_to_prometheus():
    line = MetricsConverter.sqlite_to_prometheus(
        "cpu usage", 12.5, {"host": "local"}, timestamp=1700000000
    )
    assert "cpu_usage" in line
    assert "12.5" in line
    assert 'host="local"' in line
    assert "1700000000000" in line


def test_batch_and_helpers():
    metrics = [
        {"name": "m1", "value": 1.0, "labels": {"a": "1"}},
        {"name": "m2", "value": 2.0, "labels": {}},
    ]
    batch = MetricsConverter.batch_sqlite_to_prometheus(metrics)
    assert "m1" in batch
    assert "m2" in batch

    assert MetricsConverter.sanitize_metric_name("123-metric") == "_123_metric"
    assert MetricsConverter.sanitize_label_name("1key") == "_key"
    assert '\\"' in MetricsConverter.escape_label_value('say "hi"')


def test_system_snapshot_to_prometheus():
    snapshot = {
        "cpu": {"usage_percent": 50.0, "per_core": [10.0, 20.0]},
        "memory": {"usage_percent": 60.0, "total_gb": 16.0, "used_gb": 9.6},
        "disk": {"usage_percent": 70.0, "total_gb": 512.0, "used_gb": 358.0},
    }
    lines = MetricsConverter.system_snapshot_to_prometheus(snapshot)
    assert "aiops_cpu_usage_percent" in lines
    assert "aiops_memory_used_gb" in lines
    assert "aiops_disk_total_gb" in lines
