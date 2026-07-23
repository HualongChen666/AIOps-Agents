# -*- coding: utf-8 -*-
"""
Cross-Service Tracing Implementation
Enterprise-grade cross-service tracing with context propagation
"""

from contextlib import contextmanager
from typing import Any, Dict, Optional, cast

from loguru import logger
from opentelemetry import propagate, trace
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.propagators.jaeger import JaegerPropagator
from opentelemetry.trace import Span, SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator


class TracingContext:
    """Tracing context for cross-service propagation"""

    def __init__(self):
        self.propagators = [TraceContextTextMapPropagator(), B3MultiFormat(), JaegerPropagator()]

    def inject(self, headers: Dict[str, str]) -> None:
        """
        Inject tracing context into headers

        Args:
            headers: Headers dictionary to inject into
        """
        ctx = trace.get_current_span().get_span_context()
        if ctx:
            carrier: Dict[str, str] = {}
            propagate.inject(carrier)
            headers.update(carrier)

    def extract(self, headers: Dict[str, str]) -> Any:
        """
        Extract tracing context from headers

        Args:
            headers: Headers dictionary to extract from

        Returns:
            Context object
        """
        carrier = headers
        ctx = propagate.extract(carrier)
        return ctx


class HTTPTracingInterceptor:
    """HTTP tracing interceptor for cross-service calls"""

    def __init__(self, tracing_manager):
        """
        Initialize HTTP tracing interceptor

        Args:
            tracing_manager: OpenTelemetry tracing manager
        """
        self.tracing_manager = tracing_manager
        self.tracing_context = TracingContext()

    @contextmanager
    def trace_http_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing HTTP requests

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            attributes: Additional attributes

        Yields:
            Span object
        """
        span_name = f"{method} {url}"
        span = self.tracing_manager.create_span(
            name=span_name,
            kind=SpanKind.CLIENT,
            attributes={"http.method": method, "http.url": url, **(attributes or {})},
        )

        # Inject tracing context into headers
        if headers is None:
            headers = {}
        self.tracing_context.inject(headers)

        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            span.end()

    async def trace_http_request_async(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        Async context manager for tracing HTTP requests

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            attributes: Additional attributes

        Returns:
            Span object
        """
        span_name = f"{method} {url}"
        span = self.tracing_manager.create_span(
            name=span_name,
            kind=SpanKind.CLIENT,
            attributes={"http.method": method, "http.url": url, **(attributes or {})},
        )

        # Inject tracing context into headers
        if headers is None:
            headers = {}
        self.tracing_context.inject(headers)

        return cast(Span, span)


class DatabaseTracingInterceptor:
    """Database tracing interceptor for database operations"""

    def __init__(self, tracing_manager):
        """
        Initialize database tracing interceptor

        Args:
            tracing_manager: OpenTelemetry tracing manager
        """
        self.tracing_manager = tracing_manager

    @contextmanager
    def trace_database_query(
        self,
        db_system: str,
        db_name: str,
        operation: str,
        query: str,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing database queries

        Args:
            db_system: Database system (e.g., postgresql, mysql)
            db_name: Database name
            operation: Operation type (e.g., SELECT, INSERT, UPDATE)
            query: SQL query
            attributes: Additional attributes

        Yields:
            Span object
        """
        span_name = f"{operation} {db_name}"
        span = self.tracing_manager.create_span(
            name=span_name,
            kind=SpanKind.CLIENT,
            attributes={
                "db.system": db_system,
                "db.name": db_name,
                "db.operation": operation,
                "db.statement": query,
                **(attributes or {}),
            },
        )

        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            span.end()

    async def trace_database_query_async(
        self,
        db_system: str,
        db_name: str,
        operation: str,
        query: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        Async context manager for tracing database queries

        Args:
            db_system: Database system
            db_name: Database name
            operation: Operation type
            query: SQL query
            attributes: Additional attributes

        Returns:
            Span object
        """
        span_name = f"{operation} {db_name}"
        span = self.tracing_manager.create_span(
            name=span_name,
            kind=SpanKind.CLIENT,
            attributes={
                "db.system": db_system,
                "db.name": db_name,
                "db.operation": operation,
                "db.statement": query,
                **(attributes or {}),
            },
        )

        return cast(Span, span)


class MessageQueueTracingInterceptor:
    """Message queue tracing interceptor for message operations"""

    def __init__(self, tracing_manager):
        """
        Initialize message queue tracing interceptor

        Args:
            tracing_manager: OpenTelemetry tracing manager
        """
        self.tracing_manager = tracing_manager
        self.tracing_context = TracingContext()

    @contextmanager
    def trace_message_publish(
        self,
        messaging_system: str,
        destination: str,
        message_type: str,
        message_id: str,
        headers: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing message publishing

        Args:
            messaging_system: Messaging system (e.g., kafka, rabbitmq)
            destination: Destination topic/queue
            message_type: Message type
            message_id: Message ID
            headers: Message headers
            attributes: Additional attributes

        Yields:
            Span object
        """
        span_name = f"publish {destination}"
        span = self.tracing_manager.create_span(
            name=span_name,
            kind=SpanKind.PRODUCER,
            attributes={
                "messaging.system": messaging_system,
                "messaging.destination": destination,
                "messaging.message_type": message_type,
                "messaging.message_id": message_id,
                **(attributes or {}),
            },
        )

        # Inject tracing context into message headers
        if headers is None:
            headers = {}
        self.tracing_context.inject(headers)

        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            span.end()

    @contextmanager
    def trace_message_consume(
        self,
        messaging_system: str,
        destination: str,
        message_type: str,
        message_id: str,
        headers: Optional[Dict[str, str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        Context manager for tracing message consumption

        Args:
            messaging_system: Messaging system
            destination: Source topic/queue
            message_type: Message type
            message_id: Message ID
            headers: Message headers
            attributes: Additional attributes

        Yields:
            Span object
        """
        span_name = f"consume {destination}"

        # Extract tracing context from message headers
        if headers:
            self.tracing_context.extract(headers)

        span = self.tracing_manager.create_span(
            name=span_name,
            kind=SpanKind.CONSUMER,
            attributes={
                "messaging.system": messaging_system,
                "messaging.destination": destination,
                "messaging.message_type": message_type,
                "messaging.message_id": message_id,
                **(attributes or {}),
            },
        )

        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise
        finally:
            span.end()


class CrossServiceTracingManager:
    """Enterprise-grade cross-service tracing manager"""

    def __init__(self, tracing_manager):
        """
        Initialize cross-service tracing manager

        Args:
            tracing_manager: OpenTelemetry tracing manager
        """
        self.tracing_manager = tracing_manager
        self.http_interceptor = HTTPTracingInterceptor(tracing_manager)
        self.database_interceptor = DatabaseTracingInterceptor(tracing_manager)
        self.message_queue_interceptor = MessageQueueTracingInterceptor(tracing_manager)

        # Statistics
        self.http_requests = 0
        self.database_queries = 0
        self.message_operations = 0

        logger.info("Cross-service tracing manager initialized")

    def get_http_interceptor(self) -> HTTPTracingInterceptor:
        """Get HTTP tracing interceptor"""
        return self.http_interceptor

    def get_database_interceptor(self) -> DatabaseTracingInterceptor:
        """Get database tracing interceptor"""
        return self.database_interceptor

    def get_message_queue_interceptor(self) -> MessageQueueTracingInterceptor:
        """Get message queue tracing interceptor"""
        return self.message_queue_interceptor

    def trace_service_call(
        self, service_name: str, operation: str, attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """
        Trace a service call

        Args:
            service_name: Target service name
            operation: Operation name
            attributes: Additional attributes

        Returns:
            Span object
        """
        span_name = f"{service_name}.{operation}"
        span = self.tracing_manager.create_span(
            name=span_name,
            kind=SpanKind.CLIENT,
            attributes={
                "service.name": service_name,
                "service.operation": operation,
                **(attributes or {}),
            },
        )

        self.http_requests += 1

        return cast(Span, span)

    def trace_internal_operation(
        self, component: str, operation: str, attributes: Optional[Dict[str, Any]] = None
    ) -> Span:
        """
        Trace an internal operation

        Args:
            component: Component name
            operation: Operation name
            attributes: Additional attributes

        Returns:
            Span object
        """
        span_name = f"{component}.{operation}"
        span = self.tracing_manager.create_span(
            name=span_name,
            kind=SpanKind.INTERNAL,
            attributes={
                "component.name": component,
                "component.operation": operation,
                **(attributes or {}),
            },
        )

        return cast(Span, span)

    def get_statistics(self) -> Dict[str, Any]:
        """Get cross-service tracing statistics"""
        return {
            "http_requests": self.http_requests,
            "database_queries": self.database_queries,
            "message_operations": self.message_operations,
            "total_traced_operations": (
                self.http_requests + self.database_queries + self.message_operations
            ),
        }


def get_cross_service_tracing_manager(tracing_manager) -> CrossServiceTracingManager:
    """
    Factory function to get cross-service tracing manager instance

    Args:
        tracing_manager: OpenTelemetry tracing manager

    Returns:
        CrossServiceTracingManager: Cross-service tracing manager instance
    """
    return CrossServiceTracingManager(tracing_manager)
