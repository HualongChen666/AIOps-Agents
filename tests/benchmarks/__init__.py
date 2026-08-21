# -*- coding: utf-8 -*-
"""
API Performance Benchmark Tests

This package contains performance benchmark tests for API endpoints.
These tests measure response times, latency percentiles, error rates,
and detect performance regressions.

Performance Benchmarks:
- P50 < 100ms
- P95 < 500ms
- P99 < 1s
- Error rate < 1%

To run benchmark tests:
    pytest tests/benchmarks/ -m benchmark

To run with coverage:
    pytest tests/benchmarks/ -m benchmark --cov=api --cov-report=html
"""
