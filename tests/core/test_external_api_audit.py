# -*- coding: utf-8 -*-
"""Tests for core/external_api_audit.py."""

from core.external_api_audit import (
    ExternalAPIAuditLogger,
    get_audit_logger,
    initialize_external_api_audit,
)


def test_get_audit_logger_and_initialize():
    logger = get_audit_logger()
    assert isinstance(logger, ExternalAPIAuditLogger)
    initialize_external_api_audit()
    assert get_audit_logger()._audit_enabled is True


def test_log_and_query():
    logger = ExternalAPIAuditLogger()
    logger.enable_audit()
    logger.log_api_call(
        method="GET",
        url="http://api.example.com/data?token=secret",
        headers={"authorization": "Bearer x"},
        response_status=200,
        response_time_ms=50.0,
    )
    assert len(logger._audit_logs) == 1
    record = logger._audit_logs[0]
    assert "?***" in record["url"]
    assert record["headers"]["authorization"] == "***REDACTED***"

    results = logger.query_audit_logs(method="GET")
    assert len(results) == 1

    summary = logger.get_audit_summary(hours=24)
    assert summary["total_calls"] >= 1

    exported = logger.export_audit_logs(format="json")
    assert "GET" in exported

    logger.clear_audit_logs()
    assert len(logger._audit_logs) == 0
