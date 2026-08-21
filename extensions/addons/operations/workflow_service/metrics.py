# -*- coding: utf-8 -*-
"""Prometheus metrics for the workflow microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

# Use a separate registry for tests to avoid conflicts
_registry = CollectorRegistry()

WORKFLOWS_CREATED = Counter(
    "workflows_created_total",
    "Total number of workflows created",
    ["priority"],
    registry=_registry,
)
WORKFLOWS_COMPLETED = Counter(
    "workflows_completed_total",
    "Total number of workflows completed",
    ["status"],
    registry=_registry,
)
WORKFLOW_EXECUTION_DURATION = Histogram(
    "workflow_execution_duration_seconds",
    "Time spent executing workflows",
    ["workflow_id"],
    registry=_registry,
)
WORKFLOW_NODE_EXECUTION_DURATION = Histogram(
    "workflow_node_execution_duration_seconds",
    "Time spent executing workflow nodes",
    ["node_id"],
    registry=_registry,
)
WORKFLOW_RETRY_ATTEMPTS = Counter(
    "workflow_retry_attempts_total",
    "Total number of workflow retry attempts",
    ["node_id"],
    registry=_registry,
)
WORKFLOW_SCHEDULED_TASKS = Gauge(
    "workflow_scheduled_tasks",
    "Number of scheduled workflow tasks",
    ["workflow_id"],
    registry=_registry,
)
WORKFLOW_ACTIVE_EXECUTIONS = Gauge(
    "workflow_active_executions",
    "Number of active workflow executions",
    registry=_registry,
)
WORKFLOW_VERSION_COMMITS = Counter(
    "workflow_version_commits_total",
    "Total number of workflow version commits",
    ["workflow_id"],
    registry=_registry,
)
WORKFLOW_TEMPLATE_RENDERS = Counter(
    "workflow_template_renders_total",
    "Total number of workflow template renders",
    ["template_id"],
    registry=_registry,
)
WORKFLOW_SAGA_STATUS = Gauge(
    "workflow_saga_status",
    "Current saga transaction status (0=pending,1=success,2=failed,3=compensating)",
    ["saga_id"],
    registry=_registry,
)
