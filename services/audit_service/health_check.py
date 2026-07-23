# -*- coding: utf-8 -*-
"""Health check utilities for audit service."""

from __future__ import annotations

from services.audit_service.schemas import ServiceHealth


class HealthCheckEngine:
    """Simple health check engine for audit service."""

    async def check(self, service_name: str, audit_count: int = 0) -> ServiceHealth:
        return ServiceHealth(
            status="ok",
            service=service_name,
            uptime_seconds=0,
            audit_count=audit_count,
        )
