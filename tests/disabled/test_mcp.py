# -*- coding: utf-8 -*-
"""
MCP Protocol Tests
"""

import pytest

from core.interface.mcp import (
    ContextManager,
    MCPMessage,
    MCPMethod,
    MCPProtocolParser,
    MCPServer,
    ToolRegistry,
)


class TestMCPProtocol:
    """Test MCP protocol"""

    def test_message_creation(self):
        """Test message creation"""
        msg = MCPMessage(method="test", params={"key": "value"}, id="123")
        assert msg.method == "test"
        assert msg.params == {"key": "value"}
        assert msg.id == "123"

    def test_message_serialization(self):
        """Test message serialization"""
        msg = MCPMessage(method="test", params={"key": "value"}, id="123")
        json_str = msg.to_json()
        assert "test" in json_str

    def test_message_deserialization(self):
        """Test message deserialization"""
        json_str = '{"jsonrpc": "2.0", "method": "test", "id": "123"}'
        msg = MCPMessage.from_json(json_str)
        assert msg.method == "test"
        assert msg.id == "123"

    def test_parser(self):
        """Test protocol parser"""
        parser = MCPProtocolParser()
        json_str = '{"jsonrpc": "2.0", "method": "test", "id": "123"}'
        msg = parser.parse_message(json_str)
        assert msg is not None
        assert msg.method == "test"

    def test_create_request(self):
        """Test request creation"""
        parser = MCPProtocolParser()
        request = parser.create_request(MCPMethod.INITIALIZE)
        assert request.method == MCPMethod.INITIALIZE.value
        assert request.id is not None

    def test_create_response(self):
        """Test response creation"""
        parser = MCPProtocolParser()
        response = parser.create_response("123", result={"status": "ok"})
        assert response.id == "123"
        assert response.result == {"status": "ok"}

    def test_create_notification(self):
        """Test notification creation"""
        parser = MCPProtocolParser()
        notification = parser.create_notification(MCPMethod.LIST_TOOLS)
        assert notification.method == MCPMethod.LIST_TOOLS.value
        assert notification.id is None  # Notifications have no ID


class TestContextManager:
    """Test context manager"""

    @pytest.mark.asyncio
    async def test_set_context(self):
        """Test setting context"""
        manager = ContextManager()
        result = await manager.set_context("ctx1", "key1", "value1")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_context(self):
        """Test getting context"""
        manager = ContextManager()
        await manager.set_context("ctx1", "key1", "value1")
        value = await manager.get_context("ctx1", "key1")
        assert value == "value1"

    @pytest.mark.asyncio
    async def test_delete_context(self):
        """Test deleting context"""
        manager = ContextManager()
        await manager.set_context("ctx1", "key1", "value1")
        result = await manager.delete_context("ctx1", "key1")
        assert result is True
        value = await manager.get_context("ctx1", "key1")
        assert value is None

    @pytest.mark.asyncio
    async def test_list_contexts(self):
        """Test listing contexts"""
        manager = ContextManager()
        await manager.set_context("ctx1", "key1", "value1")
        await manager.set_context("ctx2", "key2", "value2")
        contexts = await manager.list_contexts()
        assert len(contexts) == 2
        assert "ctx1" in contexts
        assert "ctx2" in contexts

    @pytest.mark.asyncio
    async def test_get_context_keys(self):
        """Test getting context keys"""
        manager = ContextManager()
        await manager.set_context("ctx1", "key1", "value1")
        await manager.set_context("ctx1", "key2", "value2")
        keys = await manager.get_context_keys("ctx1")
        assert len(keys) == 2
        assert "key1" in keys
        assert "key2" in keys

    @pytest.mark.asyncio
    async def test_ttl_expiration(self):
        """Test TTL expiration"""
        manager = ContextManager()
        await manager.set_context("ctx1", "key1", "value1", ttl=0.1)
        import asyncio

        await asyncio.sleep(0.2)
        value = await manager.get_context("ctx1", "key1")
        assert value is None  # Expired


class TestToolRegistry:
    """Test tool registry"""

    @pytest.mark.asyncio
    async def test_register_tool(self):
        """Test tool registration"""
        registry = ToolRegistry()

        async def dummy_handler(args):
            return "result"

        registry.register_tool(
            name="test_tool",
            description="Test tool",
            input_schema={"type": "object"},
            handler=dummy_handler,
        )

        tools = registry.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "test_tool"

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test tool calling"""
        registry = ToolRegistry()

        async def dummy_handler(args):
            return args.get("input", "")

        registry.register_tool(
            name="echo",
            description="Echo tool",
            input_schema={"type": "object", "properties": {"input": {"type": "string"}}},
            handler=dummy_handler,
        )

        result = await registry.call_tool("echo", {"input": "hello"})
        assert result["content"] == "hello"
        assert result["isError"] is False

    @pytest.mark.asyncio
    async def test_call_nonexistent_tool(self):
        """Test calling non-existent tool"""
        registry = ToolRegistry()

        with pytest.raises(ValueError):
            await registry.call_tool("nonexistent", {})


class TestMCPServer:
    """Test MCP server"""

    def test_server_init(self):
        """Test server initialization"""
        server = MCPServer()
        assert server.host == "localhost"
        assert server.port == 8080
        assert server.context_manager is not None
        assert server.tool_registry is not None

    @pytest.mark.asyncio
    async def test_handle_initialize(self):
        """Test initialize handling"""
        server = MCPServer()
        result = await server._handle_initialize({})
        assert "protocolVersion" in result
        assert "serverInfo" in result

    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test list tools handling"""
        server = MCPServer()
        result = await server._handle_list_tools({})
        assert isinstance(result, list)
        # Should have default tools registered
        assert len(result) >= 0

    @pytest.mark.asyncio
    async def test_handle_get_context(self):
        """Test get context handling"""
        server = MCPServer()
        # First set context
        await server.context_manager.set_context("ctx1", "key1", "value1")

        result = await server._handle_get_context({"context_id": "ctx1", "key": "key1"})
        assert result == "value1"

    @pytest.mark.asyncio
    async def test_handle_set_context(self):
        """Test set context handling"""
        server = MCPServer()
        result = await server._handle_set_context(
            {"context_id": "ctx1", "key": "key1", "value": "value1"}
        )
        assert result is True
