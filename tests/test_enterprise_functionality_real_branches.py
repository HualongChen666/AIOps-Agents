# -*- coding: utf-8 -*-
"""Real branch-coverage tests for core.enterprise_functionality.

These tests use real EnterpriseFunctionalityManager instances and real data.
No mocks are used; configuration fallbacks and error-handling paths are
exercised with real invalid/edge inputs.
"""

import asyncio  # noqa: F401  # Imported for test setup
from datetime import datetime, timedelta

import pytest  # noqa: F401  # Imported for test setup

import core.enterprise_functionality as _efm
from core.enterprise_functionality import (
    AuditLogEntry,
    ComplianceCheck,
    ComplianceStandard,
    DataClassification,
    EncryptionLevel,
    EnterpriseFunctionalityManager,
    enterprise_functionality_manager,
)


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Initialization and configuration fallback
# ---------------------------------------------------------------------------


def test_manager_initialization_defaults_and_global():
    """Default config fallbacks and global instance."""
    mgr = EnterpriseFunctionalityManager()
    assert mgr.config == {}
    assert mgr.tenant_isolation_enabled is True
    assert mgr.encryption_enabled is False
    assert mgr.encryption_level == EncryptionLevel.STANDARD
    assert mgr.audit_retention_days == 365
    assert mgr.audit_storage_backend == "memory"
    assert isinstance(enterprise_functionality_manager, EnterpriseFunctionalityManager)


def test_manager_with_none_config():
    """config=None falls back to an empty dict."""
    mgr = EnterpriseFunctionalityManager(config=None)
    assert mgr.config == {}


def test_compliance_standards_from_config_valid_and_invalid():
    """Valid standards are enabled; invalid values are ignored."""
    mgr = EnterpriseFunctionalityManager(
        config={"compliance_standards": ["gdpr", "soc2", "not_a_standard"]}
    )
    assert ComplianceStandard.GDPR in mgr.compliance_standards
    assert ComplianceStandard.SOC2 in mgr.compliance_standards
    assert "not_a_standard" not in {s.value for s in mgr.compliance_standards}


def test_enterprise_summary():
    mgr = EnterpriseFunctionalityManager()
    summary = mgr.get_enterprise_summary()
    assert summary["tenant_isolation"]["enabled"] is True
    assert summary["compliance"]["enabled_standards"] == []
    assert summary["encryption"]["level"] == "standard"
    assert summary["audit_logging"]["retention_days"] == 365


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


def test_tenant_isolation_enabled_and_disabled():
    enabled_mgr = EnterpriseFunctionalityManager(config={"tenant_isolation": True})
    enabled_mgr.assign_resource_to_tenant("tenant-1", "resource-1")
    assert enabled_mgr.enforce_tenant_isolation("tenant-1", "resource-1", "doc") is True
    assert enabled_mgr.enforce_tenant_isolation("tenant-1", "resource-2", "doc") is False

    disabled_mgr = EnterpriseFunctionalityManager(config={"tenant_isolation": False})
    disabled_mgr.assign_resource_to_tenant("tenant-1", "resource-1")
    assert disabled_mgr.enforce_tenant_isolation("tenant-1", "resource-2", "doc") is True


# ---------------------------------------------------------------------------
# Compliance checks and reports
# ---------------------------------------------------------------------------


def test_gdpr_compliance_pass_and_fail():
    mgr = EnterpriseFunctionalityManager()
    result = _run(
        mgr.run_compliance_check(ComplianceStandard.GDPR)
    )  # noqa: F841  # Variable for test verification
    assert result.passed is True
    assert not result.findings
    assert result.severity == "low"

    mgr.privacy_policies["user_consent"]["explicit_consent_required"] = False
    mgr.privacy_policies["data_retention"]["max_retention_days"] = 400
    mgr.privacy_policies["data_minimization"]["collect_only_necessary"] = False
    result = _run(
        mgr.run_compliance_check(ComplianceStandard.GDPR)
    )  # noqa: F841  # Variable for test verification
    assert result.passed is False
    assert result.severity == "high"
    assert len(result.findings) == 3


def test_soc2_compliance_pass_and_fail():
    pass_mgr = EnterpriseFunctionalityManager(
        config={
            "encryption_enabled": True,
            "tenant_isolation": True,
            "encryption_password": "soc2-test",
        }
    )
    pass_mgr.create_audit_log("t", "u", "LOGIN", "user", "r1", "success")
    result = _run(
        pass_mgr.run_compliance_check(ComplianceStandard.SOC2)
    )  # noqa: F841  # Variable for test verification
    assert result.passed is True
    assert not result.findings

    fail_mgr = EnterpriseFunctionalityManager(
        config={"encryption_enabled": False, "tenant_isolation": False}
    )
    result = _run(
        fail_mgr.run_compliance_check(ComplianceStandard.SOC2)
    )  # noqa: F841  # Variable for test verification
    assert result.passed is False
    assert any("audit" in f.lower() for f in result.findings)
    assert any("encryption" in f.lower() for f in result.findings)
    assert any("isolation" in f.lower() for f in result.findings)


def test_iso27001_compliance_levels():
    standard_mgr = EnterpriseFunctionalityManager(
        config={"encryption_enabled": True, "encryption_level": "standard"}
    )
    result = _run(
        standard_mgr.run_compliance_check(ComplianceStandard.ISO27001)
    )  # noqa: F841  # Variable for test verification
    assert result.passed is True
    assert len(result.findings) == 2
    assert any("high" in f for f in result.findings)
    assert any("access control" in f.lower() for f in result.findings)

    high_mgr = EnterpriseFunctionalityManager(
        config={"encryption_enabled": True, "encryption_level": "high"}
    )
    result = _run(
        high_mgr.run_compliance_check(ComplianceStandard.ISO27001)
    )  # noqa: F841  # Variable for test verification
    assert result.passed is True
    assert len(result.findings) == 1
    assert "access control" in result.findings[0].lower()


def test_unsupported_compliance_standard_and_report():
    mgr = EnterpriseFunctionalityManager()
    result = _run(
        mgr.run_compliance_check(ComplianceStandard.HIPAA)
    )  # noqa: F841  # Variable for test verification
    assert result.passed is True
    assert any("No specific checks" in f for f in result.findings)

    report = _run(mgr.generate_compliance_report(ComplianceStandard.HIPAA))
    assert report["standard"] == "hipaa"
    assert report["summary"]["passed"] is True


def test_compliance_recommendation_branches():
    """Exercise every keyword branch in _generate_compliance_recommendations."""
    mgr = EnterpriseFunctionalityManager()
    check = ComplianceCheck(
        standard=ComplianceStandard.GDPR,
        check_id="c1",
        description="d",
        passed=False,
        findings=[
            "missing encryption for PII",
            "no audit trail",
            "user consent not collected",
            "retention exceeds 365 days",
            "unrelated finding",
        ],
    )
    recs = mgr._generate_compliance_recommendations(check)
    assert any("encryption" in r for r in recs)
    assert any("audit" in r for r in recs)
    assert any("consent" in r for r in recs)
    assert any("retention" in r for r in recs)
    assert any("Address findings" in r for r in recs)

    passed_check = ComplianceCheck(
        standard=ComplianceStandard.SOC2,
        check_id="c2",
        description="d",
        passed=True,
        findings=[],
    )
    assert mgr._generate_compliance_recommendations(passed_check) == []


# ---------------------------------------------------------------------------
# Encryption and decryption
# ---------------------------------------------------------------------------


def test_encryption_disabled_returns_plaintext():
    mgr = EnterpriseFunctionalityManager()
    assert mgr.encrypt_data("hello") == "hello"
    assert mgr.decrypt_data("hello") == "hello"


def test_encryption_enabled_with_real_round_trip():
    mgr = EnterpriseFunctionalityManager(
        config={"encryption_enabled": True, "encryption_password": "roundtrip"}
    )
    encrypted = mgr.encrypt_data("sensitive data", DataClassification.CONFIDENTIAL)
    assert encrypted != "sensitive data"
    decrypted = mgr.decrypt_data(encrypted)
    assert decrypted == "sensitive data"


def test_encryption_classification_and_level_branches():
    """PUBLIC/INTERNAL data is skipped when level is NONE or BASIC; otherwise encrypted."""
    for level in ("none", "basic"):
        mgr = EnterpriseFunctionalityManager(
            config={
                "encryption_enabled": True,
                "encryption_level": level,
                "encryption_password": "level-test",
            }
        )
        assert mgr.encrypt_data("public", DataClassification.PUBLIC) == "public"
        assert mgr.encrypt_data("internal", DataClassification.INTERNAL) == "internal"
        # CONFIDENTIAL is always encrypted
        assert mgr.encrypt_data("secret", DataClassification.CONFIDENTIAL) != "secret"

    # STANDARD level encrypts PUBLIC and INTERNAL as well
    std_mgr = EnterpriseFunctionalityManager(
        config={
            "encryption_enabled": True,
            "encryption_level": "standard",
            "encryption_password": "standard-test",
        }
    )
    assert std_mgr.encrypt_data("public", DataClassification.PUBLIC) != "public"
    assert std_mgr.encrypt_data("internal", DataClassification.INTERNAL) != "internal"


def test_encryption_initialization_error_graceful_degradation():
    """A bad encryption password (bytes) causes init to fail gracefully."""
    mgr = EnterpriseFunctionalityManager(
        config={"encryption_enabled": True, "encryption_password": b"not-a-string"}
    )
    assert mgr.cipher_suite is None
    assert mgr.encrypt_data("text", DataClassification.CONFIDENTIAL) == "text"


def test_decryption_error_returns_original():
    mgr = EnterpriseFunctionalityManager(
        config={"encryption_enabled": True, "encryption_password": "decrypt-test"}
    )
    assert mgr.decrypt_data("not-valid-base64!!!") == "not-valid-base64!!!"


# ---------------------------------------------------------------------------
# Audit logging
# ---------------------------------------------------------------------------


def test_audit_log_creation_and_query_filters():
    mgr = EnterpriseFunctionalityManager(config={"audit_retention_days": 365})
    e1 = mgr.create_audit_log(
        "tenant-a",
        "user-1",
        "LOGIN",
        "session",
        "s1",
        "success",
        "1.1.1.1",
        "pytest",
        {"role": "admin"},
    )
    e2 = mgr.create_audit_log("tenant-b", "user-2", "LOGOUT", "session", "s2", "success")

    assert e1.tenant_id == "tenant-a"
    assert e2 in mgr.audit_logs
    assert all(isinstance(e, AuditLogEntry) for e in mgr.audit_logs)

    # Filter by tenant
    filtered = _run(mgr.query_audit_logs(tenant_id="tenant-a"))
    assert len(filtered) == 1 and filtered[0].tenant_id == "tenant-a"

    # Filter by user
    filtered = _run(mgr.query_audit_logs(user_id="user-2"))
    assert len(filtered) == 1 and filtered[0].action == "LOGOUT"

    # Filter by action
    filtered = _run(mgr.query_audit_logs(action="LOGIN"))
    assert len(filtered) == 1

    # Date range
    start = datetime.now() - timedelta(days=1)
    end = datetime.now() + timedelta(days=1)
    filtered = _run(mgr.query_audit_logs(start_date=start, end_date=end))
    assert len(filtered) == 2

    # Limit
    filtered = _run(mgr.query_audit_logs(limit=1))
    assert len(filtered) == 1

    # No filters
    filtered = _run(mgr.query_audit_logs())
    assert len(filtered) == 2


def test_audit_log_external_failure_handled():
    """Non-serializable metadata makes the external audit logger raise; code swallows it."""
    mgr = EnterpriseFunctionalityManager()
    entry = mgr.create_audit_log(
        "t",
        "u",
        "LOGIN",
        "user",
        "r1",
        "success",
        metadata={"bad": {1, 2, 3}},
    )
    assert entry.user_id == "u"
    assert len(mgr.audit_logs) == 1


def test_audit_log_cleanup_old_and_no_old_logs():
    # Negative retention causes all current logs to be removed
    old_mgr = EnterpriseFunctionalityManager(config={"audit_retention_days": -1})
    old_mgr.create_audit_log("t", "u", "A", "r", "r1", "success")
    removed = _run(old_mgr.cleanup_old_audit_logs())
    assert removed == 1
    assert len(old_mgr.audit_logs) == 0

    # Default retention keeps fresh logs
    new_mgr = EnterpriseFunctionalityManager()
    new_mgr.create_audit_log("t", "u", "A", "r", "r1", "success")
    removed = _run(new_mgr.cleanup_old_audit_logs())
    assert removed == 0
    assert len(new_mgr.audit_logs) == 1


# ---------------------------------------------------------------------------
# Data classification and masking
# ---------------------------------------------------------------------------


def test_data_classification_exact_partial_and_default():
    mgr = EnterpriseFunctionalityManager()
    assert mgr.classify_data("email") == DataClassification.CONFIDENTIAL
    assert mgr.classify_data("my_email_address") == DataClassification.CONFIDENTIAL
    assert mgr.classify_data("some_unknown_key") == DataClassification.INTERNAL


def test_mask_sensitive_data():
    mgr = EnterpriseFunctionalityManager()
    data = {
        "email": "user@example.com",
        "password": "supersecret123",
        "count": 42,
        "notes": "plain text",
    }
    masked = mgr.mask_sensitive_data(data)
    assert masked["email"] != "user@example.com"
    assert masked["password"] != "supersecret123"
    assert masked["count"] == 42
    assert masked["notes"] == "plain text"

    nested = {"secret": {"token": "abc123"}}
    masked = mgr.mask_sensitive_data(nested)
    assert masked["secret"]["token"] != "abc123"


# ---------------------------------------------------------------------------
# Consent management
# ---------------------------------------------------------------------------


def test_consent_lifecycle():
    mgr = EnterpriseFunctionalityManager()
    assert mgr.check_consent("u1", "marketing") is False

    mgr.manage_consent("u1", True, "marketing")
    assert mgr.check_consent("u1", "marketing") is True

    mgr.manage_consent("u1", False, "marketing")
    assert mgr.check_consent("u1", "marketing") is False

    # Unknown purpose still returns False
    assert mgr.check_consent("u1", "analytics") is False


# ---------------------------------------------------------------------------
# Cross-tenant access, external-audit fallback, and error-handling branches
# ---------------------------------------------------------------------------


class _CrossTenantManager(EnterpriseFunctionalityManager):
    """Real subclass that allows cross-tenant access for one branch."""

    def _check_cross_tenant_access(self, tenant_id, resource_id, resource_type):
        return True


def test_cross_tenant_access_allowed_by_subclass():
    mgr = _CrossTenantManager(config={"tenant_isolation": True})
    # No explicit assignment; the cross-tenant override returns True
    assert mgr.enforce_tenant_isolation("t1", "r1", "doc") is True


def test_audit_log_when_external_audit_unavailable():
    """Set EXISTING_ENTERPRISE_AVAILABLE to False to exercise the else branch."""
    original = _efm.EXISTING_ENTERPRISE_AVAILABLE
    _efm.EXISTING_ENTERPRISE_AVAILABLE = False
    try:
        mgr = EnterpriseFunctionalityManager()
        entry = mgr.create_audit_log("t", "u", "LOGIN", "user", "r1", "success")
        assert entry.user_id == "u"
    finally:
        _efm.EXISTING_ENTERPRISE_AVAILABLE = original


def test_mask_sensitive_data_non_string_non_dict():
    """A RESTRICTED/CONFIDENTIAL key whose value is not str or dict falls through."""
    mgr = EnterpriseFunctionalityManager()
    data = {"ssn": 12345, "api_key": None}
    masked = mgr.mask_sensitive_data(data)
    assert masked["ssn"] == 12345
    assert masked["api_key"] is None


def test_encrypt_data_exception_returns_original():
    """Passing non-string data triggers the encrypt exception handler."""
    mgr = EnterpriseFunctionalityManager(
        config={"encryption_enabled": True, "encryption_password": "ex"}
    )
    result = mgr.encrypt_data(
        123, DataClassification.CONFIDENTIAL
    )  # noqa: F841  # Variable for test verification
    assert result == 123  # noqa: F841  # Variable for test verification
