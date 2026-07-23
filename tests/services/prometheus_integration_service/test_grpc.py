# -*- coding: utf-8 -*-
"""gRPC client/server tests for the Prometheus Integration microservice."""

from __future__ import annotations

from unittest import mock

import httpx
import pytest

from services.prometheus_integration_service.grpc.client import (
    PrometheusIntegrationServiceRPCClient,
)
from services.prometheus_integration_service.grpc.server import (
    PrometheusIntegrationServiceRPCServer,
)


@pytest.mark.asyncio
async def test_rpc_server_register_and_call():
    server = PrometheusIntegrationServiceRPCServer()

    async def handler(x):
        return {"ok": True, "x": x}

    server.register("echo", handler)
    assert "echo" in server.list_methods()
    result = await server.call("echo", x=1)
    assert result == {"ok": True, "x": 1}


@pytest.mark.asyncio
async def test_rpc_server_unknown_method():
    server = PrometheusIntegrationServiceRPCServer()
    with pytest.raises(ValueError):
        await server.call("missing")


@pytest.mark.asyncio
async def test_rpc_client_call():
    client = PrometheusIntegrationServiceRPCClient(base_url="http://test")
    fake_response = mock.Mock()
    fake_response.raise_for_status = mock.Mock()
    fake_response.json = mock.Mock(return_value={"success": True})
    fake_post = mock.AsyncMock(return_value=fake_response)
    fake_client = mock.AsyncMock()
    fake_client.post = fake_post
    fake_cm = mock.AsyncMock()
    fake_cm.__aenter__ = mock.AsyncMock(return_value=fake_client)
    fake_cm.__aexit__ = mock.AsyncMock(return_value=False)
    with mock.patch.object(httpx, "AsyncClient", return_value=fake_cm):
        result = await client.call("list_methods", payload={})
    assert result == {"success": True}
    fake_post.assert_called_once_with("http://test/rpc/list_methods", json={})
