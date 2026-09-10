# -*- coding: utf-8 -*-
"""
gRPC Server Implementation
Implements gRPC server for AIOps Agent

Uses an asyncio gRPC server so the servicer in ``service.py`` can await the
core subsystems it adapts. Regenerate the bindings with
``python scripts/generate_proto.py``.
"""

from typing import List, Optional, Sequence

import grpc
from loguru import logger

from proto import aiops_pb2_grpc

from .service import AIOpsServiceServicer


class AIOpsGrpcServer:
    """
    gRPC server for AIOps Agent
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 50051,
        max_workers: int = 10,
        interceptors: Optional[Sequence[grpc.aio.ServerInterceptor]] = None,
    ):
        """
        Initialize gRPC server

        Args:
            host: Server host
            port: Server port
            max_workers: Maximum worker threads
            interceptors: Optional async server interceptors
        """
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self.interceptors: List[grpc.aio.ServerInterceptor] = list(interceptors or [])
        self._server: Optional[grpc.aio.Server] = None
        self._servicer = AIOpsServiceServicer()

    @property
    def address(self) -> str:
        """``host:port`` the server binds to."""
        return f"{self.host}:{self.port}"

    async def start(self) -> None:
        """Start gRPC server and register the AIOps service."""
        if self._server is not None:
            logger.warning("gRPC server already running")
            return

        self._server = grpc.aio.server(interceptors=self.interceptors or None)
        aiops_pb2_grpc.add_AIOpsServiceServicer_to_server(self._servicer, self._server)

        bound_port = self._server.add_insecure_port(self.address)
        if bound_port == 0:
            raise RuntimeError(f"Failed to bind gRPC server to {self.address}")

        await self._server.start()
        logger.info(f"gRPC server started on {self.address}")

    async def stop(self, grace: float = 5.0) -> None:
        """Stop gRPC server"""
        if self._server:
            await self._server.stop(grace)
            self._server = None
            logger.info("gRPC server stopped")

    async def wait_for_termination(self) -> None:
        """Wait for server termination"""
        if self._server:
            await self._server.wait_for_termination()
