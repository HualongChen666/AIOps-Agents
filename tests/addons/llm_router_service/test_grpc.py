# -*- coding: utf-8 -*-
"""Unit tests for grpc module - gRPC-like utilities for LLM router service."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from extensions.addons.ai_plus.llm_router_service.grpc.client import LLMRouterRPCClient
from extensions.addons.ai_plus.llm_router_service.grpc.server import LLMRouterRPCServer


class TestLLMRouterRPCServer:
    """Test LLMRouterRPCServer class."""

    def test_server_initialization(self):
        """Test server initialization."""
        server = LLMRouterRPCServer()

        assert server._handlers == {}
        assert isinstance(server._handlers, dict)

    def test_register_handler(self):
        """Test registering a handler."""
        server = LLMRouterRPCServer()

        async def test_handler(arg1, arg2):
            return {"result": arg1 + arg2}

        server.register("add", test_handler)

        assert "add" in server._handlers
        assert server._handlers["add"] == test_handler

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers."""
        server = LLMRouterRPCServer()

        async def handler1():
            return "handler1"

        async def handler2():
            return "handler2"

        async def handler3():
            return "handler3"

        server.register("method1", handler1)
        server.register("method2", handler2)
        server.register("method3", handler3)

        assert len(server._handlers) == 3
        assert "method1" in server._handlers
        assert "method2" in server._handlers
        assert "method3" in server._handlers

    def test_register_override_handler(self):
        """Test that registering overrides existing handler."""
        server = LLMRouterRPCServer()

        async def handler1():
            return "handler1"

        async def handler2():
            return "handler2"

        server.register("method", handler1)
        server.register("method", handler2)

        assert server._handlers["method"] == handler2

    def test_list_methods_empty(self):
        """Test listing methods when no handlers registered."""
        server = LLMRouterRPCServer()
        methods = server.list_methods()

        assert methods == []
        assert isinstance(methods, list)

    def test_list_methods_with_handlers(self):
        """Test listing methods with registered handlers."""
        server = LLMRouterRPCServer()

        async def handler1():
            return "handler1"

        async def handler2():
            return "handler2"

        server.register("method1", handler1)
        server.register("method2", handler2)

        methods = server.list_methods()

        assert len(methods) == 2
        assert "method1" in methods
        assert "method2" in methods

    @pytest.mark.asyncio
    async def test_call_sync_handler(self):
        """Test calling a synchronous handler."""
        server = LLMRouterRPCServer()

        def sync_handler(a, b):
            return a + b

        server.register("add", sync_handler)

        result = await server.call("add", a=1, b=2)

        assert result == 3

    @pytest.mark.asyncio
    async def test_call_async_handler(self):
        """Test calling an async handler."""
        server = LLMRouterRPCServer()

        async def async_handler(a, b):
            return a + b

        server.register("add", async_handler)

        result = await server.call("add", a=1, b=2)

        assert result == 3

    @pytest.mark.asyncio
    async def test_call_handler_with_no_args(self):
        """Test calling handler with no arguments."""
        server = LLMRouterRPCServer()

        async def no_arg_handler():
            return "success"

        server.register("test", no_arg_handler)

        result = await server.call("test")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_call_handler_with_args(self):
        """Test calling handler with arguments."""
        server = LLMRouterRPCServer()

        async def arg_handler(a, b, c):
            return {"a": a, "b": b, "c": c}

        server.register("test", arg_handler)

        result = await server.call("test", a=1, b=2, c=3)

        assert result == {"a": 1, "b": 2, "c": 3}

    @pytest.mark.asyncio
    async def test_call_handler_with_complex_return(self):
        """Test calling handler with complex return value."""
        server = LLMRouterRPCServer()

        async def complex_handler():
            return {
                "nested": {
                    "list": [1, 2, 3],
                    "dict": {"key": "value"},
                },
                "string": "test",
                "number": 123,
            }

        server.register("complex", complex_handler)

        result = await server.call("complex")

        assert result["nested"]["list"] == [1, 2, 3]
        assert result["nested"]["dict"]["key"] == "value"

    @pytest.mark.asyncio
    async def test_call_unknown_method(self):
        """Test calling unknown method raises ValueError."""
        server = LLMRouterRPCServer()

        with pytest.raises(ValueError, match="Unknown RPC method"):
            await server.call("unknown_method")

    @pytest.mark.asyncio
    async def test_call_handler_exception(self):
        """Test that handler exceptions are propagated."""
        server = LLMRouterRPCServer()

        async def failing_handler():
            raise ValueError("Handler error")

        server.register("fail", failing_handler)

        with pytest.raises(ValueError, match="Handler error"):
            await server.call("fail")

    @pytest.mark.asyncio
    async def test_call_handler_with_none_return(self):
        """Test calling handler that returns None."""
        server = LLMRouterRPCServer()

        async def none_handler():
            return None

        server.register("none", none_handler)

        result = await server.call("none")

        assert result is None

    @pytest.mark.asyncio
    async def test_call_handler_with_false_return(self):
        """Test calling handler that returns False."""
        server = LLMRouterRPCServer()

        async def false_handler():
            return False

        server.register("false", false_handler)

        result = await server.call("false")

        assert result is False

    @pytest.mark.asyncio
    async def test_call_handler_with_zero_return(self):
        """Test calling handler that returns 0."""
        server = LLMRouterRPCServer()

        async def zero_handler():
            return 0

        server.register("zero", zero_handler)

        result = await server.call("zero")

        assert result == 0

    @pytest.mark.asyncio
    async def test_call_handler_with_empty_string_return(self):
        """Test calling handler that returns empty string."""
        server = LLMRouterRPCServer()

        async def empty_string_handler():
            return ""

        server.register("empty", empty_string_handler)

        result = await server.call("empty")

        assert result == ""

    @pytest.mark.asyncio
    async def test_call_handler_with_empty_list_return(self):
        """Test calling handler that returns empty list."""
        server = LLMRouterRPCServer()

        async def empty_list_handler():
            return []

        server.register("empty_list", empty_list_handler)

        result = await server.call("empty_list")

        assert result == []

    @pytest.mark.asyncio
    async def test_call_handler_with_empty_dict_return(self):
        """Test calling handler that returns empty dict."""
        server = LLMRouterRPCServer()

        async def empty_dict_handler():
            return {}

        server.register("empty_dict", empty_dict_handler)

        result = await server.call("empty_dict")

        assert result == {}

    @pytest.mark.asyncio
    async def test_call_multiple_times(self):
        """Test calling the same handler multiple times."""
        server = LLMRouterRPCServer()
        call_count = 0

        async def counter_handler():
            nonlocal call_count
            call_count += 1
            return call_count

        server.register("counter", counter_handler)

        result1 = await server.call("counter")
        result2 = await server.call("counter")
        result3 = await server.call("counter")

        assert result1 == 1
        assert result2 == 2
        assert result3 == 3

    @pytest.mark.asyncio
    async def test_call_with_extra_kwargs(self):
        """Test calling handler with extra kwargs that are ignored."""
        server = LLMRouterRPCServer()

        async def handler(a):
            return a

        server.register("test", handler)

        result = await server.call("test", a=1, b=2, c=3)

        assert result == 1

    @pytest.mark.asyncio
    async def test_call_with_string_method_name(self):
        """Test calling with string method name."""
        server = LLMRouterRPCServer()

        async def handler():
            return "success"

        server.register("test", handler)

        result = await server.call("test")

        assert result == "success"

    @pytest.mark.asyncio
    async def test_call_handler_that_returns_generator(self):
        """Test calling handler that returns a generator-like object."""
        server = LLMRouterRPCServer()

        async def generator_handler():
            return [1, 2, 3]

        server.register("generator", generator_handler)

        result = await server.call("generator")

        assert result == [1, 2, 3]


class TestLLMRouterRPCClient:
    """Test LLMRouterRPCClient class."""

    def test_client_initialization_with_server(self):
        """Test client initialization with server instance."""
        server = LLMRouterRPCServer()
        client = LLMRouterRPCClient(server=server)

        assert client.server == server
        assert client.base_url is None
        assert client._http is None

    def test_client_initialization_with_base_url(self):
        """Test client initialization with base URL."""
        client = LLMRouterRPCClient(base_url="http://localhost:8000")

        assert client.server is None
        assert client.base_url == "http://localhost:8000"
        assert client._http is not None

    def test_client_initialization_without_params(self):
        """Test client initialization without parameters."""
        client = LLMRouterRPCClient()

        assert client.server is None
        assert client.base_url is None
        assert client._http is None

    def test_client_initialization_with_both_params(self):
        """Test client initialization with both server and base URL."""
        server = LLMRouterRPCServer()
        client = LLMRouterRPCClient(server=server, base_url="http://localhost:8000")

        assert client.server == server
        assert client.base_url == "http://localhost:8000"
        assert client._http is not None

    @pytest.mark.asyncio
    async def test_call_with_server(self):
        """Test calling through server instance."""
        server = LLMRouterRPCServer()

        async def handler(a, b):
            return a + b

        server.register("add", handler)
        client = LLMRouterRPCClient(server=server)

        result = await client.call("add", a=1, b=2)

        assert result == 3

    @pytest.mark.asyncio
    async def test_call_with_server_async_handler(self):
        """Test calling async handler through server instance."""
        server = LLMRouterRPCServer()

        async def async_handler(a, b):
            return a + b

        server.register("add", async_handler)
        client = LLMRouterRPCClient(server=server)

        result = await client.call("add", a=1, b=2)

        assert result == 3

    @pytest.mark.asyncio
    async def test_call_with_http_client(self):
        """Test calling through HTTP client."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response

        client = LLMRouterRPCClient(base_url="http://localhost:8000")
        client._http = mock_http

        result = await client.call("test_method", arg1="value1")

        assert result == {"result": "success"}
        mock_http.post.assert_called_once_with("/rpc/test_method", json={"arg1": "value1"})

    @pytest.mark.asyncio
    async def test_call_with_http_client_error(self):
        """Test calling through HTTP client with error."""
        import httpx

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "HTTP error", request=MagicMock(), response=MagicMock()
        )

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response

        client = LLMRouterRPCClient(base_url="http://localhost:8000")
        client._http = mock_http

        with pytest.raises(httpx.HTTPStatusError):
            await client.call("test_method")

    @pytest.mark.asyncio
    async def test_call_without_server_or_http(self):
        """Test calling without server or HTTP client raises RuntimeError."""
        client = LLMRouterRPCClient()

        with pytest.raises(RuntimeError, match="RPCClient requires a server instance or base_url"):
            await client.call("test_method")

    @pytest.mark.asyncio
    async def test_call_server_unknown_method(self):
        """Test calling unknown method through server."""
        server = LLMRouterRPCServer()
        client = LLMRouterRPCClient(server=server)

        with pytest.raises(ValueError, match="Unknown RPC method"):
            await client.call("unknown_method")

    @pytest.mark.asyncio
    async def test_call_with_no_kwargs(self):
        """Test calling with no kwargs through server."""
        server = LLMRouterRPCServer()

        async def handler():
            return "no_args"

        server.register("no_args", handler)
        client = LLMRouterRPCClient(server=server)

        result = await client.call("no_args")

        assert result == "no_args"

    @pytest.mark.asyncio
    async def test_call_with_complex_kwargs(self):
        """Test calling with complex kwargs through server."""
        server = LLMRouterRPCServer()

        async def handler(data):
            return data

        server.register("complex", handler)
        client = LLMRouterRPCClient(server=server)

        complex_data = {"nested": {"key": "value"}, "list": [1, 2, 3]}
        result = await client.call("complex", data=complex_data)

        assert result == complex_data

    @pytest.mark.asyncio
    async def test_close_http_client(self):
        """Test closing HTTP client."""
        mock_http = AsyncMock()
        mock_http.aclose = AsyncMock()

        client = LLMRouterRPCClient(base_url="http://localhost:8000")
        client._http = mock_http

        await client.close()

        mock_http.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_http_client(self):
        """Test closing without HTTP client (should not raise)."""
        client = LLMRouterRPCClient()

        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_close_with_server_only(self):
        """Test closing when only server is set (should not raise)."""
        server = LLMRouterRPCServer()
        client = LLMRouterRPCClient(server=server)

        await client.close()  # Should not raise

    @pytest.mark.asyncio
    async def test_call_http_with_timeout(self):
        """Test HTTP client is created with timeout."""
        client = LLMRouterRPCClient(base_url="http://localhost:8000")

        assert client._http is not None
        # The timeout should be set in the httpx client

    @pytest.mark.asyncio
    async def test_call_http_empty_kwargs(self):
        """Test HTTP call with empty kwargs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response

        client = LLMRouterRPCClient(base_url="http://localhost:8000")
        client._http = mock_http

        result = await client.call("test_method")

        assert result == {}
        mock_http.post.assert_called_once_with("/rpc/test_method", json={})

    @pytest.mark.asyncio
    async def test_call_http_with_special_characters(self):
        """Test HTTP call with special characters in kwargs."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status = MagicMock()

        mock_http = AsyncMock()
        mock_http.post.return_value = mock_response

        client = LLMRouterRPCClient(base_url="http://localhost:8000")
        client._http = mock_http

        result = await client.call("test_method", text="Hello 世界", emoji="🚀")

        assert result == {"result": "success"}

    @pytest.mark.asyncio
    async def test_multiple_calls_with_server(self):
        """Test multiple calls through server."""
        server = LLMRouterRPCServer()
        call_count = 0

        async def counter():
            nonlocal call_count
            call_count += 1
            return call_count

        server.register("counter", counter)
        client = LLMRouterRPCClient(server=server)

        result1 = await client.call("counter")
        result2 = await client.call("counter")
        result3 = await client.call("counter")

        assert result1 == 1
        assert result2 == 2
        assert result3 == 3

    @pytest.mark.asyncio
    async def test_call_with_none_value(self):
        """Test calling with None value through server."""
        server = LLMRouterRPCServer()

        async def handler(value):
            return value

        server.register("test", handler)
        client = LLMRouterRPCClient(server=server)

        result = await client.call("test", value=None)

        assert result is None

    @pytest.mark.asyncio
    async def test_call_with_boolean_values(self):
        """Test calling with boolean values through server."""
        server = LLMRouterRPCServer()

        async def handler(value):
            return value

        server.register("test", handler)
        client = LLMRouterRPCClient(server=server)

        result_true = await client.call("test", value=True)
        result_false = await client.call("test", value=False)

        assert result_true is True
        assert result_false is False

    @pytest.mark.asyncio
    async def test_call_with_numeric_values(self):
        """Test calling with numeric values through server."""
        server = LLMRouterRPCServer()

        async def handler(value):
            return value

        server.register("test", handler)
        client = LLMRouterRPCClient(server=server)

        result_int = await client.call("test", value=42)
        result_float = await client.call("test", value=3.14)
        result_negative = await client.call("test", value=-10)

        assert result_int == 42
        assert result_float == 3.14
        assert result_negative == -10
