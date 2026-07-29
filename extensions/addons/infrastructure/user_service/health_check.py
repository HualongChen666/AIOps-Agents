# -*- coding: utf-8 -*-
"""Health check utilities for user service."""

from __future__ import annotations

from services.user_service.schemas import ServiceHealth


class HealthCheckEngine:
    """Simple health check engine for user service."""

    async def check(self, service_name: str, user_count: int = 0) -> ServiceHealth:
        return ServiceHealth(
            status="ok",
            service=service_name,
            uptime_seconds=0,
            user_count=user_count,
        )
