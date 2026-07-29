# -*- coding: utf-8 -*-
"""
L5 Interface Layer - MCP (Model Context Protocol) Interface
Enhanced MCP interface for L5 Interface Layer
Provides standardized protocol for AI agent integration
"""

from datetime import datetime
from typing import Any, Callable, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from loguru import logger


class MCPInterface:
    """
    MCP (Model Context Protocol) interface for L5 Layer

    This interface provides:
    - Standardized JSON-RPC style endpoints
    - Tool registration and discovery
    - AI agent integration (Claude, Cursor, etc.)
    - Capability negotiation
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config
        self.router = APIRouter(prefix="/mcp", tags=["MCP"])
        self._tools: Dict[str, Any] = {}
        self._is_initialized = False

        self._register_tools()
        self._setup_routes()
        self._is_initialized = True
        logger.info("MCP Interface initialized for L5 Layer")

    def _register_tools(self) -> None:
        """Register available MCP tools"""
        # Import existing MCP tools
        try:
            from core.mcp_tools import (
                approve_repair,
                get_host_health,
                get_metrics,
                search_incident_history,
                trigger_repair_with_hitl,
            )

            self._tools = {
                "get_host_health": {
                    "name": "get_host_health",
                    "description": "Get health status of a specific host",
                    "handler": get_host_health,
                    "parameters": {"host_id": {"type": "string", "required": True}},
                },
                "trigger_repair_with_hitl": {
                    "name": "trigger_repair_with_hitl",
                    "description": "Trigger repair task with HITL (human-in-the-loop) approval",
                    "handler": trigger_repair_with_hitl,
                    "parameters": {
                        "alert_id": {"type": "string", "required": True},
                        "user": {"type": "string", "required": True},
                        "comment": {"type": "string", "required": False},
                    },
                },
                "search_incident_history": {
                    "name": "search_incident_history",
                    "description": "Search historical incident/repair records",
                    "handler": search_incident_history,
                    "parameters": {
                        "query": {"type": "string", "required": True},
                        "limit": {"type": "integer", "required": False, "default": 10},
                    },
                },
                "get_metrics": {
                    "name": "get_metrics",
                    "description": "Get current values for multiple metrics",
                    "handler": get_metrics,
                    "parameters": {
                        "host_id": {"type": "string", "required": True},
                        "metrics": {"type": "array", "required": True},
                    },
                },
                "approve_repair": {
                    "name": "approve_repair",
                    "description": "Approve or reject a repair task",
                    "handler": approve_repair,
                    "parameters": {
                        "repair_id": {"type": "string", "required": True},
                        "approved": {"type": "boolean", "required": True},
                        "comment": {"type": "string", "required": False},
                    },
                },
            }

            logger.info(f"Registered {len(self._tools)} MCP tools")

        except Exception as e:
            logger.error(f"Failed to register MCP tools: {e}")

    def _setup_routes(self) -> None:
        """Setup MCP routes"""

        @self.router.get("/tools")
        async def list_tools() -> Dict[str, Any]:
            """List available MCP tools"""
            return {
                "tools": [
                    {
                        "name": name,
                        "description": tool["description"],
                        "parameters": tool["parameters"],
                    }
                    for name, tool in self._tools.items()
                ],
                "count": len(self._tools),
            }

        @self.router.post("/tools/{tool_name}")
        async def execute_tool(tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
            """Execute a specific MCP tool"""
            if tool_name not in self._tools:
                raise HTTPException(status_code=404, detail=f"Tool {tool_name} not found")

            tool = self._tools[tool_name]
            handler = tool["handler"]

            params = self._validate_tool_params(tool_name, params)

            try:
                # Call the tool handler
                if tool_name == "get_host_health":
                    return await handler(params.get("host_id"))  # type: ignore[no-any-return]
                elif tool_name == "trigger_repair_with_hitl":
                    return await handler(  # type: ignore[no-any-return]
                        params.get("alert_id"), params.get("user"), params.get("comment")
                    )
                elif tool_name == "search_incident_history":
                    return await handler(  # type: ignore[no-any-return]
                        params.get("query"), params.get("limit", 10)
                    )
                elif tool_name == "get_metrics":
                    return await handler(  # type: ignore[no-any-return]
                        params.get("host_id"), params.get("metrics")
                    )
                elif tool_name == "approve_repair":
                    return await handler(  # type: ignore[no-any-return]
                        params.get("repair_id"), params.get("approved"), params.get("comment")
                    )
                else:
                    return await handler(**params)  # type: ignore[no-any-return]

            except Exception as e:
                logger.error(f"Tool execution error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.get("/capabilities")
        async def get_capabilities() -> Dict[str, Any]:
            """Get MCP interface capabilities"""
            return {
                "protocol": "MCP",
                "version": "1.0",
                "tools": list(self._tools.keys()),
                "features": ["tool_execution", "tool_discovery", "async_execution"],
                "timestamp": datetime.now().isoformat(),
            }

    def _validate_tool_params(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """校验 L5 MCP 工具的输入参数类型和必填项。"""
        tool = self._tools[tool_name]
        schema = tool["parameters"]
        validated: Dict[str, Any] = {}

        for name, spec in schema.items():
            required = spec.get("required", False)
            param_type = spec.get("type")
            if required and name not in params:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Missing required parameter '{name}' for tool '{tool_name}'",
                )

        for name, value in params.items():
            if name not in schema:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Unexpected parameter '{name}' for tool '{tool_name}'",
                )
            spec = schema[name]
            param_type = spec.get("type")
            if param_type == "string" and not isinstance(value, str):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Parameter '{name}' must be a string",
                )
            if param_type == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Parameter '{name}' must be an integer",
                )
            if param_type == "boolean" and not isinstance(value, bool):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Parameter '{name}' must be a boolean",
                )
            if param_type == "array" and not isinstance(value, list):
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Parameter '{name}' must be an array",
                )
            validated[name] = value

        return validated

    def get_router(self) -> APIRouter:
        """Get the MCP router"""
        return self.router

    def get_status(self) -> Dict[str, Any]:
        """Get interface status"""
        return {
            "initialized": self._is_initialized,
            "tool_count": len(self._tools),
            "tools": list(self._tools.keys()),
        }

    def register_tool(
        self, name: str, description: str, handler: Callable[..., Any], parameters: Dict[str, Any]
    ) -> None:
        """
        Register a custom MCP tool

        Args:
            name: Tool name
            description: Tool description
            handler: Tool handler function
            parameters: Tool parameter schema
        """
        self._tools[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "parameters": parameters,
        }
        logger.info(f"Registered custom MCP tool: {name}")


# Global singleton instance
_mcp_interface: Optional[MCPInterface] = None


def get_mcp_interface() -> Optional[MCPInterface]:
    """Get global MCP interface instance"""
    return _mcp_interface


def init_mcp_interface(config: Dict[str, Any]) -> MCPInterface:
    """Initialize global MCP interface"""
    global _mcp_interface
    _mcp_interface = MCPInterface(config)
    return _mcp_interface
