# -*- coding: utf-8 -*-
"""Prometheus metrics for the audit microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

AUDIT_EVENTS_RECORDED = Counter(
    "audit_events_recorded_total",
    "Total number of audit events recorded",
    ["severity", "tenant"],
)
AUDIT_LOGS_RECORDED = Counter(
    "audit_logs_recorded_total",
    "Total number of operation logs recorded",
    ["tenant"],
)
AUDIT_REPORTS_GENERATED = Counter(
    "audit_reports_generated_total",
    "Total number of compliance reports generated",
    ["report_type"],
)
AUDIT_DATA_ENCRYPTED = Counter(
    "audit_data_encrypted_total",
    "Total number of audit data encryption operations",
    ["tenant"],
)
AUDIT_DATA_DECRYPTED = Counter(
    "audit_data_decrypted_total",
    "Total number of audit data decryption operations",
    ["tenant"],
)
AUDIT_RETENTION_POLICIES = Gauge(
    "audit_retention_policies",
    "Number of retention policies",
    ["tenant"],
)
AUDIT_ALERTS_TRIGGERED = Counter(
    "audit_alerts_triggered_total",
    "Total number of audit alerts triggered",
    ["severity"],
)
AUDIT_EVENT_ROUTING_DURATION = Histogram(
    "audit_event_routing_duration_seconds",
    "Time spent routing audit events",
)
AUDIT_SAGA_STATUS = Gauge(
    "audit_saga_status",
    "Current saga transaction status (0=pending,1=success,2=failed,3=compensating)",
    ["saga_id"],
)
