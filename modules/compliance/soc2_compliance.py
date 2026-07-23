# -*- coding: utf-8 -*-
"""
soc2_compliance.py
------------------
合规认证 - SOC2 合规模块。

功能：
- 访问控制管理
- 变更管理
- 事件日志记录
- 安全监控
- 合规报告生成
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ SOC2 信任服务类别
# ----------------------------------------------------------------------
class SOC2TrustService(Enum):
    """SOC2 信任服务类别"""

    SECURITY = "security"  # 安全性
    AVAILABILITY = "availability"  # 可用性
    PROCESSING_INTEGRITY = "processing_integrity"  # 处理完整性
    CONFIDENTIALITY = "confidentiality"  # 机密性
    PRIVACY = "privacy"  # 隐私


# ----------------------------------------------------------------------
# 2️⃣ 访问控制级别
# ----------------------------------------------------------------------
class AccessLevel(Enum):
    """访问控制级别"""

    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


# ----------------------------------------------------------------------
# 3️⃣ 访问记录
# ----------------------------------------------------------------------
@dataclass
class AccessRecord:
    """访问记录"""

    id: str
    user_id: str
    resource: str
    action: str  # "read", "write", "delete", "admin"
    access_level: AccessLevel
    timestamp: datetime = field(default_factory=datetime.now)
    ip_address: str = ""
    user_agent: str = ""
    success: bool = True
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "resource": self.resource,
            "action": self.action,
            "access_level": self.access_level.value,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "success": self.success,
            "reason": self.reason,
        }


# ----------------------------------------------------------------------
# 4️⃣ 变更记录
# ----------------------------------------------------------------------
@dataclass
class ChangeRecord:
    """变更记录"""

    id: str
    changed_by: str
    resource_type: str
    resource_id: str
    change_type: str  # "create", "update", "delete"
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    justification: str = ""
    approved_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "changed_by": self.changed_by,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "change_type": self.change_type,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "timestamp": self.timestamp.isoformat(),
            "justification": self.justification,
            "approved_by": self.approved_by,
        }


# ----------------------------------------------------------------------
# 5️⃣ 安全事件
# ----------------------------------------------------------------------
@dataclass
class SecurityEvent:
    """安全事件"""

    id: str
    event_type: (
        str  # "unauthorized_access", "privilege_escalation", "data_breach", "malware_detected"
    )
    severity: str  # "low", "medium", "high", "critical"
    description: str
    affected_users: List[str] = field(default_factory=list)
    affected_resources: List[str] = field(default_factory=list)
    detected_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolution: str = ""

    @property
    def is_resolved(self) -> bool:
        """是否已解决"""
        return self.resolved_at is not None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "event_type": self.event_type,
            "severity": self.severity,
            "description": self.description,
            "affected_users": self.affected_users,
            "affected_resources": self.affected_resources,
            "detected_at": self.detected_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolution": self.resolution,
        }


# ----------------------------------------------------------------------
# 6️⃣ 访问控制管理器
# ----------------------------------------------------------------------
class AccessControlManager:
    """访问控制管理器"""

    def __init__(self):
        self.user_permissions: Dict[str, Dict[str, AccessLevel]] = {}
        self.access_records: List[AccessRecord] = []
        self.role_permissions: Dict[str, Dict[str, AccessLevel]] = {}
        self.user_roles: Dict[str, List[str]] = {}

    def assign_permission(
        self,
        user_id: str,
        resource: str,
        access_level: AccessLevel,
    ):
        """
        分配权限

        Parameters
        ----------
        user_id : str
            用户 ID
        resource : str
            资源
        access_level : AccessLevel
            访问级别
        """
        if user_id not in self.user_permissions:
            self.user_permissions[user_id] = {}

        self.user_permissions[user_id][resource] = access_level
        logger.info(f"Assigned {access_level.value} permission to {user_id} for {resource}")

    def revoke_permission(
        self,
        user_id: str,
        resource: str,
    ):
        """撤销权限"""
        if user_id in self.user_permissions and resource in self.user_permissions[user_id]:
            del self.user_permissions[user_id][resource]
            logger.info(f"Revoked permission from {user_id} for {resource}")

    def check_permission(
        self,
        user_id: str,
        resource: str,
        required_level: AccessLevel,
    ) -> bool:
        """
        检查权限

        Parameters
        ----------
        user_id : str
            用户 ID
        resource : str
            资源
        required_level : AccessLevel
            所需级别

        Returns
        -------
        bool
            是否有权限
        """
        # 检查直接权限
        if user_id in self.user_permissions and resource in self.user_permissions[user_id]:
            user_level = self.user_permissions[user_id][resource]
            return self._compare_access_levels(user_level, required_level)

        # 检查角色权限
        if user_id in self.user_roles:
            for role in self.user_roles[user_id]:
                if role in self.role_permissions and resource in self.role_permissions[role]:
                    role_level = self.role_permissions[role][resource]
                    if self._compare_access_levels(role_level, required_level):
                        return True

        return False

    def _compare_access_levels(
        self,
        user_level: AccessLevel,
        required_level: AccessLevel,
    ) -> bool:
        """比较访问级别"""
        level_order = {
            AccessLevel.READ_ONLY: 1,
            AccessLevel.READ_WRITE: 2,
            AccessLevel.ADMIN: 3,
            AccessLevel.SUPER_ADMIN: 4,
        }

        return level_order[user_level] >= level_order[required_level]

    def assign_role(
        self,
        user_id: str,
        role: str,
    ):
        """分配角色"""
        if user_id not in self.user_roles:
            self.user_roles[user_id] = []

        if role not in self.user_roles[user_id]:
            self.user_roles[user_id].append(role)
            logger.info(f"Assigned role {role} to {user_id}")

    def define_role_permissions(
        self,
        role: str,
        permissions: Dict[str, AccessLevel],
    ):
        """定义角色权限"""
        self.role_permissions[role] = permissions
        logger.info(f"Defined permissions for role {role}")

    def log_access(
        self,
        user_id: str,
        resource: str,
        action: str,
        access_level: AccessLevel,
        ip_address: str = "",
        user_agent: str = "",
        success: bool = True,
        reason: str = "",
    ):
        """记录访问"""
        record = AccessRecord(
            id=f"access-{int(datetime.now().timestamp())}",
            user_id=user_id,
            resource=resource,
            action=action,
            access_level=access_level,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
            reason=reason,
        )

        self.access_records.append(record)
        logger.debug(f"Logged access: {user_id} -> {resource} ({action})")

    def get_access_logs(
        self,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        hours: int = 24,
    ) -> List[AccessRecord]:
        """
        获取访问日志

        Parameters
        ----------
        user_id : str, optional
            用户 ID 过滤
        resource : str, optional
            资源过滤
        hours : int
            时间范围（小时）

        Returns
        -------
        List[AccessRecord]
            访问记录列表
        """
        cutoff = datetime.now() - timedelta(hours=hours)

        logs = [log for log in self.access_records if log.timestamp >= cutoff]

        if user_id:
            logs = [log for log in logs if log.user_id == user_id]

        if resource:
            logs = [log for log in logs if log.resource == resource]

        return logs


# ----------------------------------------------------------------------
# 7️⃣ 变更管理器
# ----------------------------------------------------------------------
class ChangeManager:
    """变更管理器"""

    def __init__(self):
        self.change_records: List[ChangeRecord] = []
        self.pending_approvals: Dict[str, ChangeRecord] = {}

    def record_change(
        self,
        changed_by: str,
        resource_type: str,
        resource_id: str,
        change_type: str,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        justification: str = "",
        requires_approval: bool = False,
    ) -> ChangeRecord:
        """
        记录变更

        Parameters
        ----------
        changed_by : str
            变更者
        resource_type : str
            资源类型
        resource_id : str
            资源 ID
        change_type : str
            变更类型
        old_value : str, optional
            旧值
        new_value : str, optional
            新值
        justification : str
            变更理由
        requires_approval : bool
            是否需要审批

        Returns
        -------
        ChangeRecord
            变更记录
        """
        record = ChangeRecord(
            id=f"change-{int(datetime.now().timestamp())}",
            changed_by=changed_by,
            resource_type=resource_type,
            resource_id=resource_id,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            justification=justification,
        )

        if requires_approval:
            self.pending_approvals[record.id] = record
            logger.info(f"Change pending approval: {record.id}")
        else:
            self.change_records.append(record)
            logger.info(f"Recorded change: {record.id}")

        return record

    def approve_change(
        self,
        change_id: str,
        approved_by: str,
    ) -> bool:
        """
        审批变更

        Parameters
        ----------
        change_id : str
            变更 ID
        approved_by : str
            审批人

        Returns
        -------
        bool
            是否成功
        """
        if change_id in self.pending_approvals:
            record = self.pending_approvals[change_id]
            record.approved_by = approved_by
            self.change_records.append(record)
            del self.pending_approvals[change_id]
            logger.info(f"Approved change: {change_id}")
            return True

        return False

    def reject_change(
        self,
        change_id: str,
        reason: str = "",
    ) -> bool:
        """
        拒绝变更

        Parameters
        ----------
        change_id : str
            变更 ID
        reason : str
            拒绝原因

        Returns
        -------
        bool
            是否成功
        """
        if change_id in self.pending_approvals:
            del self.pending_approvals[change_id]
            logger.info(f"Rejected change: {change_id} - {reason}")
            return True

        return False

    def get_change_history(
        self,
        resource_id: Optional[str] = None,
        days: int = 30,
    ) -> List[ChangeRecord]:
        """
        获取变更历史

        Parameters
        ----------
        resource_id : str, optional
            资源 ID 过滤
        days : int
            天数

        Returns
        -------
        List[ChangeRecord]
            变更记录列表
        """
        cutoff = datetime.now() - timedelta(days=days)

        history = [record for record in self.change_records if record.timestamp >= cutoff]

        if resource_id:
            history = [record for record in history if record.resource_id == resource_id]

        return history


# ----------------------------------------------------------------------
# 8️⃣ 安全监控器
# ----------------------------------------------------------------------
class SecurityMonitor:
    """安全监控器"""

    def __init__(self):
        self.security_events: List[SecurityEvent] = []
        self.alert_thresholds = {
            "failed_login_attempts": 5,
            "unauthorized_access_attempts": 3,
        }
        self.counters: Dict[str, int] = {}

    def detect_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        affected_users: List[str] = None,
        affected_resources: List[str] = None,
    ) -> SecurityEvent:
        """
        检测安全事件

        Parameters
        ----------
        event_type : str
            事件类型
        severity : str
            严重程度
        description : str
            描述
        affected_users : List[str], optional
            受影响用户
        affected_resources : List[str], optional
            受影响资源

        Returns
        -------
        SecurityEvent
            安全事件
        """
        event = SecurityEvent(
            id=f"event-{int(datetime.now().timestamp())}",
            event_type=event_type,
            severity=severity,
            description=description,
            affected_users=affected_users or [],
            affected_resources=affected_resources or [],
        )

        self.security_events.append(event)

        if severity in ["high", "critical"]:
            logger.critical(f"Security event detected: {event_type} - {description}")
        else:
            logger.warning(f"Security event detected: {event_type} - {description}")

        return event

    def resolve_event(
        self,
        event_id: str,
        resolution: str,
    ) -> bool:
        """
        解决安全事件

        Parameters
        ----------
        event_id : str
            事件 ID
        resolution : str
            解决方案

        Returns
        -------
        bool
            是否成功
        """
        for event in self.security_events:
            if event.id == event_id:
                event.resolved_at = datetime.now()
                event.resolution = resolution
                logger.info(f"Resolved security event: {event_id}")
                return True

        return False

    def get_unresolved_events(self) -> List[SecurityEvent]:
        """获取未解决的事件"""
        return [e for e in self.security_events if not e.is_resolved]

    def check_compliance_thresholds(self) -> List[str]:
        """检查合规阈值"""
        violations = []

        # 检查未解决的高严重性事件
        unresolved_high = [
            e for e in self.get_unresolved_events() if e.severity in ["high", "critical"]
        ]

        if len(unresolved_high) > 0:
            violations.append(f"Unresolved high-severity events: {len(unresolved_high)}")

        return violations


# ----------------------------------------------------------------------
# 9️⃣ SOC2 合规管理器
# ----------------------------------------------------------------------
class SOC2ComplianceManager:
    """SOC2 合规管理器"""

    def __init__(self):
        self.access_control = AccessControlManager()
        self.change_manager = ChangeManager()
        self.security_monitor = SecurityMonitor()
        self.trust_services: List[SOC2TrustService] = [
            SOC2TrustService.SECURITY,
            SOC2TrustService.AVAILABILITY,
            SOC2TrustService.PROCESSING_INTEGRITY,
            SOC2TrustService.CONFIDENTIALITY,
        ]

    def generate_compliance_report(
        self,
        trust_service: Optional[SOC2TrustService] = None,
    ) -> Dict[str, Any]:
        """
        生成合规报告

        Parameters
        ----------
        trust_service : SOC2TrustService, optional
            信任服务类别

        Returns
        -------
        Dict[str, Any]
            合规报告
        """
        report = {
            "generated_at": datetime.now().isoformat(),
            "trust_services": [ts.value for ts in self.trust_services],
            "access_control": {
                "total_users": len(self.access_control.user_permissions),
                "total_roles": len(self.access_control.role_permissions),
                "recent_access_logs": len(self.access_control.get_access_logs(hours=24)),
            },
            "change_management": {
                "total_changes": len(self.change_manager.change_records),
                "pending_approvals": len(self.change_manager.pending_approvals),
                "recent_changes": len(self.change_manager.get_change_history(days=7)),
            },
            "security_monitoring": {
                "total_events": len(self.security_monitor.security_events),
                "unresolved_events": len(self.security_monitor.get_unresolved_events()),
                "compliance_violations": self.security_monitor.check_compliance_thresholds(),
            },
        }

        if trust_service:
            report["focus_service"] = trust_service.value

        return report

    def run_compliance_check(self) -> Dict[str, Any]:
        """运行合规检查"""
        violations = []

        # 检查访问控制
        violations.extend(self._check_access_control())

        # 检查变更管理
        violations.extend(self._check_change_management())

        # 检查安全监控
        violations.extend(self.security_monitor.check_compliance_thresholds())

        return {
            "check_time": datetime.now().isoformat(),
            "violations": violations,
            "compliant": len(violations) == 0,
        }

    def _check_access_control(self) -> List[str]:
        """检查访问控制合规性"""
        violations = []

        # 检查是否有未授权的访问尝试
        failed_access = [log for log in self.access_control.access_records if not log.success]

        if len(failed_access) > 10:  # 阈值
            violations.append(f"High number of failed access attempts: {len(failed_access)}")

        return violations

    def _check_change_management(self) -> List[str]:
        """检查变更管理合规性"""
        violations = []

        # 检查是否有长时间未审批的变更
        old_pending = []
        cutoff = datetime.now() - timedelta(days=7)

        for record in self.change_manager.pending_approvals.values():
            if record.timestamp < cutoff:
                old_pending.append(record.id)

        if old_pending:
            violations.append(f"Pending changes older than 7 days: {len(old_pending)}")

        return violations


# ----------------------------------------------------------------------
# 🔟 工厂函数
# ----------------------------------------------------------------------
def create_soc2_compliance_manager() -> SOC2ComplianceManager:
    """创建 SOC2 合规管理器"""
    return SOC2ComplianceManager()


# ----------------------------------------------------------------------
# 1️⃣1️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试 SOC2 合规管理器
    logger.info("Testing SOC2 compliance manager")

    manager = create_soc2_compliance_manager()

    # 分配权限
    manager.access_control.assign_permission("user-1", "resource-1", AccessLevel.READ_WRITE)
    manager.access_control.assign_permission("user-1", "resource-2", AccessLevel.ADMIN)

    # 记录访问
    manager.access_control.log_access(
        user_id="user-1",
        resource="resource-1",
        action="read",
        access_level=AccessLevel.READ_WRITE,
        ip_address="192.168.1.1",
        success=True,
    )

    # 记录变更
    manager.change_manager.record_change(
        changed_by="user-1",
        resource_type="config",
        resource_id="config-1",
        change_type="update",
        old_value="value1",
        new_value="value2",
        justification="Configuration update",
        requires_approval=True,
    )

    # 检测安全事件
    manager.security_monitor.detect_event(
        event_type="unauthorized_access",
        severity="high",
        description="Unauthorized access attempt detected",
        affected_users=["user-1"],
    )

    # 生成合规报告
    report = manager.generate_compliance_report()
    logger.info(f"Compliance report: {report}")

    # 运行合规检查
    check = manager.run_compliance_check()
    logger.info(f"Compliance check: {check}")

    logger.info("Test passed!")
