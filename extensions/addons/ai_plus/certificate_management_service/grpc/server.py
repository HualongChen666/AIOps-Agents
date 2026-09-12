# -*- coding: utf-8 -*-
"""gRPC server for Certificate Management Service.

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

SERVICE_FQN = "certificate.CertificateManagementService"


class CertificateManagementRPCServer(JsonRpcServer):
    """RPC server for the certificate management service (real gRPC + HTTP dispatch)."""

    def __init__(self) -> None:
        super().__init__(SERVICE_FQN)

    async def start(self, host: str = "127.0.0.1", port: int = 50053) -> None:
        """Bind and start the real gRPC server on ``host:port``."""
        await super().start(host, port)
        logger.info(f"CertificateManagement gRPC server started on {host}:{port}")

    async def stop(self) -> None:
        """Stop the gRPC server."""
        await super().stop()
        logger.info("CertificateManagement gRPC server stopped")
