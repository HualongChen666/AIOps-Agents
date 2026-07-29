# -*- coding: utf-8 -*-
"""Health check for the LLM router microservice."""

from __future__ import annotations

from .schemas import ServiceHealth


class HealthCheckEngine:
    """Simple health check engine for the LLM router service."""

    async def check(self, service_name: str, model_count: int = 0) -> ServiceHealth:
        return ServiceHealth(
            status="ok", service=service_name, model_count=model_count, uptime_seconds=0
        )
