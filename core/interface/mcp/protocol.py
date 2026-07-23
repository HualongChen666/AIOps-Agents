# -*- coding: utf-8 -*-
"""
MCP Protocol Parser
Implements Model Context Protocol message parsing and serialization
"""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from loguru import logger


class MessageType(Enum):
    """MCP message type enumeration"""

    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


@dataclass
class MCPMessage:
    """Base MCP message"""

    jsonrpc: str = "2.0"
    id: Optional[str] = None
    method: Optional[str] = None
    params: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        msg: Dict[str, Any] = {"jsonrpc": self.jsonrpc}
        if self.id:
            msg["id"] = self.id
        if self.method:
            msg["method"] = self.method
        if self.params:
            msg["params"] = self.params
        if self.result is not None:
            msg["result"] = self.result
        if self.error:
            msg["error"] = self.error
        return msg

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPMessage":
        """Create from dictionary"""
        return cls(
            jsonrpc=data.get("jsonrpc", "2.0"),
            id=data.get("id"),
            method=data.get("method"),
            params=data.get("params"),
            result=data.get("result"),
            error=data.get("error"),
        )

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> "MCPMessage":
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)


class MCPMethod(Enum):
    """MCP method enumeration"""

    INITIALIZE = "initialize"
    LIST_TOOLS = "tools/list"
    CALL_TOOL = "tools/call"
    LIST_RESOURCES = "resources/list"
    READ_RESOURCE = "resources/read"
    LIST_PROMPTS = "prompts/list"
    GET_PROMPT = "prompts/get"
    SET_LOGGING = "logging/set"

    # Context methods
    GET_CONTEXT = "context/get"
    SET_CONTEXT = "context/set"
    LIST_CONTEXTS = "contexts/list"


class MCPProtocolParser:
    """
    MCP protocol parser and serializer
    """

    @staticmethod
    def parse_message(message: str) -> Optional[MCPMessage]:
        """
        Parse MCP message from JSON string

        Args:
            message: JSON string

        Returns:
            MCPMessage or None if invalid
        """
        try:
            return MCPMessage.from_json(message)
        except Exception as e:
            logger.error(f"Failed to parse MCP message: {e}")
            return None

    @staticmethod
    def create_request(
        method: MCPMethod, params: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None
    ) -> MCPMessage:
        """
        Create MCP request message

        Args:
            method: MCP method
            params: Request parameters
            request_id: Request ID

        Returns:
            MCPMessage
        """
        return MCPMessage(method=method.value, params=params, id=request_id or str(id(params)))

    @staticmethod
    def create_response(
        request_id: str, result: Optional[Any] = None, error: Optional[Dict[str, Any]] = None
    ) -> MCPMessage:
        """
        Create MCP response message

        Args:
            request_id: Request ID
            result: Response result
            error: Error object

        Returns:
            MCPMessage
        """
        return MCPMessage(id=request_id, result=result, error=error)

    @staticmethod
    def create_notification(
        method: MCPMethod, params: Optional[Dict[str, Any]] = None
    ) -> MCPMessage:
        """
        Create MCP notification message

        Args:
            method: MCP method
            params: Notification parameters

        Returns:
            MCPMessage
        """
        return MCPMessage(method=method.value, params=params)

    @staticmethod
    def create_error(code: int, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
        """
        Create MCP error object

        Args:
            code: Error code
            message: Error message
            data: Additional error data

        Returns:
            Error dictionary
        """
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return error
