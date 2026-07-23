# -*- coding: utf-8 -*-
# tests/test_audit_logger.py
# 审计日志单元测试
from unittest.mock import patch

import pytest

from core.audit_logger import (
    AUDIT_EVENT_TYPES,
    log_alert_generated,
    log_audit_event,
    log_data_access,
    log_login_event,
    log_logout_event,
    log_permission_change,
    log_repair_executed,
    log_token_refresh,
)


class TestAuditEventLogging:
    """审计事件日志测试"""

    @patch("core.audit_logger.logger")
    def test_log_audit_event(self, mock_logger):
        """测试基本审计事件日志"""
        log_audit_event(
            event_type="LOGIN",
            user="test_user",
            resource="api",
            action="login",
            ip_address="192.168.1.1",
            status="success",
        )

        # Verify logger was called
        mock_logger.info.assert_called_once()

        # Verify the call contains audit information
        call_args = mock_logger.info.call_args[0][0]
        assert "AUDIT:" in call_args
        assert "test_user" in call_args

    @patch("core.audit_logger.logger")
    def test_log_audit_event_with_details(self, mock_logger):
        """测试带详细信息的审计事件日志"""
        details = {"reason": "test", "duration": 1.5}
        log_audit_event(
            event_type="REPAIR_EXECUTED",
            user="admin",
            resource="server-01",
            action="restart_service",
            details=details,
            status="success",
        )

        # Verify logger was called
        mock_logger.info.assert_called_once()

    @patch("core.audit_logger.logger")
    def test_log_login_event(self, mock_logger):
        """测试登录事件日志"""
        log_login_event(user="test_user", ip_address="192.168.1.1")

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "LOGIN" in call_args

    @patch("core.audit_logger.logger")
    def test_log_logout_event(self, mock_logger):
        """测试登出事件日志"""
        log_logout_event(user="test_user", ip_address="192.168.1.1")

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "LOGOUT" in call_args

    @patch("core.audit_logger.logger")
    def test_log_token_refresh(self, mock_logger):
        """测试令牌刷新事件日志"""
        log_token_refresh(user="test_user", ip_address="192.168.1.1")

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "TOKEN_REFRESH" in call_args

    @patch("core.audit_logger.logger")
    def test_log_repair_executed(self, mock_logger):
        """测试修复执行事件日志"""
        log_repair_executed(
            user="admin",
            script_key="restart_service",
            target_host="server-01",
            status="success",
        )

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "REPAIR_EXECUTED" in call_args

    @patch("core.audit_logger.logger")
    def test_log_permission_change(self, mock_logger):
        """测试权限变更事件日志"""
        log_permission_change(
            user="admin",
            target_user="test_user",
            permission="read",
            action="granted",
        )

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "PERMISSION_GRANTED" in call_args

    @patch("core.audit_logger.logger")
    def test_log_alert_generated(self, mock_logger):
        """测试告警生成事件日志"""
        log_alert_generated(
            alert_type="cpu_high",
            severity="critical",
            details={"host": "server-01", "value": 95.0},
        )

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "ALERT_GENERATED" in call_args

    @patch("core.audit_logger.logger")
    def test_log_data_access(self, mock_logger):
        """测试数据访问事件日志"""
        log_data_access(
            user="test_user",
            resource="metrics",
            action="read",
            ip_address="192.168.1.1",
        )

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "DATA_ACCESS" in call_args


class TestAuditEventTypes:
    """审计事件类型测试"""

    def test_audit_event_types_defined(self):
        """测试审计事件类型已定义"""
        assert "LOGIN" in AUDIT_EVENT_TYPES
        assert "LOGOUT" in AUDIT_EVENT_TYPES
        assert "TOKEN_REFRESH" in AUDIT_EVENT_TYPES
        assert "REPAIR_EXECUTED" in AUDIT_EVENT_TYPES
        assert "ALERT_GENERATED" in AUDIT_EVENT_TYPES


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
