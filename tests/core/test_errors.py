# -*- coding: utf-8 -*-
"""Tests for error handling, exceptions, error codes, logging and recovery."""

import pytest  # noqa: F401  # Imported for test setup
from fastapi import FastAPI, Request

import core.error_codes
import core.error_handler
import core.error_handling
import core.error_handling_logging
import core.error_logging
import core.error_recovery.core
import core.exception_handler
import core.exceptions


def test_exceptions_raise_and_to_dict():
    with pytest.raises(core.exceptions.ResourceNotFoundException):
        raise core.exceptions.ResourceNotFoundException("missing")
    exc = core.exceptions.ValidationException("bad")
    assert "message" in exc.to_dict()


def test_error_codes():
    mgr = core.error_codes.get_error_code_manager()
    assert mgr is not None
    msg = core.error_codes.get_error_message(core.error_codes.ErrorCode.GEN_INTERNAL_ERROR.value)
    assert isinstance(msg, str)
    assert core.error_codes.ErrorCode.GEN_INTERNAL_ERROR is not None


def test_error_handling():
    exc = core.error_handling.ValidationError("field invalid")
    resp = core.error_handling.handle_aiops_exception(exc)
    assert "error_code" in resp
    generic = core.error_handling.handle_generic_exception(ValueError("x"))
    assert "error_code" in generic
    err = core.error_handling.create_error_response(
        core.error_handling.ErrorCode.INVALID_REQUEST, "bad request"
    )
    assert err.status_code in (400, 500)


def test_error_handler():
    handler = core.error_handler.ErrorHandler()
    stats = handler.get_error_stats()
    assert isinstance(stats, dict)
    assert stats["total_errors"] == 0
    handler.handle_exception(ValueError("boom"))
    assert handler.get_error_stats()["total_errors"] >= 1


def test_error_logging():
    core.error_logging.record_error("TEST", "warning", "test")
    stats = core.error_logging.get_error_stats()
    assert isinstance(stats, dict)
    count = core.error_logging.get_error_count("TEST")
    assert count >= 1
    app = FastAPI()
    core.error_logging.setup_exception_handlers(app)


async def test_exception_handler():
    app = FastAPI()
    core.exception_handler.setup_exception_handlers(app)
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
        "server": None,
        "client": ("127.0.0.1", 0),
    }
    req = Request(scope)
    exc = core.exception_handler.AIOpsException("fail")
    resp = await core.exception_handler.aiops_exception_handler(req, exc)
    assert resp.status_code == 500


async def test_error_handling_logging():
    ehl = core.error_handling_logging.ErrorHandlingAndLogging()
    record = await ehl.handle_exception(ValueError("x"))
    assert record is not None
    ehl.info("test message")


async def test_error_recovery():
    config = core.error_recovery.core.RetryConfig(max_attempts=2, base_delay=0.01, max_delay=0.1)
    policy = core.error_recovery.core.RetryPolicy(config)
    assert policy.should_retry(ValueError("x"), 1) is True
    assert policy.calculate_delay(1) >= 0

    cb = core.error_recovery.core.CircuitBreaker(
        core.error_recovery.core.CircuitBreakerConfig(
            failure_threshold=2, recovery_timeout=0.01, expected_exception=ValueError
        )
    )
    assert cb.get_state().value == "closed"

    async def good():
        return "ok"

    async def bad():
        raise ValueError("fail")

    assert await cb.call(good) == "ok"
    with pytest.raises(ValueError):
        await cb.call(bad)
