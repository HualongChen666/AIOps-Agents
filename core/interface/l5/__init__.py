# -*- coding: utf-8 -*-
"""
L5 Interface Layer - External Interfaces
Provides standardized interfaces for external system integration
"""

from .graphql_interface import GraphQLInterface, get_graphql_interface, init_graphql_interface
from .mcp_interface import MCPInterface, get_mcp_interface, init_mcp_interface

__all__ = [
    "MCPInterface",
    "get_mcp_interface",
    "init_mcp_interface",
    "GraphQLInterface",
    "get_graphql_interface",
    "init_graphql_interface",
]
