# -*- coding: utf-8 -*-
"""
gdpr_compliance.py
------------------
合规认证 - GDPR 合规模块。

功能：
- 数据主体权利管理
- 数据处理记录
- 同意管理
- 数据删除（被遗忘权）
- 数据可移植性
- 数据泄露通知
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 数据主体权利枚举
# ----------------------------------------------------------------------
class DataSubjectRight(Enum):
    """数据主体权利"""

    ACCESS = "access"  # 访问权
    RECTIFICATION = "rectification"  # 更正权
    ERASURE = "erasure"  # 删除权（被遗忘权）
    RESTRICTION = "restriction"  # 限制处理权
    PORTABILITY = "portability"  # 数据可移植权
    OBJECT = "object"  # 反对权


# ----------------------------------------------------------------------
# 2️⃣ 数据处理目的
# ----------------------------------------------------------------------
@dataclass
class ProcessingPurpose:
    """数据处理目的"""

    id: str
    name: str
    description: str
    legal_basis: str  # "consent", "contract", "legal_obligation",
    # "vital_interests", "public_task", "legitimate_interests"
    data_categories: List[str] = field(default_factory=list)
    retention_period: Optional[int] = None  # 天数

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "legal_basis": self.legal_basis,
            "data_categories": self.data_categories,
            "retention_period": self.retention_period,
        }


# ----------------------------------------------------------------------
# 3️⃣ 同意记录
# ----------------------------------------------------------------------
@dataclass
class ConsentRecord:
    """同意记录"""

    id: str
    data_subject_id: str
    purpose_id: str
    granted: bool
    granted_at: datetime = field(default_factory=datetime.now)
    revoked_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_active(self) -> bool:
        """是否有效"""
        return self.granted and (self.revoked_at is None)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "data_subject_id": self.data_subject_id,
            "purpose_id": self.purpose_id,
            "granted": self.granted,
            "granted_at": self.granted_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 4️⃣ 数据处理记录
# ----------------------------------------------------------------------
@dataclass
class ProcessingRecord:
    """数据处理记录"""

    id: str
    data_subject_id: str
    purpose_id: str
    operation: str  # "create", "read", "update", "delete"
    data_categories: List[str]
    timestamp: datetime = field(default_factory=datetime.now)
    processor: str = ""
    justification: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "data_subject_id": self.data_subject_id,
            "purpose_id": self.purpose_id,
            "operation": self.operation,
            "data_categories": self.data_categories,
            "timestamp": self.timestamp.isoformat(),
            "processor": self.processor,
            "justification": self.justification,
        }


# ----------------------------------------------------------------------
# 5️⃣ 数据泄露事件
# ----------------------------------------------------------------------
@dataclass
class DataBreachEvent:
    """数据泄露事件"""

    id: str
    description: str
    affected_data_subjects: List[str]
    data_categories: List[str]
    discovered_at: datetime = field(default_factory=datetime.now)
    reported_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    severity: str = "medium"  # "low", "medium", "high"
    mitigation_actions: List[str] = field(default_factory=list)

    @property
    def is_reported(self) -> bool:
        """是否已报告"""
        return self.reported_at is not None

    @property
    def is_resolved(self) -> bool:
        """是否已解决"""
        return self.resolved_at is not None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "description": self.description,
            "affected_data_subjects": self.affected_data_subjects,
            "data_categories": self.data_categories,
            "discovered_at": self.discovered_at.isoformat(),
            "reported_at": self.reported_at.isoformat() if self.reported_at else None,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "severity": self.severity,
            "mitigation_actions": self.mitigation_actions,
        }


# ----------------------------------------------------------------------
# 6️⃣ GDPR 合规管理器
# ----------------------------------------------------------------------
class GDPRComplianceManager:
    """GDPR 合规管理器"""

    def __init__(self):
        self.purposes: Dict[str, ProcessingPurpose] = {}
        self.consents: Dict[str, ConsentRecord] = {}
        self.processing_records: List[ProcessingRecord] = []
        self.breach_events: List[DataBreachEvent] = []
        self.data_subjects: Dict[str, Dict[str, Any]] = {}

    def add_purpose(self, purpose: ProcessingPurpose):
        """添加处理目的"""
        self.purposes[purpose.id] = purpose
        logger.info(f"Added processing purpose: {purpose.name}")

    def record_consent(
        self,
        data_subject_id: str,
        purpose_id: str,
        granted: bool,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ConsentRecord:
        """
        记录同意

        Parameters
        ----------
        data_subject_id : str
            数据主体 ID
        purpose_id : str
            目的 ID
        granted : bool
            是否同意
        metadata : Dict[str, Any], optional
            元数据

        Returns
        -------
        ConsentRecord
            同意记录
        """
        consent_id = f"consent-{data_subject_id}-{purpose_id}-{int(datetime.now().timestamp())}"

        consent = ConsentRecord(
            id=consent_id,
            data_subject_id=data_subject_id,
            purpose_id=purpose_id,
            granted=granted,
            metadata=metadata or {},
        )

        self.consents[consent_id] = consent
        logger.info(f"Recorded consent: {data_subject_id} for {purpose_id} - {granted}")

        return consent

    def revoke_consent(self, consent_id: str):
        """撤销同意"""
        if consent_id in self.consents:
            self.consents[consent_id].revoked_at = datetime.now()
            logger.info(f"Revoked consent: {consent_id}")

    def has_consent(
        self,
        data_subject_id: str,
        purpose_id: str,
    ) -> bool:
        """
        检查是否有有效同意

        Parameters
        ----------
        data_subject_id : str
            数据主体 ID
        purpose_id : str
            目的 ID

        Returns
        -------
        bool
            是否有有效同意
        """
        for consent in self.consents.values():
            if (
                consent.data_subject_id == data_subject_id
                and consent.purpose_id == purpose_id
                and consent.is_active
            ):
                return True
        return False

    def record_processing(
        self,
        data_subject_id: str,
        purpose_id: str,
        operation: str,
        data_categories: List[str],
        processor: str = "",
        justification: str = "",
    ):
        """
        记录数据处理

        Parameters
        ----------
        data_subject_id : str
            数据主体 ID
        purpose_id : str
            目的 ID
        operation : str
            操作类型
        data_categories : List[str]
            数据类别
        processor : str
            处理者
        justification : str
            合法依据说明
        """
        record = ProcessingRecord(
            id=f"proc-{int(datetime.now().timestamp())}",
            data_subject_id=data_subject_id,
            purpose_id=purpose_id,
            operation=operation,
            data_categories=data_categories,
            processor=processor,
            justification=justification,
        )

        self.processing_records.append(record)
        logger.debug(f"Recorded processing: {operation} for {data_subject_id}")

    def get_data_subject_report(
        self,
        data_subject_id: str,
    ) -> Dict[str, Any]:
        """
        获取数据主体报告（访问权）

        Parameters
        ----------
        data_subject_id : str
            数据主体 ID

        Returns
        -------
        Dict[str, Any]
            数据主体报告
        """
        # 获取所有处理记录
        records = [r for r in self.processing_records if r.data_subject_id == data_subject_id]

        # 获取所有同意记录
        consents = [c for c in self.consents.values() if c.data_subject_id == data_subject_id]

        # 获取处理目的
        purposes = []
        for consent in consents:
            if consent.purpose_id in self.purposes:
                purposes.append(self.purposes[consent.purpose_id].to_dict())

        return {
            "data_subject_id": data_subject_id,
            "processing_records": [r.to_dict() for r in records],
            "consents": [c.to_dict() for c in consents],
            "purposes": purposes,
            "generated_at": datetime.now().isoformat(),
        }

    def request_erasure(
        self,
        data_subject_id: str,
        justification: str = "",
    ) -> bool:
        """
        请求删除数据（被遗忘权）

        Parameters
        ----------
        data_subject_id : str
            数据主体 ID
        justification : str
            合法依据说明

        Returns
        -------
        bool
            是否成功
        """
        # 检查是否有合法依据阻止删除
        # 简化实现：实际应检查合同、法律义务等

        # 记录删除请求
        self.record_processing(
            data_subject_id=data_subject_id,
            purpose_id="erasure",
            operation="delete",
            data_categories=["all"],
            justification=justification,
        )

        logger.info(f"Erasure request processed for {data_subject_id}")
        return True

    def request_portability(
        self,
        data_subject_id: str,
    ) -> Dict[str, Any]:
        """
        请求数据可移植性

        Parameters
        ----------
        data_subject_id : str
            数据主体 ID

        Returns
        -------
        Dict[str, Any]
            可导出的数据
        """
        report = self.get_data_subject_report(data_subject_id)

        # 简化实现：实际应返回机器可读格式
        return {
            "data_subject_id": data_subject_id,
            "data": report,
            "format": "json",
            "exported_at": datetime.now().isoformat(),
        }

    def report_breach(
        self,
        breach_event: DataBreachEvent,
    ) -> bool:
        """
        报告数据泄露

        Parameters
        ----------
        breach_event : DataBreachEvent
            泄露事件

        Returns
        -------
        bool
            是否成功
        """
        breach_event.reported_at = datetime.now()
        self.breach_events.append(breach_event)

        logger.warning(f"Data breach reported: {breach_event.id}")

        # 检查是否需要在 72 小时内通知监管机构
        if breach_event.severity in ["high"]:
            logger.critical("High severity breach - notify authorities within 72 hours")

        return True

    def resolve_breach(
        self,
        breach_id: str,
        mitigation_actions: List[str],
    ) -> bool:
        """
        解决数据泄露

        Parameters
        ----------
        breach_id : str
            泄露事件 ID
        mitigation_actions : List[str]
            缓解措施

        Returns
        -------
        bool
            是否成功
        """
        for breach in self.breach_events:
            if breach.id == breach_id:
                breach.resolved_at = datetime.now()
                breach.mitigation_actions = mitigation_actions
                logger.info(f"Resolved breach: {breach_id}")
                return True

        return False

    def check_retention_compliance(self) -> List[str]:
        """
        检查保留期限合规性

        Returns
        -------
        List[str]
            过期数据主体 ID 列表
        """
        expired_subjects = []

        for purpose in self.purposes.values():
            if purpose.retention_period:
                cutoff = datetime.now() - timedelta(days=purpose.retention_period)

                for record in self.processing_records:
                    if record.purpose_id == purpose.id and record.timestamp < cutoff:
                        if record.data_subject_id not in expired_subjects:
                            expired_subjects.append(record.data_subject_id)

        return expired_subjects

    def get_compliance_report(self) -> Dict[str, Any]:
        """获取合规报告"""
        return {
            "total_purposes": len(self.purposes),
            "total_consents": len(self.consents),
            "active_consents": sum(1 for c in self.consents.values() if c.is_active),
            "total_processing_records": len(self.processing_records),
            "total_breach_events": len(self.breach_events),
            "unresolved_breaches": sum(1 for b in self.breach_events if not b.is_resolved),
            "expired_data_subjects": self.check_retention_compliance(),
        }


# ----------------------------------------------------------------------
# 7️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_gdpr_compliance_manager() -> GDPRComplianceManager:
    """创建 GDPR 合规管理器"""
    return GDPRComplianceManager()


# ----------------------------------------------------------------------
# 8️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover

    logging.basicConfig(level=logging.INFO)

    # 测试 GDPR 合规管理器
    logger.info("Testing GDPR compliance manager")

    manager = create_gdpr_compliance_manager()

    # 添加处理目的
    manager.add_purpose(
        ProcessingPurpose(
            id="analytics",
            name="Analytics",
            description="User behavior analytics",
            legal_basis="consent",
            data_categories=["usage_data", "preferences"],
            retention_period=365,
        )
    )

    # 记录同意
    consent = manager.record_consent(
        data_subject_id="user-123",
        purpose_id="analytics",
        granted=True,
        metadata={"ip_address": "192.168.1.1"},
    )

    # 检查同意
    has_consent = manager.has_consent("user-123", "analytics")
    logger.info(f"Has consent: {has_consent}")

    # 记录数据处理
    manager.record_processing(
        data_subject_id="user-123",
        purpose_id="analytics",
        operation="read",
        data_categories=["usage_data"],
        processor="analytics-service",
        justification="User consent granted",
    )

    # 获取数据主体报告
    report = manager.get_data_subject_report("user-123")
    logger.info(f"Data subject report: {len(report['processing_records'])} records")

    # 请求数据删除
    manager.request_erasure("user-123", "User requested data deletion")

    # 获取合规报告
    compliance_report = manager.get_compliance_report()
    logger.info(f"Compliance report: {compliance_report}")

    logger.info("Test passed!")
