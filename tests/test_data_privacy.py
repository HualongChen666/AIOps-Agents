# -*- coding: utf-8 -*-
# tests/test_data_privacy.py
# 数据隐私保护单元测试
from datetime import datetime, timedelta

import pytest

from core.data_privacy import (  # noqa: F401
    ConsentRecord,
    DataPrivacyConfig,
    DataRetentionPolicy,
    PrivacyAuditLog,
    anonymize_credit_card,
    anonymize_dict,
    anonymize_email,
    anonymize_ip,
    anonymize_phone,
    anonymize_ssn,
    anonymize_text,
    configure_privacy,
    contains_pii,
    detect_pii,
    get_privacy_audit_logs,
    get_privacy_config,
    get_privacy_stats,
    get_retention_policy,
    get_user_consents,
    has_consent,
    hash_pii,
    log_privacy_event,
    record_consent,
    set_retention_policy,
)


class TestPrivacyConfiguration:
    """隐私配置测试"""

    def test_configure_privacy(self):
        """测试配置隐私设置"""
        config = DataPrivacyConfig(
            anonymization_enabled=True,
            pii_detection_enabled=True,
        )
        configure_privacy(config)

        retrieved_config = get_privacy_config()
        assert retrieved_config.anonymization_enabled is True
        assert retrieved_config.pii_detection_enabled is True

    def test_get_privacy_config(self):
        """测试获取隐私配置"""
        config = get_privacy_config()
        assert config is not None
        assert isinstance(config, DataPrivacyConfig)


class TestPIIDetection:
    """PII检测测试"""

    def test_detect_pii_email(self):
        """测试检测邮箱"""
        text = "Contact us at support@example.com"
        detected = detect_pii(text)

        assert "email" in detected
        assert "support@example.com" in detected["email"]

    def test_detect_pii_phone(self):
        """测试检测电话号码"""
        text = "Call us at 123-456-7890"
        detected = detect_pii(text)

        assert "phone" in detected

    def test_detect_pii_multiple(self):
        """测试检测多种PII"""
        text = "Email: test@example.com, Phone: 123-456-7890"
        detected = detect_pii(text)

        assert "email" in detected
        assert "phone" in detected

    def test_contains_pii(self):
        """测试检查是否包含PII"""
        text = "Contact support@example.com"
        assert contains_pii(text) is True

        text = "No PII here"
        assert contains_pii(text) is False


class TestAnonymization:
    """匿名化测试"""

    def test_anonymize_email(self):
        """测试匿名化邮箱"""
        email = "john.doe@example.com"
        anonymized = anonymize_email(email)

        assert "@" in anonymized
        assert "*" in anonymized
        assert anonymized != email

    def test_anonymize_phone(self):
        """测试匿名化电话号码"""
        phone = "123-456-7890"
        anonymized = anonymize_phone(phone)

        assert "*" in anonymized
        assert anonymized != phone

    def test_anonymize_ssn(self):
        """测试匿名化SSN"""
        ssn = "123-45-6789"
        anonymized = anonymize_ssn(ssn)

        assert "***-**-" in anonymized
        assert "6789" in anonymized

    def test_anonymize_credit_card(self):
        """测试匿名化信用卡号"""
        card = "1234-5678-9012-3456"
        anonymized = anonymize_credit_card(card)

        assert "*" in anonymized
        assert "3456" in anonymized

    def test_anonymize_ip(self):
        """测试匿名化IP地址"""
        ip = "192.168.1.100"
        anonymized = anonymize_ip(ip)

        assert "*.*" in anonymized

    def test_anonymize_text(self):
        """测试匿名化文本中的PII"""
        text = "Email: john@example.com, Phone: 123-456-7890"
        anonymized = anonymize_text(text)

        assert "*" in anonymized
        assert anonymized != text

    def test_hash_pii(self):
        """测试哈希PII数据"""
        data = "sensitive_data"
        hashed = hash_pii(data)

        assert hashed != data
        assert len(hashed) == 64  # SHA256 hash length


class TestDictAnonymization:
    """字典匿名化测试"""

    def test_anonymize_dict(self):
        """测试匿名化字典"""
        data = {
            "name": "John Doe",
            "email": "john@example.com",
            "phone": "123-456-7890",
            "age": 30,
        }

        anonymized = anonymize_dict(data)

        assert "*" in anonymized["email"]
        assert "*" in anonymized["phone"]
        assert anonymized["age"] == 30  # Non-string unchanged


class TestDataRetention:
    """数据保留策略测试"""

    def test_retention_policy_should_retain(self):
        """测试数据保留策略"""
        policy = DataRetentionPolicy("alerts", 90)
        created = datetime.utcnow() - timedelta(days=30)

        assert policy.should_retain(created) is True

    def test_retention_policy_should_not_retain(self):
        """测试数据保留策略过期"""
        policy = DataRetentionPolicy("alerts", 90)
        created = datetime.utcnow() - timedelta(days=100)

        assert policy.should_retain(created) is False

    def test_get_retention_policy(self):
        """测试获取保留策略"""
        policy = get_retention_policy("alerts")

        assert policy is not None
        assert policy.data_type == "alerts"
        assert policy.retention_days == 90

    def test_set_retention_policy(self):
        """测试设置保留策略"""
        set_retention_policy("custom_type", 30)

        policy = get_retention_policy("custom_type")
        assert policy is not None
        assert policy.retention_days == 30


class TestConsentManagement:
    """同意管理测试"""

    def test_record_consent(self):
        """测试记录用户同意"""
        # Enable consent requirement for this test
        config = DataPrivacyConfig(consent_required=True)
        configure_privacy(config)

        record_consent("user_consent_test", "data_processing", True)

        consents = get_user_consents("user_consent_test")
        assert len(consents) == 1
        assert consents[0]["consent_type"] == "data_processing"
        assert consents[0]["granted"] is True

    def test_has_consent(self):
        """测试检查用户同意"""
        # Enable consent requirement for this test
        config = DataPrivacyConfig(consent_required=True)
        configure_privacy(config)

        record_consent("user_consent_check", "data_processing", True)

        assert has_consent("user_consent_check", "data_processing") is True
        assert has_consent("user_consent_check", "marketing") is False

    def test_get_user_consents(self):
        """测试获取用户所有同意"""
        # Use unique user ID to avoid conflicts
        record_consent("user_consents_test", "data_processing", True)
        record_consent("user_consents_test", "marketing", False)

        consents = get_user_consents("user_consents_test")
        assert len(consents) == 2


class TestPrivacyAudit:
    """隐私审计测试"""

    def test_log_privacy_event(self):
        """测试记录隐私事件"""
        log_privacy_event(
            event_type="data_access",
            user_id="user1",
            data_type="alerts",
            action="read",
        )

        logs = get_privacy_audit_logs()
        assert len(logs) >= 1

    def test_get_privacy_audit_logs_filtered(self):
        """测试获取过滤后的审计日志"""
        log_privacy_event(
            event_type="data_access",
            user_id="user1",
            data_type="alerts",
            action="read",
        )

        logs = get_privacy_audit_logs(user_id="user1")
        assert len(logs) >= 1

    def test_get_privacy_stats(self):
        """测试获取隐私统计"""
        stats = get_privacy_stats()

        assert "config" in stats
        assert "retention_policies" in stats
        assert "consent_records" in stats
        assert "audit_log_entries" in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
