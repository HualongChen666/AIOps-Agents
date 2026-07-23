# -*- coding: utf-8 -*-
"""
gRPC Server Implementation
Implements gRPC server for AIOps Agent
"""

from concurrent import futures
from typing import Optional

import grpc
from loguru import logger


class AIOpsGrpcServer:
    """
    gRPC server for AIOps Agent
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 50051, max_workers: int = 10):
        """
        Initialize gRPC server

        Args:
            host: Server host
            port: Server port
            max_workers: Maximum worker threads
        """
        self.host = host
        self.port = port
        self.max_workers = max_workers
        self._server: Optional[grpc.Server] = None

    async def start(self) -> None:
        """Start gRPC server"""
        try:
            self._server = grpc.server(futures.ThreadPoolExecutor(max_workers=self.max_workers))

            # Add service
            # from proto.aiops_pb2_grpc import add_AIOpsServiceServicer_to_server
            # from .service import AIOpsServiceServicer
            # add_AIOpsServiceServicer_to_server(AIOpsServiceServicer(), self._server)

            self._server.add_insecure_port(f"{self.host}:{self.port}")
            self._server.start()

            logger.info(f"gRPC server started on {self.host}:{self.port}")

        except Exception as e:
            logger.error(f"Failed to start gRPC server: {e}")
            raise

    async def stop(self) -> None:
        """Stop gRPC server"""
        if self._server:
            self._server.stop(grace=5)
            logger.info("gRPC server stopped")

    async def wait_for_termination(self) -> None:
        """Wait for server termination"""
        if self._server:
            await self._server.wait_for_termination()
