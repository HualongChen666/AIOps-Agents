# -*- coding: utf-8 -*-
"""
subagent.py
-----------
子代理调度器/启动器。

功能：
- 创建并启动子 Agent
- 主 Agent 可将任务分派给多个子 Agent 并行执行
- 收集并汇总子 Agent 结果
- 支持子 Agent 生命周期管理（创建、运行、查询、终止）
"""

from __future__ import annotations

import copy
import logging
import os
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from .executor import AutonomousExecutor, SafetyBoundary
from .planner import TaskPlanner
from .tools import ToolExecutor, ToolRegistry

# Limit concurrent subagent sessions (sync because SubAgent.run is synchronous).
_agent_session_semaphore = threading.BoundedSemaphore(
    int(os.environ.get("AIOPS_MAX_AGENT_SESSIONS", "50"))
)

try:
    from core.audit_logger import log_audit_event as _log_audit_event

    AUDIT_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    AUDIT_AVAILABLE = False
    _log_audit_event = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)


def _audit_subagent(
    agent_id: str, action: str, status: str, details: Optional[Dict[str, Any]] = None
) -> None:
    """Best-effort audit wrapper for subagent operations."""
    if AUDIT_AVAILABLE and callable(_log_audit_event):
        try:
            _log_audit_event(
                event_type="SUBAGENT_OPERATION",
                user="system",
                resource=agent_id,
                action=action,
                status=status,
                details=details or {},
            )
        except Exception as exc:
            logger.warning(f"Subagent audit failed: {exc}")


# ----------------------------------------------------------------------
# 1️⃣ 子代理状态与结果
# ----------------------------------------------------------------------
class SubAgentStatus(Enum):
    """子代理状态"""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TERMINATED = "terminated"


@dataclass
class SubAgentResult:
    """子代理执行结果"""

    agent_id: str
    task_id: str
    status: str
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "status": self.status,
            "result": self.result,
            "error": self.error,
            "duration": self.duration,
            "metadata": self.metadata,
        }


# ----------------------------------------------------------------------
# 2️⃣ 子代理
# ----------------------------------------------------------------------
class SubAgent:
    """子代理

    子代理拥有独立的规划器、工具执行器和自主执行引擎，
    可以独立执行分配到的子任务。
    """

    def __init__(
        self,
        agent_id: str,
        role: str = "worker",
        planner: Optional[TaskPlanner] = None,
        tool_executor: Optional[ToolExecutor] = None,
        safety_boundary: Optional[SafetyBoundary] = None,
        execution_mode: str = "hybrid",
        max_subagent_depth: int = 3,
        dry_run: bool = False,
        default_timeout: Optional[float] = None,
    ):
        """
        Parameters
        ----------
        agent_id : str
            子代理唯一 ID
        role : str
            子代理角色，如 "worker", "analyzer", "executor"
        planner : TaskPlanner, optional
            任务规划器
        tool_executor : ToolExecutor, optional
            工具执行器
        safety_boundary : SafetyBoundary, optional
            安全边界
        execution_mode : str
            子代理执行模式
        max_subagent_depth : int
            最大子代理递归深度
        dry_run : bool
            是否仅预演
        default_timeout : float, optional
            工具默认超时
        """
        self.agent_id = agent_id
        self.role = role
        self.status = SubAgentStatus.IDLE
        self.planner = planner or TaskPlanner()
        self.tool_executor = tool_executor or ToolExecutor(ToolRegistry())
        self.tool_executor.dry_run = dry_run
        if default_timeout is not None:
            self.tool_executor.default_timeout = default_timeout
        self.safety_boundary = safety_boundary or SafetyBoundary()
        self.executor = AutonomousExecutor(
            self.planner,
            self.tool_executor,
            self.safety_boundary,
            dry_run=dry_run,
        )
        self.executor.execution_mode = execution_mode
        self.executor.max_subagent_depth = max_subagent_depth
        self.executor.dry_run = dry_run
        self._stop_event = threading.Event()

    def run(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
        _depth: int = 0,
    ) -> SubAgentResult:
        """
        执行子任务

        Parameters
        ----------
        goal : str
            子任务目标
        context : Dict[str, Any]
            上下文
        available_tools : List[str]
            可用工具列表

        Returns
        -------
        SubAgentResult
            执行结果
        """
        task_id = f"subtask_{uuid.uuid4().hex[:8]}"
        self.status = SubAgentStatus.RUNNING
        start_time = time.time()

        logger.info(f"[subagent {self.agent_id}] start goal: {goal}")
        _audit_subagent(self.agent_id, "run", "started", {"goal": goal})

        if self._stop_event.is_set():
            self.status = SubAgentStatus.TERMINATED
            return SubAgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status="terminated",
                error="SubAgent terminated before execution",
                duration=0.0,
            )

        try:
            with _agent_session_semaphore:
                result = self.executor.execute_plan(goal, context, available_tools, _depth=_depth)
            self.status = SubAgentStatus.COMPLETED
            duration = time.time() - start_time
            logger.info(f"[subagent {self.agent_id}] completed in {duration:.2f}s")
            _audit_subagent(
                self.agent_id,
                "run",
                "success",
                {"goal": goal, "duration": duration, "status": "completed"},
            )
            return SubAgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status="completed",
                result=result,
                duration=duration,
                metadata={"role": self.role, "goal": goal},
            )
        except Exception as exc:  # noqa: BLE001
            logger.error(f"[subagent {self.agent_id}] failed: {exc}")
            self.status = SubAgentStatus.FAILED
            _audit_subagent(
                self.agent_id,
                "run",
                "failure",
                {"goal": goal, "error": str(exc)},
            )
            return SubAgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status="failed",
                error=str(exc),
                duration=time.time() - start_time,
                metadata={"role": self.role, "goal": goal},
            )

    def terminate(self) -> None:
        """请求终止子代理"""
        self._stop_event.set()
        _audit_subagent(self.agent_id, "terminate", "requested", {})
        logger.info(f"[subagent {self.agent_id}] termination requested")

    def is_terminated(self) -> bool:
        """是否已请求终止"""
        return self._stop_event.is_set()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "role": self.role,
            "status": self.status.value,
            "terminated": self._stop_event.is_set(),
        }


# ----------------------------------------------------------------------
# 3️⃣ 子代理调度器
# ----------------------------------------------------------------------
class SubAgentDispatcher:
    """子代理调度器

    负责管理子代理池，将任务分派给子代理并发执行，并收集结果。
    """

    def __init__(
        self,
        max_workers: int = 5,
        subagent_factory: Type[SubAgent] = SubAgent,
        safety_boundary: Optional[SafetyBoundary] = None,
        execution_mode: str = "hybrid",
        max_subagent_depth: int = 3,
        dry_run: bool = False,
        default_timeout: Optional[float] = None,
        task_timeout: Optional[float] = 300,
    ):
        """
        Parameters
        ----------
        max_workers : int
            线程池最大并发数
        subagent_factory : Type[SubAgent]
            子代理工厂类
        safety_boundary : SafetyBoundary, optional
            父代理安全边界，子代理继承
        execution_mode : str
            子代理执行模式
        max_subagent_depth : int
            最大子代理递归深度
        dry_run : bool
            是否仅预演
        default_timeout : float, optional
            工具默认超时
        task_timeout : float, optional
            等待子代理结果的最大秒数
        """
        self.max_workers = max_workers
        self.subagent_factory = subagent_factory
        self.safety_boundary = safety_boundary or SafetyBoundary()
        self.execution_mode = execution_mode
        self.max_subagent_depth = max_subagent_depth
        self.dry_run = dry_run
        self.default_timeout = default_timeout
        self.task_timeout = task_timeout
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="subagent_",
        )
        self._subagents: Dict[str, SubAgent] = {}
        self._futures: Dict[str, Future] = {}
        self._results: Dict[str, SubAgentResult] = {}

    def create_subagent(
        self,
        role: str = "worker",
        agent_id: Optional[str] = None,
        planner: Optional[TaskPlanner] = None,
        tool_executor: Optional[ToolExecutor] = None,
        safety_boundary: Optional[SafetyBoundary] = None,
        execution_mode: Optional[str] = None,
        max_subagent_depth: Optional[int] = None,
        dry_run: Optional[bool] = None,
        default_timeout: Optional[float] = None,
    ) -> SubAgent:
        """创建子代理，默认继承调度器的安全边界、执行模式和深度限制。"""
        if agent_id is None:
            agent_id = f"subagent_{uuid.uuid4().hex[:8]}"

        subagent = self.subagent_factory(
            agent_id=agent_id,
            role=role,
            planner=planner,
            tool_executor=tool_executor,
            safety_boundary=safety_boundary or self.safety_boundary,
            execution_mode=execution_mode or self.execution_mode,
            max_subagent_depth=max_subagent_depth or self.max_subagent_depth,
            dry_run=dry_run if dry_run is not None else self.dry_run,
            default_timeout=(
                default_timeout if default_timeout is not None else self.default_timeout
            ),
        )
        self._subagents[agent_id] = subagent
        logger.info(f"[subagent dispatcher] created {agent_id} role={role}")
        return subagent

    def dispatch(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        available_tools: Optional[List[str]] = None,
        role: str = "worker",
        agent_id: Optional[str] = None,
        wait: bool = True,
        _depth: int = 0,
    ) -> SubAgentResult | Future:
        """
        分派一个子任务

        Parameters
        ----------
        goal : str
            任务目标
        context : Dict[str, Any], optional
            上下文
        available_tools : List[str], optional
            可用工具
        role : str
            子代理角色
        agent_id : str, optional
            指定子代理 ID
        wait : bool
            是否等待结果
        _depth : int
            当前子代理递归深度

        Returns
        -------
        SubAgentResult or Future
            等待时返回结果，否则返回 Future
        """
        context = context or {}
        available_tools = available_tools or []

        # Copy-on-write: each subagent gets its own deep copy of context plus a
        # per-subagent session id so memory/state cannot leak between sessions.
        isolated_context = copy.deepcopy(context)
        if "session_id" not in isolated_context or not isolated_context["session_id"]:
            isolated_context["session_id"] = str(uuid.uuid4())
        isolated_context["parent_session_id"] = context.get("session_id")

        _audit_subagent(
            agent_id or "pending",
            "dispatch",
            "started",
            {"goal": goal, "role": role, "wait": wait, "_depth": _depth},
        )
        subagent = self.create_subagent(
            role=role,
            agent_id=agent_id,
        )
        future = self._executor.submit(
            subagent.run,
            goal,
            isolated_context,
            available_tools,
            _depth + 1,
        )
        self._futures[subagent.agent_id] = future

        if wait:
            try:
                result = future.result(timeout=self.task_timeout)
            except Exception as exc:  # noqa: BLE001
                result = SubAgentResult(
                    agent_id=subagent.agent_id,
                    task_id="",
                    status="failed",
                    error=str(exc),
                )
                _audit_subagent(
                    subagent.agent_id,
                    "dispatch",
                    "failure",
                    {"goal": goal, "error": str(exc)},
                )
            else:
                _audit_subagent(
                    subagent.agent_id,
                    "dispatch",
                    "success",
                    {"goal": goal, "status": result.status},
                )
            self._results[subagent.agent_id] = result
            return result

        _audit_subagent(
            subagent.agent_id,
            "dispatch",
            "pending",
            {"goal": goal, "role": role},
        )
        return future

    def dispatch_batch(
        self,
        tasks: List[Dict[str, Any]],
        _depth: int = 0,
    ) -> List[SubAgentResult]:
        """
        批量分派任务

        Parameters
        ----------
        tasks : List[Dict[str, Any]]
            每个任务包含 goal, context, available_tools, role 等
        _depth : int
            当前子代理递归深度

        Returns
        -------
        List[SubAgentResult]
            与 tasks 顺序一致的结果列表
        """
        futures: List[Future] = []
        agent_ids: List[str] = []

        for task in tasks:
            goal = task["goal"]
            context = task.get("context") or {}
            available_tools = task.get("available_tools") or []
            role = task.get("role", "worker")
            agent_id = task.get("agent_id")

            isolated_context = copy.deepcopy(context)
            if "session_id" not in isolated_context or not isolated_context["session_id"]:
                isolated_context["session_id"] = str(uuid.uuid4())
            isolated_context["parent_session_id"] = context.get("session_id")

            subagent = self.create_subagent(role=role, agent_id=agent_id)
            future = self._executor.submit(
                subagent.run,
                goal,
                isolated_context,
                available_tools,
                _depth + 1,
            )
            futures.append(future)
            agent_ids.append(subagent.agent_id)

        results: List[SubAgentResult] = []
        for agent_id, future in zip(agent_ids, futures):
            try:
                result = future.result(timeout=self.task_timeout)
            except Exception as exc:  # noqa: BLE001
                result = SubAgentResult(
                    agent_id=agent_id,
                    task_id="",
                    status="failed",
                    error=str(exc),
                )
            self._results[agent_id] = result
            results.append(result)

        return results

    def dispatch_parallel(
        self,
        tasks: List[Dict[str, Any]],
        _depth: int = 0,
    ) -> Dict[str, SubAgentResult]:
        """
        并行分派任务，返回完成顺序的迭代器结果

        Parameters
        ----------
        tasks : List[Dict[str, Any]]
            每个任务包含 goal, context, available_tools, role 等
        _depth : int
            当前子代理递归深度

        Returns
        -------
        Dict[str, SubAgentResult]
            以 agent_id 为 key 的结果字典
        """
        future_to_agent: Dict[Future, str] = {}

        for task in tasks:
            goal = task["goal"]
            context = task.get("context") or {}
            available_tools = task.get("available_tools") or []
            role = task.get("role", "worker")
            agent_id = task.get("agent_id")

            isolated_context = copy.deepcopy(context)
            if "session_id" not in isolated_context or not isolated_context["session_id"]:
                isolated_context["session_id"] = str(uuid.uuid4())
            isolated_context["parent_session_id"] = context.get("session_id")

            subagent = self.create_subagent(role=role, agent_id=agent_id)
            future = self._executor.submit(
                subagent.run,
                goal,
                isolated_context,
                available_tools,
                _depth + 1,
            )
            future_to_agent[future] = subagent.agent_id

        results: Dict[str, SubAgentResult] = {}
        for future in as_completed(future_to_agent):
            agent_id = future_to_agent[future]
            try:
                result = future.result(timeout=self.task_timeout)
            except Exception as exc:  # noqa: BLE001
                result = SubAgentResult(
                    agent_id=agent_id,
                    task_id="",
                    status="failed",
                    error=str(exc),
                )
            self._results[agent_id] = result
            results[agent_id] = result

        return results

    def get_result(self, agent_id: str) -> Optional[SubAgentResult]:
        """获取子代理结果"""
        return self._results.get(agent_id)

    def list_subagents(self) -> List[SubAgent]:
        """列出所有子代理"""
        return list(self._subagents.values())

    def get_subagent(self, agent_id: str) -> Optional[SubAgent]:
        """获取子代理"""
        return self._subagents.get(agent_id)

    def terminate(self, agent_id: str) -> bool:
        """终止指定子代理"""
        subagent = self._subagents.get(agent_id)
        if subagent is None:
            logger.warning(f"[subagent dispatcher] {agent_id} not found")
            return False

        subagent.terminate()

        future = self._futures.get(agent_id)
        if future is not None and not future.done():
            cancelled = future.cancel()
            if cancelled:
                subagent.status = SubAgentStatus.TERMINATED
                self._results[agent_id] = SubAgentResult(
                    agent_id=agent_id,
                    task_id="",
                    status="terminated",
                    error="Cancelled by dispatcher",
                )
                logger.info(f"[subagent dispatcher] cancelled {agent_id}")
                return True

        logger.info(f"[subagent dispatcher] termination requested for {agent_id}")
        return True

    def shutdown(self, wait: bool = True) -> None:
        """关闭调度器"""
        self._executor.shutdown(wait=wait)
        logger.info("[subagent dispatcher] shutdown")

    def get_summary(self) -> Dict[str, Any]:
        """获取调度摘要"""
        total = len(self._subagents)
        completed = sum(1 for r in self._results.values() if r.status == "completed")
        failed = sum(1 for r in self._results.values() if r.status == "failed")
        terminated = sum(1 for r in self._results.values() if r.status == "terminated")
        running = total - len(self._results)

        return {
            "total": total,
            "running": running,
            "completed": completed,
            "failed": failed,
            "terminated": terminated,
            "success_rate": completed / total if total > 0 else 0,
        }


# ----------------------------------------------------------------------
# 4️⃣ 便捷函数
# ----------------------------------------------------------------------
def create_subagent_dispatcher(max_workers: int = 5) -> SubAgentDispatcher:
    """创建子代理调度器"""
    return SubAgentDispatcher(max_workers=max_workers)


def dispatch_task(
    goal: str,
    context: Optional[Dict[str, Any]] = None,
    available_tools: Optional[List[str]] = None,
    role: str = "worker",
    max_workers: int = 5,
) -> SubAgentResult:
    """便捷函数：调度单个子任务"""
    dispatcher = create_subagent_dispatcher(max_workers=max_workers)
    try:
        return dispatcher.dispatch(  # type: ignore[return-value]
            goal=goal,
            context=context,
            available_tools=available_tools,
            role=role,
            wait=True,
        )
    finally:
        dispatcher.shutdown(wait=True)
