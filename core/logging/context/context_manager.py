# -*- coding: utf-8 -*-
"""
Logging Context Manager
日志上下文管理器

Provides context management for structured logging with:
- Distributed tracing integration (OpenTelemetry)
- Request chain tracking (trace_id, span_id)
- User behavior tracking (user_id, session_id)
- Thread-local context storage
- Automatic context injection
"""

import contextlib
import contextvars
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from loguru import logger
from opentelemetry import trace

# Thread-local context variables
_trace_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)
_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("span_id", default=None)
_parent_span_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "parent_span_id", default=None
)
_user_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)
_session_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "session_id", default=None
)
_request_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "request_id", default=None
)
_correlation_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)
_custom_context: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "custom_context", default={}
)


@dataclass
class LoggingContext:
    """
    Logging context data class
    日志上下文数据类

    Attributes:
        trace_id: Distributed trace ID
        span_id: Current span ID
        parent_span_id: Parent span ID
        user_id: User ID
        session_id: Session ID
        request_id: Request ID
        correlation_id: Correlation ID
        custom_context: Custom context data
        metadata: Additional metadata
    """

    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    correlation_id: Optional[str] = None
    custom_context: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert context to dictionary

        Returns:
            Dictionary representation of context
        """
        result: Dict[str, Any] = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
        }

        # Add custom context
        result.update(self.custom_context)

        # Add metadata
        if self.metadata:
            result.update(self.metadata)

        # Remove None values
        return {k: v for k, v in result.items() if v is not None}

    def merge(self, other: "LoggingContext") -> "LoggingContext":
        """
        Merge another context into this context

        Args:
            other: Other context to merge

        Returns:
            Merged context
        """
        merged_custom_context = {**self.custom_context, **other.custom_context}
        merged_metadata = {**self.metadata, **other.metadata}

        return LoggingContext(
            trace_id=other.trace_id or self.trace_id,
            span_id=other.span_id or self.span_id,
            parent_span_id=other.parent_span_id or self.parent_span_id,
            user_id=other.user_id or self.user_id,
            session_id=other.session_id or self.session_id,
            request_id=other.request_id or self.request_id,
            correlation_id=other.correlation_id or self.correlation_id,
            custom_context=merged_custom_context,
            metadata=merged_metadata,
        )


class LoggingContextManager:
    """
    Logging context manager
    日志上下文管理器

    Manages logging context with thread-local storage and OpenTelemetry integration.
    """

    def __init__(self, enable_opentelemetry: bool = True):
        """
        Initialize logging context manager

        Args:
            enable_opentelemetry: Enable OpenTelemetry integration
        """
        self.enable_opentelemetry = enable_opentelemetry
        self._tracer: Optional[trace.Tracer] = None

        if self.enable_opentelemetry:
            try:
                self._tracer = trace.get_tracer(__name__)
                logger.info("OpenTelemetry integration enabled for logging context")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenTelemetry tracer: {e}")
                self.enable_opentelemetry = False

    def create_trace_id(self) -> str:
        """
        Create a new trace ID

        Returns:
            New trace ID
        """
        return str(uuid.uuid4()).replace("-", "")

    def create_span_id(self) -> str:
        """
        Create a new span ID

        Returns:
            New span ID
        """
        return str(uuid.uuid4()).replace("-", "")[:16]

    def create_request_id(self) -> str:
        """
        Create a new request ID

        Returns:
            New request ID
        """
        return str(uuid.uuid4()).replace("-", "")

    def create_session_id(self) -> str:
        """
        Create a new session ID

        Returns:
            New session ID
        """
        return str(uuid.uuid4()).replace("-")  # type: ignore[call-arg]

    def create_correlation_id(self) -> str:
        """
        Create a new correlation ID

        Returns:
            New correlation ID
        """
        return str(uuid.uuid4()).replace("-", "")

    def set_trace_id(self, trace_id: str) -> None:
        """
        Set trace ID in context

        Args:
            trace_id: Trace ID to set
        """
        _trace_id.set(trace_id)

    def set_span_id(self, span_id: str) -> None:
        """
        Set span ID in context

        Args:
            span_id: Span ID to set
        """
        _span_id.set(span_id)

    def set_parent_span_id(self, parent_span_id: str) -> None:
        """
        Set parent span ID in context

        Args:
            parent_span_id: Parent span ID to set
        """
        _parent_span_id.set(parent_span_id)

    def set_user_id(self, user_id: str) -> None:
        """
        Set user ID in context

        Args:
            user_id: User ID to set
        """
        _user_id.set(user_id)

    def set_session_id(self, session_id: str) -> None:
        """
        Set session ID in context

        Args:
            session_id: Session ID to set
        """
        _session_id.set(session_id)

    def set_request_id(self, request_id: str) -> None:
        """
        Set request ID in context

        Args:
            request_id: Request ID to set
        """
        _request_id.set(request_id)

    def set_correlation_id(self, correlation_id: str) -> None:
        """
        Set correlation ID in context

        Args:
            correlation_id: Correlation ID to set
        """
        _correlation_id.set(correlation_id)

    def set_custom_context(self, key: str, value: Any) -> None:
        """
        Set custom context value

        Args:
            key: Context key
            value: Context value
        """
        current_context = _custom_context.get({})
        current_context[key] = value
        _custom_context.set(current_context)

    def get_current_context(self) -> LoggingContext:
        """
        Get current logging context

        Returns:
            Current logging context
        """
        # Try to get from OpenTelemetry if enabled
        if self.enable_opentelemetry and self._tracer:
            try:
                current_span = trace.get_current_span()
                if current_span:
                    span_context = current_span.get_span_context()
                    if span_context and span_context.is_valid:
                        # Get trace_id and span_id from OpenTelemetry
                        otel_trace_id = format(span_context.trace_id, "032x")
                        otel_span_id = format(span_context.span_id, "016x")

                        # Set if not already set
                        if _trace_id.get() is None:
                            _trace_id.set(otel_trace_id)
                        if _span_id.get() is None:
                            _span_id.set(otel_span_id)
            except Exception as e:
                logger.debug(f"Failed to get OpenTelemetry context: {e}")

        return LoggingContext(
            trace_id=_trace_id.get(),
            span_id=_span_id.get(),
            parent_span_id=_parent_span_id.get(),
            user_id=_user_id.get(),
            session_id=_session_id.get(),
            request_id=_request_id.get(),
            correlation_id=_correlation_id.get(),
            custom_context=_custom_context.get({}),
        )

    def clear_context(self) -> None:
        """Clear all context variables"""
        _trace_id.set(None)
        _span_id.set(None)
        _parent_span_id.set(None)
        _user_id.set(None)
        _session_id.set(None)
        _request_id.set(None)
        _correlation_id.set(None)
        _custom_context.set({})

    @contextlib.contextmanager
    def context(
        self,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        **kwargs,
    ):
        """
        Context manager for logging context

        Args:
            trace_id: Trace ID
            span_id: Span ID
            user_id: User ID
            session_id: Session ID
            request_id: Request ID
            correlation_id: Correlation ID
            **kwargs: Additional context values

        Yields:
            LoggingContext: Current logging context
        """
        # Save current context
        old_trace_id = _trace_id.get()
        old_span_id = _span_id.get()
        old_parent_span_id = _parent_span_id.get()
        old_user_id = _user_id.get()
        old_session_id = _session_id.get()
        old_request_id = _request_id.get()
        old_correlation_id = _correlation_id.get()
        old_custom_context = _custom_context.get({})

        try:
            # Set new context
            if trace_id:
                self.set_trace_id(trace_id)
            if span_id:
                self.set_span_id(span_id)
            if user_id:
                self.set_user_id(user_id)
            if session_id:
                self.set_session_id(session_id)
            if request_id:
                self.set_request_id(request_id)
            if correlation_id:
                self.set_correlation_id(correlation_id)

            # Set custom context
            for key, value in kwargs.items():
                self.set_custom_context(key, value)

            yield self.get_current_context()

        finally:
            # Restore old context
            _trace_id.set(old_trace_id)
            _span_id.set(old_span_id)
            _parent_span_id.set(old_parent_span_id)
            _user_id.set(old_user_id)
            _session_id.set(old_session_id)
            _request_id.set(old_request_id)
            _correlation_id.set(old_correlation_id)
            _custom_context.set(old_custom_context)

    def start_trace(
        self,
        trace_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> LoggingContext:
        """
        Start a new trace

        Args:
            trace_id: Optional trace ID (auto-generated if not provided)
            user_id: Optional user ID
            session_id: Optional session ID

        Returns:
            Logging context for the new trace
        """
        if trace_id is None:
            trace_id = self.create_trace_id()

        self.set_trace_id(trace_id)
        self.set_span_id(self.create_span_id())

        if user_id:
            self.set_user_id(user_id)
        if session_id:
            self.set_session_id(session_id)

        return self.get_current_context()

    def start_span(
        self,
        span_name: str,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> LoggingContext:
        """
        Start a new span

        Args:
            span_name: Span name
            attributes: Optional span attributes

        Returns:
            Logging context for the new span
        """
        # Create new span ID
        new_span_id = self.create_span_id()

        # Set as current span
        old_span_id = _span_id.get()
        _parent_span_id.set(old_span_id)
        _span_id.set(new_span_id)

        # Add span attributes to custom context
        if attributes:
            for key, value in attributes.items():
                self.set_custom_context(f"span.{key}", value)

        return self.get_current_context()

    def end_span(self) -> None:
        """End current span and restore parent span"""
        parent_span_id = _parent_span_id.get()
        if parent_span_id:
            _span_id.set(parent_span_id)
            # Clear the parent span reference since we've moved up
            _parent_span_id.set(None)
        else:
            # If no parent, clear the current span
            _span_id.set(None)


# Global context manager instance
_global_context_manager: Optional[LoggingContextManager] = None


def get_logging_context_manager() -> LoggingContextManager:
    """
    Get global logging context manager instance

    Returns:
        Logging context manager instance
    """
    global _global_context_manager
    if _global_context_manager is None:
        _global_context_manager = LoggingContextManager()
    return _global_context_manager


def get_logging_context() -> LoggingContext:
    """
    Get current logging context

    Returns:
        Current logging context
    """
    return get_logging_context_manager().get_current_context()


def get_current_trace_id() -> Optional[str]:
    """
    Get current trace ID

    Returns:
        Current trace ID or None
    """
    return _trace_id.get()


def get_current_span_id() -> Optional[str]:
    """
    Get current span ID

    Returns:
        Current span ID or None
    """
    return _span_id.get()


def get_current_user_id() -> Optional[str]:
    """
    Get current user ID

    Returns:
        Current user ID or None
    """
    return _user_id.get()


def get_current_session_id() -> Optional[str]:
    """
    Get current session ID

    Returns:
        Current session ID or None
    """
    return _session_id.get()


def set_user_context(user_id: str, session_id: Optional[str] = None) -> None:
    """
    Set user context

    Args:
        user_id: User ID
        session_id: Optional session ID
    """
    manager = get_logging_context_manager()
    manager.set_user_id(user_id)
    if session_id:
        manager.set_session_id(session_id)


def set_request_context(
    request_id: Optional[str] = None, correlation_id: Optional[str] = None
) -> None:
    """
    Set request context

    Args:
        request_id: Optional request ID
        correlation_id: Optional correlation ID
    """
    manager = get_logging_context_manager()
    if request_id:
        manager.set_request_id(request_id)
    if correlation_id:
        manager.set_correlation_id(correlation_id)
