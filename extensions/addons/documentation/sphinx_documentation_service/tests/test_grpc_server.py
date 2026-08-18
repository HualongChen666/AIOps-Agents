# -*- coding: utf-8 -*-
"""Tests for grpc/server.py - gRPC-like in-memory server."""

import asyncio
import pytest

from extensions.addons.documentation.sphinx_documentation_service.grpc.server import (
    SphinxDocumentationServiceRPCServer,
)


class TestSphinxDocumentationServiceRPCServer:
    """Test suite for SphinxDocumentationServiceRPCServer."""

    @pytest.fixture
    def server(self):
        """Fixture for RPC server."""
        return SphinxDocumentationServiceRPCServer()

    def test_init(self, server):
        """Test initialization."""
        assert isinstance(server._handlers, dict)
        assert len(server._handlers) == 0

    def test_register_handler(self, server):
        """Test registering a handler."""

        async def test_handler():
            return "result"

        server.register("test_method", test_handler)
        assert "test_method" in server._handlers
        assert server._handlers["test_method"] is test_handler

    def test_register_multiple_handlers(self, server):
        """Test registering multiple handlers."""

        async def handler1():
            return "result1"

        async def handler2():
            return "result2"

        async def handler3():
            return "result3"

        server.register("method1", handler1)
        server.register("method2", handler2)
        server.register("method3", handler3)

        assert len(server._handlers) == 3
        assert "method1" in server._handlers
        assert "method2" in server._handlers
        assert "method3" in server._handlers

    def test_register_overwrite_handler(self, server):
        """Test that registering overwrites existing handler."""

        async def handler1():
            return "result1"

        async def handler2():
            return "result2"

        server.register("test_method", handler1)
        server.register("test_method", handler2)

        assert server._handlers["test_method"] is handler2

    def test_list_methods_empty(self, server):
        """Test list_methods with no registered methods."""
        methods = server.list_methods()
        assert isinstance(methods, list)
        assert len(methods) == 0

    def test_list_methods_with_handlers(self, server):
        """Test list_methods with registered handlers."""

        async def handler1():
            return "result1"

        async def handler2():
            return "result2"

        server.register("method1", handler1)
        server.register("method2", handler2)

        methods = server.list_methods()
        assert isinstance(methods, list)
        assert len(methods) == 2
        assert "method1" in methods
        assert "method2" in methods

    @pytest.mark.asyncio
    async def test_call_registered_handler(self, server):
        """Test calling a registered handler."""

        async def test_handler(value):
            return f"processed: {value}"

        server.register("test_method", test_handler)
        result = await server.call("test_method", value="test")
        assert result == "processed: test"

    @pytest.mark.asyncio
    async def test_call_with_kwargs(self, server):
        """Test calling handler with keyword arguments."""

        async def test_handler(a, b, c):
            return a + b + c

        server.register("sum", test_handler)
        result = await server.call("sum", a=1, b=2, c=3)
        assert result == 6

    @pytest.mark.asyncio
    async def test_call_with_no_args(self, server):
        """Test calling handler with no arguments."""

        async def test_handler():
            return "no args"

        server.register("no_args", test_handler)
        result = await server.call("no_args")
        assert result == "no args"

    @pytest.mark.asyncio
    async def test_call_with_positional_args(self, server):
        """Test calling handler with keyword arguments (call only supports kwargs)."""

        async def test_handler(a, b):
            return a + b

        server.register("add", test_handler)
        result = await server.call("add", a=5, b=10)
        assert result == 15

    @pytest.mark.asyncio
    async def test_call_with_mixed_args(self, server):
        """Test calling handler with keyword arguments."""

        async def test_handler(a, b, c=0):
            return a + b + c

        server.register("mixed", test_handler)
        result = await server.call("mixed", a=1, b=2, c=3)
        assert result == 6

    @pytest.mark.asyncio
    async def test_call_unregistered_method(self, server):
        """Test calling unregistered method raises ValueError."""
        with pytest.raises(ValueError, match="Unknown RPC method"):
            await server.call("nonexistent_method")

    @pytest.mark.asyncio
    async def test_call_handler_returning_dict(self, server):
        """Test handler returning dict."""

        async def test_handler():
            return {"key": "value", "number": 123}

        server.register("dict_handler", test_handler)
        result = await server.call("dict_handler")
        assert result == {"key": "value", "number": 123}

    @pytest.mark.asyncio
    async def test_call_handler_returning_list(self, server):
        """Test handler returning list."""

        async def test_handler():
            return [1, 2, 3, 4, 5]

        server.register("list_handler", test_handler)
        result = await server.call("list_handler")
        assert result == [1, 2, 3, 4, 5]

    @pytest.mark.asyncio
    async def test_call_handler_returning_none(self, server):
        """Test handler returning None."""

        async def test_handler():
            return None

        server.register("none_handler", test_handler)
        result = await server.call("none_handler")
        assert result is None

    @pytest.mark.asyncio
    async def test_call_handler_returning_number(self, server):
        """Test handler returning number."""

        async def test_handler():
            return 42

        server.register("number_handler", test_handler)
        result = await server.call("number_handler")
        assert result == 42

    @pytest.mark.asyncio
    async def test_call_handler_returning_string(self, server):
        """Test handler returning string."""

        async def test_handler():
            return "test string"

        server.register("string_handler", test_handler)
        result = await server.call("string_handler")
        assert result == "test string"

    @pytest.mark.asyncio
    async def test_call_handler_returning_bool(self, server):
        """Test handler returning boolean."""

        async def test_handler():
            return True

        server.register("bool_handler", test_handler)
        result = await server.call("bool_handler")
        assert result is True

    @pytest.mark.asyncio
    async def test_call_handler_raising_exception(self, server):
        """Test handler that raises exception."""

        async def failing_handler():
            raise ValueError("handler error")

        server.register("failing", failing_handler)
        with pytest.raises(ValueError, match="handler error"):
            await server.call("failing")

    @pytest.mark.asyncio
    async def test_call_handler_with_async_operation(self, server):
        """Test handler with async operation."""

        async def async_handler():
            await asyncio.sleep(0.01)
            return "async result"

        server.register("async_op", async_handler)
        result = await server.call("async_op")
        assert result == "async result"

    @pytest.mark.asyncio
    async def test_call_non_async_handler(self, server):
        """Test calling a non-async handler (should work)."""

        def sync_handler():
            return "sync result"

        server.register("sync", sync_handler)
        result = await server.call("sync")
        assert result == "sync result"

    @pytest.mark.asyncio
    async def test_call_with_unicode_method_name(self, server):
        """Test calling handler with unicode method name."""

        async def handler():
            return "result"

        server.register("测试方法", handler)
        result = await server.call("测试方法")
        assert result == "result"

    @pytest.mark.asyncio
    async def test_call_with_special_characters_method_name(self, server):
        """Test calling handler with special characters in method name."""

        async def handler():
            return "result"

        server.register("test-method_v1.0", handler)
        result = await server.call("test-method_v1.0")
        assert result == "result"

    @pytest.mark.asyncio
    async def test_concurrent_calls(self, server):
        """Test concurrent calls to different handlers."""

        async def handler1():
            await asyncio.sleep(0.01)
            return "result1"

        async def handler2():
            await asyncio.sleep(0.01)
            return "result2"

        async def handler3():
            await asyncio.sleep(0.01)
            return "result3"

        server.register("method1", handler1)
        server.register("method2", handler2)
        server.register("method3", handler3)

        results = await asyncio.gather(
            server.call("method1"),
            server.call("method2"),
            server.call("method3"),
        )
        assert results == ["result1", "result2", "result3"]

    @pytest.mark.asyncio
    async def test_concurrent_calls_same_handler(self, server):
        """Test concurrent calls to the same handler."""

        async def counter_handler(value):
            await asyncio.sleep(0.01)
            return value

        server.register("counter", counter_handler)

        results = await asyncio.gather(
            server.call("counter", value=1),
            server.call("counter", value=2),
            server.call("counter", value=3),
        )
        assert len(results) == 3
        assert results == [1, 2, 3]

    def test_multiple_servers(self):
        """Test multiple server instances."""
        server1 = SphinxDocumentationServiceRPCServer()
        server2 = SphinxDocumentationServiceRPCServer()

        async def handler1():
            return "server1"

        async def handler2():
            return "server2"

        server1.register("test", handler1)
        server2.register("test", handler2)

        assert "test" in server1._handlers
        assert "test" in server2._handlers
        assert server1._handlers["test"] is not server2._handlers["test"]

    @pytest.mark.asyncio
    async def test_call_with_complex_return_value(self, server):
        """Test handler returning complex nested structure."""

        async def complex_handler():
            return {
                "string": "value",
                "number": 123,
                "list": [1, 2, 3],
                "nested": {"key": "value"},
                "mixed": [1, "two", {"three": 3}],
            }

        server.register("complex", complex_handler)
        result = await server.call("complex")
        assert result["string"] == "value"
        assert result["number"] == 123
        assert result["list"] == [1, 2, 3]
        assert result["nested"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_call_handler_with_default_args(self, server):
        """Test handler with default arguments."""

        async def default_handler(a, b=10, c=20):
            return a + b + c

        server.register("defaults", default_handler)
        result1 = await server.call("defaults", a=1)
        result2 = await server.call("defaults", a=1, b=2)
        result3 = await server.call("defaults", a=1, b=2, c=3)
        assert result1 == 31
        assert result2 == 23
        assert result3 == 6

    @pytest.mark.asyncio
    async def test_call_handler_with_varargs(self, server):
        """Test handler with keyword arguments (varargs not supported)."""

        async def varargs_handler(**kwargs):
            return sum(kwargs.values())

        server.register("varargs", varargs_handler)
        result = await server.call("varargs", a=1, b=2, c=3, d=4, e=5)
        assert result == 15

    @pytest.mark.asyncio
    async def test_call_handler_with_kwargs(self, server):
        """Test handler with variable keyword arguments."""

        async def kwargs_handler(**kwargs):
            return len(kwargs)

        server.register("kwargs", kwargs_handler)
        result = await server.call("kwargs", a=1, b=2, c=3)
        assert result == 3

    @pytest.mark.asyncio
    async def test_list_methods_after_registration(self, server):
        """Test list_methods returns correct list after registrations."""

        async def handler1():
            return "1"

        async def handler2():
            return "2"

        server.register("method1", handler1)
        methods1 = server.list_methods()
        server.register("method2", handler2)
        methods2 = server.list_methods()

        assert len(methods1) == 1
        assert len(methods2) == 2
        assert "method2" in methods2

    @pytest.mark.asyncio
    async def test_call_empty_method_name(self, server):
        """Test calling with empty method name."""
        with pytest.raises(ValueError, match="Unknown RPC method"):
            await server.call("")

    @pytest.mark.asyncio
    async def test_call_handler_with_large_return(self, server):
        """Test handler returning large data structure."""

        async def large_handler():
            return {"items": list(range(1000))}

        server.register("large", large_handler)
        result = await server.call("large")
        assert len(result["items"]) == 1000

    @pytest.mark.asyncio
    async def test_call_handler_with_unicode_return(self, server):
        """Test handler returning unicode data."""

        async def unicode_handler():
            return {"text": "测试数据", "emoji": "🌍"}

        server.register("unicode", unicode_handler)
        result = await server.call("unicode")
        assert result["text"] == "测试数据"
        assert result["emoji"] == "🌍"
