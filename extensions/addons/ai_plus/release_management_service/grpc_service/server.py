# -*- coding: utf-8 -*-
"""gRPC server for Release Management Service.

The handler registry stored here is served over a *real* gRPC endpoint (JSON
codec) via :class:`JsonRpcServer`; the same registry also backs the service's
HTTP ``/rpc/{method}`` endpoint.
"""

import os
import sys
from typing import Any, Dict, Optional

try:
    from ..config import Config
except ImportError:
    from config import Config

try:
    from ...json_grpc_rpc import JsonRpcServer
except ImportError:  # pragma: no cover - bare import fallback
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
    from json_grpc_rpc import JsonRpcServer

import logging

logger = logging.getLogger(Config.SERVICE_NAME)

SERVICE_FQN = "release.ReleaseManagementService"


class ReleaseManagementRPCServer(JsonRpcServer):
    """RPC server for the release management service (real gRPC + HTTP dispatch)."""

    def __init__(self) -> None:
        super().__init__(SERVICE_FQN)

    async def start(self, host: str = None, port: int = None) -> None:
        """Bind and start the real gRPC server."""
        await super().start(host or Config.GRPC_HOST, port or Config.GRPC_PORT)
        logger.info(f"ReleaseManagement gRPC server started on {host}:{port}")

    async def stop(self) -> None:
        """Stop the gRPC server."""
        await super().stop()
        logger.info("ReleaseManagement gRPC server stopped")
