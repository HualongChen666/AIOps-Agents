# -*- coding: utf-8 -*-
"""gRPC server for Compliance Monitoring Service.

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

SERVICE_FQN = "compliance.ComplianceMonitoringService"


class ComplianceMonitoringRPCServer(JsonRpcServer):
    """RPC server for the compliance monitoring service (real gRPC + HTTP dispatch)."""

    def __init__(self) -> None:
        super().__init__(SERVICE_FQN)

    async def start(self, host: str = "127.0.0.1", port: int = 50060) -> None:
        """Bind and start the real gRPC server on ``host:port``."""
        await super().start(host, port)
        logger.info(f"ComplianceMonitoring gRPC server started on {host}:{port}")

    async def stop(self) -> None:
        """Stop the gRPC server."""
        await super().stop()
        logger.info("ComplianceMonitoring gRPC server stopped")


# Module-level singleton so endpoint registration and the served registry are the same.
rpc_server = ComplianceMonitoringRPCServer()


async def serve(host: str = "127.0.0.1", port: int = 50060) -> None:
    """Start the gRPC server (blocking until termination)."""
    await rpc_server.start(host, port)
    await rpc_server.wait_for_termination()
