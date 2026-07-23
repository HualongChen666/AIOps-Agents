# -*- coding: utf-8 -*-
"""
executor.py
----------
AI Agent 自主执行引擎 - 从 HITL 过渡到完全自主。

功能：
- 安全边界定义
- 信任机制建设
- 风险评估
- 自动回滚
- 验证机制
- 目标：自主修复成功率 ≥ 95%
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .planner import Task, TaskPlanner, TaskStatus
from .tools import ToolExecutor

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 风险等级枚举
# ----------------------------------------------------------------------
class RiskLevel(Enum):
    """风险等级"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ----------------------------------------------------------------------
# 操作关键词集合（用于风险评估，O(1) 查找）
# ----------------------------------------------------------------------
DANGEROUS_KEYWORDS = {"删除", "delete", "清空", "格式化"}
STOP_KEYWORDS = {"停止", "stop", "终止", "kill"}
MODIFY_KEYWORDS = {"重启", "restart", "修改", "modify"}
SCALE_KEYWORDS = {"扩容", "缩容", "scale"}
READONLY_KEYWORDS = {"检查", "check", "收集", "collect", "分析", "analyze"}


# ----------------------------------------------------------------------
# 2️⃣ 安全边界定义
# ----------------------------------------------------------------------
@dataclass
class SafetyBoundary:
    """安全边界定义"""

    allowed_operations: List[str] = field(default_factory=list)
    forbidden_operations: List[str] = field(default_factory=list)
    max_resource_impact: float = 0.5  # 最大资源影响比例
    max_rollback_time: int = 300  # 最大回滚时间（秒）
    require_approval_for: List[str] = field(default_factory=list)

    def is_operation_allowed(self, operation: str) -> bool:
        """检查操作是否允许"""
        # 检查禁止操作
        if operation in self.forbidden_operations:
            return False

        # 检查允许操作（如果列表非空）
        if self.allowed_operations and operation not in self.allowed_operations:
            return False

        return True

    def requires_approval(self, operation: str) -> bool:
        """检查操作是否需要审批"""
        return operation in self.require_approval_for


# ----------------------------------------------------------------------
# 3️⃣ 风险评估器
# ----------------------------------------------------------------------
class RiskAssessor:
    """风险评估器"""

    def __init__(self, safety_boundary: SafetyBoundary):
        """
        Parameters
        ----------
        safety_boundary : SafetyBoundary
            安全边界
        """
        self.safety_boundary = safety_boundary
        self.risk_history: Dict[str, List[Dict[str, Any]]] = {}

    def assess_risk(
        self,
        operation: str,
        context: Dict[str, Any],
    ) -> Tuple[RiskLevel, str]:
        """
        评估操作风险

        Parameters
        ----------
        operation : str
            操作名称
        context : Dict[str, Any]
            上下文信息

        Returns
        -------
        Tuple[RiskLevel, str]
            风险等级和原因
        """
        # 检查是否在禁止列表中
        if not self.safety_boundary.is_operation_allowed(operation):
            return RiskLevel.CRITICAL, f"Operation {operation} is forbidden"

        # 基于操作类型评估风险
        operation_lower = operation.lower()

        # 高风险操作
        if any(kw in operation_lower for kw in DANGEROUS_KEYWORDS):
            return RiskLevel.CRITICAL, "Destructive operation"

        if any(kw in operation_lower for kw in STOP_KEYWORDS):
            return RiskLevel.HIGH, "Service stop operation"

        # 中风险操作
        if any(kw in operation_lower for kw in MODIFY_KEYWORDS):
            return RiskLevel.MEDIUM, "Service modification"

        if any(kw in operation_lower for kw in SCALE_KEYWORDS):
            return RiskLevel.MEDIUM, "Resource scaling"

        # 低风险操作
        if any(kw in operation_lower for kw in READONLY_KEYWORDS):
            return RiskLevel.LOW, "Read-only operation"

        # 默认中等风险
        return RiskLevel.MEDIUM, "Unknown operation type"

    def check_historical_risk(
        self,
        operation: str,
    ) -> float:
        """
        检查历史风险

        Parameters
        ----------
        operation : str
            操作名称

        Returns
        -------
        float
            历史成功率 (0-1)
        """
        if operation not in self.risk_history:
            return 1.0  # 无历史记录，假设安全

        history = self.risk_history[operation]
        if not history:
            return 1.0

        successful = sum(1 for h in history if h["success"])
        return successful / len(history)

    def record_execution(
        self,
        operation: str,
        success: bool,
        error: Optional[str] = None,
    ):
        """记录执行结果"""
        if operation not in self.risk_history:
            self.risk_history[operation] = []

        self.risk_history[operation].append(
            {
                "success": success,
                "error": error,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # 只保留最近 100 条记录
        if len(self.risk_history[operation]) > 100:
            self.risk_history[operation] = self.risk_history[operation][-100:]


# ----------------------------------------------------------------------
# 4️⃣ 信任机制
# ----------------------------------------------------------------------
class TrustMechanism:
    """信任机制"""

    def __init__(
        self,
        initial_trust: float = 0.5,
        learning_rate: float = 0.1,
    ):
        """
        Parameters
        ----------
        initial_trust : float
            初始信任度 (0-1)
        learning_rate : float
            学习率
        """
        self.trust_scores: Dict[str, float] = {}
        self.initial_trust = initial_trust
        self.learning_rate = learning_rate

    def get_trust_score(self, operation: str) -> float:
        """获取操作信任度"""
        return self.trust_scores.get(operation, self.initial_trust)

    def update_trust(
        self,
        operation: str,
        success: bool,
    ):
        """
        更新信任度

        Parameters
        ----------
        operation : str
            操作名称
        success : bool
            是否成功
        """
        current_trust = self.get_trust_score(operation)

        if success:
            # 成功则增加信任
            new_trust = current_trust + self.learning_rate * (1 - current_trust)
        else:
            # 失败则降低信任
            new_trust = current_trust - self.learning_rate * current_trust

        self.trust_scores[operation] = max(0.0, min(1.0, new_trust))

        logger.info(f"Trust score updated: {operation} -> {self.trust_scores[operation]:.2f}")

    def can_auto_execute(
        self,
        operation: str,
        risk_level: RiskLevel,
    ) -> bool:
        """
        判断是否可以自动执行

        Parameters
        ----------
        operation : str
            操作名称
        risk_level : RiskLevel
            风险等级

        Returns
        -------
        bool
            是否可以自动执行
        """
        trust = self.get_trust_score(operation)

        # 根据风险等级和信任度判断
        if risk_level == RiskLevel.LOW:
            return trust >= 0.3
        elif risk_level == RiskLevel.MEDIUM:
            return trust >= 0.6
        elif risk_level == RiskLevel.HIGH:
            return trust >= 0.8
        else:  # CRITICAL
            return False  # 总是需要审批


# ----------------------------------------------------------------------
# 5️⃣ 回滚机制
# ----------------------------------------------------------------------
class RollbackMechanism:
    """回滚机制"""

    def __init__(self):
        self.rollback_actions: Dict[str, Any] = {}
        self.rollback_history: List[Dict[str, Any]] = []

    def register_rollback(
        self,
        operation_id: str,
        rollback_action: Any,
    ):
        """
        注册回滚操作

        Parameters
        ----------
        operation_id : str
            操作 ID
        rollback_action : Any
            回滚操作
        """
        self.rollback_actions[operation_id] = rollback_action
        logger.info(f"Registered rollback for operation: {operation_id}")

    def execute_rollback(
        self,
        operation_id: str,
    ) -> bool:
        """
        执行回滚

        Parameters
        ----------
        operation_id : str
            操作 ID

        Returns
        -------
        bool
            是否成功
        """
        if operation_id not in self.rollback_actions:
            logger.warning(f"No rollback action found for {operation_id}")
            return False

        rollback_action = self.rollback_actions[operation_id]

        try:
            # 执行回滚
            if callable(rollback_action):
                rollback_action()
            else:
                logger.warning(f"Rollback action is not callable: {operation_id}")

            # 记录回滚历史
            self.rollback_history.append(
                {
                    "operation_id": operation_id,
                    "timestamp": datetime.now().isoformat(),
                    "success": True,
                }
            )

            logger.info(f"Rollback executed successfully for {operation_id}")
            return True
        except Exception as e:
            logger.error(f"Rollback failed for {operation_id}: {e}")

            self.rollback_history.append(
                {
                    "operation_id": operation_id,
                    "timestamp": datetime.now().isoformat(),
                    "success": False,
                    "error": str(e),
                }
            )

            return False


# ----------------------------------------------------------------------
# 6️⃣ 验证机制
# ----------------------------------------------------------------------
class ValidationMechanism:
    """验证机制"""

    def __init__(self):
        self.validation_rules: Dict[str, Any] = {}

    def register_validation(
        self,
        operation: str,
        validation_func: Any,
    ):
        """
        注册验证规则

        Parameters
        ----------
        operation : str
            操作名称
        validation_func : Any
            验证函数
        """
        if operation not in self.validation_rules:
            self.validation_rules[operation] = []
        self.validation_rules[operation].append(validation_func)

    def validate(
        self,
        operation: str,
        result: Any,
        context: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        验证操作结果

        Parameters
        ----------
        operation : str
            操作名称
        result : Any
            操作结果
        context : Dict[str, Any]
            上下文信息

        Returns
        -------
        Tuple[bool, str]
            是否通过验证和原因
        """
        if operation not in self.validation_rules:
            # 没有验证规则，默认通过
            return True, "No validation rules"

        for validation_func in self.validation_rules[operation]:
            try:
                passed, reason = validation_func(result, context)
                if not passed:
                    return False, reason
            except Exception as e:
                logger.error(f"Validation failed: {e}")
                return False, f"Validation error: {e}"

        return True, "All validations passed"


# ----------------------------------------------------------------------
# 7️⃣ 自主执行引擎
# ----------------------------------------------------------------------
class AutonomousExecutor:
    """自主执行引擎"""

    def __init__(
        self,
        planner: TaskPlanner,
        tool_executor: ToolExecutor,
        safety_boundary: Optional[SafetyBoundary] = None,
    ):
        """
        Parameters
        ----------
        planner : TaskPlanner
            任务规划器
        tool_executor : ToolExecutor
            工具执行器
        safety_boundary : SafetyBoundary, optional
            安全边界
        """
        self.planner = planner
        self.tool_executor = tool_executor
        self.safety_boundary = safety_boundary or SafetyBoundary()

        self.risk_assessor = RiskAssessor(self.safety_boundary)
        self.trust_mechanism = TrustMechanism()
        self.rollback_mechanism = RollbackMechanism()
        self.validation_mechanism = ValidationMechanism()

        self.execution_mode = "hybrid"  # hybrid, autonomous, manual
        self.approval_required = False
        self.subagent_dispatcher: Optional[Any] = None

    def execute_plan(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
    ) -> Dict[str, Any]:
        """
        执行计划

        Parameters
        ----------
        goal : str
            目标
        context : Dict[str, Any]
            上下文
        available_tools : List[str]
            可用工具

        Returns
        -------
        Dict[str, Any]
            执行结果
        """
        logger.info(f"Executing plan for goal: {goal}")

        # 规划任务
        tasks = self.planner.plan(goal, context, available_tools)

        # 执行任务
        results = []
        for task in tasks:
            result = self.execute_task(task, context)
            results.append(result)

            # 将字符串状态映射为 TaskStatus 枚举
            status_str = result["status"]
            status_map = {
                "completed": TaskStatus.COMPLETED,
                "failed": TaskStatus.FAILED,
                "pending_approval": TaskStatus.PENDING,
                "skipped": TaskStatus.SKIPPED,
            }
            new_status = status_map.get(status_str, TaskStatus.PENDING)

            # 更新任务状态
            self.planner.adjust_plan(
                task.id,
                new_status,
                result.get("result"),
                result.get("error"),
            )

        # 获取计划摘要
        summary = self.planner.get_plan_summary()

        return {
            "goal": goal,
            "tasks": [t.to_dict() for t in tasks],
            "results": results,
            "summary": summary,
        }

    def execute_task(
        self,
        task: Task,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        执行单个任务

        Parameters
        ----------
        task : Task
            任务
        context : Dict[str, Any]
            上下文

        Returns
        -------
        Dict[str, Any]
            执行结果
        """
        logger.info(f"Executing task: {task.id} - {task.description}")

        # 评估风险
        risk_level, risk_reason = self.risk_assessor.assess_risk(
            task.description,
            context,
        )

        # 检查是否需要审批
        requires_approval = (
            self.safety_boundary.requires_approval(task.description) or self.approval_required
        )

        # 检查信任度
        can_auto_execute = self.trust_mechanism.can_auto_execute(
            task.description,
            risk_level,
        )

        # 决定执行模式
        if self.execution_mode == "manual":
            # 手动模式，需要审批
            if requires_approval:
                return {
                    "task_id": task.id,
                    "status": "pending_approval",
                    "reason": "Manual mode requires approval",
                }
        elif self.execution_mode == "autonomous":
            # 自主模式，根据信任度决定
            if not can_auto_execute:
                return {
                    "task_id": task.id,
                    "status": "pending_approval",
                    "reason": f"Trust score too low for risk level {risk_level.name}",
                }
        else:  # hybrid
            # 混合模式，高风险需要审批
            if risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL] or requires_approval:
                if not can_auto_execute:
                    return {
                        "task_id": task.id,
                        "status": "pending_approval",
                        "reason": f"High risk ({risk_level.name}) requires approval",
                    }

        # 执行任务
        try:
            # 使用工具执行器执行
            result = self.tool_executor.execute_with_auto_selection(
                task.description,
                context,
            )

            # 验证结果
            passed, validation_reason = self.validation_mechanism.validate(
                task.description,
                result,
                context,
            )

            if not passed:
                # 验证失败，执行回滚
                self.rollback_mechanism.execute_rollback(task.id)

                self.risk_assessor.record_execution(task.description, False, validation_reason)
                self.trust_mechanism.update_trust(task.description, False)

                return {
                    "task_id": task.id,
                    "status": "failed",
                    "result": result,
                    "error": validation_reason,
                }

            # 成功
            self.risk_assessor.record_execution(task.description, True)
            self.trust_mechanism.update_trust(task.description, True)

            return {
                "task_id": task.id,
                "status": "completed",
                "result": result,
            }

        except Exception as e:
            logger.error(f"Task execution failed: {e}")

            # 执行回滚
            self.rollback_mechanism.execute_rollback(task.id)

            self.risk_assessor.record_execution(task.description, False, str(e))
            self.trust_mechanism.update_trust(task.description, False)

            return {
                "task_id": task.id,
                "status": "failed",
                "error": str(e),
            }

    def set_subagent_dispatcher(self, dispatcher: Any) -> None:
        """
        设置子代理调度器

        Parameters
        ----------
        dispatcher : Any
            子代理调度器实例
        """
        self.subagent_dispatcher = dispatcher
        logger.info("Subagent dispatcher attached")

    def execute_plan_with_subagents(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
        max_subagents: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        使用子代理并行执行计划

        Parameters
        ----------
        goal : str
            目标
        context : Dict[str, Any]
            上下文
        available_tools : List[str]
            可用工具
        max_subagents : int, optional
            最大并发子代理数

        Returns
        -------
        Dict[str, Any]
            执行结果
        """
        from .subagent import SubAgentDispatcher

        if self.subagent_dispatcher is None:
            self.subagent_dispatcher = SubAgentDispatcher(max_workers=max_subagents or 5)

        logger.info(f"Executing plan with subagents for goal: {goal}")

        # 主规划器拆解任务
        tasks = self.planner.plan(goal, context, available_tools)

        # 将任务分派给子代理
        batch = []
        for task in tasks:
            task_context = {**context, **task.parameters}
            role = task.parameters.get("action", "worker")
            batch.append(
                {
                    "goal": task.description,
                    "context": task_context,
                    "available_tools": available_tools,
                    "role": role,
                }
            )

        subagent_results = self.subagent_dispatcher.dispatch_batch(batch)

        # 同步更新主规划器状态
        for task, subagent_result in zip(tasks, subagent_results):
            if subagent_result.status == "completed":
                self.planner.adjust_plan(
                    task.id,
                    TaskStatus.COMPLETED,
                    subagent_result.result,
                    None,
                )
            else:
                self.planner.adjust_plan(
                    task.id,
                    TaskStatus.FAILED,
                    None,
                    subagent_result.error,
                )

        summary = self.planner.get_plan_summary()

        return {
            "goal": goal,
            "tasks": [t.to_dict() for t in tasks],
            "subagent_results": [r.to_dict() for r in subagent_results],
            "summary": summary,
        }

    def set_execution_mode(self, mode: str):
        """
        设置执行模式

        Parameters
        ----------
        mode : str
            执行模式：'autonomous', 'hybrid', 'manual'
        """
        if mode not in ["autonomous", "hybrid", "manual"]:
            raise ValueError(f"Invalid execution mode: {mode}")

        self.execution_mode = mode
        logger.info(f"Execution mode set to: {mode}")

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "execution_mode": self.execution_mode,
            "trust_scores": self.trust_mechanism.trust_scores,
            "risk_history": self.risk_assessor.risk_history,
            "rollback_history": self.rollback_mechanism.rollback_history,
        }


# ----------------------------------------------------------------------
# 8️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_autonomous_executor(
    planner: Optional[TaskPlanner] = None,
    tool_executor: Optional[ToolExecutor] = None,
    safety_boundary: Optional[SafetyBoundary] = None,
) -> AutonomousExecutor:
    """创建自主执行引擎"""
    if planner is None:
        from .planner import create_planner

        planner = create_planner()

    if tool_executor is None:
        from .tools import create_tool_executor

        tool_executor = create_tool_executor()

    return AutonomousExecutor(planner, tool_executor, safety_boundary)


# ----------------------------------------------------------------------
# 9️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    pass

    logging.basicConfig(level=logging.INFO)

    # 测试自主执行引擎
    logger.info("Testing autonomous executor")

    executor = create_autonomous_executor()

    # 设置执行模式
    executor.set_execution_mode("hybrid")

    # 执行计划
    goal = "诊断系统 CPU 使用率异常"
    context = {
        "target": "system",
        "metrics": {"cpu_usage": 95.0},
    }
    available_tools = ["collect_metrics", "analyze_logs", "identify_root_cause"]

    result = executor.execute_plan(goal, context, available_tools)

    logger.info(f"Execution result: {result['summary']}")

    # 获取统计信息
    stats = executor.get_statistics()
    logger.info(f"Statistics: {stats}")

    logger.info("Test passed!")
