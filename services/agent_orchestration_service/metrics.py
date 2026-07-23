# -*- coding: utf-8 -*-
"""Prometheus metrics for the Agent Orchestration microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, Info

AGENT_INFO = Info("agent_orchestration_service", "Agent Orchestration service information")

AGENT_REQUESTS_TOTAL = Counter(
    "agent_requests_total",
    "Total number of agent orchestration requests",
    ["operation", "agent_type"],
)

AGENT_REQUEST_FAILURES_TOTAL = Counter(
    "agent_request_failures_total",
    "Total number of agent orchestration request failures",
    ["operation", "agent_type", "error"],
)

AGENT_REQUEST_LATENCY = Histogram(
    "agent_request_latency_seconds",
    "Latency of agent orchestration requests in seconds",
    ["operation"],
)

AGENT_ACTIVE_AGENTS = Gauge(
    "agent_active_agents",
    "Number of active agents in a plan",
    ["agent_type"],
)

AGENT_PLAN_SIZE = Gauge(
    "agent_plan_size",
    "Size of the current execution plan",
)

AGENT_CACHE_HITS = Counter(
    "agent_cache_hits_total",
    "Total number of cache hits",
)

AGENT_CACHE_MISSES = Counter(
    "agent_cache_misses_total",
    "Total number of cache misses",
)

AGENT_RETRIES_TOTAL = Counter(
    "agent_retries_total",
    "Total number of retries",
    ["operation"],
)

AGENT_ERROR_RECOVERIES_TOTAL = Counter(
    "agent_error_recoveries_total",
    "Total number of error recoveries",
    ["strategy"],
)
