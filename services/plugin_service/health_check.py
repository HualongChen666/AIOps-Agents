# -*- coding: utf-8 -*-
"""Health check utilities for the plugin microservice."""

from __future__ import annotations

import time

from pydantic import BaseModel, Field

_STARTED_AT = time.monotonic()


class ServiceHealth(BaseModel):
    """Health payload returned by ``GET /health``."""

    status: str = Field(..., description="ok / degraded")
    service: str = Field(..., description="Service name")
    uptime_seconds: float = Field(..., description="Process uptime in seconds")
    database: str = Field(..., description="Database backend in use")
    plugin_count: int = Field(0, description="Number of registered plugins")


class HealthCheckEngine:
    """Health check engine for the plugin microservice."""

    async def check(
        self,
        service_name: str,
        plugin_count: int = 0,
        database: str = "unknown",
    ) -> ServiceHealth:
        return ServiceHealth(
            status="ok",
            service=service_name,
            uptime_seconds=round(time.monotonic() - _STARTED_AT, 3),
            database=database,
            plugin_count=plugin_count,
        )
