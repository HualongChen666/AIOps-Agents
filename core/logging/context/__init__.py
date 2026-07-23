# -*- coding: utf-8 -*-
"""
Logging Context Module
日志上下文模块

Provides context management for structured logging, including:
- Distributed tracing integration (OpenTelemetry)
- Request chain tracking (trace_id, span_id)
- User behavior tracking (user_id, session_id)
- Automatic context injection
"""

from .context_manager import (
    LoggingContext,
    LoggingContextManager,
    get_current_session_id,
    get_current_span_id,
    get_current_trace_id,
    get_current_user_id,
    get_logging_context,
    set_request_context,
    set_user_context,
)

__all__ = [
    "LoggingContext",
    "LoggingContextManager",
    "get_logging_context",
    "get_current_trace_id",
    "get_current_span_id",
    "get_current_user_id",
    "get_current_session_id",
    "set_user_context",
    "set_request_context",
]
