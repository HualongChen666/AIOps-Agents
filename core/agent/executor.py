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

import copy
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..command_guard import RiskLevel
from .behavior_monitor import get_behavior_monitor
from .memory_bridge import MemoryBridge, _action_signature
from .planner import Task, TaskPlanner, TaskStatus
from .state import DiagnosticState
from .tools import ToolCategory, ToolExecutor

logger = logging.getLogger(__name__)

try:
    from core.audit_logger import log_audit_event as _log_audit_event

    AUDIT_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    AUDIT_AVAILABLE = False
    _log_audit_event = None  # type: ignore[assignment]


def _audit_executor(
    agent_id: str,
    action: str,
    resource: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Best-effort audit wrapper for agent execution events."""
    if AUDIT_AVAILABLE and _log_audit_event:
        try:
            _log_audit_event(
                event_type="AGENT_EXECUTION",
                user=agent_id,
                resource=resource,
                action=action,
                status=status,
                details=details or {},
            )
        except Exception as exc:
            logger.warning(f"Agent audit log failed: {exc}")


# ----------------------------------------------------------------------
# 操作关键词集合（用于风险评估，O(1) 查找）
# ----------------------------------------------------------------------
DANGEROUS_KEYWORDS = {"删除", "delete", "清空", "格式化"}
STOP_KEYWORDS = {"停止", "stop", "终止", "kill"}
MODIFY_KEYWORDS = {"重启", "restart", "修改", "modify"}
SCALE_KEYWORDS = {"扩容", "缩容", "scale"}
READONLY_KEYWORDS = {"检查", "check", "收集", "collect", "分析", "analyze"}

# 置信度阈值：低于该值时不得自动执行修复操作
EXECUTION_CONFIDENCE_THRESHOLD = 0.75


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
        tool_category: Optional[ToolCategory] = None,
    ) -> Tuple[RiskLevel, str]:
        """
        评估操作风险

        Parameters
        ----------
        operation : str
            操作名称
        context : Dict[str, Any]
            上下文信息
        tool_category : ToolCategory, optional
            工具类别，用于更准确地判定操作风险。

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

        # 若提供了工具类别，据此进一步判定
        if tool_category == ToolCategory.EXECUTION:
            return RiskLevel.MEDIUM, "Execution tool requires confirmation"
        if tool_category in (
            ToolCategory.DIAGNOSTIC,
            ToolCategory.MONITORING,
            ToolCategory.ANALYSIS,
        ):
            return RiskLevel.LOW, "Read-only/observability operation"

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
        dry_run: bool = False,
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
        dry_run : bool
            如为 True，所有执行类工具仅返回预演结果。
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
        self.dry_run = dry_run
        self.subagent_dispatcher: Optional[Any] = None

        # Anti-DoS / anti-loop limits
        self.max_tasks = 20
        self.max_iterations = 50
        self.max_subagent_depth = 3

        # Propagate dry-run and timeout settings to tool executor
        if self.dry_run:
            self.tool_executor.dry_run = True

        # Propagate safety boundary and execution mode to subagents later

        # O21: behavior anomaly monitor per executor instance
        self.behavior_monitor = get_behavior_monitor()
        self.agent_id = f"agent_{uuid.uuid4().hex[:12]}"

        # Cross-session memory bridge (lazy, can be disabled by setting to None)
        self.memory_bridge: Optional[MemoryBridge] = None

    def set_memory_bridge(self, bridge: Optional[MemoryBridge]) -> None:
        """Attach or detach a cross-session memory bridge."""
        self.memory_bridge = bridge

    def execute_plan(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
        _depth: int = 0,
    ) -> Dict[str, Any]:
        """
        执行计划（增强版：会话隔离、结构化诊断状态、动作级循环检测、跨会话记忆）
        """
        logger.info(f"Executing plan for goal: {goal} (depth={_depth})")
        _audit_executor(
            self.agent_id,
            "execute_plan_start",
            str(goal)[:128],
            "success",
            {"session_id": context.get("session_id"), "depth": _depth},
        )

        # Multi-session isolation: deep-copy the context so concurrent sessions
        # or subagents cannot mutate each other's mutable objects.
        context = copy.deepcopy(context)

        # Ensure every execution has a session id.
        if "session_id" not in context or not context["session_id"]:
            context["session_id"] = str(uuid.uuid4())

        # Structured diagnostic state: create or deserialize.
        diag_state = context.get("diagnostic_state")
        if isinstance(diag_state, dict):
            diag_state = DiagnosticState.from_dict(diag_state)
        elif not isinstance(diag_state, DiagnosticState):
            diag_state = DiagnosticState()
        context["diagnostic_state"] = diag_state

        # O21: record each planning iteration and check for anomalous behavior
        self.behavior_monitor.record_iteration(self.agent_id)
        anomaly = self.behavior_monitor.check_anomaly(self.agent_id)
        if anomaly:
            return {
                "goal": goal,
                "tasks": [],
                "results": [],
                "summary": {},
                "error": f"Behavior anomaly detected: {anomaly.get('messages')}",
                "behavior_alert": anomaly,
            }

        if _depth > self.max_subagent_depth:
            self.behavior_monitor.record_error(self.agent_id)
            return {
                "goal": goal,
                "tasks": [],
                "results": [],
                "summary": {},
                "error": f"Maximum subagent recursion depth {self.max_subagent_depth} exceeded",
            }

        # Anti-loop: track visited goals in context
        visited_goals: set = context.get("__visited_goals", set())
        if goal in visited_goals:
            return {
                "goal": goal,
                "tasks": [],
                "results": [],
                "summary": {},
                "error": "Repeated goal detected; aborting to prevent loop",
            }
        visited_goals = set(visited_goals)
        visited_goals.add(goal)
        context = {**context, "__visited_goals": visited_goals}

        # Action-level loop detection state.
        visited_actions: set = context.get("__visited_actions", set())
        execution_log: list = context.get("__execution_log", [])

        # Cross-session memory: retrieve relevant experiences before planning.
        if context.get("enable_memory", True) and self.memory_bridge is not None:
            try:
                relevant = self.memory_bridge.retrieve_relevant_experiences(
                    goal, top_k=3, session_id=context.get("session_id")
                )
                if relevant:
                    context["relevant_experiences"] = relevant
            except Exception as exc:
                logger.warning(f"Memory retrieval failed: {exc}")

        # 规划任务
        tasks = self.planner.plan(goal, context, available_tools)

        if len(tasks) > self.max_tasks:
            return {
                "goal": goal,
                "tasks": [t.to_dict() for t in tasks],
                "results": [],
                "summary": {},
                "error": f"Planned tasks ({len(tasks)}) exceed maximum {self.max_tasks}",
            }

        # 执行任务
        results = []
        executed = 0
        for task in tasks:
            executed += 1
            if executed > self.max_iterations:
                results.append(
                    {
                        "task_id": task.id,
                        "status": "failed",
                        "error": f"Maximum iteration count {self.max_iterations} reached",
                    }
                )
                self.behavior_monitor.record_error(self.agent_id)
                break

            # Resolve tool for loop-detection; in tests this may be a Mock.
            try:
                tool = self.tool_executor.selector.select_tool(task.description, context)
                tool_name = getattr(tool, "name", "")
                if not isinstance(tool_name, str):
                    tool_name = ""
            except Exception as e:
                logging.exception("Unexpected exception: %s", e)
                tool_name = ""

            # Parameter-level loop detection before execution.
            action_key = _action_signature(goal, task.description, tool_name, task.parameters)
            if action_key in visited_actions:
                result = {
                    "task_id": task.id,
                    "status": "failed",
                    "error": f"Repeated action signature detected; aborting to prevent loop: {action_key}",  # noqa: E501
                }
                self.behavior_monitor.record_error(self.agent_id)
                results.append(result)
                break
            visited_actions.add(action_key)

            # O21: record tool execution attempt and check for anomalies
            self.behavior_monitor.record_iteration(self.agent_id)
            result = self.execute_task(task, context, _depth=_depth)
            _audit_executor(
                self.agent_id,
                "execute_task",
                str(task.id),
                result.get("status", "unknown"),
                {
                    "tool": tool_name,
                    "error": result.get("error"),
                    "session_id": context.get("session_id"),
                },
            )
            if result.get("status") == "completed":
                self.behavior_monitor.record_tool_call(self.agent_id, tool_name or "auto_selected")
                self.behavior_monitor.record_action(self.agent_id, action_key)
            elif result.get("status") == "failed":
                self.behavior_monitor.record_error(self.agent_id)

            # Update execution log and structured diagnostic state.
            execution_log.append(
                {
                    "goal": goal,
                    "task": task.description,
                    "tool": tool_name,
                    "status": result.get("status"),
                    "error": result.get("error"),
                    "summary": str(result.get("result"))[:200],
                }
            )
            context["__execution_log"] = execution_log
            context["__visited_actions"] = visited_actions

            # Feed collected tool results back into context so downstream tools
            # (especially root_cause_analysis) can consume them.
            self._merge_tool_result_into_context(tool_name, result.get("result"), context)

            diag_state.update_from_task(
                task.description,
                result.get("result"),
                result.get("error"),
            )
            context["diagnostic_state"] = diag_state

            anomaly = self.behavior_monitor.check_anomaly(self.agent_id)
            if anomaly:
                result["behavior_alert"] = anomaly
                results.append(result)
                break

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
        summary["diagnostic_state"] = diag_state.to_dict()

        # Persist cross-session experience.
        if context.get("enable_memory", True) and self.memory_bridge is not None and tasks:
            try:
                memory_result = self.memory_bridge.save_experience(
                    goal=goal,
                    tasks=tasks,
                    results=results,
                    summary=summary,
                    session_id=context.get("session_id"),
                )
                if memory_result:
                    logger.info(f"Experience saved: {memory_result}")
                    summary["memory"] = memory_result
            except Exception as exc:
                logger.warning(f"Memory save failed: {exc}")

        return {
            "goal": goal,
            "tasks": [t.to_dict() for t in tasks],
            "results": results,
            "summary": summary,
            "diagnostic_state": diag_state.to_dict(),
            "session_id": context.get("session_id"),
        }

    def execute_task(
        self,
        task: Task,
        context: Dict[str, Any],
        _depth: int = 0,
    ) -> Dict[str, Any]:
        """
        执行单个任务

        Parameters
        ----------
        task : Task
            任务
        context : Dict[str, Any]
            上下文信息
        _depth : int
            当前子代理递归深度

        Returns
        -------
        Dict[str, Any]
            执行结果
        """
        logger.info(f"Executing task: {task.id} - {task.description}")
        _audit_executor(
            self.agent_id,
            "execute_task_attempt",
            str(task.id),
            "success",
            {"description": str(task.description)[:200], "session_id": context.get("session_id")},
        )

        # 选择合适的工具并基于工具类别评估风险
        tool = self.tool_executor.selector.select_tool(task.description, context)
        if tool is None:
            return {
                "task_id": task.id,
                "status": "failed",
                "error": f"No tool found for task: {task.description}",
            }

        risk_level, risk_reason = self.risk_assessor.assess_risk(
            task.description,
            context,
            tool_category=tool.category,
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

        # 置信度门控：修复类操作必须提供诊断置信度，且不得低于阈值
        execution_confidence = self._get_execution_confidence(context)
        is_remediation = self._is_remediation_action(task.description)
        low_confidence_reason = ""
        if is_remediation:
            if execution_confidence is None:
                can_auto_execute = False
                requires_approval = True
                low_confidence_reason = "Execution confidence is required for remediation actions"
            elif execution_confidence < EXECUTION_CONFIDENCE_THRESHOLD:
                can_auto_execute = False
                requires_approval = True
                low_confidence_reason = (
                    f"Execution confidence {execution_confidence:.2f} below threshold "
                    f"{EXECUTION_CONFIDENCE_THRESHOLD}"
                )

        # 决定执行模式
        if self.execution_mode == "manual":
            # 手动模式，需要审批
            if requires_approval:
                return {
                    "task_id": task.id,
                    "status": "pending_approval",
                    "reason": low_confidence_reason or "Manual mode requires approval",
                }
        elif self.execution_mode == "autonomous":
            # 自主模式，根据信任度和置信度决定
            if not can_auto_execute:
                return {
                    "task_id": task.id,
                    "status": "pending_approval",
                    "reason": (
                        low_confidence_reason
                        or f"Trust score too low for risk level {risk_level.name}"
                    ),
                }
        else:  # hybrid
            # 混合模式，中高及以上风险或需要审批时必须能自动执行
            if (
                risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.BLOCKED]
                or requires_approval
            ):
                if not can_auto_execute:
                    return {
                        "task_id": task.id,
                        "status": "pending_approval",
                        "reason": (
                            low_confidence_reason
                            or f"Risk level {risk_level.name} requires approval or higher trust"
                        ),
                    }

        # 推导工具参数并执行；子代理工具需要传递递归深度和 dry-run 状态
        merged_context = {**context, **task.parameters}
        if tool.name == "dispatch_subagent":
            merged_context["_depth"] = _depth
            merged_context["dry_run"] = self.tool_executor.dry_run

        try:
            result = self.tool_executor.execute_with_auto_selection(
                task.description,
                merged_context,
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

    def _get_execution_confidence(self, context: Dict[str, Any]) -> Optional[float]:
        """从上下文中提取诊断/修复置信度"""
        if "execution_confidence" in context:
            try:
                return float(context["execution_confidence"])
            except (TypeError, ValueError):
                pass

        for key in ["diagnosis", "root_cause_analysis", "analysis", "result"]:
            if key in context:
                data = context[key]
                if isinstance(data, dict):
                    if "confidence" in data:
                        try:
                            return float(data["confidence"])
                        except (TypeError, ValueError):
                            pass
                    if "candidates" in data and isinstance(data["candidates"], list):
                        candidates = data["candidates"]
                        if candidates:
                            try:
                                return float(candidates[0].get("confidence", 0.0))
                            except (TypeError, ValueError, AttributeError):
                                pass

        return None

    def _is_remediation_action(self, task_description: str) -> bool:
        """判断任务是否为修复/变更类动作（需要置信度门控）"""
        task_lower = task_description.lower()
        remediation_keywords = {
            "重启",
            "restart",
            "扩容",
            "缩容",
            "scale",
            "修改",
            "modify",
            "删除",
            "delete",
            "清空",
            "清理",
            "清理",
            "回滚",
            "rollback",
            "执行",
            "execute",
            "修复",
            "fix",
            "apply",
            "部署",
            "deploy",
            "停止",
            "stop",
            "kill",
            "终止",
        }
        return any(kw in task_lower for kw in remediation_keywords)

    def _merge_tool_result_into_context(
        self,
        tool_name: str,
        result: Any,
        context: Dict[str, Any],
    ) -> None:
        """将工具执行结果按类型合并回上下文，供后续工具（尤其是根因分析）消费。"""
        if not isinstance(result, (dict, list)):
            return

        # PII redaction + token-aware truncation before it reaches the planner/LLM
        try:
            from core.observability_query import prepare_for_llm as _prepare_for_llm

            sanitized = _prepare_for_llm(result, max_tokens=12000, max_items=1000)
        except Exception as e:
            logging.exception("Unexpected exception: %s", e)
            sanitized = result

        metric_collecting_tools = {
            "collect_metrics",
            "collect_service_metrics",
            "collect_network_metrics",
            "collect_container_metrics",
            "collect_host_metrics",
            "collect_database_metrics",
        }

        if tool_name in metric_collecting_tools and isinstance(sanitized, dict):
            metrics_data = context.get("metrics_data", {})
            if not isinstance(metrics_data, dict):
                metrics_data = {}
            # Avoid overwriting user-provided data with empty placeholders
            for key, value in sanitized.items():
                if value is not None or key not in metrics_data:
                    metrics_data[key] = value
            context["metrics_data"] = metrics_data
        elif tool_name == "collect_correlated_alerts" and isinstance(sanitized, list):
            context["correlated_alerts"] = sanitized
        elif tool_name == "collect_change_events" and isinstance(sanitized, list):
            context["change_events"] = sanitized
        elif tool_name == "collect_kubernetes_events" and isinstance(sanitized, list):
            context["kubernetes_events"] = sanitized
        elif tool_name == "collect_logs":
            context["logs_data"] = sanitized
        elif tool_name == "collect_topology" and isinstance(sanitized, dict):
            context["topology"] = sanitized

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
            self.subagent_dispatcher = SubAgentDispatcher(
                max_workers=max_subagents or 5,
                safety_boundary=self.safety_boundary,
                execution_mode=self.execution_mode,
                max_subagent_depth=self.max_subagent_depth,
                dry_run=self.dry_run,
                default_timeout=self.tool_executor.default_timeout,
                task_timeout=300,
            )

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

        subagent_results = self.subagent_dispatcher.dispatch_batch(batch, _depth=1)

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

    def execute_plan_parallel(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
        _depth: int = 0,
    ) -> Dict[str, Any]:
        """并行多 subagent 执行计划：按任务依赖分批派发子代理。

        与 ``execute_plan`` 不同，该方法会把当前所有无依赖的前置任务
        一次性交给 ``SubAgentDispatcher.dispatch_parallel`` 并行执行，
        每完成一批后立即更新计划状态并进入下一批，直到全部完成或出错。
        """
        from .subagent import SubAgentDispatcher

        logger.info(f"Executing plan in parallel for goal: {goal} (depth={_depth})")

        # 会话隔离与结构化状态
        context = copy.deepcopy(context)
        if "session_id" not in context or not context["session_id"]:
            context["session_id"] = str(uuid.uuid4())

        diag_state = context.get("diagnostic_state")
        if isinstance(diag_state, dict):
            diag_state = DiagnosticState.from_dict(diag_state)
        elif not isinstance(diag_state, DiagnosticState):
            diag_state = DiagnosticState()
        context["diagnostic_state"] = diag_state

        # 行为异常检测
        self.behavior_monitor.record_iteration(self.agent_id)
        anomaly = self.behavior_monitor.check_anomaly(self.agent_id)
        if anomaly:
            return {
                "goal": goal,
                "tasks": [],
                "results": [],
                "summary": {},
                "error": f"Behavior anomaly detected: {anomaly.get('messages')}",
                "behavior_alert": anomaly,
            }

        # 子代理递归深度
        if _depth > self.max_subagent_depth:
            self.behavior_monitor.record_error(self.agent_id)
            return {
                "goal": goal,
                "tasks": [],
                "results": [],
                "summary": {},
                "error": f"Maximum subagent recursion depth {self.max_subagent_depth} exceeded",
            }

        # 防重复 goal 循环
        visited_goals: set = context.get("__visited_goals", set())
        if goal in visited_goals:
            return {
                "goal": goal,
                "tasks": [],
                "results": [],
                "summary": {},
                "error": "Repeated goal detected; aborting to prevent loop",
            }
        visited_goals = set(visited_goals)
        visited_goals.add(goal)
        context = {**context, "__visited_goals": visited_goals}

        # 跨会话记忆
        if context.get("enable_memory", True) and self.memory_bridge is not None:
            try:
                relevant = self.memory_bridge.retrieve_relevant_experiences(
                    goal, top_k=3, session_id=context.get("session_id")
                )
                if relevant:
                    context["relevant_experiences"] = relevant
            except Exception as exc:
                logger.warning(f"Memory retrieval failed: {exc}")

        # 规划
        tasks = self.planner.plan(goal, context, available_tools)
        if len(tasks) > self.max_tasks:
            return {
                "goal": goal,
                "tasks": [t.to_dict() for t in tasks],
                "results": [],
                "summary": {},
                "error": f"Planned tasks ({len(tasks)}) exceed maximum {self.max_tasks}",
            }

        dispatcher = SubAgentDispatcher(
            max_workers=min(self.max_tasks, 10),
            safety_boundary=self.safety_boundary,
            execution_mode=self.execution_mode,
            max_subagent_depth=self.max_subagent_depth,
            dry_run=self.tool_executor.dry_run,
            default_timeout=self.tool_executor.default_timeout,
            task_timeout=300,
        )
        results: List[Dict[str, Any]] = []

        try:
            iteration = 0
            while any(t.status == TaskStatus.PENDING for t in self.planner.tasks.values()):
                iteration += 1
                if iteration > self.max_iterations:
                    results.append(
                        {
                            "task_id": "batch",
                            "status": "failed",
                            "error": f"Maximum iteration count {self.max_iterations} reached",
                        }
                    )
                    self.behavior_monitor.record_error(self.agent_id)
                    break

                ready = self.planner.get_ready_tasks()
                if not ready:
                    # 剩余 PENDING 任务均因依赖失败/成环无法执行
                    for task in list(self.planner.tasks.values()):
                        if task.status == TaskStatus.PENDING:
                            self.planner.adjust_plan(
                                task.id,
                                TaskStatus.FAILED,
                                None,
                                "Unmet dependencies or cycle detected",
                            )
                            results.append(
                                {
                                    "task_id": task.id,
                                    "status": "failed",
                                    "error": "Unmet dependencies or cycle detected",
                                }
                            )
                    self.behavior_monitor.record_error(self.agent_id)
                    break

                # 构造 subagent 批次
                batch = []
                for task in ready:
                    task_context = {**context, **task.parameters}
                    role = task.parameters.get("action", "worker")
                    batch.append(
                        {
                            "goal": task.description,
                            "context": task_context,
                            "available_tools": available_tools,
                            "role": role,
                            "agent_id": task.id,
                        }
                    )

                subagent_results = dispatcher.dispatch_parallel(batch, _depth=_depth)

                # 同步结果
                for task in ready:
                    sub_res = subagent_results.get(task.id)
                    if sub_res is None:
                        self.planner.adjust_plan(
                            task.id,
                            TaskStatus.FAILED,
                            None,
                            "Subagent did not return a result",
                        )
                        results.append(
                            {
                                "task_id": task.id,
                                "agent_id": None,
                                "status": "failed",
                                "error": "Subagent did not return a result",
                            }
                        )
                        self.behavior_monitor.record_error(self.agent_id)
                        continue

                    if sub_res.status == "completed":
                        new_status = TaskStatus.COMPLETED
                    elif sub_res.status == "pending_approval":
                        new_status = TaskStatus.PENDING
                    else:
                        new_status = TaskStatus.FAILED

                    self.planner.adjust_plan(
                        task.id,
                        new_status,
                        sub_res.result,
                        sub_res.error,
                    )

                    self._merge_tool_result_into_context("subagent", sub_res.result, context)
                    diag_state.update_from_task(
                        task.description,
                        sub_res.result,
                        sub_res.error,
                    )
                    context["diagnostic_state"] = diag_state

                    results.append(
                        {
                            "task_id": task.id,
                            "agent_id": sub_res.agent_id,
                            "status": sub_res.status,
                            "result": sub_res.result,
                            "error": sub_res.error,
                        }
                    )

                    if new_status == TaskStatus.COMPLETED:
                        self.behavior_monitor.record_tool_call(self.agent_id, "subagent")
                    else:
                        self.behavior_monitor.record_error(self.agent_id)

                # 每批结束后再检查行为异常
                anomaly = self.behavior_monitor.check_anomaly(self.agent_id)
                if anomaly:
                    for task in list(self.planner.tasks.values()):
                        if task.status == TaskStatus.PENDING:
                            self.planner.adjust_plan(
                                task.id,
                                TaskStatus.SKIPPED,
                                None,
                                "Aborted due to behavior anomaly",
                            )
                    results.append(
                        {
                            "task_id": "batch",
                            "status": "failed",
                            "error": f"Behavior anomaly detected: {anomaly.get('messages')}",
                            "behavior_alert": anomaly,
                        }
                    )
                    break

        finally:
            dispatcher.shutdown(wait=True)

        summary = self.planner.get_plan_summary()
        summary["diagnostic_state"] = diag_state.to_dict()

        # 持久化跨会话经验
        if context.get("enable_memory", True) and self.memory_bridge is not None and tasks:
            try:
                memory_result = self.memory_bridge.save_experience(
                    goal=goal,
                    tasks=tasks,
                    results=results,
                    summary=summary,
                    session_id=context.get("session_id"),
                )
                if memory_result:
                    logger.info(f"Experience saved: {memory_result}")
                    summary["memory"] = memory_result
            except Exception as exc:
                logger.warning(f"Memory save failed: {exc}")

        return {
            "goal": goal,
            "tasks": [t.to_dict() for t in tasks],
            "results": results,
            "summary": summary,
            "diagnostic_state": diag_state.to_dict(),
            "session_id": context.get("session_id"),
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
