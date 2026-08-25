# -*- coding: utf-8 -*-
"""gRPC components for Secret Management Service."""

from .client import SecretManagementRPCClient
from .server import SecretManagementRPCServer

__all__ = ["SecretManagementRPCClient", "SecretManagementRPCServer"]
