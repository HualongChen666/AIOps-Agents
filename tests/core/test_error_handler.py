# -*- coding: utf-8 -*-
"""Tests for core/error_handler.py."""

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
