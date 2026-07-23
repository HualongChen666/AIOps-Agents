# -*- coding: utf-8 -*-
"""测试错误处理器模块"""

import asyncio

import pytest


class TestExceptionClasses:
    def test_aiops_exception_to_dict(self):
        from core.error_handler import AIOpsException, ErrorCategory, ErrorSeverity

        exc = AIOpsException("msg", ErrorSeverity.CRITICAL, ErrorCategory.SYSTEM)
        data = exc.to_dict()
        assert data["message"] == "msg"
        assert data["severity"] == "critical"
        assert data["category"] == "system"

    def test_validation_error(self):
        from core.error_handler import ValidationError

        exc = ValidationError("bad", field="f")
        assert exc.context["field"] == "f"

    def test_network_error(self):
        from core.error_handler import NetworkError

        exc = NetworkError("timeout", url="http://x")
        assert exc.context["url"] == "http://x"

    def test_database_error(self):
        from core.error_handler import DatabaseError

        exc = DatabaseError("fail", query="SELECT 1")
        assert exc.context["query"] == "SELECT 1"


class TestErrorHandler:
    def test_handle_validation_error(self):
        from core.error_handler import ErrorCategory, ErrorHandler, ErrorSeverity

        handler = ErrorHandler()
        ctx = handler.handle_exception(ValueError("invalid"))
        assert ctx.severity == ErrorSeverity.WARNING
        assert ctx.category == ErrorCategory.VALIDATION

    def test_handle_network_error(self):
        from core.error_handler import ErrorCategory, ErrorHandler, ErrorSeverity

        handler = ErrorHandler()
        ctx = handler.handle_exception(TimeoutError("slow"))
        assert ctx.severity == ErrorSeverity.ERROR
        assert ctx.category == ErrorCategory.NETWORK

    def test_handle_aiops_exception(self):
        from core.error_handler import AIOpsException, ErrorHandler

        handler = ErrorHandler()
        ctx = handler.handle_exception(AIOpsException("x"))
        assert ctx.error_type == "AIOpsException"

    def test_critical_alert_queued(self):
        from core.error_handler import AIOpsException, ErrorHandler, ErrorSeverity

        handler = ErrorHandler()
        ctx = handler.handle_exception(AIOpsException("boom", severity=ErrorSeverity.CRITICAL))
        assert ctx in handler.alert_queue

    def test_error_stats(self):
        from core.error_handler import ErrorHandler

        handler = ErrorHandler()
        handler.handle_exception(ValueError("v"))
        handler.handle_exception(ValueError("v"))
        stats = handler.get_error_stats()
        assert stats["total_errors"] == 2

    def test_error_report(self):
        from core.error_handler import ErrorHandler

        handler = ErrorHandler()
        handler.handle_exception(ValueError("v"))
        report = handler.get_error_report(hours=24)
        assert report["period_hours"] == 24
        assert report["total_errors"] == 1

    def test_calculate_trends(self):
        from core.error_handler import ErrorHandler

        handler = ErrorHandler()
        handler.handle_exception(ValueError("a"))
        report = handler.get_error_report(hours=24)
        assert report["error_trends"]["trend_direction"] == "stable"


class TestRetryDecorator:
    def test_retry_success_after_failure(self):
        from core.error_handler import ErrorHandler

        handler = ErrorHandler()
        calls = []

        @handler.retry(max_retries=2, base_delay=0, exponential_backoff=False)
        def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise TimeoutError("fail")
            return "ok"

        assert flaky() == "ok"
        assert len(calls) == 2

    def test_retry_non_retryable(self):
        from core.error_handler import ErrorHandler

        handler = ErrorHandler()

        @handler.retry(max_retries=2, base_delay=0, exponential_backoff=False)
        def bad():
            raise ValueError("nope")

        with pytest.raises(ValueError):
            bad()

    def test_retry_async_success(self):
        from core.error_handler import ErrorHandler

        handler = ErrorHandler()
        calls = []

        @handler.retry(max_retries=2, base_delay=0, exponential_backoff=False)
        async def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise TimeoutError("fail")
            return "ok"

        result = asyncio.run(flaky())
        assert result == "ok"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
