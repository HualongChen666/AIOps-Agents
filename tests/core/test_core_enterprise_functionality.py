# -*- coding: utf-8 -*-
"""测试企业功能模块"""

import asyncio
from datetime import datetime, timedelta

import pytest

from core.enterprise_functionality import (
    AuditLogEntry,
    ComplianceStandard,
    DataClassification,
    EncryptionKey,
    EncryptionLevel,
    EnterpriseFunctionalityManager,
)


@pytest.fixture
def patched(monkeypatch):
    # 避免依赖外部审计/脱敏实现
    monkeypatch.setattr("core.enterprise_functionality.audit_log", lambda **kwargs: None)
    monkeypatch.setattr("core.enterprise_functionality.mask_sensitive", lambda x: "***")


@pytest.fixture
def manager(patched):
    return EnterpriseFunctionalityManager()


class TestEnumsAndDataclasses:
    def test_enum_values(self):
        assert ComplianceStandard.GDPR.value == "gdpr"
        assert EncryptionLevel.HIGH.value == "high"
        assert DataClassification.RESTRICTED.value == "restricted"

    def test_dataclasses(self):
        key = EncryptionKey(key_id="k1", algorithm="aes", key_version=1)
        assert key.status == "active"

        entry = AuditLogEntry(
            entry_id="e1",
            tenant_id="t1",
            user_id="u1",
            action="read",
            resource_type="file",
            resource_id="r1",
            outcome="success",
            ip_address="127.0.0.1",
            user_agent="test-agent",
        )
        assert entry.outcome == "success"


class TestInitialization:
    def test_default_init(self, manager):
        assert manager.tenant_isolation_enabled is True
        assert manager.encryption_enabled is False

    def test_config_init(self):
        m = EnterpriseFunctionalityManager(
            {
                "tenant_isolation": False,
                "encryption_enabled": True,
                "encryption_level": "high",
                "compliance_standards": ["soc2", "invalid"],
            }
        )
        assert m.tenant_isolation_enabled is False
        assert m.encryption_level == EncryptionLevel.HIGH
        assert ComplianceStandard.SOC2 in m.compliance_standards


class TestTenantIsolation:
    def test_disabled_allows_all(self, patched):
        m = EnterpriseFunctionalityManager({"tenant_isolation": False})
        assert m.enforce_tenant_isolation("t1", "r1", "file") is True

    def test_enabled_allows_assigned(self, manager):
        manager.assign_resource_to_tenant("t1", "r1")
        assert manager.enforce_tenant_isolation("t1", "r1", "file") is True
        assert manager.enforce_tenant_isolation("t2", "r1", "file") is False

    def test_cross_tenant_default(self, manager):
        assert manager._check_cross_tenant_access("t1", "r2", "file") is False


class TestCompliance:
    def test_run_gdpr_pass(self, manager):
        result = asyncio.run(manager.run_compliance_check(ComplianceStandard.GDPR))
        assert result.passed is True
        assert result.standard == ComplianceStandard.GDPR

    def test_run_gdpr_fail(self, manager):
        manager.privacy_policies["user_consent"]["explicit_consent_required"] = False
        result = asyncio.run(manager.run_compliance_check(ComplianceStandard.GDPR))
        assert result.passed is False
        assert any("consent" in f.lower() for f in result.findings)

    def test_run_soc2(self, patched):
        m = EnterpriseFunctionalityManager({"encryption_enabled": True})
        m.create_audit_log("t1", "u1", "read", "file", "r1", "success")
        result = asyncio.run(m.run_compliance_check(ComplianceStandard.SOC2))
        assert result.passed is True

    def test_run_iso27001(self):
        m = EnterpriseFunctionalityManager({"encryption_level": "high"})
        result = asyncio.run(m.run_compliance_check(ComplianceStandard.ISO27001))
        assert result.passed is True

    def test_generate_report(self, manager):
        report = asyncio.run(manager.generate_compliance_report(ComplianceStandard.GDPR))
        assert report["standard"] == "gdpr"
        assert "summary" in report
        assert isinstance(report["recommendations"], list)

    def test_recommendations(self, manager):
        from core.enterprise_functionality import ComplianceCheck

        check = ComplianceCheck(
            standard=ComplianceStandard.SOC2,
            check_id="c1",
            description="d",
            passed=False,
            findings=["audit logs missing", "encryption disabled"],
        )
        recs = manager._generate_compliance_recommendations(check)
        assert any("audit" in r.lower() for r in recs)
        assert any("encryption" in r.lower() for r in recs)


class TestEncryptionAndData:
    def test_encrypt_disabled(self, manager):
        data = "secret"
        assert manager.encrypt_data(data, DataClassification.RESTRICTED) == data

    def test_decrypt_disabled(self, manager):
        assert manager.decrypt_data("secret") == "secret"

    def test_classify_data(self, manager):
        assert manager.classify_data("email") == DataClassification.CONFIDENTIAL
        assert manager.classify_data("token") == DataClassification.RESTRICTED
        assert manager.classify_data("foo_marketing") == DataClassification.PUBLIC
        assert manager.classify_data("unknown") == DataClassification.INTERNAL

    def test_mask_sensitive_data(self, manager):
        data = {"email": "a@b.com", "name": "x", "api_key": {"token": "abc"}}
        masked = manager.mask_sensitive_data(data)
        assert masked["email"] == "***"
        assert masked["name"] == "x"
        assert masked["api_key"]["token"] == "***"


class TestAuditAndConsent:
    def test_create_audit_log(self, manager):
        entry = manager.create_audit_log("t1", "u1", "read", "file", "r1", "success")
        assert entry.tenant_id == "t1"
        assert entry.action == "read"

    def test_query_audit_logs(self, manager):
        manager.create_audit_log("t1", "u1", "read", "file", "r1", "success")
        manager.create_audit_log("t2", "u2", "write", "db", "r2", "success")

        results = asyncio.run(manager.query_audit_logs(tenant_id="t1"))
        assert len(results) == 1

        results = asyncio.run(manager.query_audit_logs(user_id="u2", action="write"))
        assert len(results) == 1

    def test_cleanup_old_audit_logs(self, manager):
        old = datetime.now() - timedelta(days=1000)
        manager.audit_logs.append(
            AuditLogEntry(
                entry_id="old",
                tenant_id="t1",
                user_id="u1",
                action="read",
                resource_type="file",
                resource_id="r1",
                outcome="success",
                ip_address="127.0.0.1",
                user_agent="test-agent",
                timestamp=old,
            )
        )
        removed = asyncio.run(manager.cleanup_old_audit_logs())
        assert removed == 1

    def test_consent(self, manager):
        manager.manage_consent("u1", True, "marketing")
        assert manager.check_consent("u1", "marketing") is True
        assert manager.check_consent("u1", "analytics") is False
        assert manager.check_consent("u2", "marketing") is False


class TestSummary:
    def test_get_enterprise_summary(self, manager):
        manager.assign_resource_to_tenant("t1", "r1")
        manager.create_audit_log("t1", "u1", "read", "file", "r1", "success")
        summary = manager.get_enterprise_summary()
        assert summary["tenant_isolation"]["tenants_count"] == 1
        assert summary["tenant_isolation"]["resources_isolated"] == 1
        assert summary["audit_logging"]["total_logs"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
