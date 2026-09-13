# -*- coding: utf-8 -*-
"""Prometheus HTTP metrics middleware.

Records every HTTP request into the default-registry exporter
(``core.prometheus_metrics``), which is what the application exposes at
``/metrics``. Without this the ``aiops_api_*`` series had no producer and every
API panel / alert stayed permanently empty.

Implemented as a pure ASGI middleware (not BaseHTTPMiddleware) so it adds no
buffering and works for streaming responses.
"""

from __future__ import annotations

import time

from starlette.types import ASGIApp, Receive, Scope, Send

try:  # pragma: no cover - import guard
    from core.prometheus_metrics import get_metrics_exporter
except Exception:  # pragma: no cover - exporter is optional
    get_metrics_exporter = None  # type: ignore[assignment]

# Paths that should never be counted (the scrape endpoint itself, docs, static).
_EXCLUDE_PREFIXES = ("/metrics", "/docs", "/redoc", "/openapi.json", "/static")


def _endpoint_label(scope: Scope) -> str:
    """Use the matched route template (low cardinality) when available."""
    route = scope.get("route")
    template = getattr(route, "path", None)
    if template:
        return template
    return scope.get("path", "")


class PrometheusMetricsMiddleware:
    """ASGI middleware recording request count / latency / errors."""

    def __init__(self, app: ASGIApp):
        self.app = app
        self._in_flight = 0

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope.get("type") != "http" or not callable(get_metrics_exporter):
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path.startswith(_EXCLUDE_PREFIXES):
            await self.app(scope, receive, send)
            return

        start = time.perf_counter()
        status_holder = {"status": 500}
        self._in_flight += 1
        try:
            get_metrics_exporter().api_connections_active.set(self._in_flight)
        except Exception:  # pragma: no cover
            pass

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration = time.perf_counter() - start
            self._in_flight = max(0, self._in_flight - 1)
            try:
                exporter = get_metrics_exporter()
                exporter.record_api_request(
                    endpoint=_endpoint_label(scope),
                    method=scope.get("method", ""),
                    duration=duration,
                    status=status_holder["status"],
                )
                exporter.api_connections_active.set(self._in_flight)
            except Exception:  # pragma: no cover - never break a request over metrics
                pass


def add_prometheus_metrics_middleware(app) -> None:
    """Register the Prometheus metrics middleware on a FastAPI app."""
    app.add_middleware(PrometheusMetricsMiddleware)
