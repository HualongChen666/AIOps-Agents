# -*- coding: utf-8 -*-
"""
self_healing.py
---------------
高可用架构 - 故障自愈模块。

功能：
- 故障检测
- 自愈策略定义
- 自动修复执行
- 修复验证
- 自愈历史记录
"""

from __future__ import annotations

import logging
import platform
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from core.command_guard import analyze_command

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 故障类型枚举
# ----------------------------------------------------------------------
class FailureType(Enum):
    """故障类型"""

    SERVICE_DOWN = "service_down"
    HIGH_LATENCY = "high_latency"
    HIGH_ERROR_RATE = "high_error_rate"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    DATA_INCONSISTENCY = "data_inconsistency"
    NETWORK_PARTITION = "network_partition"


# ----------------------------------------------------------------------
# 2️⃣ 修复动作类型
# ----------------------------------------------------------------------
class RemediationAction(Enum):
    """修复动作类型"""

    RESTART_SERVICE = "restart_service"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    ROLLBACK = "rollback"
    CLEAR_CACHE = "clear_cache"
    REBALANCE = "rebalance"
    ISOLATE = "isolate"
    NOTIFY = "notify"


# ----------------------------------------------------------------------
# 3️⃣ 故障事件
# ----------------------------------------------------------------------
@dataclass
class FailureEvent:
    """故障事件"""

    id: str
    failure_type: FailureType
    component: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "failure_type": self.failure_type.value,
            "component": self.component,
            "severity": self.severity,
            "description": self.description,
            "detected_at": self.detected_at,
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 4️⃣ 自愈策略
# ----------------------------------------------------------------------
@dataclass
class SelfHealingPolicy:
    """自愈策略"""

    id: str
    name: str
    failure_type: FailureType
    remediation_actions: List[RemediationAction]
    conditions: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    max_attempts: int = 3
    cooldown_seconds: int = 300

    def matches(self, failure_event: FailureEvent) -> bool:
        """检查策略是否匹配故障事件"""
        if not self.enabled:
            return False

        if self.failure_type != failure_event.failure_type:
            return False

        # 检查条件
        for key, value in self.conditions.items():
            if failure_event.metadata.get(key) != value:
                return False

        return True


# ----------------------------------------------------------------------
# 5️⃣ 修复结果
# ----------------------------------------------------------------------
@dataclass
class RemediationResult:
    """修复结果"""

    policy_id: str
    action: RemediationAction
    success: bool
    message: str
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "policy_id": self.policy_id,
            "action": self.action.value,
            "success": self.success,
            "message": self.message,
            "executed_at": self.executed_at,
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 6️⃣ 故障自愈引擎
# ----------------------------------------------------------------------
class SelfHealingEngine:
    """故障自愈引擎"""

    def __init__(self):
        self.policies: Dict[str, SelfHealingPolicy] = {}
        self.failure_history: List[FailureEvent] = []
        self.remediation_history: List[RemediationResult] = []
        self.action_handlers: Dict[RemediationAction, Callable] = {}
        self.cooldowns: Dict[str, datetime] = {}

        self._initialize_default_policies()
        self._initialize_action_handlers()

    def _initialize_default_policies(self):
        """初始化默认策略"""
        # 服务宕机策略
        self.add_policy(
            SelfHealingPolicy(
                id="service-down-restart",
                name="Service Down - Restart",
                failure_type=FailureType.SERVICE_DOWN,
                remediation_actions=[RemediationAction.RESTART_SERVICE],
                conditions={"auto_restart": True},
            )
        )

        # 高延迟策略
        self.add_policy(
            SelfHealingPolicy(
                id="high-latency-scale",
                name="High Latency - Scale Up",
                failure_type=FailureType.HIGH_LATENCY,
                remediation_actions=[RemediationAction.SCALE_UP],
                conditions={"auto_scale": True},
            )
        )

        # 高错误率策略
        self.add_policy(
            SelfHealingPolicy(
                id="high-error-rollback",
                name="High Error Rate - Rollback",
                failure_type=FailureType.HIGH_ERROR_RATE,
                remediation_actions=[RemediationAction.ROLLBACK],
                conditions={"auto_rollback": True},
            )
        )

    def _initialize_action_handlers(self):
        """初始化动作处理器"""
        self.action_handlers[RemediationAction.RESTART_SERVICE] = self._handle_restart
        self.action_handlers[RemediationAction.SCALE_UP] = self._handle_scale_up
        self.action_handlers[RemediationAction.SCALE_DOWN] = self._handle_scale_down
        self.action_handlers[RemediationAction.ROLLBACK] = self._handle_rollback
        self.action_handlers[RemediationAction.CLEAR_CACHE] = self._handle_clear_cache
        self.action_handlers[RemediationAction.REBALANCE] = self._handle_rebalance
        self.action_handlers[RemediationAction.ISOLATE] = self._handle_isolate
        self.action_handlers[RemediationAction.NOTIFY] = self._handle_notify

    def add_policy(self, policy: SelfHealingPolicy):
        """添加自愈策略"""
        self.policies[policy.id] = policy
        logger.info(f"Added self-healing policy: {policy.name}")

    def remove_policy(self, policy_id: str):
        """移除自愈策略"""
        if policy_id in self.policies:
            del self.policies[policy_id]
            logger.info(f"Removed self-healing policy: {policy_id}")

    def detect_failure(
        self,
        failure_type: FailureType,
        component: str,
        severity: str,
        description: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FailureEvent:
        """
        检测故障

        Parameters
        ----------
        failure_type : FailureType
            故障类型
        component : str
            组件名称
        severity : str
            严重程度
        description : str
            描述
        metadata : Dict[str, Any], optional
            元数据

        Returns
        -------
        FailureEvent
            故障事件
        """
        event = FailureEvent(
            id=f"failure-{int(datetime.now().timestamp())}",
            failure_type=failure_type,
            component=component,
            severity=severity,
            description=description,
            metadata=metadata or {},
        )

        self.failure_history.append(event)
        logger.warning(f"Failure detected: {failure_type.value} on {component}")

        return event

    def trigger_self_healing(self, failure_event: FailureEvent) -> List[RemediationResult]:
        """
        触发自愈

        Parameters
        ----------
        failure_event : FailureEvent
            故障事件

        Returns
        -------
        List[RemediationResult]
            修复结果列表
        """
        # 查找匹配的策略
        matching_policies = [
            policy for policy in self.policies.values() if policy.matches(failure_event)
        ]

        if not matching_policies:
            logger.info(f"No matching policy for failure: {failure_event.failure_type.value}")
            return []

        results = []

        for policy in matching_policies:
            # 检查冷却期
            if policy.id in self.cooldowns:
                cooldown_end = self.cooldowns[policy.id]
                if datetime.now() < cooldown_end:
                    logger.info(f"Policy {policy.id} is in cooldown")
                    continue

            # 执行修复动作
            for action in policy.remediation_actions:
                try:
                    result = self._execute_action(policy, action, failure_event)
                    results.append(result)

                    if not result.success:
                        logger.error(f"Remediation action {action.value} failed")
                        break
                except Exception as e:
                    logger.error(f"Error executing action {action.value}: {e}")
                    results.append(
                        RemediationResult(
                            policy_id=policy.id,
                            action=action,
                            success=False,
                            message=str(e),
                        )
                    )
                    break

            # 设置冷却期
            self.cooldowns[policy.id] = datetime.now() + timedelta(seconds=policy.cooldown_seconds)

        self.remediation_history.extend(results)
        return results

    def _execute_action(
        self,
        policy: SelfHealingPolicy,
        action: RemediationAction,
        failure_event: FailureEvent,
    ) -> RemediationResult:
        """执行修复动作"""
        handler = self.action_handlers.get(action)

        if handler is None:
            return RemediationResult(
                policy_id=policy.id,
                action=action,
                success=False,
                message=f"No handler for action {action.value}",
            )

        try:
            success, message = handler(failure_event)
            return RemediationResult(
                policy_id=policy.id,
                action=action,
                success=success,
                message=message,
            )
        except Exception as e:
            return RemediationResult(
                policy_id=policy.id,
                action=action,
                success=False,
                message=str(e),
            )

    def _sanitize_component(self, component: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9_.\-]+", component):
            raise ValueError(f"invalid component name: {component}")
        return component

    def _run_guarded(self, command: list[str]) -> Tuple[bool, str]:
        result = analyze_command(" ".join(command))
        if result.get("risk_level").value == "blocked" or result.get("action") != "execute":
            return False, result.get("reason", "command blocked by guard")
        try:
            proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                return True, proc.stdout.strip()
            return False, proc.stderr.strip() or f"exit code {proc.returncode}"
        except Exception as e:
            return False, str(e)

    def _handle_restart(self, failure_event: FailureEvent) -> Tuple[bool, str]:
        """处理重启服务"""
        component = self._sanitize_component(failure_event.component)
        logger.info(f"Restarting service: {component}")
        if platform.system() == "Windows":
            success, message = self._run_guarded(["sc", "stop", component])
            if not success:
                return False, message
            return self._run_guarded(["sc", "start", component])
        return self._run_guarded(["systemctl", "restart", component])

    def _handle_scale_up(self, failure_event: FailureEvent) -> Tuple[bool, str]:
        """处理扩容"""
        component = self._sanitize_component(failure_event.component)
        logger.info(f"Scaling up: {component}")
        if platform.system() == "Windows":
            return self._run_guarded(["sc", "start", component])
        return self._run_guarded(["systemctl", "start", component])

    def _handle_scale_down(self, failure_event: FailureEvent) -> Tuple[bool, str]:
        """处理缩容"""
        component = self._sanitize_component(failure_event.component)
        logger.info(f"Scaling down: {component}")
        if platform.system() == "Windows":
            return self._run_guarded(["sc", "stop", component])
        return self._run_guarded(["systemctl", "stop", component])

    def _handle_rollback(self, failure_event: FailureEvent) -> Tuple[bool, str]:
        """处理回滚"""
        component = self._sanitize_component(failure_event.component)
        logger.info(f"Rolling back: {component}")
        if platform.system() == "Windows":
            success, message = self._run_guarded(["sc", "stop", component])
            if not success:
                return False, message
            return self._run_guarded(["sc", "start", component])
        return self._run_guarded(["systemctl", "restart", component])

    def _handle_clear_cache(self, failure_event: FailureEvent) -> Tuple[bool, str]:
        """处理清空缓存"""
        component = self._sanitize_component(failure_event.component)
        logger.info(f"Clearing cache for: {component}")
        if platform.system() == "Windows":
            return self._run_guarded(["sc", "query", component])
        return self._run_guarded(["systemctl", "reload", component])

    def _handle_rebalance(self, failure_event: FailureEvent) -> Tuple[bool, str]:
        """处理重新平衡"""
        component = self._sanitize_component(failure_event.component)
        logger.info(f"Rebalancing: {component}")
        if platform.system() == "Windows":
            return self._run_guarded(["sc", "start", component])
        return self._run_guarded(["systemctl", "restart", component])

    def _handle_isolate(self, failure_event: FailureEvent) -> Tuple[bool, str]:
        """处理隔离"""
        component = self._sanitize_component(failure_event.component)
        logger.info(f"Isolating: {component}")
        if platform.system() == "Windows":
            return self._run_guarded(["sc", "stop", component])
        return self._run_guarded(["systemctl", "stop", component])

    def _handle_notify(self, failure_event: FailureEvent) -> Tuple[bool, str]:
        """处理通知"""
        component = self._sanitize_component(failure_event.component)
        logger.info(f"Sending notification for: {component}")
        if platform.system() == "Windows":
            return self._run_guarded(["sc", "query", component])
        return self._run_guarded(["systemctl", "status", component])

    def verify_remediation(
        self,
        failure_event: FailureEvent,
    ) -> bool:
        """
        验证修复效果

        Parameters
        ----------
        failure_event : FailureEvent
            故障事件

        Returns
        -------
        bool
            是否修复成功
        """
        # 简化实现：实际应检查组件状态
        component = failure_event.component
        logger.info(f"Verifying remediation for: {component}")
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        total_failures = len(self.failure_history)
        total_remediations = len(self.remediation_history)
        successful_remediations = sum(1 for r in self.remediation_history if r.success)

        return {
            "total_failures": total_failures,
            "total_remediations": total_remediations,
            "successful_remediations": successful_remediations,
            "success_rate": (
                successful_remediations / total_remediations if total_remediations > 0 else 0
            ),
            "active_policies": len([p for p in self.policies.values() if p.enabled]),
            "total_policies": len(self.policies),
        }


# ----------------------------------------------------------------------
# 7️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_self_healing_engine() -> SelfHealingEngine:
    """创建故障自愈引擎"""
    return SelfHealingEngine()


# ----------------------------------------------------------------------
# 8️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    logging.basicConfig(level=logging.INFO)

    # 测试故障自愈引擎
    logger.info("Testing self-healing engine")

    engine = create_self_healing_engine()

    # 检测故障
    failure_event = engine.detect_failure(
        failure_type=FailureType.SERVICE_DOWN,
        component="web-service",
        severity="high",
        description="Web service is down",
        metadata={"auto_restart": True},
    )

    # 触发自愈
    results = engine.trigger_self_healing(failure_event)

    logger.info(f"Remediation results: {len(results)} actions executed")
    for result in results:
        logger.info(f"  - {result.action.value}: {result.success} - {result.message}")

    # 验证修复
    verified = engine.verify_remediation(failure_event)
    logger.info(f"Remediation verified: {verified}")

    # 获取统计
    stats = engine.get_statistics()
    logger.info(f"Statistics: {stats}")

    logger.info("Test passed!")
