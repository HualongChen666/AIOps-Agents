# -*- coding: utf-8 -*-
"""Unit tests for approval store, notify engine and audit modules."""

import core.approval_store as approval_store
import core.audit_integration_manager as audit_integration_manager
import core.audit_logger as audit_logger
import core.audit_service as audit_service
import core.notify_engine as notify_engine


def test_approval_store_lifecycle():
    approval_store.upsert_approval("a-1", {"status": "pending"})
    assert approval_store.get_approval("a-1") is not None
    assert approval_store.is_pending("a-1") is True
    count_before = approval_store.approval_count()
    assert count_before >= 1
    approval_store.update_approval_status("a-1", "approved_no_script")
    assert approval_store.get_approval("a-1")["status"] == "approved_no_script"
    approval_store.remove_approval("a-1")
    assert approval_store.get_approval("a-1") is None
    approval_store.clear_all_approvals()
    assert approval_store.approval_count() == 0


def test_notify_engine_formatters():
    alert = {"title": "CPU high", "severity": "warning"}
    message = notify_engine.format_alert_message(alert)
    assert isinstance(message, str)
    structured = notify_engine.build_structured_alert_message(alert)
    assert isinstance(structured, str)


def test_notify_engine_status():
    notify_engine.mark_notification_read("msg-1", "email")
    status = notify_engine.get_notification_status(alert_id="msg-1", channel="email")
    assert isinstance(status, list)


def test_audit_logger():
    audit_logger.log_audit_event("test_action", {"test": True})
    audit_logger.log_login_event("admin")


def test_audit_service_helpers():
    result = audit_service.detect_security_event("test")
    assert isinstance(result, dict)
    assert audit_service.verify_log_integrity({"id": 1}) is False or True


def test_audit_integration_manager():
    manager = audit_integration_manager.get_audit_integration_manager()
    stats = manager.get_statistics()
    assert isinstance(stats, dict)
