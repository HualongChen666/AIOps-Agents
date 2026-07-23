# -*- coding: utf-8 -*-
"""
Request Tracking Middleware
请求追踪中间件

Provides request ID tracking for the AIOps Agent system.
Generates unique request IDs and makes them available throughout the request lifecycle.
"""

import uuid
from contextvars import ContextVar
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Context variable for request ID
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request tracking IDs to all requests"""

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID"):
        """
        Initialize request tracking middleware

        Args:
            app: ASGI application
            header_name: Header name for request ID
        """
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]  # noqa: E501
    ) -> Response:
        """
        Process request and add tracking ID

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response with request ID header
        """
        # Generate or extract request ID
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())

        # Set request ID in context
        request_id_var.set(request_id)

        # Add request ID to request state
        request.state.request_id = request_id

        # Process request
        response = await call_next(request)

        # Add request ID to response header
        response.headers[self.header_name] = request_id

        return response


def get_request_id() -> str:
    """
    Get current request ID from context

    Returns:
        Current request ID or empty string if not set
    """
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """
    Set request ID in context

    Args:
        request_id: Request ID to set
    """
    request_id_var.set(request_id)


class RequestContextManager:
    """Manager for request context and tracking"""

    def __init__(self):
        """Initialize request context manager"""
        self._contexts: Dict[str, Dict[str, Any]] = {}  # noqa: E501

    def create_context(
        self, request_id: str, user_id: Optional[str] = None, client_ip: Optional[str] = None
    ) -> None:
        """
        Create a new request context

        Args:
            request_id: Unique request identifier
            user_id: User ID (optional)
            client_ip: Client IP address (optional)
        """
        self._contexts[request_id] = {
            "request_id": request_id,
            "user_id": user_id,
            "client_ip": client_ip,
            "start_time": None,
            "end_time": None,
            "metadata": {},
        }

    def set_start_time(self, request_id: str) -> None:
        """Set request start time"""
        if request_id in self._contexts:
            import time

            self._contexts[request_id]["start_time"] = time.time()

    def set_end_time(self, request_id: str) -> None:
        """Set request end time"""
        if request_id in self._contexts:
            import time

            self._contexts[request_id]["end_time"] = time.time()

    def add_metadata(self, request_id: str, key: str, value: Any) -> None:
        """Add metadata to request context"""
        if request_id in self._contexts:
            self._contexts[request_id]["metadata"][key] = value

    def get_context(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get request context"""
        return self._contexts.get(request_id)

    def remove_context(self, request_id: str) -> None:
        """Remove request context"""
        if request_id in self._contexts:
            del self._contexts[request_id]

    def get_duration(self, request_id: str) -> float:
        """Get request duration in seconds"""
        context = self._contexts.get(request_id)
        if context and context["start_time"] is not None and context["end_time"] is not None:
            start_time = float(context["start_time"])
            end_time = float(context["end_time"])
            return end_time - start_time
        return 0.0


# Global request context manager
request_context_manager = RequestContextManager()
