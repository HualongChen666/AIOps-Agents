# -*- coding: utf-8 -*-
"""
MCP Tool Calling Interface
Implements tool invocation and management
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from loguru import logger


@dataclass
class Tool:
    """Tool definition"""

    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable

    async def execute(self, arguments: Dict[str, Any]) -> Any:
        """Execute tool with arguments"""
        return await self.handler(arguments)


class ToolRegistry:
    """
    Registry for MCP tools
    """

    def __init__(self):
        """Initialize tool registry"""
        self._tools: Dict[str, Tool] = {}

    def register_tool(
        self, name: str, description: str, input_schema: Dict[str, Any], handler: Callable
    ) -> None:
        """
        Register a tool

        Args:
            name: Tool name
            description: Tool description
            input_schema: JSON schema for input validation
            handler: Async handler function
        """
        self._tools[name] = Tool(
            name=name, description=description, input_schema=input_schema, handler=handler
        )
        logger.info(f"Registered tool: {name}")

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool result
        """
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")

        tool = self._tools[name]

        try:
            result = await tool.execute(arguments)
            return {"content": result, "isError": False}
        except Exception as e:
            logger.error(f"Tool execution failed: {name}: {e}")
            return {"content": str(e), "isError": True}

    def list_tools(self) -> List[Dict[str, Any]]:
        """
        List all registered tools

        Returns:
            List of tool definitions
        """
        return [
            {"name": tool.name, "description": tool.description, "inputSchema": tool.input_schema}
            for tool in self._tools.values()
        ]

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self._tools.get(name)


# Default tools for AIOps Agent
async def execute_command_handler(arguments: Dict[str, Any]) -> str:
    """Execute system command with security validation

    🔧 P0 Security Fix: Added command validation to prevent command injection
    - Only allows whitelisted safe commands
    - Validates command structure and arguments
    - Prevents shell metacharacters and dangerous operations
    """
    import re
    import shlex
    import subprocess  # nosec B404

    command = arguments.get("command")
    if not command:
        raise ValueError("Command is required")

    # 🔧 P0 Security: Command validation
    # Define whitelist of safe commands (no shell metacharacters)
    SAFE_COMMANDS = {
        "echo",
        "date",
        "hostname",
        "whoami",
        "pwd",
        "ls",
        "dir",
        "df",
        "free",
        "uptime",
        "uname",
        "arch",
        "nproc",
    }

    # Parse command safely
    try:
        # Use shlex to parse command safely
        parts = shlex.split(command)
        if not parts:
            raise ValueError("Invalid command format")

        base_command = parts[0].strip().lower()

        # Check if command is in whitelist
        if base_command not in SAFE_COMMANDS:
            raise ValueError(
                f"Command '{base_command}' is not in the allowed safe commands list. "
                f"Allowed commands: {', '.join(sorted(SAFE_COMMANDS))}"
            )

        # Validate no shell metacharacters in arguments
        for arg in parts[1:]:
            # Check for dangerous patterns
            dangerous_patterns = [
                r"[;&|`$()]",  # Shell metacharacters
                r"\.\./",  # Path traversal
                r">",  # Output redirection
                r"<",  # Input redirection
            ]
            for pattern in dangerous_patterns:
                if re.search(pattern, arg):
                    raise ValueError(f"Argument contains dangerous pattern: {arg}")

        # Execute using list form (no shell=True)
        result = subprocess.run(
            parts,
            capture_output=True,
            text=True,
            shell=False,  # nosec B603
            timeout=30,  # Add timeout for safety
        )

        return f"stdout: {result.stdout}\nstderr: {result.stderr}\nreturncode: {result.returncode}"

    except subprocess.TimeoutExpired:
        raise ValueError("Command execution timed out (30s limit)")
    except ValueError as e:
        raise ValueError(f"Command validation failed: {e}")
    except Exception as e:
        raise ValueError(f"Command execution failed: {e}")


async def get_metrics_handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Get system metrics"""
    # Placeholder - integrate with actual metrics collector
    return {"cpu_usage": 45.2, "memory_usage": 68.3, "disk_usage": 52.1}


async def check_alerts_handler(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check active alerts"""
    # Placeholder - integrate with actual alert engine
    return [
        {
            "id": "alert-1",
            "level": "warning",
            "title": "High CPU usage",
            "timestamp": "2024-01-01T00:00:00Z",
        }
    ]


def register_default_tools(registry: ToolRegistry) -> None:
    """Register default AIOps tools"""
    registry.register_tool(
        name="execute_command",
        description="Execute a system command",
        input_schema={
            "type": "object",
            "properties": {"command": {"type": "string", "description": "Command to execute"}},
            "required": ["command"],
        },
        handler=execute_command_handler,
    )

    registry.register_tool(
        name="get_metrics",
        description="Get current system metrics",
        input_schema={"type": "object", "properties": {}},
        handler=get_metrics_handler,
    )

    registry.register_tool(
        name="check_alerts",
        description="Check active alerts",
        input_schema={
            "type": "object",
            "properties": {"level": {"type": "string", "description": "Alert level filter"}},
        },
        handler=check_alerts_handler,
    )
