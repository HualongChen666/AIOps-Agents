# -*- coding: utf-8 -*-
"""
MCP Client SDK
Client library for connecting to MCP servers
"""

from typing import Any, Dict, List, Optional, cast

import httpx
from loguru import logger

from .protocol import MCPMethod, MCPProtocolParser


class MCPClient:
    """
    MCP client for connecting to MCP servers
    """

    def __init__(self, server_url: str, timeout: float = 30.0):
        """
        Initialize MCP client

        Args:
            server_url: MCP server URL
            timeout: Request timeout
        """
        self.server_url = server_url
        self.timeout = timeout
        self.parser = MCPProtocolParser()
        self._client = httpx.AsyncClient(timeout=timeout)

    async def initialize(self) -> Dict[str, Any]:
        """
        Initialize connection to MCP server

        Returns:
            Server capabilities
        """
        request = self.parser.create_request(MCPMethod.INITIALIZE)
        response_str = await self._send_request(request.to_json())
        response = self.parser.parse_message(response_str)

        if response and response.result:
            logger.info(
                f"Connected to MCP server: {response.result.get('serverInfo', {}).get('name')}"
            )
            return cast(Dict[str, Any], response.result)

        raise Exception("Failed to initialize MCP connection")

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        List available tools

        Returns:
            List of tool definitions
        """
        request = self.parser.create_request(MCPMethod.LIST_TOOLS)
        response_str = await self._send_request(request.to_json())
        response = self.parser.parse_message(response_str)

        if response and response.result:
            return cast(List[Dict[str, Any]], response.result)

        return []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        request = self.parser.create_request(
            MCPMethod.CALL_TOOL, params={"name": name, "arguments": arguments}
        )
        response_str = await self._send_request(request.to_json())
        response = self.parser.parse_message(response_str)

        if response and response.result:
            return cast(Dict[str, Any], response.result)

        raise Exception(f"Tool call failed: {name}")

    async def get_context(self, context_id: str, key: str) -> Optional[Any]:
        """
        Get context value

        Args:
            context_id: Context identifier
            key: Context key

        Returns:
            Context value
        """
        request = self.parser.create_request(
            MCPMethod.GET_CONTEXT, params={"context_id": context_id, "key": key}
        )
        response_str = await self._send_request(request.to_json())
        response = self.parser.parse_message(response_str)

        if response and response.result:
            return response.result

        return None

    async def set_context(
        self,
        context_id: str,
        key: str,
        value: Any,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[float] = None,
    ) -> bool:
        """
        Set context value

        Args:
            context_id: Context identifier
            key: Context key
            value: Context value
            metadata: Metadata
            ttl: Time to live

        Returns:
            True if successful
        """
        request = self.parser.create_request(
            MCPMethod.SET_CONTEXT,
            params={
                "context_id": context_id,
                "key": key,
                "value": value,
                "metadata": metadata,
                "ttl": ttl,
            },
        )
        response_str = await self._send_request(request.to_json())
        response = self.parser.parse_message(response_str)

        if response and response.result:
            return cast(bool, response.result)

        return False

    async def list_contexts(self) -> List[str]:
        """
        List all contexts

        Returns:
            List of context IDs
        """
        request = self.parser.create_request(MCPMethod.LIST_CONTEXTS)
        response_str = await self._send_request(request.to_json())
        response = self.parser.parse_message(response_str)

        if response and response.result:
            return cast(List[str], response.result)

        return []

    async def _send_request(self, message: str) -> str:
        """
        Send request to MCP server

        Args:
            message: JSON message string

        Returns:
            Response JSON string
        """
        try:
            response = await self._client.post(
                self.server_url,
                json={"message": message},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return cast(str, response.json().get("response", ""))
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            raise

    async def close(self) -> None:
        """Close client connection"""
        await self._client.aclose()
        logger.info("MCP client closed")
