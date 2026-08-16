# -*- coding: utf-8 -*-
"""Global RBAC middleware: all non-public routes require a valid token;
write methods additionally require operator or admin."""

from __future__ import annotations

from typing import Optional

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from core.auth_service import decode_token

PUBLIC_PREFIXES = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/static/",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/refresh",
    "/api/v1/alerts/",  # webhooks from monitoring systems
    "/api/v1/alerts/prometheus",
    "/api/v1/alerts/grafana",
    "/api/v1/alerts/datadog",
    "/api/v1/alerts/zabbix",
    "/api/v1/alerts/cloudwatch",
    "/api/v1/alerts/pagerduty",
    "/webhook/",
    "/hitl-page/",
    "/api/v1/hitl-page/",
    "/sw.js",
    "/sw-register.js",
    "/metrics",
}

WRITE_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def _is_public(path: str) -> bool:
    """Return True if the request path is public."""
    lowered = path.lower()
    for prefix in PUBLIC_PREFIXES:
        if lowered.startswith(prefix):
            return True
    # Exact public paths
    if lowered in {"/", "/health"}:
        return True
    return False


class RBACMiddleware(BaseHTTPMiddleware):
    """Enforce authentication and write-method role checks globally."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path
        if _is_public(path):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        token: Optional[str] = None
        if auth.startswith("Bearer "):
            token = auth[7:].strip()

        if not token:
            return JSONResponse(
                status_code=401,
                content={"detail": "Missing or invalid Authorization header"},
            )

        parts = token.split(".")
        if len(parts) != 3 or not all(parts):
            return JSONResponse(
                status_code=401,
                content={"detail": "Could not validate credentials"},
            )

        try:
            payload = decode_token(token)
        except Exception:
            return JSONResponse(
                status_code=401,
                content={"detail": "Could not validate credentials"},
            )

        request.state.user = payload
        request.state.tenant_id = str(payload.get("tenant_id", "default"))
        request.state.role = str(payload.get("role", "viewer")).lower()

        if request.method in WRITE_METHODS:
            role = request.state.role
            if role not in {"operator", "admin", "business"}:
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": f"Method {request.method} requires operator or admin role"
                    },
                )

        return await call_next(request)
