# -*- coding: utf-8 -*-
"""Health check utilities for workflow service."""

from __future__ import annotations

from services.workflow_service.schemas import ServiceHealth


class HealthCheckEngine:
    """Simple health check engine for workflow service."""

    async def check(self, service_name: str, workflow_count: int = 0) -> ServiceHealth:
        return ServiceHealth(
            status="ok",
            service=service_name,
            uptime_seconds=0,
            workflow_count=workflow_count,
        )
