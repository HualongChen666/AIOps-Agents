# -*- coding: utf-8 -*-
"""Throughput baseline for the performance report.

Runs a CPU-bound micro-benchmark and asserts the environment can sustain at
least 10,000 operations per second.
"""

import time

import pytest


@pytest.mark.performance
def test_computational_throughput_baseline():
    """纯计算吞吐基线（>= 10,000 ops/s）。"""
    n = 200_000

    start = time.perf_counter_ns()
    result = sum(range(n))
    elapsed = (time.perf_counter_ns() - start) / 1e9

    ops_per_sec = n / elapsed
    assert ops_per_sec >= 10_000, f"Throughput too low: {ops_per_sec:.0f} ops/s"
    assert result == n * (n - 1) // 2
