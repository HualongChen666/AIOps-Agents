# -*- coding: utf-8 -*-
"""gRPC module for Dependency Management Service."""

from .client import (
    DependencyManagementRPCClient,
    SyncDependencyManagementRPCClient,
)
from .server import DependencyManagementRPCServer

__all__ = [
    "DependencyManagementRPCClient",
    "SyncDependencyManagementRPCClient",
    "DependencyManagementRPCServer",
]
