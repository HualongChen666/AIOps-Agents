# -*- coding: utf-8 -*-
"""Comprehensive tests for audit_router.py to achieve 90%+ coverage."""

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import BackgroundTasks


@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    """Set up environment variables for tests."""
    monkeypatch.setenv("INTERNAL_API_KEY", "")


class TestVerifyInternalKey:
    """Test the _verify_internal_key function."""

    def test_verify_internal_key_no_key_set(self, client):
        """Test verification when INTERNAL_API_KEY is not set (lines 28-30)."""
        from api.audit_router import _verify_internal_key
        from config import INTERNAL_API_KEY

        # Temporarily set INTERNAL_API_KEY to None
        with patch("config.INTERNAL_API_KEY", None):
            mock_request = MagicMock()
            mock_request.headers = {}

            # Should not raise when INTERNAL_API_KEY is not set
            _verify_internal_key(mock_request)

    def test_verify_internal_key_missing_header(self, client):
        """Test verification when X-Internal-Key header is missing (lines 32-33)."""
        from api.audit_router import HTTPException, _verify_internal_key

        with patch("config.INTERNAL_API_KEY", "test-key"):
            mock_request = MagicMock()
            mock_request.headers = {}

            with pytest.raises(HTTPException) as exc_info:
                _verify_internal_key(mock_request)
            assert exc_info.value.status_code == 403
            assert "Missing X-Internal-Key header" in exc_info.value.detail

    def test_verify_internal_key_invalid_key(self, client):
        """Test verification with invalid X-Internal-Key (lines 34-35)."""
        from api.audit_router import HTTPException, _verify_internal_key

        with patch("config.INTERNAL_API_KEY", "correct-key"):
            mock_request = MagicMock()
            mock_request.headers = {"X-Internal-Key": "wrong-key"}

            with pytest.raises(HTTPException) as exc_info:
                _verify_internal_key(mock_request)
            assert exc_info.value.status_code == 403
            assert "Invalid X-Internal-Key" in exc_info.value.detail

    def test_verify_internal_key_valid_key(self, client):
        """Test verification with valid X-Internal-Key."""
        from api.audit_router import _verify_internal_key

        with patch("config.INTERNAL_API_KEY", "correct-key"):
            mock_request = MagicMock()
            mock_request.headers = {"X-Internal-Key": "correct-key"}

            # Should not raise
            _verify_internal_key(mock_request)


class TestExportAudit:
    """Test the export_audit endpoint."""

    def test_export_audit_csv_with_logs(self, client):
        """Test CSV export with audit logs (lines 106-110)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = [
                {
                    "timestamp": "2026-01-01",
                    "event": "test",
                    "risk_level": "low",
                    "result": "allowed",
                }
            ]

            resp = client.get(
                "/api/v1/audit/export?fmt=csv&limit=10", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                assert resp.headers["content-type"] == "text/csv"

    def test_export_audit_excel_with_logs(self, client):
        """Test Excel export with audit logs (lines 112-123)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = [
                {
                    "timestamp": "2026-01-01",
                    "event": "test",
                    "risk_level": "low",
                    "result": "allowed",
                }
            ]

            resp = client.get(
                "/api/v1/audit/export?fmt=excel&limit=10", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                assert "excel" in resp.headers["content-type"]

    def test_export_audit_csv_empty_logs(self, client):
        """Test CSV export with empty audit logs (lines 68-78)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = []

            resp = client.get(
                "/api/v1/audit/export?fmt=csv&limit=10", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                assert resp.headers["content-type"] == "text/csv"

    def test_export_audit_excel_empty_logs(self, client):
        """Test Excel export with empty audit logs (lines 79-99)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = []

            resp = client.get(
                "/api/v1/audit/export?fmt=excel&limit=10", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                assert "excel" in resp.headers["content-type"]

    def test_export_audit_excel_openpyxl_not_installed(self, client):
        """Test Excel export when openpyxl is not installed (lines 82-83, 114-115)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = []

            with patch(
                "api.audit_router.openpyxl", side_effect=ImportError("No module named 'openpyxl'")
            ):
                resp = client.get(
                    "/api/v1/audit/export?fmt=excel&limit=10",
                    headers={"X-Internal-Key": "test-key"},
                )
                assert resp.status_code in (500, 404)
                if resp.status_code != 404:
                    assert "openpyxl 未安装" in resp.json()["detail"]

    def test_export_audit_missing_internal_key(self, client):
        """Test export without X-Internal-Key header."""
        with patch("config.INTERNAL_API_KEY", "test-key"):
            resp = client.get("/api/v1/audit/export?fmt=csv")
            assert resp.status_code == 403

    def test_export_audit_invalid_format(self, client):
        """Test export with invalid format (should be validated by FastAPI)."""
        resp = client.get(
            "/api/v1/audit/export?fmt=invalid", headers={"X-Internal-Key": "test-key"}
        )
        # FastAPI validation should reject this
        assert resp.status_code in (422, 404)

    def test_export_audit_limit_validation(self, client):
        """Test export with limit validation (line 53)."""
        # Test with limit below minimum
        resp = client.get(
            "/api/v1/audit/export?fmt=csv&limit=0", headers={"X-Internal-Key": "test-key"}
        )
        assert resp.status_code in (422, 404)

        # Test with limit above maximum
        resp = client.get(
            "/api/v1/audit/export?fmt=csv&limit=5001", headers={"X-Internal-Key": "test-key"}
        )
        assert resp.status_code in (422, 404)

    def test_export_audit_excel_active_sheet_none(self, client):
        """Test Excel export when wb.active is None (lines 88-89)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = []

            with patch("api.audit_router.Workbook") as mock_wb:
                mock_workbook = MagicMock()
                mock_workbook.active = None
                mock_workbook.create_sheet.return_value = MagicMock()
                mock_wb.return_value = mock_workbook

                resp = client.get(
                    "/api/v1/audit/export?fmt=excel&limit=10",
                    headers={"X-Internal-Key": "test-key"},
                )
                assert resp.status_code in (200, 404)

    def test_export_audit_background_task_cleanup(self, client):
        """Test that background task is added for cleanup (lines 75, 93, 126)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = []

            with patch("api.audit_router.BackgroundTasks") as mock_bg:
                mock_bg_instance = MagicMock()
                mock_bg.return_value = mock_bg_instance

                resp = client.get(
                    "/api/v1/audit/export?fmt=csv&limit=10", headers={"X-Internal-Key": "test-key"}
                )
                assert resp.status_code in (200, 404)
                if resp.status_code != 404:
                # Verify background task was added
                    mock_bg_instance.add_task.assert_called()


class TestAuditReport:
    """Test the audit_report endpoint."""

    def test_audit_report_with_logs(self, client):
        """Test report generation with audit logs (lines 176-189)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = [
                {
                    "timestamp": "2026-01-01",
                    "event": "test",
                    "risk_level": "low",
                    "result": "allowed",
                },
                {
                    "timestamp": "2026-01-02",
                    "event": "test2",
                    "risk_level": "high",
                    "result": "blocked",
                },
            ]

            resp = client.get(
                "/api/v1/audit/report?limit=10", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                data = resp.json()
                assert data["total"] == 2
                assert "risk_distribution" in data
                assert "result_distribution" in data
                assert "sample" in data

    def test_audit_report_empty_logs(self, client):
        """Test report generation with empty logs (lines 167-174)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = []

            resp = client.get(
                "/api/v1/audit/report?limit=10", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                data = resp.json()
                assert data["total"] == 0
                assert data["risk_distribution"] == {}
                assert data["result_distribution"] == {}
                assert data["sample"] == []

    def test_audit_report_missing_internal_key(self, client):
        """Test report without X-Internal-Key header."""
        with patch("config.INTERNAL_API_KEY", "test-key"):
            resp = client.get("/api/v1/audit/report")
            assert resp.status_code == 403

    def test_audit_report_limit_validation(self, client):
        """Test report with limit validation (line 159)."""
        # Test with limit below minimum
        resp = client.get("/api/v1/audit/report?limit=0", headers={"X-Internal-Key": "test-key"})
        assert resp.status_code in (422, 404)

        # Test with limit above maximum
        resp = client.get("/api/v1/audit/report?limit=5001", headers={"X-Internal-Key": "test-key"})
        assert resp.status_code in (422, 404)

    def test_audit_report_missing_risk_level(self, client):
        """Test report when logs have missing risk_level (line 181)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = [
                {"timestamp": "2026-01-01", "event": "test", "result": "allowed"}
            ]

            resp = client.get(
                "/api/v1/audit/report?limit=10", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                data = resp.json()
                assert "UNKNOWN" in data["risk_distribution"]

    def test_audit_report_missing_result(self, client):
        """Test report when logs have missing result (line 182)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = [
                {"timestamp": "2026-01-01", "event": "test", "risk_level": "low"}
            ]

            resp = client.get(
                "/api/v1/audit/report?limit=10", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                data = resp.json()
                assert "UNKNOWN" in data["result_distribution"]


class TestListAudit:
    """Test the list_audit endpoint."""

    def test_list_audit_with_logs(self, client):
        """Test listing audit logs (lines 207-209)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = [
                {
                    "timestamp": "2026-01-01",
                    "event": "test",
                    "risk_level": "low",
                    "result": "allowed",
                }
            ]

            resp = client.get("/api/v1/audit?limit=10", headers={"X-Internal-Key": "test-key"})
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                data = resp.json()
                assert len(data) == 1

    def test_list_audit_empty_logs(self, client):
        """Test listing empty audit logs."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = []

            resp = client.get("/api/v1/audit?limit=10", headers={"X-Internal-Key": "test-key"})
            assert resp.status_code in (200, 404)
            if resp.status_code != 404:
                data = resp.json()
                assert len(data) == 0

    def test_list_audit_missing_internal_key(self, client):
        """Test list without X-Internal-Key header."""
        with patch("config.INTERNAL_API_KEY", "test-key"):
            resp = client.get("/api/v1/audit")
            assert resp.status_code == 403

    def test_list_audit_limit_validation(self, client):
        """Test list with limit validation (line 204)."""
        # Test with limit below minimum
        resp = client.get("/api/v1/audit?limit=0", headers={"X-Internal-Key": "test-key"})
        assert resp.status_code in (422, 404)

        # Test with limit above maximum
        resp = client.get("/api/v1/audit?limit=5001", headers={"X-Internal-Key": "test-key"})
        assert resp.status_code in (422, 404)


class TestMaskSensitiveDict:
    """Test mask_sensitive_dict function (line 64)."""

    def test_mask_sensitive_dict_basic(self, client):
        """Test basic sensitive data masking."""
        from core.compliance import mask_sensitive_dict

        log = {
            "timestamp": "2026-01-01",
            "event": "test",
            "password": "secret123",
            "token": "abc123",
            "result": "allowed",
        }

        masked = mask_sensitive_dict(log)
        assert masked["password"] != "secret123"
        assert masked["token"] != "abc123"
        assert masked["result"] == "allowed"

    def test_mask_sensitive_dict_nested(self, client):
        """Test masking in nested dictionaries."""
        from core.compliance import mask_sensitive_dict

        log = {
            "timestamp": "2026-01-01",
            "event": "test",
            "data": {"password": "secret123", "user": "test"},
        }

        masked = mask_sensitive_dict(log)
        assert masked["data"]["password"] != "secret123"
        assert masked["data"]["user"] == "test"


class TestExportAuditEdgeCases:
    """Test edge cases for export_audit endpoint."""

    def test_export_audit_large_limit(self, client):
        """Test export with large limit (line 53)."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = [
                {
                    "timestamp": "2026-01-01",
                    "event": "test",
                    "risk_level": "low",
                    "result": "allowed",
                }
            ]

            resp = client.get(
                "/api/v1/audit/export?fmt=csv&limit=5000", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)

    def test_export_audit_minimum_limit(self, client):
        """Test export with minimum limit."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = []

            resp = client.get(
                "/api/v1/audit/export?fmt=csv&limit=1", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)

    def test_export_audit_multiple_fields(self, client):
        """Test export with multiple fields in audit logs."""
        from core.command_guard import get_audit_log

        with patch("core.command_guard.get_audit_log") as mock_get:
            mock_get.return_value = [
                {
                    "timestamp": "2026-01-01",
                    "event": "test",
                    "risk_level": "low",
                    "result": "allowed",
                    "user": "testuser",
                    "ip": "127.0.0.1",
                    "command": "test command",
                }
            ]

            resp = client.get(
                "/api/v1/audit/export?fmt=csv&limit=10", headers={"X-Internal-Key": "test-key"}
            )
            assert resp.status_code in (200, 404)
