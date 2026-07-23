# -*- coding: utf-8 -*-
"""
gRPC Interceptors
Implements authentication and logging interceptors
"""

from typing import Callable

import grpc
from loguru import logger


class LoggingInterceptor(grpc.ServerInterceptor):
    """Logging interceptor for gRPC calls"""

    def intercept_service(
        self, continuation: Callable, handler_call_details: grpc.HandlerCallDetails
    ):
        """Intercept service call for logging"""
        method = handler_call_details.method

        logger.info(f"gRPC call: {method}")

        try:
            response = continuation(handler_call_details)
            logger.info(f"gRPC response: {method} - success")
            return response
        except Exception as e:
            logger.error(f"gRPC error: {method} - {e}")
            raise


class AuthInterceptor(grpc.ServerInterceptor):
    """Authentication interceptor for gRPC calls"""

    def __init__(self, api_key: str):
        """
        Initialize auth interceptor

        Args:
            api_key: Valid API key
        """
        self.api_key = api_key

    def intercept_service(
        self, continuation: Callable, handler_call_details: grpc.HandlerCallDetails
    ):
        """Intercept service call for authentication"""
        # Get metadata
        metadata = dict(handler_call_details.invocation_metadata)

        # Check API key
        client_key = metadata.get("api-key")
        if client_key != self.api_key:
            logger.warning("Invalid API key in gRPC request")
            context = grpc.ServicerContext()
            context.set_code(grpc.StatusCode.UNAUTHENTICATED)
            context.set_details("Invalid API key")
            return context

        # Continue with call
        return continuation(handler_call_details)


class MetricsInterceptor(grpc.ServerInterceptor):
    """Metrics interceptor for gRPC calls"""

    def __init__(self):
        """Initialize metrics interceptor"""
        self._call_counts = {}

    def intercept_service(
        self, continuation: Callable, handler_call_details: grpc.HandlerCallDetails
    ):
        """Intercept service call for metrics collection"""
        method = handler_call_details.method

        # Increment call count
        self._call_counts[method] = self._call_counts.get(method, 0) + 1

        # Continue with call
        return continuation(handler_call_details)

    def get_metrics(self) -> dict:
        """Get call metrics"""
        return self._call_counts.copy()
