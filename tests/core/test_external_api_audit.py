# -*- coding: utf-8 -*-
"""测试外部API审计模块"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from core.external_api_audit import (
    ExternalAPIAuditLogger,
    audit_aiohttp_call,
    audit_httpx_call,
    get_audit_logger,
    initialize_external_api_audit,
)


class TestExternalAPIAuditLogger:
    """测试 ExternalAPIAuditLogger"""

    def test_log_api_call_records_entry(self):
        logger = ExternalAPIAuditLogger()
        logger.log_api_call(
            method="GET",
            url="https://api.example.com/data?token=secret",
            headers={"Authorization": "Bearer secret", "X-Custom": "value"},
            body={"key": "value"},
            response_status=200,
            response_time_ms=150.0,
            caller="test",
        )
        assert len(logger._audit_logs) == 1
        entry = logger._audit_logs[0]
        assert entry["method"] == "GET"
        assert "?***" in entry["url"]
        assert entry["headers"]["Authorization"] == "***REDACTED***"
        assert entry["headers"]["X-Custom"] == "value"

    def test_log_api_call_disabled(self):
        logger = ExternalAPIAuditLogger()
        logger.disable_audit()
        logger.log_api_call(method="GET", url="https://example.com")
        assert len(logger._audit_logs) == 0

    def test_log_api_call_with_error(self, caplog):
        logger = ExternalAPIAuditLogger()
        with caplog.at_level("ERROR", logger="core.external_api_audit"):
            logger.log_api_call(
                method="POST",
                url="https://example.com",
                response_status=500,
                error="timeout",
            )
        assert len(logger._audit_logs) == 1

    def test_query_audit_logs_by_method(self):
        logger = ExternalAPIAuditLogger()
        logger.log_api_call(method="GET", url="https://example.com/a")
        logger.log_api_call(method="POST", url="https://example.com/b")
        results = logger.query_audit_logs(method="get")
        assert len(results) == 1
        assert results[0]["method"] == "GET"

    def test_query_audit_logs_by_time_and_url(self):
        logger = ExternalAPIAuditLogger()
        logger.log_api_call(method="GET", url="https://example.com/target")
        start = datetime.now(timezone.utc) - timedelta(minutes=5)
        end = datetime.now(timezone.utc) + timedelta(minutes=5)
        results = logger.query_audit_logs(
            start_time=start,
            end_time=end,
            url_pattern="target",
            min_status=200,
            max_status=200,
        )
        assert len(results) == 1

    def test_get_audit_summary(self):
        logger = ExternalAPIAuditLogger()
        logger.log_api_call(method="GET", url="https://example.com/1", response_status=200)
        logger.log_api_call(
            method="POST",
            url="https://example.com/2",
            response_status=500,
            response_time_ms=1500,
        )
        summary = logger.get_audit_summary(hours=24)
        assert summary["total_calls"] == 2
        assert summary["failed_calls"] == 1
        assert summary["slow_calls"] == 1
        assert "GET" in summary["method_distribution"]

    def test_clear_audit_logs(self):
        logger = ExternalAPIAuditLogger()
        logger.log_api_call(method="GET", url="https://example.com")
        logger.clear_audit_logs()
        assert len(logger._audit_logs) == 0

    def test_clear_audit_logs_older_than(self):
        logger = ExternalAPIAuditLogger()
        old_entry = {
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "method": "GET",
            "url": "https://example.com",
        }
        new_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": "GET",
            "url": "https://example.com",
        }
        logger._audit_logs.append(old_entry)
        logger._audit_logs.append(new_entry)
        logger.clear_audit_logs(older_than_hours=1)
        assert len(logger._audit_logs) == 1

    def test_export_audit_logs_json(self):
        logger = ExternalAPIAuditLogger()
        logger.log_api_call(method="GET", url="https://example.com")
        exported = logger.export_audit_logs("json")
        assert '"method": "GET"' in exported

    def test_export_audit_logs_csv(self):
        logger = ExternalAPIAuditLogger()
        logger.log_api_call(method="GET", url="https://example.com", response_status=200)
        exported = logger.export_audit_logs("csv")
        assert "method" in exported
        assert "GET" in exported

    def test_export_audit_logs_unsupported_format(self):
        logger = ExternalAPIAuditLogger()
        with pytest.raises(ValueError):
            logger.export_audit_logs("xml")


class TestAuditDecorators:
    """测试审计装饰器"""

    @pytest.mark.asyncio
    async def test_audit_httpx_call_success(self):
        result = type("Response", (), {"status_code": 200})()
        func = AsyncMock(return_value=result)
        decorated = audit_httpx_call(func)
        out = await decorated(method="GET", url="https://example.com")
        assert out is result
        func.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_audit_httpx_call_failure(self):
        func = AsyncMock(side_effect=RuntimeError("boom"))
        decorated = audit_httpx_call(func)
        with pytest.raises(RuntimeError):
            await decorated(method="POST", url="https://example.com")

    @pytest.mark.asyncio
    async def test_audit_aiohttp_call_success(self):
        func = AsyncMock(return_value="ok")
        decorated = audit_aiohttp_call(func)
        out = await decorated()
        assert out == "ok"

    @pytest.mark.asyncio
    async def test_audit_aiohttp_call_failure(self):
        func = AsyncMock(side_effect=RuntimeError("boom"))
        decorated = audit_aiohttp_call(func)
        with pytest.raises(RuntimeError):
            await decorated()


class TestModuleFunctions:
    """测试模块级函数"""

    def test_get_audit_logger_singleton(self):
        logger1 = get_audit_logger()
        logger2 = get_audit_logger()
        assert logger1 is logger2

    def test_initialize_external_api_audit_enabled(self, monkeypatch):
        monkeypatch.setenv("EXTERNAL_API_AUDIT_ENABLED", "true")
        initialize_external_api_audit()
        logger = get_audit_logger()
        assert logger._audit_enabled is True

    def test_initialize_external_api_audit_disabled(self, monkeypatch):
        monkeypatch.setenv("EXTERNAL_API_AUDIT_ENABLED", "false")
        initialize_external_api_audit()
        logger = get_audit_logger()
        assert logger._audit_enabled is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
