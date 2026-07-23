# -*- coding: utf-8 -*-
"""测试错误处理日志模块"""

import asyncio

import pytest


class TestExceptionClasses:
    def test_aiops_exception_to_dict(self):
        from core.error_handling_logging import (
            AIOpsException,
            ErrorCategory,
            ErrorSeverity,
        )

        exc = AIOpsException("msg", ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL)
        data = exc.to_dict()
        assert data["error_message"] == "msg"
        assert data["category"] == "system"
        assert data["severity"] == "critical"

    def test_network_exception(self):
        from core.error_handling_logging import NetworkException

        exc = NetworkException("fail")
        assert exc.category.value == "network"

    def test_database_exception(self):
        from core.error_handling_logging import DatabaseException

        exc = DatabaseException("fail")
        assert exc.category.value == "database"


class TestErrorHandler:
    def test_initialize(self):
        from core.error_handling_logging import ErrorHandler

        handler = ErrorHandler()
        asyncio.run(handler.initialize())
        assert "default" in handler.retry_policies

    def test_handle_exception(self):
        from core.error_handling_logging import ErrorHandler

        handler = ErrorHandler()
        asyncio.run(handler.initialize())
        record = asyncio.run(handler.handle_exception(ValueError("bad")))
        assert record.error_type == "ValueError"

    def test_handle_aiops_exception(self):
        from core.error_handling_logging import (
            AIOpsException,
            ErrorCategory,
            ErrorHandler,
            ErrorSeverity,
        )

        handler = ErrorHandler()
        asyncio.run(handler.initialize())
        exc = AIOpsException("x", ErrorCategory.SYSTEM, ErrorSeverity.ERROR)
        record = asyncio.run(handler.handle_exception(exc))
        assert record.category == ErrorCategory.SYSTEM

    def test_get_error_record(self):
        from core.error_handling_logging import ErrorHandler

        handler = ErrorHandler()
        asyncio.run(handler.initialize())
        record = asyncio.run(handler.handle_exception(ValueError("bad")))
        found = asyncio.run(handler.get_error_record(record.id))
        assert found is record

    def test_get_error_statistics(self):
        from core.error_handling_logging import ErrorHandler

        handler = ErrorHandler()
        asyncio.run(handler.initialize())
        asyncio.run(handler.handle_exception(ValueError("bad")))
        stats = asyncio.run(handler.get_error_statistics())
        assert stats["total_errors"] == 1

    def test_register_custom_handler(self):
        from core.error_handling_logging import ErrorHandler

        handler = ErrorHandler()
        calls = []
        handler.register_error_handler(ValueError, lambda r: calls.append(r))
        asyncio.run(handler.handle_exception(ValueError("bad")))
        assert len(calls) == 1

    def test_register_retry_policy(self):
        from core.error_handling_logging import ErrorHandler, RetryPolicy

        handler = ErrorHandler()
        handler.register_retry_policy("custom", RetryPolicy())
        assert "custom" in handler.retry_policies


class TestWithRetry:
    def test_retry_async_success(self):
        from core.error_handling_logging import ErrorHandler, RetryPolicy

        handler = ErrorHandler()
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=3,
            backoff_factor=1.0,
            initial_delay=0.0,
            max_delay=0.0,
            retry_on=[RuntimeError],
        )
        calls = []

        @handler.with_retry("default")
        async def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise RuntimeError("fail")
            return "ok"

        result = asyncio.run(flaky())
        assert result == "ok"
        assert len(calls) == 2

    def test_retry_sync_success(self):
        from core.error_handling_logging import ErrorHandler, RetryPolicy

        handler = ErrorHandler()
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=3,
            backoff_factor=1.0,
            initial_delay=0.0,
            max_delay=0.0,
            retry_on=[RuntimeError],
        )
        calls = []

        @handler.with_retry("default")
        def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise RuntimeError("fail")
            return "ok"

        result = flaky()
        assert result == "ok"

    def test_retry_not_matching_exception(self):
        from core.error_handling_logging import ErrorHandler, RetryPolicy

        handler = ErrorHandler()
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=3,
            backoff_factor=1.0,
            initial_delay=0.0,
            max_delay=0.0,
            retry_on=[RuntimeError],
        )

        @handler.with_retry("default")
        def bad():
            raise ValueError("nope")

        with pytest.raises(ValueError):
            bad()


class TestStructuredLogger:
    def test_log_and_get(self):
        from core.error_handling_logging import StructuredLogger

        logger = StructuredLogger()
        logger.info("hello")
        entries = asyncio.run(logger.get_log_entries(limit=10))
        assert len(entries) == 1
        assert entries[0].message == "hello"

    def test_log_levels(self):
        from core.error_handling_logging import StructuredLogger

        logger = StructuredLogger()
        logger.debug("d")
        logger.info("i")
        logger.warning("w")
        logger.error("e")
        logger.critical("c")
        assert len(logger.log_entries) == 5

    def test_get_log_entries_filter(self):
        from core.error_handling_logging import StructuredLogger

        logger = StructuredLogger()
        logger.info("i")
        logger.error("e")
        entries = asyncio.run(logger.get_log_entries(level="ERROR"))
        assert len(entries) == 1
        assert entries[0].level == "ERROR"

    def test_get_log_statistics(self):
        from core.error_handling_logging import StructuredLogger

        logger = StructuredLogger()
        logger.info("i")
        logger.error("e")
        stats = asyncio.run(logger.get_log_statistics())
        assert stats["total_entries"] == 2


class TestErrorHandlingAndLogging:
    def test_error_handling_and_logging(self):
        from core.error_handling_logging import ErrorHandlingAndLogging

        ehl = ErrorHandlingAndLogging()
        ehl.info("test")
        stats = asyncio.run(ehl.get_statistics())
        assert "error_statistics" in stats
        assert "log_statistics" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
