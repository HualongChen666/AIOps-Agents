# -*- coding: utf-8 -*-
"""Prometheus metrics for the repair microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

REPAIR_TASKS_CREATED = Counter(
    "repair_tasks_created_total",
    "Total number of repair tasks created",
    ["platform"],
)
REPAIR_TASKS_COMPLETED = Counter(
    "repair_tasks_completed_total",
    "Total number of repair tasks completed",
    ["status", "platform"],
)
REPAIR_EXECUTION_DURATION = Histogram(
    "repair_execution_duration_seconds",
    "Time spent executing repair runbooks",
    ["platform"],
)
REPAIR_VERIFICATION_DURATION = Histogram(
    "repair_verification_duration_seconds",
    "Time spent verifying repair results",
    ["strategy"],
)
REPAIR_ROLLBACK_COUNT = Counter(
    "repair_rollback_total",
    "Total number of repair rollbacks",
    ["result"],
)
REPAIR_AUDIT_EVENTS = Counter(
    "repair_audit_events_total",
    "Total number of repair audit events",
    ["event_type"],
)
REPAIR_SAGA_STATUS = Gauge(
    "repair_saga_status",
    "Current saga transaction status (0=pending,1=success,2=failed,3=compensating)",
    ["saga_id"],
)
REPAIR_ACTIVE_EXECUTIONS = Gauge(
    "repair_active_executions",
    "Number of active repair executions",
)
