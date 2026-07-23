# -*- coding: utf-8 -*-
"""Tests for user microservice (task 29)."""

from __future__ import annotations

import pytest

from services.user_service.audit_logger import UserAuditLogger
from services.user_service.grpc.client import UserRPCClient
from services.user_service.grpc.server import UserRPCServer
from services.user_service.main_app import app
from services.user_service.orchestrator import UserOrchestrator
from services.user_service.organization import OrganizationManager
from services.user_service.rbac import RBACManager
from services.user_service.repository import InMemoryUserRepository
from services.user_service.schemas import (
    Organization,
    SagaStep,
    SagaTransaction,
    UserCreate,
    UserRole,
    UserUpdate,
)
from services.user_service.session import SessionManager
from services.user_service.user_manager import UserManager


@pytest.fixture
async def repo():
    return InMemoryUserRepository()


@pytest.fixture
async def orchestrator(repo):
    return UserOrchestrator(repo)


@pytest.mark.asyncio
async def test_user_crud(repo):
    manager = UserManager(repo)
    user = await manager.create(UserCreate(username="alice", email="alice@example.com"))
    assert user.username == "alice"
    assert (await manager.get(user.user_id)).user_id == user.user_id
    assert len(await manager.list("default")) == 1
    updated = await manager.update(user.user_id, UserUpdate(email="a@b.com"))
    assert updated is not None
    assert await manager.delete(user.user_id)


@pytest.mark.asyncio
async def test_rbac_permissions(repo):
    rbac = RBACManager(repo)
    from services.user_service.schemas import User

    user = User(user_id="u1", username="u1", email="u1@b.com", role=UserRole.OPERATOR)
    assert rbac.check_permission(user, "user", "read")
    assert rbac.check_permission(user, "user", "write")


@pytest.mark.asyncio
async def test_organization_tree(repo):
    manager = OrganizationManager(repo)
    await manager.create(Organization(org_id="o1", name="Root"))
    await manager.create(Organization(org_id="o2", name="Child", parent_id="o1"))
    tree = await manager.tree("default")
    assert len(tree) == 1
    assert tree[0]["children"]


@pytest.mark.asyncio
async def test_auth_login(orchestrator):
    await orchestrator.create_user(UserCreate(username="bob", email="bob@example.com"))
    token = await orchestrator.login("bob", "password")
    assert token is not None
    assert token.access_token


@pytest.mark.asyncio
async def test_session(repo):
    manager = SessionManager(repo)
    session = await manager.create("u1")
    assert session.user_id == "u1"
    assert await manager.get(session.session_id)
    assert await manager.delete(session.session_id)


@pytest.mark.asyncio
async def test_audit_logger(repo):
    logger = UserAuditLogger(repo)
    entry = await logger.log("u1", "login", {"ip": "127.0.0.1"})
    assert entry.user_id == "u1"


@pytest.mark.asyncio
async def test_rpc_server():
    server = UserRPCServer()
    server.register("echo", lambda **kwargs: kwargs)
    result = await server.call("echo", message="hi")
    assert result == {"message": "hi"}


@pytest.mark.asyncio
async def test_rpc_client():
    server = UserRPCServer()
    server.register("ping", lambda **kwargs: "pong")
    client = UserRPCClient(server=server)
    result = await client.call("ping")
    assert result == "pong"


@pytest.mark.asyncio
async def test_saga(orchestrator):
    saga = SagaTransaction(
        saga_id="s1",
        task_id="t1",
        steps=[
            SagaStep(step_id="s1", service="user", action="noop", compensation="noop"),
        ],
    )
    result = await orchestrator.run_saga(saga)
    assert result.status == "success"


@pytest.mark.asyncio
async def test_app_lifespan():
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_config():
    from services.user_service.config import settings

    assert settings.service_name == "user-service"
