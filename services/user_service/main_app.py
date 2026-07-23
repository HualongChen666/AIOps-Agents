# -*- coding: utf-8 -*-
"""User service main FastAPI application."""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.responses import Response

from services.user_service.health_check import HealthCheckEngine
from services.user_service.metrics import USER_LOGINS, USERS_CREATED
from services.user_service.orchestrator import UserOrchestrator
from services.user_service.repository import InMemoryUserRepository
from services.user_service.schemas import (
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
