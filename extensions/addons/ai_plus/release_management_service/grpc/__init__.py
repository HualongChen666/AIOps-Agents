# -*- coding: utf-8 -*-
"""gRPC module for Release Management Service."""

from .client import ReleaseManagementClient, create_client
from .server import ReleaseManagementRPCServer

__all__ = ["ReleaseManagementClient", "create_client", "ReleaseManagementRPCServer"]
