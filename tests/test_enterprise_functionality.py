# -*- coding: utf-8 -*-
"""
Unit Tests for Enterprise Functionality
======================================

Comprehensive unit tests for the enterprise functionality module.
"""

from datetime import datetime, timedelta  # noqa: F401
from typing import Any, Dict  # noqa: F401

import pytest

try:
    from core.enterprise_functionality import (  # noqa: F401
        AuditLogEntry,
        ComplianceCheck,
        ComplianceStandard,
        DataClassification,
        EncryptionLevel,
        EnterpriseFunctionalityManager,
    )

    ENTERPRISE_AVAILABLE = True
except ImportError:
    ENTERPRISE_AVAILABLE = False


@pytest.mark.skipif(not ENTERPRISE_AVAILABLE, reason="Enterprise functionality not available")
class TestEnterpriseFunctionalityManager:
    """Test suite for EnterpriseFunctionalityManager"""

    @pytest.fixture
    def enterprise_manager(self):
        """Fixture for EnterpriseFunctionalityManager instance"""
        return EnterpriseFunctionalityManager()

    def test_initialization(self, enterprise_manager):
        """Test that EnterpriseFunctionalityManager initializes correctly"""
        assert enterprise_manager is not None
        assert hasattr(enterprise_manager, "tenant_isolation_enabled")
        assert hasattr(enterprise_manager, "compliance_standards")
        assert hasattr(enterprise_manager, "encryption_enabled")
        assert hasattr(enterprise_manager, "audit_logs")

    def test_enforce_tenant_isolation(self, enterprise_manager):
        """Test tenant isolation enforcement"""
        result = enterprise_manager.enforce_tenant_isolation(
            tenant_id="tenant_1", resource_id="resource_1", resource_type="data"
        )

        # Should return True if isolation is disabled or resource belongs to tenant
        assert isinstance(result, bool)

    def test_assign_resource_to_tenant(self, enterprise_manager):
        """Test assigning resource to tenant"""
        enterprise_manager.assign_resource_to_tenant("tenant_1", "resource_1")

        assert "resource_1" in enterprise_manager.tenant_data_isolation["tenant_1"]

    @pytest.mark.asyncio
    async def test_run_compliance_check(self, enterprise_manager):
        """Test compliance check"""
        result = await enterprise_manager.run_compliance_check(ComplianceStandard.GDPR)

        assert result is not None
        assert result.standard == ComplianceStandard.GDPR
        assert result.check_id is not None
        assert isinstance(result.passed, bool)
        assert isinstance(result.findings, list)

    @pytest.mark.asyncio
    async def test_generate_compliance_report(self, enterprise_manager):
        """Test compliance report generation"""
        report = await enterprise_manager.generate_compliance_report(ComplianceStandard.SOC2)

        assert report is not None
        assert "standard" in report
        assert "summary" in report
        assert "findings" in report
        assert "recommendations" in report

    def test_encrypt_data(self, enterprise_manager):
        """Test data encryption"""
        original_data = "sensitive information"

        encrypted = enterprise_manager.encrypt_data(original_data, DataClassification.CONFIDENTIAL)

        # If encryption is enabled, data should be different
        if enterprise_manager.encryption_enabled:
            assert encrypted != original_data
        else:
            # If encryption is disabled, should return original
            assert encrypted == original_data

    def test_decrypt_data(self, enterprise_manager):
        """Test data decryption"""
        original_data = "sensitive information"

        if enterprise_manager.encryption_enabled:
            encrypted = enterprise_manager.encrypt_data(
                original_data, DataClassification.CONFIDENTIAL
            )
            decrypted = enterprise_manager.decrypt_data(encrypted)
            assert decrypted == original_data

    def test_create_audit_log(self, enterprise_manager):
        """Test audit log creation"""
        log = enterprise_manager.create_audit_log(
            tenant_id="tenant_1",
            user_id="user_1",
            action="create",
            resource_type="alert",
            resource_id="alert_1",
            outcome="success",
            ip_address="192.168.1.1",
            user_agent="test_agent",
            data_classification=DataClassification.INTERNAL,
        )

        assert log is not None
        assert log.entry_id is not None
        assert log.tenant_id == "tenant_1"
        assert log.user_id == "user_1"
        assert log.action == "create"
        assert log.outcome == "success"

    @pytest.mark.asyncio
    async def test_query_audit_logs(self, enterprise_manager):
        """Test audit log querying"""
        # Create some audit logs first
        enterprise_manager.create_audit_log(
            tenant_id="tenant_1",
            user_id="user_1",
            action="create",
            resource_type="alert",
            resource_id="alert_1",
            outcome="success",
        )

        enterprise_manager.create_audit_log(
            tenant_id="tenant_1",
            user_id="user_1",
            action="delete",
            resource_type="alert",
            resource_id="alert_2",
            outcome="success",
        )

        # Query logs
        logs = await enterprise_manager.query_audit_logs(tenant_id="tenant_1", limit=10)

        assert logs is not None
        assert len(logs) > 0

    @pytest.mark.asyncio
    async def test_cleanup_old_audit_logs(self, enterprise_manager):
        """Test cleanup of old audit logs"""
        # Set a short retention period for testing
        enterprise_manager.audit_retention_days = 0

        # Create an audit log
        enterprise_manager.create_audit_log(
            tenant_id="tenant_1",
            user_id="user_1",
            action="test",
            resource_type="test",
            resource_id="test_1",
            outcome="success",
        )

        # Cleanup
        removed = await enterprise_manager.cleanup_old_audit_logs()

        assert isinstance(removed, int)
        assert removed >= 0

    def test_classify_data(self, enterprise_manager):
        """Test data classification"""
        classification = enterprise_manager.classify_data("email")

        assert classification == DataClassification.CONFIDENTIAL

        classification = enterprise_manager.classify_data("password")

        assert classification == DataClassification.RESTRICTED

    def test_mask_sensitive_data(self, enterprise_manager):
        """Test sensitive data masking"""
        data = {
            "username": "test_user",
            "password": "secret123",
            "email": "test@example.com",
            "name": "Test User",
        }

        masked = enterprise_manager.mask_sensitive_data(data)

        assert "username" in masked
        assert "password" in masked
        # Password should be masked
        assert masked["password"] != "secret123"
        # Username should not be masked
        assert masked["username"] == "test_user"

    def test_manage_consent(self, enterprise_manager):
        """Test consent management"""
        enterprise_manager.manage_consent(
            user_id="user_1", consent_given=True, consent_purpose="data_processing"
        )

        assert "user_1" in enterprise_manager.consent_management
        assert "data_processing" in enterprise_manager.consent_management["user_1"]
        assert (
            enterprise_manager.consent_management["user_1"]["data_processing"]["consent_given"]
            is True
        )

    def test_check_consent(self, enterprise_manager):
        """Test consent checking"""
        # First, set consent
        enterprise_manager.manage_consent(
            user_id="user_1", consent_given=True, consent_purpose="data_processing"
        )

        # Check consent
        has_consent = enterprise_manager.check_consent("user_1", "data_processing")

        assert has_consent is True

        # Check non-existent consent
        no_consent = enterprise_manager.check_consent("user_1", "marketing")
        assert no_consent is False

    def test_get_enterprise_summary(self, enterprise_manager):
        """Test getting enterprise summary"""
        summary = enterprise_manager.get_enterprise_summary()

        assert summary is not None
        assert "tenant_isolation" in summary
        assert "compliance" in summary
        assert "encryption" in summary
        assert "audit_logging" in summary
        assert "privacy" in summary


@pytest.mark.skipif(not ENTERPRISE_AVAILABLE, reason="Enterprise functionality not available")
class TestComplianceCheck:
    """Test suite for ComplianceCheck"""

    def test_compliance_check_creation(self):
        """Test ComplianceCheck creation"""
        check = ComplianceCheck(
            standard=ComplianceStandard.GDPR,
            check_id="check_1",
            description="GDPR compliance check",
            passed=True,
            findings=["All requirements met"],
        )

        assert check.standard == ComplianceStandard.GDPR
        assert check.check_id == "check_1"
        assert check.passed is True
        assert len(check.findings) == 1


@pytest.mark.skipif(not ENTERPRISE_AVAILABLE, reason="Enterprise functionality not available")
class TestAuditLogEntry:
    """Test suite for AuditLogEntry"""

    def test_audit_log_entry_creation(self):
        """Test AuditLogEntry creation"""
        log = AuditLogEntry(
            entry_id="log_1",
            tenant_id="tenant_1",
            user_id="user_1",
            action="create",
            resource_type="alert",
            resource_id="alert_1",
            outcome="success",
            ip_address="192.168.1.1",
            user_agent="test_agent",
        )

        assert log.entry_id == "log_1"
        assert log.tenant_id == "tenant_1"
        assert log.user_id == "user_1"
        assert log.action == "create"
        assert log.outcome == "success"
