# -*- coding: utf-8 -*-
"""
gRPC Interceptors
Implements authentication and logging interceptors

These are **asyncio** server interceptors (``grpc.aio.ServerInterceptor``) to
match the asyncio server in :mod:`core.interface.grpc.server`.
"""

from typing import Any, Callable

import grpc
from loguru import logger


class LoggingInterceptor(grpc.aio.ServerInterceptor):
    """Logging interceptor for gRPC calls"""

    async def intercept_service(
        self, continuation: Callable, handler_call_details: grpc.HandlerCallDetails
    ) -> Any:
        """Intercept service call for logging"""
        method = handler_call_details.method
        logger.info(f"gRPC call: {method}")
        try:
            handler = await continuation(handler_call_details)
        except Exception as exc:
            logger.error(f"gRPC error: {method} - {exc}")
            raise
        logger.info(f"gRPC response: {method} - success")
        return handler


class AuthInterceptor(grpc.aio.ServerInterceptor):
    """Authentication interceptor for gRPC calls"""

    def __init__(self, api_key: str):
        """
        Initialize auth interceptor

        Args:
            api_key: Valid API key
        """
        self.api_key = api_key

    async def intercept_service(
        self, continuation: Callable, handler_call_details: grpc.HandlerCallDetails
    ) -> Any:
        """Intercept service call for authentication.

        Rejects the call with ``UNAUTHENTICATED`` when the ``api-key`` metadata
        entry is missing or wrong; otherwise forwards to the real handler.
        """
        metadata = dict(handler_call_details.invocation_metadata or ())
        if metadata.get("api-key") != self.api_key:
            logger.warning("Invalid API key in gRPC request")

            async def _deny(request: Any, context: grpc.aio.ServicerContext) -> None:
                await context.abort(grpc.StatusCode.UNAUTHENTICATED, "Invalid API key")

            return grpc.unary_unary_rpc_method_handler(_deny)

        return await continuation(handler_call_details)


class MetricsInterceptor(grpc.aio.ServerInterceptor):
    """Metrics interceptor for gRPC calls"""

    def __init__(self) -> None:
        """Initialize metrics interceptor"""
        self._call_counts: dict[str, int] = {}

    async def intercept_service(
        self, continuation: Callable, handler_call_details: grpc.HandlerCallDetails
    ) -> Any:
        """Intercept service call for metrics collection"""
        method = handler_call_details.method
        self._call_counts[method] = self._call_counts.get(method, 0) + 1
        return await continuation(handler_call_details)

    def get_metrics(self) -> dict:
        """Get call metrics"""
        return self._call_counts.copy()
