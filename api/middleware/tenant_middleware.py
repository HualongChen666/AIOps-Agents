# -*- coding: utf-8 -*-
"""Multi-tenant middleware: attach tenant_id to every request."""

from __future__ import annotations


from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from core.auth_service import decode_token


class TenantMiddleware(BaseHTTPMiddleware):
    """Resolve tenant_id from JWT token or X-Tenant-ID header and store it on request.state."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
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
