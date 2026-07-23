# -*- coding: utf-8 -*-
"""
Enterprise Router Tests
企业功能路由API基础测试
"""

import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api.enterprise_router as enterprise_router

# Mock problematic imports before importing router
sys.modules["core.enterprise_functionality"] = MagicMock()
sys.modules["core.enterprise_functionality"].ENTERPRISE_AVAILABLE = True
sys.modules["core.enterprise_functionality"].ComplianceStandard = MagicMock()
sys.modules["core.enterprise_functionality"].DataClassification = MagicMock()
sys.modules["core.enterprise_functionality"].enterprise_functionality_manager = MagicMock()


@pytest.fixture
def client():
    """创建测试客户端（绕过认证）"""
    app = FastAPI()
    app.include_router(enterprise_router.router)
    return TestClient(app)


class TestEnterpriseRouter:
    """测试企业功能路由"""

    def test_check_tenant_isolation(self, client):
        """测试检查租户隔离"""
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.enforce_tenant_isolation.return_value = True

            response = client.post(
                "/api/v1/enterprise/tenant/isolation/check",
                json={
                    "tenant_id": "tenant-001",
                    "resource_id": "resource-001",
                    "resource_type": "database",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_assign_resource_to_tenant(self, client):
        """测试分配资源到租户"""
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.assign_resource_to_tenant.return_value = None

            response = client.post(
                "/api/v1/enterprise/tenant/resource/assign",
                params={"tenant_id": "tenant-001", "resource_id": "resource-001"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_run_compliance_check(self, client):
        """测试合规性检查"""
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.ComplianceStandard") as mock_standard,
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_standard.return_value = MagicMock(value="GDPR")
            mock_check = Mock()
            mock_check.standard.value = "GDPR"
            mock_check.check_id = "check-001"
            mock_check.description = "GDPR合规检查"
            mock_check.passed = True
            mock_check.findings = []
            mock_check.severity = "low"
            mock_check.checked_at.isoformat.return_value = "2026-07-03T10:00:00Z"

            async def mock_run_check(standard):
                return mock_check

            mock_manager.run_compliance_check = mock_run_check

            response = client.post("/api/v1/enterprise/compliance/check", json={"standard": "GDPR"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_encrypt_data(self, client):
        """测试加密数据"""
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.DataClassification") as mock_classification,
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_classification.return_value = MagicMock(value="confidential")
            mock_manager.encrypt_data.return_value = "encrypted_string"

            response = client.post(
                "/api/v1/enterprise/encryption/encrypt",
                json={"data": "test data", "classification": "confidential"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_create_audit_log(self, client):
        """测试创建审计日志"""
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.DataClassification") as mock_classification,
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_classification.return_value = MagicMock(value="internal")
            mock_audit = Mock()
            mock_audit.entry_id = "audit-001"
            mock_audit.tenant_id = "tenant-001"
            mock_audit.user_id = "user-001"
            mock_audit.action = "read"
            mock_audit.resource_type = "database"
            mock_audit.resource_id = "resource-001"
            mock_audit.outcome = "success"
            mock_audit.timestamp.isoformat.return_value = "2026-07-03T10:00:00Z"
            mock_audit.data_classification.value = "internal"
            mock_manager.create_audit_log.return_value = mock_audit

            response = client.post(
                "/api/v1/enterprise/audit/log",
                json={
                    "tenant_id": "tenant-001",
                    "user_id": "user-001",
                    "action": "read",
                    "resource_type": "database",
                    "resource_id": "resource-001",
                    "outcome": "success",
                    "data_classification": "internal",
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_get_enterprise_summary(self, client):
        """测试获取企业功能摘要"""
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.get_enterprise_summary.return_value = {
                "tenant_count": 10,
                "compliance_checks": 100,
                "encryption_enabled": True,
            }

            response = client.get("/api/v1/enterprise/summary")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"


class TestEnterpriseRouterAdditional:
    """补充企业功能路由测试"""

    def test_generate_compliance_report(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.ComplianceStandard") as mock_standard,
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_standard.return_value = MagicMock(value="GDPR")
            mock_manager.generate_compliance_report = AsyncMock(
                return_value={"standard": "GDPR", "summary": "compliant"}
            )

            response = client.post(
                "/api/v1/enterprise/compliance/report", json={"standard": "GDPR"}
            )
            assert response.status_code == 200

    def test_decrypt_data(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.decrypt_data.return_value = "original_string"

            response = client.post(
                "/api/v1/enterprise/encryption/decrypt",
                params={"encrypted_data": "encrypted_string"},
            )
            assert response.status_code == 200

    def test_query_audit_logs(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_log = SimpleNamespace(
                entry_id="audit-001",
                tenant_id="tenant-001",
                user_id="user-001",
                action="read",
                resource_type="database",
                resource_id="resource-001",
                outcome="success",
                ip_address="127.0.0.1",
                user_agent="test",
                timestamp=datetime(2026, 7, 4, 0, 0, 0),
                data_classification=SimpleNamespace(value="internal"),
                metadata={},
            )
            mock_manager.query_audit_logs = AsyncMock(return_value=[mock_log])

            response = client.get("/api/v1/enterprise/audit/logs")
            assert response.status_code == 200

    def test_query_audit_logs_invalid_date(self, client):
        with patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True):
            response = client.get("/api/v1/enterprise/audit/logs?start_date=invalid")
            assert response.status_code == 400

    def test_cleanup_old_audit_logs(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.audit_retention_days = 90
            mock_manager.cleanup_old_audit_logs = AsyncMock(return_value=100)

            response = client.post("/api/v1/enterprise/audit/cleanup")
            assert response.status_code == 200

    def test_manage_consent(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.manage_consent.return_value = None

            response = client.post(
                "/api/v1/enterprise/privacy/consent",
                json={
                    "user_id": "user-001",
                    "consent_given": True,
                    "consent_purpose": "analytics",
                },
            )
            assert response.status_code == 200

    def test_check_consent(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.check_consent.return_value = True

            response = client.get(
                "/api/v1/enterprise/privacy/consent/user-001",
                params={"consent_purpose": "analytics"},
            )
            assert response.status_code == 200

    def test_mask_sensitive_data(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.mask_sensitive_data.return_value = {"email": "***@***.com"}

            response = client.post(
                "/api/v1/enterprise/privacy/mask",
                json={"email": "user@example.com"},
            )
            assert response.status_code == 200

    def test_get_compliance_standards(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.ComplianceStandard") as mock_standard,
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_standard.__iter__ = lambda self: iter(
                [SimpleNamespace(value="GDPR"), SimpleNamespace(value="HIPAA")]
            )
            mock_manager.compliance_standards = [SimpleNamespace(value="GDPR")]

            response = client.get("/api/v1/enterprise/compliance/standards")
            assert response.status_code == 200

    def test_get_encryption_status(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.encryption_enabled = True
            mock_manager.encryption_level = SimpleNamespace(value="AES-256")
            mock_manager.encryption_keys = ["k1"]
            mock_manager.cipher_suite = object()

            response = client.get("/api/v1/enterprise/encryption/status")
            assert response.status_code == 200

    def test_get_data_classification_rules(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.data_classification_rules = {
                "email": SimpleNamespace(value="confidential")
            }

            response = client.get("/api/v1/enterprise/data/classification/rules")
            assert response.status_code == 200

    def test_classify_data(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.enterprise_functionality_manager") as mock_manager,
        ):
            mock_manager.classify_data.return_value = SimpleNamespace(value="confidential")

            response = client.post(
                "/api/v1/enterprise/data/classify",
                params={"data_key": "email"},
            )
            assert response.status_code == 200

    def test_compliance_check_invalid_standard(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.ComplianceStandard") as mock_standard,
        ):
            mock_standard.side_effect = ValueError("invalid")

            response = client.post(
                "/api/v1/enterprise/compliance/check", json={"standard": "invalid"}
            )
            assert response.status_code == 400

    def test_encrypt_data_invalid_classification(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.DataClassification") as mock_classification,
        ):
            mock_classification.side_effect = ValueError("invalid")

            response = client.post(
                "/api/v1/enterprise/encryption/encrypt",
                json={"data": "test", "classification": "invalid"},
            )
            assert response.status_code == 400

    def test_create_audit_log_invalid_classification(self, client):
        with (
            patch("api.enterprise_router.ENTERPRISE_AVAILABLE", True),
            patch("api.enterprise_router.DataClassification") as mock_classification,
        ):
            mock_classification.side_effect = ValueError("invalid")

            response = client.post(
                "/api/v1/enterprise/audit/log",
                json={
                    "tenant_id": "tenant-001",
                    "user_id": "user-001",
                    "action": "read",
                    "resource_type": "database",
                    "resource_id": "resource-001",
                    "outcome": "success",
                    "data_classification": "invalid",
                },
            )
            assert response.status_code == 400

    def test_endpoint_unavailable(self, client):
        with patch("api.enterprise_router.ENTERPRISE_AVAILABLE", False):
            response = client.get("/api/v1/enterprise/summary")
            assert response.status_code == 503


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
