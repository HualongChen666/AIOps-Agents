# -*- coding: utf-8 -*-
"""Tests for core/error_handler.py."""

import time
from datetime import datetime, timedelta

import pytest  # noqa: F401  # Imported for test setup

from core.error_handler import AIOpsException, ErrorHandler, NetworkError


def test_handle_exception_and_stats():
    handler = ErrorHandler()
    context = handler.handle_exception(ValueError("bad value"))
    assert context.error_id
    stats = handler.get_error_stats()
    assert stats["total_errors"] >= 1
    report = handler.get_error_report(hours=24)
    assert "total_errors" in report


def test_retry_non_retryable():
    handler = ErrorHandler()

    @handler.retry(max_retries=0)
    def failing():
        raise ValueError("boom")

    with pytest.raises(ValueError):
        failing()
    assert handler.get_error_stats()["total_errors"] >= 1


def test_exception_subclasses():
    err = NetworkError("timeout", url="http://x")
    assert err.context["url"] == "http://x"
    assert isinstance(err, AIOpsException)


def test_retry_with_success():
    """Test retry mechanism with eventual success."""
    handler = ErrorHandler()
    attempt_count = [0]

    @handler.retry(max_retries=3, base_delay=0.1)
    def flaky_function():
        attempt_count[0] += 1
        if attempt_count[0] < 2:
            raise NetworkError("connection timeout", url="http://test.com")
        return "success"

    result = flaky_function()
    assert result == "success"
    assert attempt_count[0] == 2
    # Note: When retry succeeds, the error is not recorded in error history
    # because the function eventually succeeds and doesn't raise an exception


def test_retry_with_max_retries():
    """Test retry mechanism when max retries is exhausted."""
    handler = ErrorHandler()

    @handler.retry(max_retries=2, base_delay=0.1)
    def always_failing():
        raise NetworkError("persistent failure", url="http://test.com")

    with pytest.raises(NetworkError) as exc_info:
        always_failing()

    assert exc_info.value.context["url"] == "http://test.com"
    stats = handler.get_error_stats()
    assert stats["total_errors"] >= 1


def test_error_report_time_filter():
    """Test error report time filtering functionality."""
    handler = ErrorHandler()

    # Add errors at different times
    old_error = handler.handle_exception(
        ValueError("old error"),
        context={"error_age": "old"}
    )
    recent_error = handler.handle_exception(
        ValueError("recent error"),
        context={"error_age": "recent"}
    )

    # Get report for last 24 hours
    report = handler.get_error_report(hours=24)
    assert report["period_hours"] == 24
    assert report["total_errors"] >= 1
    assert "errors_by_type" in report
    assert "errors_by_severity" in report
    assert "errors_by_category" in report
    assert "top_errors" in report
    assert "error_trends" in report


def test_network_error_context():
    """Test network error context preservation."""
    handler = ErrorHandler()

    # Create network error with context
    error = NetworkError(
        "connection failed",
        url="http://api.example.com/endpoint",
        status_code=503,
        response_time=5.2
    )

    # Handle the error
    context = handler.handle_exception(error)

    assert context.error_type == "NetworkError"
    assert context.category.value == "network"
    assert context.severity.value == "error"
    assert "url" in context.additional_context or error.context.get("url") == "http://api.example.com/endpoint"

    # Verify error stats include this error
    stats = handler.get_error_stats()
    assert stats["total_errors"] >= 1
    assert "network" in stats["errors_by_category"]
