# -*- coding: utf-8 -*-
"""Targeted tests for core.error_handling_logging helpers."""

from unittest.mock import AsyncMock

import pytest

import core.error_handling_logging as ehll
from core.error_handling_logging import (
    AIOpsException,
    AuthenticationException,
    DatabaseException,
    ErrorCategory,
    ErrorHandlingAndLogging,
    ErrorSeverity,
    NetworkException,
    RetryPolicy,
    StructuredLogger,
    ValidationException,
)


@pytest.fixture
def ehal(monkeypatch):
    """Return a fresh ErrorHandlingAndLogging instance without loguru reconfiguration."""
    monkeypatch.setattr(StructuredLogger, "_configure_loguru", lambda self: None)
    instance = ErrorHandlingAndLogging()
    return instance


class TestExceptions:
    def test_aiops_exception_to_dict(self) -> None:
        exc = AIOpsException("msg", category=ErrorCategory.NETWORK, severity=ErrorSeverity.ERROR)
        d = exc.to_dict()
        assert d["category"] == "network"
        assert d["severity"] == "error"

    def test_network_exception(self) -> None:
        exc = NetworkException("net")
        assert exc.category == ErrorCategory.NETWORK

    def test_database_exception(self) -> None:
        exc = DatabaseException("db")
        assert exc.category == ErrorCategory.DATABASE

    def test_authentication_exception(self) -> None:
        exc = AuthenticationException("auth")
        assert exc.category == ErrorCategory.AUTHENTICATION

    def test_validation_exception(self) -> None:
        exc = ValidationException("val")
        assert exc.category == ErrorCategory.VALIDATION


class TestErrorHandler:
    @pytest.mark.asyncio
    async def test_initialize(self, ehal) -> None:
        handler = ehal.error_handler
        await handler.initialize()
        assert "default" in handler.retry_policies
        assert AIOpsException in handler.error_handlers

    @pytest.mark.asyncio
    async def test_handle_exception_records_and_routes(self, ehal) -> None:
        handler = ehal.error_handler
        await handler.initialize()
        record = await handler.handle_exception(NetworkException("boom"))
        assert record.error_type == "NetworkException"
        assert handler.error_index.get(record.id) is record

    @pytest.mark.asyncio
    async def test_handle_exception_builtin(self, ehal) -> None:
        handler = ehal.error_handler
        record = await handler.handle_exception(RuntimeError("x"))
        assert record.category == ErrorCategory.UNKNOWN

    @pytest.mark.asyncio
    async def test_handle_exception_triggers_alert(self, ehal) -> None:
        handler = ehal.error_handler
        await handler.initialize()
        record = await handler.handle_exception(
            AIOpsException("crit", category=ErrorCategory.SYSTEM, severity=ErrorSeverity.CRITICAL)
        )
        assert record.severity == ErrorSeverity.CRITICAL

    @pytest.mark.asyncio
    async def test_get_error_record_and_statistics(self, ehal) -> None:
        handler = ehal.error_handler
        record = await handler.handle_exception(ValidationException("bad"))
        fetched = await handler.get_error_record(record.id)
        assert fetched is record
        stats = await handler.get_error_statistics()
        assert stats["total_errors"] >= 1
        assert "by_category" in stats

    def test_register_error_handler(self, ehal) -> None:
        async def custom_handler(record):
            record.resolved = True

        handler = ehal.error_handler
        handler.error_handlers[ValueError] = custom_handler
        assert ValueError in handler.error_handlers

    def test_register_retry_policy(self, ehal) -> None:
        handler = ehal.error_handler
        handler.retry_policies["custom"] = RetryPolicy(max_attempts=2)
        assert "custom" in handler.retry_policies

    @pytest.mark.asyncio
    async def test_handle_exception_handler_raises(self, ehal) -> None:
        handler = ehal.error_handler
        await handler.initialize()

        async def bad_handler(record):
            raise RuntimeError("handler boom")

        handler.error_handlers[ValueError] = bad_handler
        record = await handler.handle_exception(ValueError("x"))
        assert record.error_type == "ValueError"

    @pytest.mark.asyncio
    async def test_default_error_handlers_log(self, ehal) -> None:
        handler = ehal.error_handler
        await handler.initialize()
        for exc in (
            NetworkException("n"),
            DatabaseException("d"),
            AuthenticationException("a"),
            ValidationException("v"),
        ):
            await handler.handle_exception(exc)

    @pytest.mark.asyncio
    async def test_default_error_handler_methods(self, ehal) -> None:
        handler = ehal.error_handler
        await handler.initialize()
        record = await handler._record_error(AIOpsException("x"), {})
        await handler._handle_network_exception(record)
        await handler._handle_database_exception(record)
        await handler._handle_authentication_exception(record)
        await handler._handle_validation_exception(record)

    @pytest.mark.asyncio
    async def test_register_error_handler_logs(self, ehal) -> None:
        handler = ehal.error_handler

        async def dummy(r):
            pass

        handler.register_error_handler(ValueError, dummy)

    @pytest.mark.asyncio
    async def test_register_retry_policy_logs(self, ehal) -> None:
        handler = ehal.error_handler
        handler.register_retry_policy("custom", RetryPolicy(max_attempts=2))

    @pytest.mark.asyncio
    async def test_error_alert_threshold_branches(self, ehal) -> None:
        handler = ehal.error_handler
        await handler.initialize()
        # Severity with threshold 0 should skip alert block
        await handler.handle_exception(
            AIOpsException("info", severity=ErrorSeverity.INFO, category=ErrorCategory.SYSTEM)
        )

    @pytest.mark.asyncio
    async def test_error_alert_trigger(self, ehal) -> None:
        handler = ehal.error_handler
        await handler.initialize()
        handler.alert_thresholds[ErrorSeverity.ERROR] = 1
        for _ in range(2):
            await handler.handle_exception(
                AIOpsException("err", severity=ErrorSeverity.ERROR, category=ErrorCategory.SYSTEM)
            )


class TestRetryDecorator:
    def test_with_retry_success(self, ehal) -> None:
        handler = ehal.error_handler
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=3, initial_delay=0.0, backoff_factor=1.0, max_delay=0.0
        )

        @handler.with_retry()
        def ok():
            return 42

        assert ok() == 42

    def test_with_retry_exhaust_sync(self, ehal, monkeypatch) -> None:
        monkeypatch.setattr("core.error_handling_logging.time.sleep", lambda x: None)
        handler = ehal.error_handler
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=2,
            initial_delay=0.0,
            backoff_factor=1.0,
            max_delay=0.0,
            retry_on=[NetworkException],
        )

        @handler.with_retry()
        def fail():
            raise NetworkException("x")

        with pytest.raises(NetworkException):
            fail()

    @pytest.mark.asyncio
    async def test_with_retry_async_success(self, ehal) -> None:
        handler = ehal.error_handler
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=3, initial_delay=0.0, backoff_factor=1.0, max_delay=0.0
        )

        @handler.with_retry()
        async def ok():
            return 42

        assert await ok() == 42

    @pytest.mark.asyncio
    async def test_with_retry_async_exhaust(self, ehal, monkeypatch) -> None:
        monkeypatch.setattr("core.error_handling_logging.asyncio.sleep", AsyncMock())
        handler = ehal.error_handler
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=2,
            initial_delay=0.0,
            backoff_factor=1.0,
            max_delay=0.0,
            retry_on=[NetworkException],
        )

        @handler.with_retry()
        async def fail():
            raise NetworkException("x")

        with pytest.raises(NetworkException):
            await fail()

    def test_with_retry_non_retryable_sync(self, ehal) -> None:
        handler = ehal.error_handler
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=2,
            initial_delay=0.0,
            backoff_factor=1.0,
            max_delay=0.0,
            retry_on=[NetworkException],
        )

        @handler.with_retry()
        def fail():
            raise ValueError("x")

        with pytest.raises(ValueError):
            fail()

    @pytest.mark.asyncio
    async def test_with_retry_non_retryable_async(self, ehal) -> None:
        handler = ehal.error_handler
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=2,
            initial_delay=0.0,
            backoff_factor=1.0,
            max_delay=0.0,
            retry_on=[NetworkException],
        )

        @handler.with_retry()
        async def fail():
            raise ValueError("x")

        with pytest.raises(ValueError):
            await fail()

    def test_with_retry_zero_attempts(self, ehal) -> None:
        handler = ehal.error_handler
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=0, initial_delay=0.0, backoff_factor=1.0, max_delay=0.0
        )

        @handler.with_retry()
        def ok():
            return 1

        assert ok() is None

    @pytest.mark.asyncio
    async def test_with_retry_async_zero_attempts(self, ehal) -> None:
        handler = ehal.error_handler
        handler.retry_policies["default"] = RetryPolicy(
            max_attempts=0, initial_delay=0.0, backoff_factor=1.0, max_delay=0.0
        )

        @handler.with_retry()
        async def ok():
            return 1

        assert await ok() is None


class TestStructuredLogger:
    @pytest.mark.asyncio
    async def test_log_levels_and_query(self, ehal) -> None:
        logger = ehal.structured_logger
        logger.debug("debug msg", extra="x")
        logger.info("info msg")
        logger.warning("warn msg")
        logger.error("error msg")
        logger.critical("critical msg")

        all_entries = await logger.get_log_entries(limit=10)
        assert len(all_entries) == 5

        filtered = await logger.get_log_entries(level="INFO")
        assert len(filtered) >= 1

    @pytest.mark.asyncio
    async def test_get_log_statistics(self, ehal) -> None:
        logger = ehal.structured_logger
        logger.info("a")
        logger.error("b")
        stats = await logger.get_log_statistics()
        assert stats["total_entries"] == 2
        assert stats["by_level"]["INFO"] == 1
        assert stats["by_level"]["ERROR"] == 1

    @pytest.mark.asyncio
    async def test_get_log_entries_filters_and_limit(self, ehal) -> None:
        from datetime import datetime, timedelta

        logger = ehal.structured_logger
        logger.info("old")
        logger.info("recent")
        logger.error("err")

        now = datetime.now()
        filtered = await logger.get_log_entries(
            level="INFO",
            start_time=now - timedelta(seconds=1),
            end_time=now + timedelta(seconds=1),
            limit=1,
        )
        assert len(filtered) == 1

    @pytest.mark.asyncio
    async def test_get_log_entries_time_exclusions(self, ehal) -> None:
        from datetime import datetime, timedelta

        logger = ehal.structured_logger
        logger.info("msg")

        now = datetime.now()
        before = await logger.get_log_entries(end_time=now - timedelta(seconds=1))
        assert len(before) == 0
        after = await logger.get_log_entries(start_time=now + timedelta(seconds=1))
        assert len(after) == 0


class TestErrorHandlingAndLoggingFacade:
    @pytest.mark.asyncio
    async def test_initialize(self, ehal) -> None:
        await ehal.initialize()
        assert "default" in ehal.error_handler.retry_policies

    @pytest.mark.asyncio
    async def test_handle_exception(self, ehal) -> None:
        record = await ehal.handle_exception(DatabaseException("db"))
        assert record.error_type == "DatabaseException"

    @pytest.mark.asyncio
    async def test_log_and_get_statistics(self, ehal) -> None:
        ehal.info("test")
        ehal.error("bad")
        stats = await ehal.get_statistics()
        assert "error_statistics" in stats
        assert "log_statistics" in stats
        assert stats["log_statistics"]["total_entries"] == 2

    def test_log_facade_levels(self, ehal) -> None:
        ehal.log("INFO", "log")
        ehal.debug("debug")
        ehal.warning("warn")
        ehal.critical("crit")

    def test_module_singletons(self) -> None:
        assert isinstance(ehll.error_handling_logging, ErrorHandlingAndLogging)
        assert isinstance(ehll.logger, StructuredLogger)
