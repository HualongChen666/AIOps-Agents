# -*- coding: utf-8 -*-
"""Tests for KnowledgeGraphRPCServer module."""

import pytest
import asyncio

from extensions.addons.ai_plus.knowledge_graph_service.grpc.server import (
    KnowledgeGraphRPCServer,
)


class TestKnowledgeGraphRPCServer:
    """Test cases for KnowledgeGraphRPCServer class."""

    def test_initialization(self):
        """Test server initialization."""
        server = KnowledgeGraphRPCServer()
        assert server._handlers == {}
        assert isinstance(server._handlers, dict)

    def test_register_handler(self):
        """Test registering a handler."""
        server = KnowledgeGraphRPCServer()

        def test_handler():
            return "test"

        server.register("test_method", test_handler)

        assert "test_method" in server._handlers
        assert server._handlers["test_method"] == test_handler

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers."""
        server = KnowledgeGraphRPCServer()

        def handler1():
            return "handler1"

        def handler2():
            return "handler2"

        server.register("method1", handler1)
        server.register("method2", handler2)

        assert len(server._handlers) == 2
        assert "method1" in server._handlers
        assert "method2" in server._handlers

    def test_register_overwrite_handler(self):
        """Test overwriting an existing handler."""
        server = KnowledgeGraphRPCServer()

        def handler1():
            return "handler1"

        def handler2():
            return "handler2"

        server.register("test_method", handler1)
        server.register("test_method", handler2)

        assert server._handlers["test_method"] == handler2

    def test_list_methods_empty(self):
        """Test listing methods when none registered."""
        server = KnowledgeGraphRPCServer()
        methods = server.list_methods()
        assert methods == []

    def test_list_methods_with_handlers(self):
        """Test listing methods with registered handlers."""
        server = KnowledgeGraphRPCServer()

        def handler1():
            return "handler1"

        def handler2():
            return "handler2"

        server.register("method1", handler1)
        server.register("method2", handler2)

        methods = server.list_methods()
        assert len(methods) == 2
        # Check that methods are in the list (order may vary)
        assert "method1" in methods or "method2" in methods

    @pytest.mark.asyncio
    async def test_call_sync_handler(self):
        """Test calling a synchronous handler."""
        server = KnowledgeGraphRPCServer()

        def sync_handler(value):
            return value * 2

        server.register("double", sync_handler)

        result = await server.call("double", value=5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_call_async_handler(self):
        """Test calling an async handler."""
        server = KnowledgeGraphRPCServer()

        async def async_handler(value):
            await asyncio.sleep(0)
            return value * 2

        server.register("double_async", async_handler)

        result = await server.call("double_async", value=5)
        assert result == 10

    @pytest.mark.asyncio
    async def test_call_handler_with_no_args(self):
        """Test calling handler with no arguments."""
        server = KnowledgeGraphRPCServer()

        def no_args_handler():
            return "success"

        server.register("no_args", no_args_handler)

        result = await server.call("no_args")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_call_handler_with_multiple_args(self):
        """Test calling handler with multiple arguments."""
        server = KnowledgeGraphRPCServer()

        def multi_args_handler(a, b, c):
            return a + b + c

        server.register("sum", multi_args_handler)

        result = await server.call("sum", a=1, b=2, c=3)
        assert result == 6

    @pytest.mark.asyncio
    async def test_call_handler_with_dict_kwargs(self):
        """Test calling handler with dictionary kwargs."""
        server = KnowledgeGraphRPCServer()

        def dict_handler(data):
            return data["key"]

        server.register("dict_handler", dict_handler)

        result = await server.call("dict_handler", data={"key": "value"})
        assert result == "value"

    @pytest.mark.asyncio
    async def test_call_unknown_method(self):
        """Test calling an unknown method."""
        server = KnowledgeGraphRPCServer()

        with pytest.raises(ValueError, match="Unknown method"):
            await server.call("unknown_method")

    @pytest.mark.asyncio
    async def test_call_handler_that_raises_exception(self):
        """Test calling handler that raises an exception."""
        server = KnowledgeGraphRPCServer()

        def failing_handler():
            raise ValueError("Handler error")

        server.register("failing", failing_handler)

        with pytest.raises(ValueError, match="Handler error"):
            await server.call("failing")

    @pytest.mark.asyncio
    async def test_call_async_handler_that_raises_exception(self):
        """Test calling async handler that raises an exception."""
        server = KnowledgeGraphRPCServer()

        async def async_failing_handler():
            raise RuntimeError("Async handler error")

        server.register("async_failing", async_failing_handler)

        with pytest.raises(RuntimeError, match="Async handler error"):
            await server.call("async_failing")

    @pytest.mark.asyncio
    async def test_call_handler_returning_none(self):
        """Test calling handler that returns None."""
        server = KnowledgeGraphRPCServer()

        def none_handler():
            return None

        server.register("none", none_handler)

        result = await server.call("none")
        assert result is None

    @pytest.mark.asyncio
    async def test_call_handler_returning_complex_object(self):
        """Test calling handler that returns complex object."""
        server = KnowledgeGraphRPCServer()

        def complex_handler():
            return {"key": "value", "number": 42, "list": [1, 2, 3]}

        server.register("complex", complex_handler)

        result = await server.call("complex")
        assert result == {"key": "value", "number": 42, "list": [1, 2, 3]}

    @pytest.mark.asyncio
    async def test_call_handler_with_default_args(self):
        """Test calling handler with default arguments."""
        server = KnowledgeGraphRPCServer()

        def default_args_handler(a, b=10):
            return a + b

        server.register("default_args", default_args_handler)

        result = await server.call("default_args", a=5)
        assert result == 15

        result = await server.call("default_args", a=5, b=20)
        assert result == 25

    @pytest.mark.asyncio
    async def test_call_lambda_handler(self):
        """Test calling a lambda handler."""
        server = KnowledgeGraphRPCServer()

        server.register("lambda", lambda x: x * 3)

        result = await server.call("lambda", x=7)
        assert result == 21

    @pytest.mark.asyncio
    async def test_call_method_with_underscore(self):
        """Test calling method with underscore in name."""
        server = KnowledgeGraphRPCServer()

        def underscore_handler():
            return "success"

        server.register("test_method", underscore_handler)

        result = await server.call("test_method")
        assert result == "success"

    @pytest.mark.asyncio
    async def test_multiple_concurrent_calls(self):
        """Test multiple concurrent calls to different methods."""
        server = KnowledgeGraphRPCServer()

        async def slow_handler(value):
            await asyncio.sleep(0)
            return value * 2

        async def fast_handler(value):
            return value * 3

        server.register("slow", slow_handler)
        server.register("fast", fast_handler)

        # Execute calls concurrently
        results = await asyncio.gather(
            server.call("slow", value=5),
            server.call("fast", value=5),
        )

        assert results[0] == 10
        assert results[1] == 15

    @pytest.mark.asyncio
    async def test_call_handler_with_varargs(self):
        """Test calling handler with variable arguments."""
        server = KnowledgeGraphRPCServer()

        def varargs_handler(*args, **kwargs):
            return {"args": args, "kwargs": kwargs}

        server.register("varargs", varargs_handler)

        result = await server.call("varargs", a=1, b=2)
        assert result == {"args": (), "kwargs": {"a": 1, "b": 2}}

    @pytest.mark.asyncio
    async def test_list_methods_after_registration(self):
        """Test that list_methods reflects current registrations."""
        server = KnowledgeGraphRPCServer()

        assert server.list_methods() == []

        def handler1():
            pass

        server.register("method1", handler1)
        assert len(server.list_methods()) == 1

        def handler2():
            pass

        server.register("method2", handler2)
        assert len(server.list_methods()) == 2

    @pytest.mark.asyncio
    async def test_call_preserves_handler_state(self):
        """Test that handler state is preserved across calls."""
        server = KnowledgeGraphRPCServer()
        
        class Counter:
            def __init__(self):
                self.value = 0
        
        counter = Counter()

        def stateful_handler():
            counter.value += 1
            return counter.value

        server.register("counter", stateful_handler)

        result1 = await server.call("counter")
        result2 = await server.call("counter")
        result3 = await server.call("counter")

        assert result1 == 1
        assert result2 == 2
        assert result3 == 3
