# -*- coding: utf-8 -*-
"""Tests for core/observability_schema.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.observability_schema import (
    CommonLabels,
    LogRecord,
    MetricInfo,
    TraceContext,
    build_log_record,
)


def test_common_labels():
    labels = CommonLabels(service="api", env="dev", region="us-east", instance="i-1")
    assert labels.service == "api"
    with pytest.raises(ValueError):
        CommonLabels(service="api", env="test", region="us", instance="i-1")


def test_log_record():
    record = LogRecord(
        level="INFO",
        message="hello",
        service="api",
        env="dev",
        region="us-east",
        instance="i-1",
    )
    assert record.level == "INFO"
    with pytest.raises(ValueError):
        LogRecord(
            level="FATAL",
            message="hello",
            service="api",
            env="dev",
            region="us-east",
            instance="i-1",
        )


def test_metric_info_and_trace_context():
    metric = MetricInfo(name="cpu", description="cpu usage", type="gauge", labels=["host"])
    assert metric.name == "cpu"
    trace = TraceContext(trace_id="a" * 32, span_id="b" * 16)
    assert trace.trace_id == "a" * 32
    assert trace.to_header().startswith("00-")


def test_build_log_record():
    payload = {
        "level": "ERROR",
        "message": "boom",
        "service": "api",
        "env": "dev",
        "region": "us-east",
        "instance": "i-1",
    }
    record = build_log_record(payload)
    assert record.message == "boom"
