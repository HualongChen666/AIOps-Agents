# -*- coding: utf-8 -*-
"""Tests for core/metrics_history.py."""

from core.metrics_history import MetricsHistory


def test_push_and_to_dict():
    history = MetricsHistory(maxlen=10)
    history.push(10.0, 20.0, 30.0, "12:00:00")
    data = history.to_dict()
    assert data["cpu"] == [10.0]
    assert data["memory"] == [20.0]
    assert data["net_in"] == [30.0]


def test_push_metric_query_and_latest():
    history = MetricsHistory(maxlen=10)
    history.push_metric("cpu", 55.0, service="svc")
    history.push_metric("cpu", 60.0, service="svc")
    assert history.sample_count == 2
    assert history.get_latest("cpu", service="svc") == 60.0
    assert len(history.query("cpu", service="svc")) == 2


def test_clear_and_size():
    history = MetricsHistory(maxlen=10)
    history.push(1.0, 2.0, 3.0, "12:00:00")
    assert history.size == 1
    history.clear()
    assert history.size == 0
    assert history.sample_count == 0


def test_dynamic_threshold():
    history = MetricsHistory(maxlen=100)
    for i in range(35):
        history.push_metric("cpu", float(i), service="global")
    threshold, info = history.get_dynamic_threshold("cpu", 50.0, service="global")
    assert isinstance(threshold, float)
    assert "source" in info


def test_invalid_maxlen():
    history = MetricsHistory(maxlen=-5)
    assert history.size == 0
