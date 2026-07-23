# -*- coding: utf-8 -*-
"""Prometheus metrics for the user microservice."""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram

USERS_CREATED = Counter(
    "users_created_total",
    "Total number of users created",
    ["tenant"],
)
USERS_DELETED = Counter(
    "users_deleted_total",
    "Total number of users deleted",
    ["tenant"],
)
USER_LOGINS = Counter(
    "user_logins_total",
    "Total number of user logins",
    ["tenant"],
)
USER_SESSIONS = Gauge(
    "user_sessions_active",
    "Number of active user sessions",
    ["tenant"],
)
USER_AUTH_DURATION = Histogram(
    "user_auth_duration_seconds",
    "Time spent authenticating users",
)
USER_SAGA_STATUS = Gauge(
    "user_saga_status",
    "Current saga transaction status (0=pending,1=success,2=failed,3=compensating)",
    ["saga_id"],
)
