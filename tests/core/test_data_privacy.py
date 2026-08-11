# -*- coding: utf-8 -*-
"""Tests for core/data_privacy.py."""

from core.data_privacy import (
    DataPrivacyConfig,
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


def test_data_privacy_config():
    config = DataPrivacyConfig(anonymization_enabled=True, gdpr_compliance=True)
    configure_privacy(config)
    assert get_privacy_config().anonymization_enabled is True


def test_detect_and_contains_pii():
    text = "Contact me at user@example.com or call 123-456-7890"
    result = detect_pii(text)
    assert "email" in result
    assert contains_pii(text) is True
    assert contains_pii("no pii here") is False


def test_anonymizers():
    assert "*" in anonymize_email("user@example.com")
    assert "*" in anonymize_phone("123-456-7890")
    assert "*" in anonymize_ssn("123-45-6789")
    assert "*" in anonymize_credit_card("4111111111111111")
    assert "*" in anonymize_ip("192.168.1.1")
    assert "*" in anonymize_text("email user@example.com here")


def test_anonymize_dict():
    data = {"password": "secret", "email": "user@example.com", "other": "ok"}
    redacted = anonymize_dict(data)
    assert redacted["password"] == "secret"
    assert "**" in redacted["email"]
    assert redacted["other"] == "ok"


def test_hash_pii():
    h1 = hash_pii("sensitive")
    h2 = hash_pii("sensitive")
    assert isinstance(h1, str)
    assert h1 == h2


def test_retention_policy_and_consent():
    set_retention_policy("metrics", 60)
    policy = get_retention_policy("metrics")
    assert policy.retention_days == 60

    record_consent("u1", "analytics", True)
    assert has_consent("u1", "analytics") is True
    assert get_user_consents("u1")[0]["user_id"] == "u1"


def test_privacy_audit_log():
    log_privacy_event("access", "u1", "metrics", "read", details={"status": "success"})
    logs = get_privacy_audit_logs()
    assert len(logs) >= 1
    stats = get_privacy_stats()
    assert "audit_log_entries" in stats
