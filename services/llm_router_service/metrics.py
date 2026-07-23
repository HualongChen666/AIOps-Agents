# -*- coding: utf-8 -*-
"""Prometheus metrics for the LLM router microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

ROUTER_REQUESTS_TOTAL = Counter(
    "llm_router_requests_total",
    "Total number of LLM router requests",
    ["provider", "model", "strategy"],
)
ROUTER_REQUEST_FAILURES_TOTAL = Counter(
    "llm_router_request_failures_total",
    "Total number of LLM router request failures",
    ["provider", "model", "error"],
)
ROUTER_RETRIES_TOTAL = Counter(
    "llm_router_retries_total",
    "Total number of LLM router retries",
    ["provider", "model", "policy"],
)
ROUTER_LATENCY = Histogram(
    "llm_router_request_latency_seconds",
    "LLM router request latency",
    ["provider", "model"],
)
ROUTER_PROVIDER_LATENCY = Histogram(
    "llm_router_provider_latency_seconds",
    "Provider call latency",
    ["provider", "model"],
)
ROUTER_COST = Histogram(
    "llm_router_request_cost_dollars",
    "LLM router request cost",
    ["provider", "model"],
)
ROUTER_TOKENS = Histogram(
    "llm_router_tokens_total",
    "Total number of tokens used",
    ["provider", "model"],
)
ROUTER_CIRCUIT_BREAKER_STATE = Gauge(
    "llm_router_circuit_breaker_state",
    "Circuit breaker state per model",
    ["provider", "model"],
)
ROUTER_MODEL_AVAILABILITY = Gauge(
    "llm_router_model_availability",
    "Model availability",
    ["provider", "model"],
)
ROUTER_HOURLY_COST = Gauge(
    "llm_router_hourly_cost_dollars",
    "Hourly cost",
    ["service"],
)
ROUTER_HOURLY_REQUESTS = Gauge(
    "llm_router_hourly_requests",
    "Hourly request count",
    ["service"],
)
ROUTER_ACTIVE_MODELS = Gauge(
    "llm_router_active_models",
    "Number of active models",
    ["service"],
)
ROUTER_CACHE_HITS = Counter(
    "llm_router_cache_hits_total",
    "Cache hits",
    ["provider", "model"],
)
ROUTER_CACHE_MISSES = Counter(
    "llm_router_cache_misses_total",
    "Cache misses",
    ["provider", "model"],
)
ROUTER_BATCH_REQUESTS = Counter(
    "llm_router_batch_requests_total",
    "Batch routing requests",
    ["service"],
)
ROUTER_BATCH_SIZE = Histogram(
    "llm_router_batch_size",
    "Batch request size",
    ["service"],
)
ROUTER_PROVIDER_FAILURES = Counter(
    "llm_router_provider_failures_total",
    "Provider call failures",
    ["provider", "model"],
)
ROUTER_FALLBACK_TOTAL = Counter(
    "llm_router_fallback_total",
    "Fallback to alternate model",
    ["from_model", "to_model"],
)
ROUTER_COST_OPTIMIZATION_SAVINGS = Gauge(
    "llm_router_cost_optimization_savings_dollars",
    "Estimated cost savings from routing",
    ["service"],
)
ROUTER_LOAD_BALANCE_SCORE = Gauge(
    "llm_router_load_balance_score",
    "Load balance score per model",
    ["provider", "model"],
)
ROUTER_RETRY_POLICY_USAGE = Counter(
    "llm_router_retry_policy_usage_total",
    "Retry policy usage",
    ["policy"],
)
