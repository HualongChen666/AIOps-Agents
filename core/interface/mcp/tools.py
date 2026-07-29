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

    @staticmethod
    def _validate_arguments(tool: Tool, arguments: Dict[str, Any]) -> None:
        """Validate arguments against the tool's input schema."""
        if not isinstance(arguments, dict):
            raise ValueError("Arguments must be a dictionary")

        schema = tool.input_schema or {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        for key in required:
            if key not in arguments:
                raise ValueError(f"Missing required argument: {key}")

        for key, value in arguments.items():
            if key not in properties:
                raise ValueError(f"Unexpected argument: {key}")
            prop = properties[key]
            prop_type = prop.get("type")
            if prop_type == "string" and not isinstance(value, str):
                raise ValueError(f"Argument '{key}' must be a string")
            if prop_type == "integer" and not isinstance(value, int):
                raise ValueError(f"Argument '{key}' must be an integer")
            if prop_type == "array" and not isinstance(value, list):
                raise ValueError(f"Argument '{key}' must be an array")
            if prop_type == "boolean" and not isinstance(value, bool):
                raise ValueError(f"Argument '{key}' must be a boolean")
            allowed = prop.get("enum")
            if allowed is not None and value not in allowed:
                raise ValueError(f"Argument '{key}' must be one of {allowed}, got {value!r}")
            if isinstance(value, str) and len(value) > 4096:
                raise ValueError(f"Argument '{key}' exceeds maximum length of 4096")

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
            self._validate_arguments(tool, arguments)
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

    🔧 P0 Security Fix: Restricted command whitelist and arguments
    - Only allows a small set of read-only commands
    - Each command has a strict argument allow-list regex
    - Blocks shell metacharacters, absolute paths, path traversal, and
      recursive/network/privilege flags
    """
    import re
    import shlex
    import subprocess  # nosec B404

    command = arguments.get("command")
    if not isinstance(command, str) or not command.strip():
        raise ValueError("Command is required and must be a non-empty string")
    if len(command) > 512:
        raise ValueError("Command exceeds maximum length of 512")

    # Parse command safely
    try:
        parts = shlex.split(command)
    except ValueError as exc:
        raise ValueError(f"Invalid command format: {exc}") from exc
    if not parts:
        raise ValueError("Invalid command format")

    base_command = parts[0].strip().lower()

    # SAFE_COMMANDS: command -> regex that each argument must match.
    # Removed "ls"/"dir" because they inherently accept arbitrary paths.
    SAFE_COMMANDS = {
        "echo": r"^.*$",
        "date": r"^$",
        "hostname": r"^$",
        "whoami": r"^$",
        "pwd": r"^$",  # nosec B105
        "df": r"^(-h|--help)?$",
        "free": r"^(-h|--help)?$",
        "uptime": r"^$",
        "uname": r"^$",
        "arch": r"^$",
        "nproc": r"^$",
    }

    if base_command not in SAFE_COMMANDS:
        raise ValueError(
            f"Command '{base_command}' is not in the allowed safe commands list. "
            f"Allowed commands: {', '.join(sorted(SAFE_COMMANDS))}"
        )

    arg_pattern = SAFE_COMMANDS[base_command]
    recursive_flags = {"-R", "-r", "--recursive"}

    for arg in parts[1:]:
        # Reject shell metacharacters and redirections.
        if re.search(r"[;&|`$()<>]", arg):
            raise ValueError(f"Argument contains dangerous characters: {arg}")
        # Reject path traversal and absolute paths.
        if ".." in arg or arg.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", arg):
            raise ValueError(f"Argument contains path traversal or absolute path: {arg}")
        # Reject recursive flags.
        if arg in recursive_flags:
            raise ValueError(f"Recursive flag '{arg}' is not allowed")
        # Reject anything not matching the command-specific argument allow-list.
        if not re.match(arg_pattern, arg):
            raise ValueError(f"Argument '{arg}' is not allowed for command '{base_command}'")

    # Execute using list form (no shell=True)
    result = subprocess.run(
        parts,
        capture_output=True,
        text=True,
        shell=False,  # nosec B603
        timeout=30,  # Add timeout for safety
    )

    return f"stdout: {result.stdout}\nstderr: {result.stderr}\n" f"returncode: {result.returncode}"


async def get_metrics_handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Get system metrics"""
    if arguments:
        raise ValueError("get_metrics does not accept any arguments")
    # default_value - integrate with actual metrics collector
    return {"cpu_usage": 45.2, "memory_usage": 68.3, "disk_usage": 52.1}


async def check_alerts_handler(arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Check active alerts"""
    level = arguments.get("level")
    if level is not None:
        if not isinstance(level, str):
            raise ValueError("level must be a string")
        if level.lower() not in {"info", "warning", "error", "critical"}:
            raise ValueError("level must be one of info, warning, error, critical")
    # default_value - integrate with actual alert engine
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
            "properties": {
                "level": {
                    "type": "string",
                    "description": "Alert level filter",
                    "enum": ["info", "warning", "error", "critical"],
                }
            },
        },
        handler=check_alerts_handler,
    )
