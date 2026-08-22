# -*- coding: utf-8 -*-
"""Health check for the Knowledge Graph microservice."""

from __future__ import annotations

import time

from .config import settings

_START_TIME = time.time()


class HealthCheckEngine:
    """Simple health check."""

    async def check(self) -> dict:
        uptime_seconds = int(time.time() - _START_TIME)
        status = "ok"
        try:
            import psutil

            if psutil.virtual_memory().percent > 95 or psutil.disk_usage("/").percent > 98:
                status = "degraded"
        except Exception:
            pass
        return {
            "status": status,
            "service": settings.service_name,
            "environment": getattr(settings, "environment", "dev"),
            "uptime_seconds": uptime_seconds,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
