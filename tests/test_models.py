# -*- coding: utf-8 -*-
# tests/test_models.py
# 🔧 P0-7: ORM模型单元测试

from datetime import datetime

import pytest  # noqa: F401

from core.models import (
    Alert,
    AlertSeverity,
    AlertStatus,
    ApprovalStatus,
    AuditLog,
    PendingApproval,
    RepairRecord,
    RepairStatus,
    SystemMetrics,
    User,
)


class TestUserModel:
    """用户模型测试"""

    def test_user_creation(self):
        """测试用户创建"""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_password",
            role="user",
            disabled=False,
            mfa_enabled=False,
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "user"
        assert user.disabled is False
        assert user.mfa_enabled is False

    def test_user_repr(self):
        """测试用户字符串表示"""
        user = User(
            id=1,
            username="testuser",
            hashed_password="hash",
            role="user",
        )

        repr_str = repr(user)
        assert "testuser" in repr_str
        assert "user" in repr_str


class TestAlertModel:
    """告警模型测试"""

    def test_alert_creation(self):
        """测试告警创建"""
        alert = Alert(
            id="alert-123",
            level="critical",
            category="system",
            title="CPU High",
            description="CPU usage is high",
            detected_at=datetime.now(),
            status=AlertStatus.PENDING.value,
            host="localhost",
            platform="windows",
            priority="P1",
        )

        assert alert.id == "alert-123"
        assert alert.level == "critical"
        assert alert.status == AlertStatus.PENDING.value
        assert alert.priority == "P1"

    def test_alert_repr(self):
        """测试告警字符串表示"""
        alert = Alert(
            id="alert-123",
            level="critical",
            title="Test Alert",
            description="Test",
            detected_at=datetime.now(),
            platform="windows",
        )

        repr_str = repr(alert)
        assert "alert-123" in repr_str
        assert "critical" in repr_str


class TestRepairRecordModel:
    """修复记录模型测试"""

    def test_repair_record_creation(self):
        """测试修复记录创建"""
        repair = RepairRecord(
            id="repair-123",
            alert_id="alert-123",
            script_key="restart_service",
            script_name="Restart Service",
            success=True,
            status=RepairStatus.SUCCESS.value,
            repair_time=datetime.now(),
            repair_duration_sec=10.5,
            platform="windows",
            output="Success",
            return_code=0,
            risk="low",
        )

        assert repair.id == "repair-123"
        assert repair.success is True
        assert repair.status == RepairStatus.SUCCESS.value
        assert repair.risk == "low"

    def test_repair_record_repr(self):
        """测试修复记录字符串表示"""
        repair = RepairRecord(
            id="repair-123",
            script_name="Test Script",
            success=True,
            repair_time=datetime.now(),
            repair_duration_sec=10.0,
            platform="windows",
            output="Success",
            return_code=0,
            risk="low",
        )

        repr_str = repr(repair)
        assert "repair-123" in repr_str
        assert "True" in repr_str


class TestPendingApprovalModel:
    """待审批记录模型测试"""

    def test_pending_approval_creation(self):
        """测试待审批记录创建"""
        approval = PendingApproval(
            id="approval-123",
            alert_id="alert-123",
            alert_json='{"id": "alert-123"}',
            rule_name="auto_restart",
            script_key="restart",
            proposal="Restart the service",
            risk_level="medium",
            status=ApprovalStatus.PENDING.value,
        )

        assert approval.id == "approval-123"
        assert approval.alert_id == "alert-123"
        assert approval.status == ApprovalStatus.PENDING.value
        assert approval.risk_level == "medium"

    def test_pending_approval_repr(self):
        """测试待审批记录字符串表示"""
        approval = PendingApproval(
            id="approval-123",
            alert_id="alert-123",
            alert_json="{}",
            rule_name="test",
            script_key="test",
            proposal="test",
            risk_level="low",
            status=ApprovalStatus.PENDING.value,
        )

        repr_str = repr(approval)
        assert "approval-123" in repr_str
        assert "pending" in repr_str


class TestAuditLogModel:
    """审计日志模型测试"""

    def test_audit_log_creation(self):
        """测试审计日志创建"""
        log = AuditLog(
            action="login",
            resource_type="user",
            resource_id="1",
            user_id=1,
            username="testuser",
            ip_address="127.0.0.1",
            success=True,
            changes={"details": "User logged in"},
        )

        assert log.action == "login"
        assert log.resource_type == "user"
        assert log.username == "testuser"
        assert log.success is True

    def test_audit_log_repr(self):
        """测试审计日志字符串表示"""
        log = AuditLog(
            id=1,
            action="login",
            resource_type="user",
            username="testuser",
            success=True,
        )

        repr_str = repr(log)
        assert "login" in repr_str
        assert "testuser" in repr_str


class TestSystemMetricsModel:
    """系统指标模型测试"""

    def test_system_metrics_creation(self):
        """测试系统指标创建"""
        metrics = SystemMetrics(
            host="localhost",
            platform="windows",
            timestamp=datetime.now(),
            cpu_usage=75.5,
            memory_usage=60.0,
            memory_total=16.0,
            memory_available=8.0,
            network_in=10.0,
            network_out=5.0,
        )

        assert metrics.host == "localhost"
        assert metrics.platform == "windows"
        assert metrics.cpu_usage == 75.5
        assert metrics.memory_usage == 60.0

    def test_system_metrics_with_json_fields(self):
        """测试系统指标JSON字段"""
        metrics = SystemMetrics(
            host="localhost",
            platform="windows",
            timestamp=datetime.now(),
            disk_usage=80.0,
        )

        assert metrics.disk_usage is not None
        assert metrics.cpu_usage is None


class TestEnums:
    """枚举测试"""

    def test_alert_severity_enum(self):
        """测试告警严重程度枚举"""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.CRITICAL.value == "critical"
        assert AlertSeverity.FATAL.value == "fatal"

    def test_alert_status_enum(self):
        """测试告警状态枚举"""
        assert AlertStatus.PENDING.value == "pending"
        assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
        assert AlertStatus.RESOLVED.value == "resolved"
        assert AlertStatus.SUPPRESSED.value == "suppressed"

    def test_repair_status_enum(self):
        """测试修复状态枚举"""
        assert RepairStatus.PENDING.value == "pending"
        assert RepairStatus.IN_PROGRESS.value == "in_progress"
        assert RepairStatus.SUCCESS.value == "success"
        assert RepairStatus.FAILED.value == "failed"
        assert RepairStatus.CANCELLED.value == "cancelled"

    def test_approval_status_enum(self):
        """测试审批状态枚举"""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.CANCELLED.value == "cancelled"
