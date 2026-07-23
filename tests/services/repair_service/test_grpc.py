# -*- coding: utf-8 -*-
"""Tests for repair microservice gRPC-like RPC."""

from __future__ import annotations

import pytest

from services.repair_service.grpc.client import RPCClient
from services.repair_service.grpc.server import RPCServer


class TestRPC:
    @pytest.mark.asyncio
    async def test_rpc_call(self):
        server = RPCServer()

        async def echo(name: str) -> str:
            return f"hello {name}"

        server.register("echo", echo)
        client = RPCClient(server=server)
        result = await client.call("echo", name="world")
        assert result == "hello world"

    def test_list_methods(self):
        server = RPCServer()

        async def noop() -> None:
            return None

        server.register("noop", noop)
        assert "noop" in server.list_methods()
