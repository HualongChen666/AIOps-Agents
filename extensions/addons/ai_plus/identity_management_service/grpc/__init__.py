# -*- coding: utf-8 -*-
"""gRPC client and server for Identity Management Service."""

from .client import IdentityManagementClient
from .server import serve

__all__ = ["IdentityManagementClient", "serve"]
