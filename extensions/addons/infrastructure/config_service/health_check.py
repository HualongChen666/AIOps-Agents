# -*- coding: utf-8 -*-
"""Health check utilities for config service."""

from __future__ import annotations

from services.config_service.schemas import ServiceHealth


class HealthCheckEngine:
    """Simple health check engine for config service."""

    async def check(self, service_name: str, config_count: int = 0) -> ServiceHealth:
        return ServiceHealth(
            status="ok",
            service=service_name,
            uptime_seconds=0,
            config_count=config_count,
        )
