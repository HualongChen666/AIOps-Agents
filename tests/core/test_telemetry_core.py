# -*- coding: utf-8 -*-
"""Tests for core/telemetry_core.py."""

from core.telemetry_core import (
    get_apm_metrics,
    get_meter,
    get_tracer,
    instrument_asyncpg,
    instrument_fastapi,
    instrument_httpx,
    instrument_redis,
    record_apm_metric,
    reset_apm_metrics,
    shutdown_telemetry,
    trace_operation,
)


def test_initialize_and_getters():
    assert get_tracer("test") is None
    assert get_meter("test") is None


def test_trace_operation():
    with trace_operation(None, "op") as span:
        assert span is None


def test_instrument_noop():
    instrument_fastapi(None)
    instrument_httpx()
    instrument_asyncpg()
    instrument_redis()
    shutdown_telemetry()


def test_apm_metrics():
    record_apm_metric("request_count", 1.0, {"endpoint": "/api"})
    metrics = get_apm_metrics()
    assert metrics["request_count"] == 1.0
    reset_apm_metrics()
    assert get_apm_metrics()["request_count"] == 0
