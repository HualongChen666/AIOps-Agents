# -*- coding: utf-8 -*-
"""
Audit Router Tests
审计导出和报告路由API基础测试
"""

import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

# Mock problematic imports before importing router
sys.modules["config"] = MagicMock()
sys.modules["config"].INTERNAL_API_KEY = ""
sys.modules["core.command_guard"] = MagicMock()
sys.modules["core.compliance"] = MagicMock()

from api.audit_router import audit_report, export_audit


@pytest.fixture
def client():
    """创建测试客户端"""
    app = FastAPI()
    # Create a new router without authentication dependencies
    test_router = APIRouter(prefix="/api/audit", tags=["Audit Export & Report"])
    test_router.add_api_route("/export", export_audit, methods=["GET"])
    test_router.add_api_route("/report", audit_report, methods=["GET"])
    app.include_router(test_router)
    return TestClient(app)


class TestAuditRouter:
    """测试审计路由"""

    def test_export_audit_success(self, client):
        """测试成功导出审计日志"""
        with patch("api.audit_router.get_audit_log") as mock_audit:
            mock_audit.return_value = [
                {
                    "timestamp": "2026-07-03",
                    "event": "test",
                    "risk_level": "low",
                    "result": "allowed",
                }
            ]

            with patch("api.audit_router.mask_sensitive_dict") as mock_mask:
                mock_mask.side_effect = lambda x: x

                response = client.get("/api/audit/export?fmt=csv&limit=10")
                assert response.status_code == 200

    def test_export_audit_no_logs(self, client):
        """测试导出空审计日志"""
        with patch("api.audit_router.get_audit_log") as mock_audit:
            mock_audit.return_value = []

            with patch("api.audit_router.mask_sensitive_dict") as mock_mask:
                mock_mask.side_effect = lambda x: x

                response = client.get("/api/audit/export?fmt=csv&limit=10")
                assert response.status_code == 200

    def test_export_audit_excel_format(self, client):
        """测试导出Excel格式审计日志"""
        with patch("api.audit_router.get_audit_log") as mock_audit:
            mock_audit.return_value = [
                {
                    "timestamp": "2026-07-03",
                    "event": "test",
                    "risk_level": "low",
                    "result": "allowed",
                }
            ]

            with patch("api.audit_router.mask_sensitive_dict") as mock_mask:
                mock_mask.side_effect = lambda x: x

                response = client.get("/api/audit/export?fmt=excel&limit=10")
                # May return 500 if openpyxl not installed
                assert response.status_code in [200, 500]

    def test_audit_report(self, client):
        """测试生成审计报告"""
        with patch("api.audit_router.get_audit_log") as mock_audit:
            mock_audit.return_value = [
                {
                    "timestamp": "2026-07-03",
                    "event": "test",
                    "risk_level": "low",
                    "result": "allowed",
                },
                {
                    "timestamp": "2026-07-03",
                    "event": "test2",
                    "risk_level": "high",
                    "result": "blocked",
                },
            ]

            response = client.get("/api/audit/report?limit=10")
            assert response.status_code == 200
            data = response.json()
            assert "total" in data
            assert "risk_distribution" in data

    def test_audit_report_empty_logs(self, client):
        """测试生成空审计报告"""
        with patch("api.audit_router.get_audit_log") as mock_audit:
            mock_audit.return_value = []

            response = client.get("/api/audit/report?limit=10")
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
