# -*- coding: utf-8 -*-
"""Real tests for the gateway module.

These tests exercise the real service registry and microservice gateway client.
No external services are assumed; only cold snapshots and local fallbacks are tested.
"""

import httpx
import pytest

from gateway import service_registry
from gateway.services_client import (
    _close_http_client,
    _get_http_client,
    _is_remote,
    _remote_call,
)


def test_default_service_registry_cold_snapshot():
    """AddOnServiceRegistry.list_services returns cold data without network I/O."""
    registry = service_registry.AddOnServiceRegistry()
    services = registry.list_services()
    assert len(services) > 0
    first = services[0]
    assert first.url_env.endswith("_SERVICE_URL")
    assert first.url.startswith("http://")
    assert first.healthy is False
    assert "not performed" in (first.error or "")


def test_is_healthy_before_check():
    """is_healthy returns False before any health check has been cached."""
    registry = service_registry.AddOnServiceRegistry()
    assert registry.is_healthy("RAG_SERVICE_URL") is False


def test_default_microservice_mode_is_local():
    """_is_remote returns False when MICROSERVICE_MODE defaults to local."""
    assert _is_remote() is False


@pytest.mark.asyncio
async def test_http_client_lifecycle():
    """_get_http_client returns a usable httpx AsyncClient and _close_http_client closes it."""
    client = _get_http_client()
    assert isinstance(client, httpx.AsyncClient)
    assert not client.is_closed
    await _close_http_client()
    assert _get_http_client() is not client
    await _close_http_client()


@pytest.mark.asyncio
async def test_remote_call_unconfigured_service_raises():
    """_remote_call raises RuntimeError when a service URL is not configured."""
    with pytest.raises(RuntimeError, match="not configured"):
        await _remote_call("UNKNOWN_SERVICE_URL", "GET", "/")


@pytest.mark.asyncio
async def test_remote_call_unsupported_method_raises():
    """_remote_call raises ValueError for unsupported HTTP methods."""
    with pytest.raises(ValueError, match="Unsupported HTTP method"):
        await _remote_call("RAG_SERVICE_URL", "PUT", "/")


@pytest.mark.asyncio
async def test_check_all_marks_unreachable_services_unhealthy():
    """check_all pings all add-on services and caches unhealthy statuses.

    No real add-on services are expected to be running, so every service
    should be reported as unhealthy.
    """
    registry = service_registry.AddOnServiceRegistry()
    results = await registry.check_all()
    assert len(results) > 0
    assert all(not r.healthy for r in results)
    assert all(r.error for r in results)
    assert registry.is_healthy("RAG_SERVICE_URL") is False
