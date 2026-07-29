# -*- coding: utf-8 -*-
"""Prometheus metrics for the Scenario Memory microservice."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

request_counter = Counter(
    "scenario_memory_requests_total",
    "Total requests",
    ["operation"],
)

latency_histogram = Histogram(
    "scenario_memory_request_duration_seconds",
    "Request latency",
    ["operation"],
)

memory_size_gauge = Counter(
    "scenario_memory_entries_total",
    "Total stored memory entries",
    ["memory_type"],
)
