# -*- coding: utf-8 -*-
"""gRPC components for Automated Testing Service."""

from .client import AutomatedTestingRPCClient
from .server import AutomatedTestingRPCServer

__all__ = ["AutomatedTestingRPCClient", "AutomatedTestingRPCServer"]
