# -*- coding: utf-8 -*-
"""Multi-tenant middleware: attach tenant_id to every request."""

from __future__ import annotations

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from core.auth_service import decode_token

logger = logging.getLogger(__name__)

# Public paths that don't require authentication
# (kept in sync with api/middleware/rbac_middleware.py)

# Exact paths that are public and have no sub-paths
PUBLIC_EXACT_PATHS = {
    "/",
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/health",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/register-admin",
    "/api/v1/auth/refresh",
}

# Prefixes that are public and DO have sub-paths (webhooks / static assets)
PUBLIC_PREFIXES = {
    "/api/v1/alerts/prometheus",
    "/api/v1/alerts/grafana",
    "/api/v1/alerts/datadog",
    "/api/v1/alerts/zabbix",
    "/api/v1/alerts/cloudwatch",
    "/api/v1/alerts/pagerduty",
    "/webhook/",
    "/hitl-page/",
    "/api/v1/hitl-page/",
    "/static/",
    "/sw.js",
    "/sw-register.js",
}

# Roles allowed to impersonate another tenant via the X-Tenant-ID header /
# ?tenant_id query parameter.
_TENANT_OVERRIDE_ROLES = {"admin", "superadmin", "service-account", "service_account"}


def _is_public(path: str) -> bool:
    """Return True if the request path is public."""
    lowered = path.lower()
    if lowered in PUBLIC_EXACT_PATHS:
        return True
    for prefix in PUBLIC_PREFIXES:
        if lowered.startswith(prefix):
            return True
    return False


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve tenant_id from JWT token or X-Tenant-ID header and store it on request.state."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        logger.info(f"Tenant Middleware: Processing request {path}")
        
        # Skip tenant resolution for public endpoints
        if _is_public(path):
            logger.info(f"Tenant Middleware: Path {path} is public, setting default tenant")
            request.state.tenant_id = "default"
            return await call_next(request)
        
        # Explicitly skip for register-admin endpoint
        if path == "/api/v1/auth/register-admin":
            logger.info(f"Tenant Middleware: Allowing register-admin endpoint")
            request.state.tenant_id = "default"
            return await call_next(request)

        tenant_id = await self._resolve_tenant_id(request)
        request.state.tenant_id = tenant_id
        logger.info(f"Tenant Middleware: Resolved tenant_id={tenant_id}")
        return await call_next(request)

    async def _resolve_tenant_id(self, request: Request) -> str:
        # The bearer token (when present) is the authoritative source of the
        # caller's identity, role and tenant.  Decode it once up-front.
        role = ""
        token_tenant = None
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth[7:].strip()
            try:
                payload = decode_token(token)
                tenant = payload.get("tenant_id")
                if isinstance(tenant, str) and tenant.strip():
                    token_tenant = tenant.strip()
                role = str(payload.get("role", "") or "").lower()
            except Exception:
                token_tenant = None

        # 1. Tenant override (impersonation) is only honoured for privileged
        #    callers — an authenticated admin / service account.  Every other
        #    caller (including anonymous ones) must not be able to pick an
        #    arbitrary tenant via the header / query string.
        override = (
            request.headers.get("x-tenant-id")
            or request.headers.get("X-Tenant-ID")
            or request.query_params.get("tenant_id")
        )
        if isinstance(override, str) and override.strip():
            if role in _TENANT_OVERRIDE_ROLES:
                return override.strip()
            logger.warning(
                f"Tenant Middleware: ignoring tenant override '{override.strip()}' "
                f"from role='{role or 'anonymous'}' (override requires admin/service account)"
            )

        # 2. Fall back to the token's own tenant.
        if token_tenant:
            return token_tenant

        return "default"
