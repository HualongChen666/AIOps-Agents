# -*- coding: utf-8 -*-
"""Health check for the microservice."""

from __future__ import annotations

from .schemas import ServiceHealth


class HealthCheckEngine:
    """Simple health check engine."""

    async def check(self, service_name: str, index_size: int = 0) -> ServiceHealth:
        return ServiceHealth(
            status="ok",
            service=service_name,
            index_size=index_size,
            uptime_seconds=0,
        )
