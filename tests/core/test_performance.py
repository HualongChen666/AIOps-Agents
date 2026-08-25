# -*- coding: utf-8 -*-
"""Unit tests for the performance optimizer."""

import pytest  # noqa: F401  # Imported for test setup

from core.performance_optimizer import (
    PerformanceMetric,
    get_performance_optimizer,
)


def test_cache_operations():
    opt = get_performance_optimizer()
    opt.cache_set("metrics", "key1", "value1")
    assert opt.cache_get("metrics", "key1") == "value1"
    assert opt.cache_delete("metrics", "key1") is True
    assert opt.cache_get("metrics", "key1") is None


def test_cache_clear():
    opt = get_performance_optimizer()
    opt.cache_set("metrics", "key1", "value1")
    count = opt.cache_clear("metrics")
    assert count >= 0


def test_monitor_performance_and_report():
    opt = get_performance_optimizer()
    opt.monitor_performance("test", PerformanceMetric.RESPONSE_TIME, 0.1)
    report = opt.get_performance_report()
    assert "bottlenecks" in report


def test_optimize_memory_usage():
    opt = get_performance_optimizer()
    result = opt.optimize_memory_usage()  # noqa: F841  # Variable for test verification
    assert result is None or isinstance(result, dict)


def test_optimize_database_query():
    opt = get_performance_optimizer()

    @opt.optimize_database_query
    def sample_query():
        return "result"

    assert sample_query() == "result"


@pytest.mark.asyncio
async def test_with_semaphore():
    opt = get_performance_optimizer()

    async def work():
        return 42

    result = await opt.with_semaphore(
        "api_requests", work
    )  # noqa: F841  # Variable for test verification
    assert result == 42  # noqa: F841  # Variable for test verification
