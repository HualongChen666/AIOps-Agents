# -*- coding: utf-8 -*-
"""Health check for the Scenario Memory microservice."""

from __future__ import annotations

from .config import settings


class HealthCheckEngine:
    """Simple health check."""

    async def check(self) -> dict:
        """Return health status."""
        return {
            "status": "ok",
            "service": settings.service_name,
            "environment": settings.environment,
        }
