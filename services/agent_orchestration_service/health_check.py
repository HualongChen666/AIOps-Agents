# -*- coding: utf-8 -*-
"""Health check engine for the agent orchestration service."""

from __future__ import annotations

from .schemas import HealthResponse


class HealthCheckEngine:
    """Return the health status of the service."""

    async def check(self) -> HealthResponse:
        return HealthResponse(status="ok", service="agent-orchestration-service")
