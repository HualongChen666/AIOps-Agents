# -*- coding: utf-8 -*-
"""Tests for config microservice (task 30)."""

from __future__ import annotations

import pytest

from services.config_service.audit_logger import ConfigAuditLogger
from services.config_service.config_manager import ConfigManager
from services.config_service.encryption import ConfigEncryption
from services.config_service.grpc.client import ConfigRPCClient
from services.config_service.grpc.server import ConfigRPCServer
from services.config_service.hot_update import HotUpdateManager
from services.config_service.main_app import app
from services.config_service.namespace import NamespaceManager
from services.config_service.orchestrator import ConfigOrchestrator
from services.config_service.repository import InMemoryConfigRepository
from services.config_service.rollback import RollbackManager
from services.config_service.schemas import (
    ConfigUpdateEvent,
    ConfigValue,
    SagaStep,
    SagaTransaction,
)
from services.config_service.version_control import ConfigVersionControl


@pytest.fixture
async def repo():
    return InMemoryConfigRepository()


@pytest.fixture
async def orchestrator(repo):
    return ConfigOrchestrator(repo, "test-key-32-bytes-long!!!")


@pytest.mark.asyncio
async def test_config_manager(repo):
    manager = ConfigManager(repo)
    config = ConfigValue(config_id="c1", key="timeout", value="30", namespace="default")
    created = await manager.create(config)
    assert created.config_id == "c1"
    assert (await manager.get("c1")).value == "30"
    updated = await manager.update("c1", "60")
    assert updated.value == "60"
    assert await manager.delete("c1")


@pytest.mark.asyncio
async def test_namespace_isolation(repo):
    manager = NamespaceManager(repo)
    await manager.create("dev", "timeout", "10")
    await manager.create("prod", "timeout", "30")
    dev = await manager.list("dev")
    prod = await manager.list("prod")
    assert len(dev) == 1
    assert len(prod) == 1
    assert dev[0].value != prod[0].value


@pytest.mark.asyncio
async def test_version_control(repo):
    manager = NamespaceManager(repo)
    await manager.create("default", "timeout", "30")
    vc = ConfigVersionControl(repo)
    version = await vc.commit("default", "initial commit")
    assert version.commit_hash
    assert version.message == "initial commit"


@pytest.mark.asyncio
async def test_hot_update(repo):
    manager = HotUpdateManager()

    class FakeConnection:
        def __init__(self):
            self.messages = []

        async def send_json(self, data):
            self.messages.append(data)

    conn = FakeConnection()
    await manager.subscribe("default", conn)
    event = ConfigUpdateEvent(event_id="e1", config_id="c1", namespace="default", new_value="60")
    count = await manager.publish(event)
    assert count == 1
    assert conn.messages[0]["config_id"] == "c1"


@pytest.mark.asyncio
async def test_encryption():
    encryption = ConfigEncryption("test-key-32-bytes-long!!!")
    encrypted = encryption.encrypt("secret")
    assert encryption.decrypt(encrypted) == "secret"


@pytest.mark.asyncio
async def test_audit_logger(repo):
    logger = ConfigAuditLogger(repo)
    entry = await logger.log("c1", "created", {"by": "admin"})
    assert entry.config_id == "c1"


@pytest.mark.asyncio
async def test_snapshot_and_rollback(repo):
    manager = NamespaceManager(repo)
    await manager.create("default", "timeout", "30")
    rollback = RollbackManager(repo)
    snapshot = await rollback.snapshot("default")
    await manager.create("default", "timeout", "60")  # overwrite
    restored = await rollback.restore(snapshot.snapshot_id)
    assert len(restored) == 1


@pytest.mark.asyncio
async def test_rpc_server():
    server = ConfigRPCServer()
    server.register("echo", lambda **kwargs: kwargs)
    result = await server.call("echo", message="hi")
    assert result == {"message": "hi"}


@pytest.mark.asyncio
async def test_rpc_client():
    server = ConfigRPCServer()
    server.register("ping", lambda **kwargs: "pong")
    client = ConfigRPCClient(server=server)
    result = await client.call("ping")
    assert result == "pong"


@pytest.mark.asyncio
async def test_orchestrator(orchestrator):
    config = ConfigValue(config_id="c1", key="timeout", value="30", namespace="default")
    created = await orchestrator.create_config(config)
    assert created.config_id == "c1"
    updated = await orchestrator.update_config("c1", "60")
    assert updated.value == "60"
    version = await orchestrator.commit_version("default", "update timeout")
    assert version.message == "update timeout"


@pytest.mark.asyncio
async def test_saga(orchestrator):
    saga = SagaTransaction(
        saga_id="s1",
        task_id="t1",
        steps=[
            SagaStep(step_id="s1", service="config", action="noop", compensation="noop"),
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
    from services.config_service.config import settings

    assert settings.service_name == "config-service"
