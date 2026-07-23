# -*- coding: utf-8 -*-
"""
Unit tests for logging context manager
日志上下文管理器单元测试
"""

from core.logging.context import (
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


class TestLoggingContext:
    """Test cases for LoggingContext data class"""

    def test_logging_context_initialization(self):
        """Test logging context initialization"""
        context = LoggingContext(
            trace_id="test_trace",
            span_id="test_span",
            user_id="test_user",
        )

        assert context.trace_id == "test_trace"
        assert context.span_id == "test_span"
        assert context.user_id == "test_user"
        assert context.session_id is None

    def test_logging_context_to_dict(self):
        """Test converting logging context to dictionary"""
        context = LoggingContext(
            trace_id="test_trace",
            span_id="test_span",
            user_id="test_user",
            custom_context={"key": "value"},
        )

        result = context.to_dict()

        assert result["trace_id"] == "test_trace"
        assert result["span_id"] == "test_span"
        assert result["user_id"] == "test_user"
        assert result["key"] == "value"
        assert "session_id" not in result  # None values should be removed

    def test_logging_context_merge(self):
        """Test merging two logging contexts"""
        context1 = LoggingContext(
            trace_id="trace1",
            user_id="user1",
            custom_context={"key1": "value1"},
        )
        context2 = LoggingContext(
            span_id="span2",
            user_id="user2",
            custom_context={"key2": "value2"},
        )

        merged = context1.merge(context2)

        assert merged.trace_id == "trace1"
        assert merged.span_id == "span2"
        assert merged.user_id == "user2"  # Should use context2's value
        assert merged.custom_context["key1"] == "value1"
        assert merged.custom_context["key2"] == "value2"


class TestLoggingContextManager:
    """Test cases for LoggingContextManager"""

    def test_context_manager_initialization(self):
        """Test context manager initialization"""
        manager = LoggingContextManager()

        assert manager is not None
        assert manager.enable_opentelemetry is True

    def test_context_manager_without_opentelemetry(self):
        """Test context manager without OpenTelemetry"""
        manager = LoggingContextManager(enable_opentelemetry=False)

        assert manager.enable_opentelemetry is False
        assert manager._tracer is None

    def test_create_trace_id(self):
        """Test trace ID creation"""
        manager = LoggingContextManager()
        trace_id = manager.create_trace_id()

        assert isinstance(trace_id, str)
        assert len(trace_id) == 32  # UUID without hyphens

    def test_create_span_id(self):
        """Test span ID creation"""
        manager = LoggingContextManager()
        span_id = manager.create_span_id()

        assert isinstance(span_id, str)
        assert len(span_id) == 16

    def test_create_request_id(self):
        """Test request ID creation"""
        manager = LoggingContextManager()
        request_id = manager.create_request_id()

        assert isinstance(request_id, str)
        assert len(request_id) == 32

    def test_set_and_get_trace_id(self):
        """Test setting and getting trace ID"""
        manager = LoggingContextManager()
        manager.set_trace_id("test_trace")

        context = manager.get_current_context()
        assert context.trace_id == "test_trace"

    def test_set_and_get_span_id(self):
        """Test setting and getting span ID"""
        manager = LoggingContextManager()
        manager.set_span_id("test_span")

        context = manager.get_current_context()
        assert context.span_id == "test_span"

    def test_set_and_get_user_id(self):
        """Test setting and getting user ID"""
        manager = LoggingContextManager()
        manager.set_user_id("test_user")

        context = manager.get_current_context()
        assert context.user_id == "test_user"

    def test_set_and_get_session_id(self):
        """Test setting and getting session ID"""
        manager = LoggingContextManager()
        manager.set_session_id("test_session")

        context = manager.get_current_context()
        assert context.session_id == "test_session"

    def test_set_custom_context(self):
        """Test setting custom context"""
        manager = LoggingContextManager()
        manager.set_custom_context("key", "value")

        context = manager.get_current_context()
        assert context.custom_context["key"] == "value"

    def test_context_context_manager(self):
        """Test context manager as context manager"""
        manager = LoggingContextManager()

        with manager.context(
            trace_id="test_trace",
            span_id="test_span",
            user_id="test_user",
            custom_key="custom_value",
        ) as context:
            assert context.trace_id == "test_trace"
            assert context.span_id == "test_span"
            assert context.user_id == "test_user"
            assert context.custom_context["custom_key"] == "custom_value"

    def test_context_restoration_after_context_manager(self):
        """Test context restoration after context manager exit"""
        manager = LoggingContextManager()

        # Set initial context
        manager.set_trace_id("initial_trace")
        manager.set_user_id("initial_user")

        # Enter context manager
        with manager.context(trace_id="inner_trace", user_id="inner_user"):
            assert get_current_trace_id() == "inner_trace"
            assert get_current_user_id() == "inner_user"

        # Verify context is restored
        assert get_current_trace_id() == "initial_trace"
        assert get_current_user_id() == "initial_user"

    def test_start_trace(self):
        """Test starting a new trace"""
        manager = LoggingContextManager()

        context = manager.start_trace(user_id="test_user")

        assert context.trace_id is not None
        assert context.span_id is not None
        assert context.user_id == "test_user"
        assert len(context.trace_id) == 32

    def test_start_trace_with_custom_id(self):
        """Test starting a trace with custom trace ID"""
        manager = LoggingContextManager()

        context = manager.start_trace(trace_id="custom_trace")

        assert context.trace_id == "custom_trace"
        assert context.span_id is not None

    def test_start_span(self):
        """Test starting a new span"""
        manager = LoggingContextManager()
        manager.start_trace()

        initial_span_id = get_current_span_id()
        context = manager.start_span("test_span", {"attr": "value"})

        assert context.span_id != initial_span_id
        assert context.parent_span_id == initial_span_id
        assert context.custom_context["span.attr"] == "value"

    def test_end_span(self):
        """Test ending a span"""
        manager = LoggingContextManager()
        manager.start_trace()

        initial_span_id = get_current_span_id()
        manager.start_span("child_span")

        assert get_current_span_id() != initial_span_id

        manager.end_span()

        assert get_current_span_id() == initial_span_id

    def test_clear_context(self):
        """Test clearing all context"""
        manager = LoggingContextManager()

        manager.set_trace_id("test_trace")
        manager.set_user_id("test_user")
        manager.set_custom_context("key", "value")

        manager.clear_context()

        context = manager.get_current_context()
        assert context.trace_id is None
        assert context.user_id is None
        assert len(context.custom_context) == 0


class TestGlobalFunctions:
    """Test cases for global convenience functions"""

    def test_get_logging_context(self):
        """Test getting logging context"""
        from core.logging.context.context_manager import get_logging_context_manager

        manager = get_logging_context_manager()
        manager.set_trace_id("test_trace")

        context = get_logging_context()
        assert context.trace_id == "test_trace"

    def test_get_current_trace_id(self):
        """Test getting current trace ID"""
        from core.logging.context.context_manager import get_logging_context_manager

        manager = get_logging_context_manager()
        manager.set_trace_id("test_trace")

        trace_id = get_current_trace_id()
        assert trace_id == "test_trace"

    def test_get_current_span_id(self):
        """Test getting current span ID"""
        from core.logging.context.context_manager import get_logging_context_manager

        manager = get_logging_context_manager()
        manager.set_span_id("test_span")

        span_id = get_current_span_id()
        assert span_id == "test_span"

    def test_get_current_user_id(self):
        """Test getting current user ID"""
        from core.logging.context.context_manager import get_logging_context_manager

        manager = get_logging_context_manager()
        manager.set_user_id("test_user")

        user_id = get_current_user_id()
        assert user_id == "test_user"

    def test_get_current_session_id(self):
        """Test getting current session ID"""
        from core.logging.context.context_manager import get_logging_context_manager

        manager = get_logging_context_manager()
        manager.set_session_id("test_session")

        session_id = get_current_session_id()
        assert session_id == "test_session"

    def test_set_user_context(self):
        """Test setting user context"""
        set_user_context("test_user", "test_session")

        assert get_current_user_id() == "test_user"
        assert get_current_session_id() == "test_session"

    def test_set_request_context(self):
        """Test setting request context"""
        set_request_context("test_request", "test_correlation")

        from core.logging.context.context_manager import _correlation_id, _request_id

        assert _request_id.get() == "test_request"
        assert _correlation_id.get() == "test_correlation"

    def test_set_user_context_without_session(self):
        """Test setting user context without session ID"""
        # Clear any existing session_id first
        from core.logging.context.context_manager import _session_id

        _session_id.set(None)

        set_user_context("test_user")

        assert get_current_user_id() == "test_user"
        assert get_current_session_id() is None


class TestContextIntegration:
    """Test cases for context integration scenarios"""

    def test_nested_contexts(self):
        """Test nested context managers"""
        manager = LoggingContextManager()

        with manager.context(trace_id="outer_trace", user_id="outer_user"):
            assert get_current_trace_id() == "outer_trace"

            with manager.context(trace_id="inner_trace", user_id="inner_user"):
                assert get_current_trace_id() == "inner_trace"
                assert get_current_user_id() == "inner_user"

            # Context should be restored to outer
            assert get_current_trace_id() == "outer_trace"
            assert get_current_user_id() == "outer_user"

    def test_trace_span_hierarchy(self):
        """Test trace and span hierarchy"""
        manager = LoggingContextManager()

        # Start trace
        manager.start_trace(user_id="test_user")
        trace_id = get_current_trace_id()
        root_span_id = get_current_span_id()

        # Start child span
        manager.start_span("child_span_1")
        child_span_1_id = get_current_span_id()
        assert child_span_1_id != root_span_id
        assert manager.get_current_context().parent_span_id == root_span_id

        # Start nested child span
        manager.start_span("child_span_2")
        child_span_2_id = get_current_span_id()
        assert child_span_2_id != child_span_1_id
        assert manager.get_current_context().parent_span_id == child_span_1_id

        # End spans
        manager.end_span()
        # After ending child_span_2, we should be back to child_span_1
        assert get_current_span_id() == child_span_1_id

        manager.end_span()
        # After ending child_span_1, there's no parent span, so span_id is cleared
        assert get_current_span_id() is None

        # Trace ID should remain the same
        assert get_current_trace_id() == trace_id

    def test_context_with_multiple_custom_fields(self):
        """Test context with multiple custom fields"""
        manager = LoggingContextManager()

        with manager.context(
            trace_id="test_trace",
            custom_field1="value1",
            custom_field2="value2",
            custom_field3=123,
        ):
            context = manager.get_current_context()
            assert context.custom_context["custom_field1"] == "value1"
            assert context.custom_context["custom_field2"] == "value2"
            assert context.custom_context["custom_field3"] == 123

    def test_context_isolation_between_threads(self):
        """Test context isolation between different threads"""
        import threading
        import time

        manager = LoggingContextManager()
        results = {}

        def thread_func(thread_id):
            manager.set_trace_id(f"trace_{thread_id}")
            time.sleep(0.01)
            results[thread_id] = get_current_trace_id()

        threads = [
            threading.Thread(target=thread_func, args=(1,)),
            threading.Thread(target=thread_func, args=(2,)),
            threading.Thread(target=thread_func, args=(3,)),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        # Each thread should have its own context
        assert results[1] == "trace_1"
        assert results[2] == "trace_2"
        assert results[3] == "trace_3"
