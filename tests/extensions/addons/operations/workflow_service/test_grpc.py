# -*- coding: utf-8 -*-
"""Tests for workflow_service grpc module."""

import pytest

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from extensions.addons.operations.workflow_service.grpc.client import WorkflowRPCClient
from extensions.addons.operations.workflow_service.grpc.server import WorkflowRPCServer


class TestWorkflowRPCServer:
    """Test cases for WorkflowRPCServer class."""

    def test_server_initialization(self, grpc_server):
        """Test that server initializes correctly."""
        assert grpc_server is not None
        assert len(grpc_server._handlers) == 0

    def test_register_handler(self, grpc_server):
        """Test registering a handler."""
        async def test_handler(**kwargs):
            return {"result": "success"}

        grpc_server.register("test_method", test_handler)

        assert "test_method" in grpc_server._handlers
        assert len(grpc_server._handlers) == 1

    def test_register_multiple_handlers(self, grpc_server):
        """Test registering multiple handlers."""
        async def handler1(**kwargs):
            return {"result": "success1"}

        async def handler2(**kwargs):
            return {"result": "success2"}

        grpc_server.register("method1", handler1)
        grpc_server.register("method2", handler2)

        assert len(grpc_server._handlers) == 2

    def test_register_overwrites_existing(self, grpc_server):
        """Test that registering with same method name overwrites existing."""
        async def handler1(**kwargs):
            return {"result": "handler1"}

        async def handler2(**kwargs):
            return {"result": "handler2"}

        grpc_server.register("test_method", handler1)
        grpc_server.register("test_method", handler2)

        assert len(grpc_server._handlers) == 1
        # The handler should be the second one
        assert grpc_server._handlers["test_method"] == handler2

    @pytest.mark.asyncio
    async def test_call_registered_method(self, grpc_server):
        """Test calling a registered method."""
        async def test_handler(**kwargs):
            return {"result": "success", "input": kwargs}

        grpc_server.register("test_method", test_handler)

        result = await grpc_server.call("test_method", key="value")

        assert result["result"] == "success"
        assert result["input"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_call_unregistered_method(self, grpc_server):
        """Test calling an unregistered method raises ValueError."""
        with pytest.raises(ValueError, match="Unknown RPC method"):
            await grpc_server.call("non_existent_method")

    @pytest.mark.asyncio
    async def test_call_with_no_arguments(self, grpc_server):
        """Test calling a method with no arguments."""
        async def no_args_handler(**kwargs):
            return {"result": "no args"}

        grpc_server.register("no_args", no_args_handler)

        result = await grpc_server.call("no_args")

        assert result["result"] == "no args"

    @pytest.mark.asyncio
    async def test_call_with_multiple_arguments(self, grpc_server):
        """Test calling a method with multiple arguments."""
        async def multi_args_handler(**kwargs):
            return {"args": kwargs}

        grpc_server.register("multi_args", multi_args_handler)

        result = await grpc_server.call("multi_args", arg1="value1", arg2="value2", arg3=42)

        assert result["args"]["arg1"] == "value1"
        assert result["args"]["arg2"] == "value2"
        assert result["args"]["arg3"] == 42

    @pytest.mark.asyncio
    async def test_call_with_complex_arguments(self, grpc_server):
        """Test calling a method with complex argument types."""
        async def complex_handler(**kwargs):
            return {"received": kwargs}

        grpc_server.register("complex", complex_handler)

        complex_args = {
            "string": "test",
            "number": 42,
            "bool": True,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        result = await grpc_server.call("complex", **complex_args)

        assert result["received"] == complex_args

    @pytest.mark.asyncio
    async def test_call_handler_raises_exception(self, grpc_server):
        """Test that handler exceptions are propagated."""
        async def failing_handler(**kwargs):
            raise ValueError("Handler failed")

        grpc_server.register("failing", failing_handler)

        with pytest.raises(ValueError, match="Handler failed"):
            await grpc_server.call("failing")

    @pytest.mark.asyncio
    async def test_call_handler_returns_none(self, grpc_server):
        """Test calling a handler that returns None."""
        async def none_handler(**kwargs):
            return None

        grpc_server.register("none", none_handler)

        result = await grpc_server.call("none")

        assert result is None

    @pytest.mark.asyncio
    async def test_call_handler_returns_string(self, grpc_server):
        """Test calling a handler that returns a string."""
        async def string_handler(**kwargs):
            return "string result"

        grpc_server.register("string", string_handler)

        result = await grpc_server.call("string")

        assert result == "string result"

    @pytest.mark.asyncio
    async def test_call_handler_returns_dict(self, grpc_server):
        """Test calling a handler that returns a dict."""
        async def dict_handler(**kwargs):
            return {"key": "value", "number": 42}

        grpc_server.register("dict", dict_handler)

        result = await grpc_server.call("dict")

        assert result["key"] == "value"
        assert result["number"] == 42

    @pytest.mark.asyncio
    async def test_call_handler_returns_list(self, grpc_server):
        """Test calling a handler that returns a list."""
        async def list_handler(**kwargs):
            return [1, 2, 3, 4, 5]

        grpc_server.register("list", list_handler)

        result = await grpc_server.call("list")

        assert result == [1, 2, 3, 4, 5]

    def test_list_methods(self, grpc_server):
        """Test listing registered methods."""
        async def handler1(**kwargs):
            return {"result": "success1"}

        async def handler2(**kwargs):
            return {"result": "success2"}

        grpc_server.register("method1", handler1)
        grpc_server.register("method2", handler2)

        methods = grpc_server.list_methods()

        assert len(methods) == 2
        assert "method1" in methods
        assert "method2" in methods

    def test_list_methods_empty(self, grpc_server):
        """Test listing methods when none are registered."""
        methods = grpc_server.list_methods()
        assert methods == []

    def test_list_methods_order(self, grpc_server):
        """Test that list_methods returns methods in registration order."""
        async def handler(**kwargs):
            return {"result": "success"}

        grpc_server.register("method1", handler)
        grpc_server.register("method2", handler)
        grpc_server.register("method3", handler)

        methods = grpc_server.list_methods()

        assert methods == ["method1", "method2", "method3"]


class TestWorkflowRPCClient:
    """Test cases for WorkflowRPCClient class."""

    def test_client_initialization_with_server(self, grpc_server):
        """Test client initialization with server instance."""
        client = WorkflowRPCClient(server=grpc_server)

        assert client.server == grpc_server
        assert client.base_url is None
        assert client._http is None

    def test_client_initialization_with_base_url(self):
        """Test client initialization with base URL."""
        client = WorkflowRPCClient(base_url="http://localhost:8000")

        assert client.server is None
        assert client.base_url == "http://localhost:8000"
        assert client._http is not None

    def test_client_initialization_without_server_or_url(self):
        """Test client initialization without server or base URL."""
        client = WorkflowRPCClient()

        assert client.server is None
        assert client.base_url is None
        assert client._http is None

    def test_client_initialization_with_both_server_and_url(self, grpc_server):
        """Test client initialization with both server and base URL."""
        client = WorkflowRPCClient(server=grpc_server, base_url="http://localhost:8000")

        assert client.server == grpc_server
        assert client.base_url == "http://localhost:8000"
        # Should prefer server over HTTP
        assert client._http is not None

    @pytest.mark.asyncio
    async def test_call_with_server(self, grpc_server):
        """Test calling through client with server instance."""
        async def test_handler(**kwargs):
            return {"result": "success", "input": kwargs}

        grpc_server.register("test_method", test_handler)
        client = WorkflowRPCClient(server=grpc_server)

        result = await client.call("test_method", key="value")

        assert result["result"] == "success"
        assert result["input"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_call_with_server_unregistered_method(self, grpc_server):
        """Test calling unregistered method through client with server."""
        client = WorkflowRPCClient(server=grpc_server)

        with pytest.raises(ValueError, match="Unknown RPC method"):
            await client.call("non_existent")

    @pytest.mark.asyncio
    async def test_call_without_server_or_url(self):
        """Test calling when neither server nor base URL is set."""
        client = WorkflowRPCClient()

        with pytest.raises(RuntimeError, match="RPCClient requires a server instance or base_url"):
            await client.call("test_method")

    @pytest.mark.asyncio
    async def test_close_with_http_client(self):
        """Test closing client with HTTP client."""
        client = WorkflowRPCClient(base_url="http://localhost:8000")

        await client.close()

        # After close, _http should be None or closed
        assert client._http is None

    @pytest.mark.asyncio
    async def test_close_without_http_client(self, grpc_server):
        """Test closing client without HTTP client."""
        client = WorkflowRPCClient(server=grpc_server)

        # Should not raise an error
        await client.close()

    @pytest.mark.asyncio
    async def test_close_idempotent(self):
        """Test that close can be called multiple times."""
        client = WorkflowRPCClient(base_url="http://localhost:8000")

        await client.close()
        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_call_with_server_after_close(self, grpc_server):
        """Test calling through server client after close."""
        async def test_handler(**kwargs):
            return {"result": "success"}

        grpc_server.register("test_method", test_handler)
        client = WorkflowRPCClient(server=grpc_server)

        await client.close()

        # Server-based client should still work after close
        result = await client.call("test_method")

        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_call_with_various_base_urls(self):
        """Test client initialization with various base URLs."""
        urls = [
            "http://localhost:8000",
            "http://example.com:8080",
            "https://api.example.com",
        ]

        for url in urls:
            client = WorkflowRPCClient(base_url=url)
            assert client.base_url == url
            assert client._http is not None

            await client.close()

    @pytest.mark.asyncio
    async def test_call_with_empty_base_url(self):
        """Test client with empty base URL string."""
        client = WorkflowRPCClient(base_url="")

        assert client.base_url == ""
        assert client._http is None  # Empty URL should not create HTTP client

        await client.close()  # Should not raise error even without HTTP client

    @pytest.mark.asyncio
    async def test_call_with_special_characters_in_method_name(self, grpc_server):
        """Test calling method with special characters in name."""
        async def test_handler(**kwargs):
            return {"result": "success"}

        grpc_server.register("method-with_special.chars", test_handler)
        client = WorkflowRPCClient(server=grpc_server)

        result = await client.call("method-with_special.chars")

        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_call_with_unicode_method_name(self, grpc_server):
        """Test calling method with unicode characters in name."""
        async def test_handler(**kwargs):
            return {"result": "success"}

        grpc_server.register("方法测试", test_handler)
        client = WorkflowRPCClient(server=grpc_server)

        result = await client.call("方法测试")

        assert result["result"] == "success"

    @pytest.mark.asyncio
    async def test_server_client_integration(self, grpc_server):
        """Test full integration between server and client."""
        # Register a handler
        async def complex_handler(**kwargs):
            return {
                "operation": kwargs.get("operation", "unknown"),
                "data": kwargs.get("data", {}),
                "status": "completed",
            }

        grpc_server.register("complex_operation", complex_handler)

        # Create client
        client = WorkflowRPCClient(server=grpc_server)

        # Call the method
        result = await client.call(
            "complex_operation",
            operation="test",
            data={"key": "value", "number": 42},
        )

        assert result["operation"] == "test"
        assert result["data"]["key"] == "value"
        assert result["data"]["number"] == 42
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_multiple_clients_same_server(self, grpc_server):
        """Test multiple clients using the same server."""
        async def counter_handler(**kwargs):
            return {"count": kwargs.get("count", 0)}

        grpc_server.register("counter", counter_handler)

        client1 = WorkflowRPCClient(server=grpc_server)
        client2 = WorkflowRPCClient(server=grpc_server)

        result1 = await client1.call("counter", count=1)
        result2 = await client2.call("counter", count=2)

        assert result1["count"] == 1
        assert result2["count"] == 2

    @pytest.mark.asyncio
    async def test_server_preserves_handler_state(self, grpc_server):
        """Test that server preserves handler state across calls."""
        call_count = 0

        async def stateful_handler(**kwargs):
            nonlocal call_count
            call_count += 1
            return {"call_count": call_count}

        grpc_server.register("stateful", stateful_handler)
        client = WorkflowRPCClient(server=grpc_server)

        result1 = await client.call("stateful")
        result2 = await client.call("stateful")
        result3 = await client.call("stateful")

        assert result1["call_count"] == 1
        assert result2["call_count"] == 2
        assert result3["call_count"] == 3

    @pytest.mark.asyncio
    async def test_client_with_none_server(self):
        """Test client with None server parameter."""
        client = WorkflowRPCClient(server=None)

        assert client.server is None

        with pytest.raises(RuntimeError, match="RPCClient requires a server instance or base_url"):
            await client.call("test")
