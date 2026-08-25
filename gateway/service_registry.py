# -*- coding: utf-8 -*-
"""Add-on service registry with lazy health checks.

Provides a central place to discover whether remote add-on microservices are
reachable before the gateway tries to call them.  If a service is not healthy
we return a clear error instead of a connection timeout.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

from gateway.services_client import _DEFAULT_SERVICE_URLS, _get_http_client

logger = logging.getLogger(__name__)


@dataclass
class ServiceHealth:
    """Health status for a single add-on service."""

    name: str
    url_env: str
    url: str
    healthy: bool
    error: Optional[str] = None


class AddOnServiceRegistry:
    """Registry that pings all configured add-on services and caches results."""

    def __init__(self) -> None:
        self._health_cache: Dict[str, ServiceHealth] = {}

    def list_services(self) -> List[ServiceHealth]:
        """Return the latest known health for every add-on with a default URL."""
        if not self._health_cache:
            # Return a cold snapshot without performing network I/O.
            return [
                ServiceHealth(
                    name=env.replace("_SERVICE_URL", "").replace("_", " ").lower().title(),
                    url_env=env,
                    url=default_url,
                    healthy=False,
                    error="Health check not performed",
                )
                for env, default_url in _DEFAULT_SERVICE_URLS.items()
            ]
        return list(self._health_cache.values())

    async def check_all(self) -> List[ServiceHealth]:
        """Ping the /health endpoint of every add-on and cache the result."""
        results: List[ServiceHealth] = []
        client = _get_http_client()
        for env, url in _DEFAULT_SERVICE_URLS.items():
            url = url.rstrip("/")
            service_name = env.replace("_SERVICE_URL", "").replace("_", " ").lower()
            try:
                response = await client.get(f"{url}/health", timeout=5.0)
                healthy = response.status_code == 200
                error: Optional[str] = None if healthy else f"HTTP {response.status_code}"
            except Exception as exc:  # pragma: no cover - network failure expected when offline
                healthy = False
                error = str(exc)
                logger.debug("Add-on %s at %s is not reachable", service_name, url)

            health = ServiceHealth(
                name=service_name,
                url_env=env,
                url=url,
                healthy=healthy,
                error=error,
            )
            self._health_cache[env] = health
            results.append(health)
        return results

    def is_healthy(self, service_url_env: str) -> bool:
        """Return True if the service was healthy the last time it was checked."""
        health = self._health_cache.get(service_url_env)
        return health.healthy if health is not None else False


# Global singleton registry
add_on_registry = AddOnServiceRegistry()
