# -*- coding: utf-8 -*-
"""Health check utilities for topology service."""

from __future__ import annotations

from services.topology_service.schemas import ServiceHealth


class HealthCheckEngine:
    """Simple health check engine for topology service."""

    async def check(self, service_name: str, topology_count: int = 0) -> ServiceHealth:
        return ServiceHealth(
            status="ok",
            service=service_name,
            uptime_seconds=0,
            topology_count=topology_count,
        )
