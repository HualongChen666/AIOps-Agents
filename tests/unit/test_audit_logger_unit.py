# -*- coding: utf-8 -*-
# tests/unit/test_audit_logger_unit.py
# Audit Logger模块单元测试
from unittest.mock import patch

import pytest  # noqa: F401


class TestAuditLogger:
    """测试审计日志"""

    def test_audit_event_types(self):
        """测试审计事件类型"""
        from core.audit_logger import AUDIT_EVENT_TYPES

        assert "LOGIN" in AUDIT_EVENT_TYPES
        assert "LOGOUT" in AUDIT_EVENT_TYPES
        assert "TOKEN_REFRESH" in AUDIT_EVENT_TYPES
        assert "PERMISSION_GRANTED" in AUDIT_EVENT_TYPES
        assert "PERMISSION_REVOKED" in AUDIT_EVENT_TYPES
        assert "REPAIR_EXECUTED" in AUDIT_EVENT_TYPES
        assert "ALERT_GENERATED" in AUDIT_EVENT_TYPES
        assert "CONFIG_CHANGED" in AUDIT_EVENT_TYPES
        assert "DATA_ACCESS" in AUDIT_EVENT_TYPES

    @patch("core.audit_logger.logger")
    def test_log_audit_event(self, mock_logger):
        """测试记录审计事件"""
        from core.audit_logger import log_audit_event

        log_audit_event(
            event_type="LOGIN",
            user="test_user",
            resource="test_resource",
            action="test_action",
            details={"key": "value"},
            ip_address="127.0.0.1",
            status="success",
        )

        assert mock_logger.info.called

    @patch("core.audit_logger.logger")
    def test_log_login_event(self, mock_logger):
        """测试记录登录事件"""
        from core.audit_logger import log_login_event

        log_login_event(user="test_user", ip_address="127.0.0.1")

        assert mock_logger.info.called

    @patch("core.audit_logger.logger")
    def test_log_logout_event(self, mock_logger):
        """测试记录登出事件"""
        from core.audit_logger import log_logout_event

        log_logout_event(user="test_user", ip_address="127.0.0.1")

        assert mock_logger.info.called

    @patch("core.audit_logger.logger")
    def test_log_token_refresh(self, mock_logger):
        """测试记录令牌刷新事件"""
        from core.audit_logger import log_token_refresh

        log_token_refresh(user="test_user", ip_address="127.0.0.1")

        assert mock_logger.info.called

    @patch("core.audit_logger.logger")
    def test_log_repair_executed(self, mock_logger):
        """测试记录修复执行事件"""
        from core.audit_logger import log_repair_executed

        log_repair_executed(
            user="test_user", script_key="test_script", target_host="test_host", status="success"
        )

        assert mock_logger.info.called

    @patch("core.audit_logger.logger")
    def test_log_permission_change(self, mock_logger):
        """测试记录权限变更事件"""
        from core.audit_logger import log_permission_change

        log_permission_change(
            user="admin_user",
            target_user="target_user",
            permission="admin",
            action="granted",
            status="success",
        )

        assert mock_logger.info.called

    @patch("core.audit_logger.logger")
    def test_log_alert_generated(self, mock_logger):
        """测试记录告警生成事件"""
        from core.audit_logger import log_alert_generated

        log_alert_generated(alert_type="high_cpu", severity="critical", details={"cpu_usage": 95.5})

        assert mock_logger.info.called

    @patch("core.audit_logger.logger")
    def test_log_data_access(self, mock_logger):
        """测试记录数据访问事件"""
        from core.audit_logger import log_data_access

        log_data_access(
            user="test_user", resource="sensitive_data", action="read", ip_address="127.0.0.1"
        )

        assert mock_logger.info.called
