# -*- coding: utf-8 -*-
"""测试安全审计系统模块"""

import pytest


class TestSecurityAuditSystemModule:
    """测试安全审计系统模块"""

    def test_security_audit_system_module_exists(self):
        """测试安全审计系统模块存在"""
        from core import security_audit_system

        assert security_audit_system is not None

    def test_security_audit_system_has_enums(self):
        """测试安全审计系统模块有枚举"""
        from core import security_audit_system

        # 检查模块有枚举
        assert hasattr(security_audit_system, "AuditEventType")
        assert hasattr(security_audit_system, "AuditSeverity")

    def test_security_audit_system_has_dataclasses(self):
        """测试安全审计系统模块有数据类"""
        from core import security_audit_system

        # 检查模块有数据类
        assert hasattr(security_audit_system, "AuditEvent")
        assert hasattr(security_audit_system, "AuditPolicy")

    def test_security_audit_system_has_classes(self):
        """测试安全审计系统模块有类"""
        from core import security_audit_system

        # 检查模块有类
        assert hasattr(security_audit_system, "SecurityAuditSystem")

    def test_security_audit_system_has_functions(self):
        """测试安全审计系统模块有函数"""
        from core import security_audit_system

        # 检查模块有函数
        assert hasattr(security_audit_system, "get_security_audit_system")


class TestAuditEventType:
    """测试审计事件类型枚举"""

    def test_audit_event_type_values(self):
        """测试审计事件类型值"""
        from core.security_audit_system import AuditEventType

        assert AuditEventType.USER_LOGIN.value == "user_login"
        assert AuditEventType.USER_LOGOUT.value == "user_logout"
        assert AuditEventType.DATA_ACCESS.value == "data_access"
        assert AuditEventType.CONFIGURATION_CHANGE.value == "configuration_change"
        assert AuditEventType.PRIVILEGE_ESCALATION.value == "privilege_escalation"
        assert AuditEventType.SECURITY_INCIDENT.value == "security_incident"
        assert AuditEventType.POLICY_VIOLATION.value == "policy_violation"
        assert AuditEventType.API_ACCESS.value == "api_access"
        assert AuditEventType.SYSTEM_CHANGE.value == "system_change"


class TestAuditSeverity:
    """测试审计严重性枚举"""

    def test_audit_severity_values(self):
        """测试审计严重性值"""
        from core.security_audit_system import AuditSeverity

        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.ERROR.value == "error"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestAuditEvent:
    """测试审计事件数据类"""

    def test_audit_event_creation(self):
        """测试审计事件创建"""
        from core.security_audit_system import (
            AuditEvent,
            AuditEventType,
            AuditSeverity,
        )

        event = AuditEvent(
            event_id="test_event",
            event_type=AuditEventType.USER_LOGIN,
            severity=AuditSeverity.INFO,
            user_id="user1",
            action="User logged in",
        )

        assert event.event_id == "test_event"
        assert event.event_type == AuditEventType.USER_LOGIN
        assert event.severity == AuditSeverity.INFO
        assert event.user_id == "user1"
        assert event.action == "User logged in"


class TestAuditPolicy:
    """测试审计策略数据类"""

    def test_audit_policy_creation(self):
        """测试审计策略创建"""
        from core.security_audit_system import AuditEventType, AuditPolicy, AuditSeverity

        policy = AuditPolicy(
            policy_id="test_policy",
            policy_name="Test Policy",
            event_types=[AuditEventType.USER_LOGIN],
            severity_filter=AuditSeverity.INFO,
        )

        assert policy.policy_id == "test_policy"
        assert policy.policy_name == "Test Policy"
        assert len(policy.event_types) == 1
        assert policy.severity_filter == AuditSeverity.INFO


class TestSecurityAuditSystem:
    """测试安全审计系统类"""

    def test_security_audit_system_initialization(self):
        """测试安全审计系统初始化"""
        from core.security_audit_system import SecurityAuditSystem

        system = SecurityAuditSystem()

        assert system.config == {}
        assert len(system.audit_events) == 0
        assert len(system.audit_policies) > 0

    def test_security_audit_system_initialization_with_config(self):
        """测试安全审计系统初始化（带配置）"""
        from core.security_audit_system import SecurityAuditSystem

        config = {"audit_log_dir": "./test_audit"}
        system = SecurityAuditSystem(config)

        assert system.config == config

    def test_security_audit_system_default_policies(self):
        """测试安全审计系统默认策略"""
        from core.security_audit_system import SecurityAuditSystem

        system = SecurityAuditSystem()

        assert "security_events" in system.audit_policies
        assert "data_access" in system.audit_policies
        assert "config_changes" in system.audit_policies
        assert "api_access" in system.audit_policies

    def test_register_policy(self):
        """测试注册策略"""
        from core.security_audit_system import (
            AuditEventType,
            AuditPolicy,
            SecurityAuditSystem,
        )

        system = SecurityAuditSystem()
        policy = AuditPolicy(
            policy_id="new_policy",
            policy_name="New Policy",
            event_types=[AuditEventType.USER_LOGIN],
        )

        system.register_policy(policy)

        assert "new_policy" in system.audit_policies

    @pytest.mark.asyncio
    async def test_log_event(self):
        """测试记录事件"""
        from core.security_audit_system import (
            AuditEventType,
            AuditSeverity,
            SecurityAuditSystem,
        )

        system = SecurityAuditSystem()

        event_id = await system.log_event(
            event_type=AuditEventType.USER_LOGIN,
            action="User logged in",
            user_id="user1",
            severity=AuditSeverity.INFO,
        )

        assert event_id.startswith("audit_")
        assert len(system.audit_events) == 1
        assert system.total_events == 1

    @pytest.mark.asyncio
    async def test_log_event_critical(self):
        """测试记录事件（严重）"""
        from core.security_audit_system import (
            AuditEventType,
            AuditSeverity,
            SecurityAuditSystem,
        )

        system = SecurityAuditSystem()

        event_id = await system.log_event(
            event_type=AuditEventType.SECURITY_INCIDENT,
            action="Security incident",
            user_id="user1",
            severity=AuditSeverity.CRITICAL,
        )

        assert event_id.startswith("audit_")
        assert system.critical_events == 1

    def test_query_events(self):
        """测试查询事件"""
        import asyncio

        from core.security_audit_system import (
            AuditEventType,
            AuditSeverity,
            SecurityAuditSystem,
        )

        system = SecurityAuditSystem()

        # Log some events
        asyncio.run(
            system.log_event(
                event_type=AuditEventType.USER_LOGIN,
                action="User logged in",
                user_id="user1",
                severity=AuditSeverity.INFO,
            )
        )

        events = system.query_events()

        assert len(events) == 1

    def test_query_events_with_filter(self):
        """测试查询事件（带过滤器）"""
        import asyncio

        from core.security_audit_system import (
            AuditEventType,
            AuditSeverity,
            SecurityAuditSystem,
        )

        system = SecurityAuditSystem()

        # Log some events
        asyncio.run(
            system.log_event(
                event_type=AuditEventType.USER_LOGIN,
                action="User logged in",
                user_id="user1",
                severity=AuditSeverity.INFO,
            )
        )

        events = system.query_events(event_type=AuditEventType.USER_LOGIN)

        assert len(events) == 1

    def test_get_audit_summary(self):
        """测试获取审计摘要"""
        from core.security_audit_system import SecurityAuditSystem

        system = SecurityAuditSystem()

        summary = system.get_audit_summary()

        assert "total_events" in summary
        assert "by_severity" in summary
        assert "by_type" in summary
        assert "unique_users" in summary

    def test_register_alert_handler(self):
        """测试注册警报处理器"""
        from core.security_audit_system import SecurityAuditSystem

        system = SecurityAuditSystem()

        def handler(alert_data):
            pass

        system.register_alert_handler(handler)

        assert len(system.alert_handlers) == 1

    @pytest.mark.asyncio
    async def test_generate_audit_report(self):
        """测试生成审计报告"""
        from datetime import datetime, timezone

        from core.security_audit_system import SecurityAuditSystem

        system = SecurityAuditSystem()

        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)

        report_path = await system.generate_audit_report(start_time, end_time)

        assert report_path.endswith(".json")

    def test_get_statistics(self):
        """测试获取统计信息"""
        from core.security_audit_system import SecurityAuditSystem

        system = SecurityAuditSystem()

        stats = system.get_statistics()

        assert "total_events" in stats
        assert "critical_events" in stats
        assert "enabled_policies" in stats
        assert "registered_policies" in stats


class TestGetSecurityAuditSystem:
    """测试获取安全审计系统"""

    def test_get_security_audit_system(self):
        """测试获取安全审计系统"""
        from core.security_audit_system import get_security_audit_system

        system = get_security_audit_system()

        assert system is not None
        assert hasattr(system, "audit_events")

    def test_get_security_audit_system_with_config(self):
        """测试获取安全审计系统（带配置）"""
        from core.security_audit_system import get_security_audit_system

        config = {"audit_log_dir": "./test_audit"}
        system = get_security_audit_system(config)

        assert system.config == config


class TestSecurityAuditSystemIntegration:
    """测试安全审计系统集成"""

    @pytest.mark.asyncio
    async def test_complete_audit_workflow(self):
        """测试完整审计工作流"""
        from core.security_audit_system import (
            AuditEventType,
            AuditSeverity,
            SecurityAuditSystem,
        )

        system = SecurityAuditSystem()

        # Log events
        event_id = await system.log_event(
            event_type=AuditEventType.USER_LOGIN,
            action="User logged in",
            user_id="user1",
            severity=AuditSeverity.INFO,
        )

        assert event_id in [e.event_id for e in system.audit_events]

        # Query events
        events = system.query_events(user_id="user1")
        assert len(events) == 1

        # Get summary
        summary = system.get_audit_summary()
        assert summary["total_events"] == 1

        # Get statistics
        stats = system.get_statistics()
        assert stats["total_events"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
