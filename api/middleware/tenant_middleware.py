# -*- coding: utf-8 -*-
"""Multi-tenant middleware: attach tenant_id to every request."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from core.auth_service import decode_token

# Public prefixes that don't require authentication
PUBLIC_PREFIXES = {
    "/docs",
    "/redoc",
    "/openapi.json",
    "/health",
    "/static/",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/register-admin",
    "/api/v1/auth/refresh",
    "/api/v1/auth/me",
    "/api/v1/users/me",
    "/api/v1/users/me/",
    "/api/v1/users/me/mfa",
    "/api/v1/users/me/audit-logs",
    "/api/v1/alerts/",
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
    "/api/i18n/",
}


def _is_public(path: str) -> bool:
    """Return True if the request path is public."""
    lowered = path.lower()
    for prefix in PUBLIC_PREFIXES:
        if lowered.startswith(prefix):
            return True
    if lowered in {"/", "/health"}:
        return True
    return False


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve tenant_id from JWT token or X-Tenant-ID header and store it on request.state."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip tenant resolution for public endpoints
        if _is_public(request.url.path):
            request.state.tenant_id = "default"
            return await call_next(request)
        
        # Explicitly skip for register-admin endpoint
        if request.url.path == "/api/v1/auth/register-admin":
            request.state.tenant_id = "default"
            return await call_next(request)
        
        tenant_id = await self._resolve_tenant_id(request)
        request.state.tenant_id = tenant_id
        return await call_next(request)

    async def _resolve_tenant_id(self, request: Request) -> str:
        # 1. Header override (admin/service-account impersonation)
        header_tenant = request.headers.get("x-tenant-id") or request.headers.get("X-Tenant-ID")
        if header_tenant:
            return header_tenant.strip() or "default"

        # 2. JWT token
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
            try:
                payload = decode_token(token)
                tenant = payload.get("tenant_id")
                if isinstance(tenant, str) and tenant.strip():
                    return tenant.strip()
            except Exception:
                pass

        # 3. Query string
        tenant = request.query_params.get("tenant_id")
        if isinstance(tenant, str) and tenant.strip():
            return tenant.strip()

        return "default"
