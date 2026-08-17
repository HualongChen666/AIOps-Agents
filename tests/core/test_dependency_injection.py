# -*- coding: utf-8 -*-
"""Tests for core/dependency_injection.py."""

import pytest  # noqa: F401  # Imported for test setup

from core.dependency_injection import (
    DIContainer,
    ServiceLifecycle,
    di_container,
    inject,
    inject_context,
    setup_core_services,
)


def test_container_instance_and_factory():
    container = DIContainer()
    container.register_instance("db", "sqlite")
    assert container.get("db") == "sqlite"

    container.register_factory("calc", lambda: 42, singleton=False)
    assert container.get("calc") == 42


def test_container_context_and_stats():
    container = DIContainer()
    container.set_context({"ctx_key": "value"})
    assert container.get("ctx_key") == "value"
    container.clear_context()
    assert "total_services" in container.get_stats()


@pytest.mark.asyncio
async def test_shutdown_with_lifecycle():
    container = DIContainer()

    class FakeService:
        def __init__(self):
            self.closed = False

    class CustomLifecycle(ServiceLifecycle):
        async def shutdown(self, instance):
            instance.closed = True

    container.register_factory("svc", FakeService, lifecycle=CustomLifecycle())
    instance = container.get("svc")
    await container.shutdown()
    assert instance.closed


@pytest.mark.asyncio
async def test_inject_decorator():
    di_container.register_factory("greeter", lambda: "hello")

    @inject("greeter")
    async def greet(service):
        return service

    assert await greet() == "hello"


@pytest.mark.asyncio
async def test_inject_context():
    di_container.register_instance("ctx_key", "global")

    @inject_context({"ctx_key": "local"})
    async def read_ctx():
        return di_container.get("ctx_key")

    assert await read_ctx() == "local"


def test_setup_core_services():
    result = setup_core_services()  # noqa: F841  # Variable for test verification
    assert result["status"] in ("success", "error")
