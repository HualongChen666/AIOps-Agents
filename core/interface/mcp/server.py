# -*- coding: utf-8 -*-
"""
MCP Server Implementation
Implements Model Context Protocol server for AIOps Agent
"""

from typing import Any, Dict, List, Optional

from loguru import logger

from .context import ContextManager
from .protocol import MCPMethod, MCPProtocolParser
from .tools import ToolRegistry, register_default_tools


class MCPServer:
    """
    MCP Server for AIOps Agent
    """

    def __init__(self, host: str = "localhost", port: int = 8080, max_contexts: int = 1000):
        """
        Initialize MCP server

        Args:
            host: Server host
            port: Server port
            max_contexts: Maximum number of contexts
        """
        self.host = host
        self.port = port
        self.parser = MCPProtocolParser()
        self.context_manager = ContextManager(max_contexts)
        self.tool_registry = ToolRegistry()

        # Register default tools
        register_default_tools(self.tool_registry)

        self._running = False

    async def start(self) -> None:
        """Start MCP server"""
        self._running = True
        logger.info(f"MCP Server started on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop MCP server"""
        self._running = False
        logger.info("MCP Server stopped")

    async def handle_message(self, message: str) -> str:
        """
        Handle incoming MCP message

        Args:
            message: JSON message string

        Returns:
            JSON response string
        """
        try:
            msg = self.parser.parse_message(message)
            if not msg:
                error = self.parser.create_error(-32700, "Parse error")
                response = self.parser.create_response("", error=error)
                return response.to_json()

            # Route based on method
            result: Any
            if msg.method == MCPMethod.INITIALIZE.value:
                result = await self._handle_initialize(msg.params or {})
            elif msg.method == MCPMethod.LIST_TOOLS.value:
                result = await self._handle_list_tools(msg.params or {})
            elif msg.method == MCPMethod.CALL_TOOL.value:
                result = await self._handle_call_tool(msg.params or {})
            elif msg.method == MCPMethod.GET_CONTEXT.value:
                result = await self._handle_get_context(msg.params or {})
            elif msg.method == MCPMethod.SET_CONTEXT.value:
                result = await self._handle_set_context(msg.params or {})
            elif msg.method == MCPMethod.LIST_CONTEXTS.value:
                result = await self._handle_list_contexts(msg.params or {})
            else:
                error = self.parser.create_error(-32601, "Method not found")
                response = self.parser.create_response(msg.id or "", error=error)
                return response.to_json()

            response = self.parser.create_response(msg.id or "", result=result)
            return response.to_json()

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            error = self.parser.create_error(-32603, "Internal error", str(e))
            response = self.parser.create_response("", error=error)
            return response.to_json()

    async def _handle_initialize(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle initialize request"""
        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "aiops-agent", "version": "1.0.0"},
            "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
        }

    async def _handle_list_tools(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Handle list tools request"""
        return self.tool_registry.list_tools()

    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle call tool request"""
        name = params.get("name")
        if name is None:
            raise ValueError("Tool name is required")
        arguments = params.get("arguments", {})
        return await self.tool_registry.call_tool(name, arguments)

    async def _handle_get_context(self, params: Dict[str, Any]) -> Optional[Any]:
        """Handle get context request"""
        context_id = params.get("context_id")
        key = params.get("key")
        if context_id is None or key is None:
            raise ValueError("context_id and key are required")
        return await self.context_manager.get_context(context_id, key)

    async def _handle_set_context(self, params: Dict[str, Any]) -> bool:
        """Handle set context request"""
        context_id = params.get("context_id")
        key = params.get("key")
        if context_id is None or key is None:
            raise ValueError("context_id and key are required")
        value = params.get("value")
        metadata = params.get("metadata")
        ttl = params.get("ttl")
        return await self.context_manager.set_context(context_id, key, value, metadata, ttl)

    async def _handle_list_contexts(self, params: Dict[str, Any]) -> List[str]:
        """Handle list contexts request"""
        return await self.context_manager.list_contexts()

    def get_context_manager(self) -> ContextManager:
        """Get context manager instance"""
        return self.context_manager

    def get_tool_registry(self) -> ToolRegistry:
        """Get tool registry instance"""
        return self.tool_registry
