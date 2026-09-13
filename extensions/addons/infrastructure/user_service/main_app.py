# -*- coding: utf-8 -*-
"""User service main FastAPI application."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from core.auth_service import get_current_user, has_role, is_internal_key

from .health_check import HealthCheckEngine
from .metrics import USER_LOGINS, USERS_CREATED
from .orchestrator import UserOrchestrator
from .repository import InMemoryUserRepository
from .schemas import (
    Organization,
    Role,
    SagaTransaction,
    ServiceHealth,
    User,
    UserCreate,
    UserUpdate,
)

_orchestrator: Optional[UserOrchestrator] = None


def get_orchestrator() -> UserOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = UserOrchestrator(InMemoryUserRepository())
    return _orchestrator


app = FastAPI(
    title="User Service",
    description="User microservice for identity, RBAC, sessions and audit.",
    version="0.1.0",
)

# Reachable without a forwarded identity (probes, docs, and the login flow the
# gateway proxies to after injecting nothing).
PUBLIC_PATHS = {
    "/health",
    "/metrics",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/docs/oauth2-redirect",
    "/auth/login",
}


@app.middleware("http")
async def require_gateway_auth(request: Request, call_next):
    """Enforce gateway-injected identity for all user-management endpoints.

    历史问题（已修复）：本服务此前**全部端点无鉴权**，任何人可 ``POST /users``
    （甚至传 admin 角色）。现按网关注入约定：仅接受网关携带的内部服务密钥
    （``is_internal_key``）或具备 ``admin`` 角色的 JWT；``/auth/login`` 与健康/
    指标/文档端点保持公开。
    """
    if request.method == "OPTIONS" or request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    if is_internal_key(request):
        return await call_next(request)

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[len("Bearer "):]
        try:
            user = get_current_user(token=token, request=request)
        except HTTPException:
            user = None
        if user is not None and has_role(user, "admin"):
            return await call_next(request)

    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"detail": "Authentication required"},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.get("/health", response_model=ServiceHealth)
async def health() -> ServiceHealth:
    o = get_orchestrator()
    count = len(await o.repo.list_users(tenant_id="default"))
    return await HealthCheckEngine().check("user-service", count)


@app.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post("/users", response_model=User)
async def create_user(data: UserCreate) -> User:
    o = get_orchestrator()
    user = await o.create_user(data)
    USERS_CREATED.labels(tenant=user.tenant_id).inc()
    return user


@app.get("/users")
async def list_users(tenant_id: str = "default", limit: int = 100) -> Dict[str, Any]:
    o = get_orchestrator()
    users = await o.users.list(tenant_id, limit)
    return {"total": len(users), "items": [u.model_dump() for u in users]}


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str) -> User:
    o = get_orchestrator()
    user = await o.users.get(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.patch("/users/{user_id}", response_model=User)
async def update_user(user_id: str, data: UserUpdate) -> User:
    o = get_orchestrator()
    user = await o.users.update(user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.delete("/users/{user_id}")
async def delete_user(user_id: str) -> Dict[str, Any]:
    o = get_orchestrator()
    success = await o.users.delete(user_id)
    if not success:
        raise HTTPException(status_code=404, detail="User not found")
    return {"deleted": True}


@app.post("/auth/login")
async def login(username: str, password: str) -> Dict[str, Any]:
    o = get_orchestrator()
    token = await o.login(username, password)
    if not token:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    USER_LOGINS.labels(tenant="default").inc()
    return token.model_dump()


@app.post("/roles", response_model=Role)
async def create_role(role: Role) -> Role:
    o = get_orchestrator()
    return await o.create_role(role)


@app.get("/roles")
async def list_roles(tenant_id: str = "default") -> Dict[str, Any]:
    o = get_orchestrator()
    roles = await o.rbac.list_roles(tenant_id)
    return {"total": len(roles), "items": [r.model_dump() for r in roles]}


@app.post("/organizations", response_model=Organization)
async def create_organization(org: Organization) -> Organization:
    o = get_orchestrator()
    return await o.create_organization(org)


@app.get("/organizations/tree")
async def get_org_tree(tenant_id: str = "default") -> Dict[str, Any]:
    o = get_orchestrator()
    tree = await o.organizations.tree(tenant_id)
    return {"tenant_id": tenant_id, "tree": tree}


@app.post("/sessions")
async def create_session(user_id: str) -> Dict[str, Any]:
    o = get_orchestrator()
    session = await o.create_session(user_id)
    return session.model_dump()


@app.post("/sagas")
async def execute_saga(saga: SagaTransaction) -> Dict[str, Any]:
    o = get_orchestrator()
    result = await o.run_saga(saga)
    return result.model_dump()
