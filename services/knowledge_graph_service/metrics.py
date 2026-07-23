# -*- coding: utf-8 -*-
"""Prometheus metrics for the Knowledge Graph microservice."""

from __future__ import annotations

from prometheus_client import Counter, Histogram

request_counter = Counter(
    "knowledge_graph_requests_total",
    "Total requests",
    ["operation"],
)

latency_histogram = Histogram(
    "knowledge_graph_request_duration_seconds",
    "Request latency",
    ["operation"],
)

graph_size_gauge = Counter(
    "knowledge_graph_entries_total",
    "Total stored graph entries",
    ["entry_type"],
)
