# -*- coding: utf-8 -*-
"""Health check utilities for topology service."""

from __future__ import annotations

import time

from services.topology_service.schemas import ServiceHealth

_START_TIME = time.time()


class HealthCheckEngine:
    """Simple health check engine for topology service."""

    async def check(self, service_name: str, index_size: int = 1) -> ServiceHealth:
        uptime_seconds = int(time.time() - _START_TIME)
        status = "ok"
        try:
            import psutil

            if psutil.virtual_memory().percent > 95 or psutil.disk_usage("/").percent > 98:
                status = "degraded"
        except Exception:
            pass
        return ServiceHealth(
            status=status,
            service=service_name,
            index_size=index_size,
            uptime_seconds=uptime_seconds,
        )
