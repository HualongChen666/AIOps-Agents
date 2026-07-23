# -*- coding: utf-8 -*-
"""Targeted tests for core.error_handler helpers."""

from unittest.mock import AsyncMock

import pytest

from core.error_handler import (
    AIOpsException,
    AuthenticationError,
    AuthorizationError,
    DatabaseError,
    ErrorCategory,
    ErrorContext,
    ErrorHandler,
    ErrorSeverity,
    ExternalServiceError,
    NetworkError,
    ValidationError,
)


@pytest.fixture
def handler(monkeypatch):
    """Return a fresh ErrorHandler without real logging/thread side effects."""
    monkeypatch.setattr(ErrorHandler, "_configure_logging", lambda self: None)
    monkeypatch.setattr(ErrorHandler, "_start_alert_processor", lambda self: None)
    h = ErrorHandler()
    h.error_history.clear()
    h.error_stats.clear()
    h.error_patterns.clear()
    h.alert_queue.clear()
    return h


class TestEnumsAndExceptions:
    def test_error_severity(self) -> None:
        assert ErrorSeverity.ERROR.value == "error"

    def test_error_category(self) -> None:
        assert ErrorCategory.NETWORK.value == "network"

    def test_aiops_exception_to_dict(self) -> None:
        exc = AIOpsException(
            "msg", severity=ErrorSeverity.WARNING, category=ErrorCategory.VALIDATION
        )
        assert exc.to_dict()["severity"] == "warning"
        assert exc.to_dict()["category"] == "validation"

    def test_validation_error(self) -> None:
        exc = ValidationError("bad", field="f")
        assert exc.context["field"] == "f"

    def test_network_error(self) -> None:
        exc = NetworkError("net", url="http://x")
        assert exc.context["url"] == "http://x"

    def test_database_error(self) -> None:
        exc = DatabaseError("db", query="SELECT 1")
        assert exc.context["query"] == "SELECT 1"

    def test_authentication_error(self) -> None:
        exc = AuthenticationError("auth", user_id="u1")
        assert exc.context["user_id"] == "u1"

    def test_external_service_error(self) -> None:
        exc = ExternalServiceError("ext", service="svc")
        assert exc.context["service"] == "svc"

    def test_authorization_error(self) -> None:
        exc = AuthorizationError("denied", resource="/admin")
        assert exc.context["resource"] == "/admin"


class TestHandleException:
    def test_handle_aiops_exception(self, handler) -> None:
        exc = NetworkError("boom")
        ctx = handler.handle_exception(exc)
        assert isinstance(ctx, ErrorContext)
        assert ctx.severity == ErrorSeverity.ERROR
        assert ctx.category == ErrorCategory.NETWORK

    def test_handle_validation_error(self, handler) -> None:
        ctx = handler.handle_exception(ValidationError("x"))
        assert ctx.category == ErrorCategory.VALIDATION

    def test_handle_builtin_value_error(self, handler) -> None:
        ctx = handler.handle_exception(ValueError("x"))
        assert ctx.severity == ErrorSeverity.WARNING
        assert ctx.category == ErrorCategory.VALIDATION

    def test_handle_connection_error(self, handler) -> None:
        ctx = handler.handle_exception(ConnectionError("x"))
        assert ctx.category == ErrorCategory.NETWORK

    def test_handle_generic_error(self, handler) -> None:
        ctx = handler.handle_exception(RuntimeError("x"))
        assert ctx.category == ErrorCategory.UNKNOWN

    def test_handle_error_with_context_and_ids(self, handler) -> None:
        ctx = handler.handle_exception(
            RuntimeError("x"), context={"foo": "bar"}, user_id="u", request_id="r"
        )
        assert ctx.user_id == "u"
        assert ctx.request_id == "r"
        assert ctx.additional_context == {"foo": "bar"}

    def test_handle_critical_queues_alert(self, handler) -> None:
        exc = AIOpsException("crit", severity=ErrorSeverity.CRITICAL)
        ctx = handler.handle_exception(exc)
        assert ctx in handler.alert_queue


class TestErrorStatsAndReports:
    def test_get_error_stats(self, handler) -> None:
        handler.handle_exception(NetworkError("n"))
        handler.handle_exception(DatabaseError("d"))
        stats = handler.get_error_stats()
        assert stats["total_errors"] == 2

    def test_get_error_report(self, handler) -> None:
        handler.handle_exception(NetworkError("n"))
        report = handler.get_error_report(hours=24)
        assert report["total_errors"] == 1
        assert "top_errors" in report
        assert "error_trends" in report


class TestRetryDecorator:
    def test_retry_success(self, handler) -> None:
        @handler.retry(max_retries=2, base_delay=0.0)
        def ok():
            return 42

        assert ok() == 42

    def test_retry_non_retryable_raises(self, handler) -> None:
        @handler.retry(max_retries=2, base_delay=0.0)
        def fail():
            raise RuntimeError("x")

        with pytest.raises(RuntimeError):
            fail()

    def test_retry_retryable_exhausts_sync(self, handler, monkeypatch) -> None:
        monkeypatch.setattr("core.error_handler.time.sleep", lambda x: None)

        @handler.retry(max_retries=2, base_delay=0.0)
        def fail_network():
            raise NetworkError("x")

        with pytest.raises(NetworkError):
            fail_network()

    @pytest.mark.asyncio
    async def test_retry_async_success(self, handler) -> None:
        @handler.retry(max_retries=2, base_delay=0.0)
        async def ok():
            return 42

        assert await ok() == 42

    @pytest.mark.asyncio
    async def test_retry_async_non_retryable(self, handler) -> None:
        @handler.retry(max_retries=2, base_delay=0.0)
        async def fail():
            raise RuntimeError("x")

        with pytest.raises(RuntimeError):
            await fail()

    @pytest.mark.asyncio
    async def test_retry_async_retryable_exhausts(self, handler, monkeypatch) -> None:
        monkeypatch.setattr("core.error_handler.asyncio.sleep", AsyncMock())

        @handler.retry(max_retries=2, base_delay=0.0)
        async def fail_network():
            raise NetworkError("x")

        with pytest.raises(NetworkError):
            await fail_network()


class TestLogSeverity:
    def test_handle_debug_and_info(self, handler) -> None:
        handler.handle_exception(AIOpsException("dbg", severity=ErrorSeverity.DEBUG))
        handler.handle_exception(AIOpsException("info", severity=ErrorSeverity.INFO))
        assert handler.error_stats["unknown:AIOpsException"] == 2


class TestFatalSeverity:
    def test_fatal_without_stack_trace(self, handler) -> None:
        handler.handle_exception(AIOpsException("fatal", severity=ErrorSeverity.FATAL))

    def test_fatal_with_stack_trace(self, handler) -> None:
        try:
            raise RuntimeError("boom")
        except Exception:
            ctx = handler.handle_exception(AIOpsException("fatal", severity=ErrorSeverity.FATAL))
            assert ctx.stack_trace is not None


class TestRetryBranches:
    def test_sync_retry_non_exponential(self, handler, monkeypatch) -> None:
        monkeypatch.setattr("core.error_handler.time.sleep", lambda x: None)

        @handler.retry(max_retries=1, base_delay=0.5, exponential_backoff=False)
        def fail_network():
            raise NetworkError("x")

        with pytest.raises(NetworkError):
            fail_network()

    @pytest.mark.asyncio
    async def test_async_retry_non_exponential(self, handler, monkeypatch) -> None:
        monkeypatch.setattr("core.error_handler.asyncio.sleep", AsyncMock())

        @handler.retry(max_retries=1, base_delay=0.5, exponential_backoff=False)
        async def fail_network():
            raise NetworkError("x")

        with pytest.raises(NetworkError):
            await fail_network()

    def test_sync_retry_zero_attempts(self, handler) -> None:
        @handler.retry(max_retries=-1, base_delay=0.0)
        def ok():
            return 1

        with pytest.raises(RuntimeError, match="All retries exhausted"):
            ok()

    @pytest.mark.asyncio
    async def test_async_retry_zero_attempts(self, handler) -> None:
        @handler.retry(max_retries=-1, base_delay=0.0)
        async def ok():
            return 1

        with pytest.raises(RuntimeError, match="All retries exhausted"):
            await ok()

    def test_log_fatal_without_stack_trace(self, handler) -> None:
        ctx = ErrorContext(
            error_id="x",
            error_type="AIOpsException",
            error_message="fatal",
            severity=ErrorSeverity.FATAL,
            category=ErrorCategory.UNKNOWN,
            stack_trace=None,
        )
        handler._log_error(ctx)


class TestErrorTrends:
    def test_error_report_with_trend(self, handler) -> None:
        from datetime import datetime, timedelta

        for i in range(2):
            ctx = ErrorContext(
                error_id=f"e{i}",
                error_type="RuntimeError",
                error_message="x",
                severity=ErrorSeverity.ERROR,
                category=ErrorCategory.UNKNOWN,
                timestamp=datetime.now() - timedelta(hours=i),
            )
            handler.error_history.append(ctx)
        handler.error_stats["unknown:RuntimeError"] = 2

        report = handler.get_error_report(hours=24)
        assert report["total_errors"] == 2
        assert "error_trends" in report


class TestAlertProcessing:
    def test_process_alerts(self, handler) -> None:
        handler.handle_exception(AIOpsException("fatal", severity=ErrorSeverity.FATAL))
        handler._process_alerts()
        assert handler.alert_queue == []

    def test_send_alert(self, handler) -> None:
        ctx = handler.handle_exception(AIOpsException("fatal", severity=ErrorSeverity.FATAL))
        # Should not raise
        handler._send_alert(ctx)

    def test_alert_processing_loop_handles_errors(self, handler, monkeypatch) -> None:
        call_count = 0

        def raise_once():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("alert loop failure")

        sleep_calls = 0

        def counted_sleep(x):
            nonlocal sleep_calls
            sleep_calls += 1
            if sleep_calls >= 2:
                raise SystemExit("break loop")

        monkeypatch.setattr(handler, "_process_alerts", raise_once)
        monkeypatch.setattr("core.error_handler.time.sleep", counted_sleep)

        with pytest.raises(SystemExit):
            handler._alert_processing_loop()

        assert call_count >= 1
