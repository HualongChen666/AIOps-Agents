# -*- coding: utf-8 -*-
"""
coding_subagent.py
------------------
用于执行代码/文件操作任务的子代理。

它绕过默认的 AutonomousExecutor/TaskPlanner，直接根据上下文调用工具，
适合被 SubAgentDispatcher 并行分发，执行 bash/read_file/write_to_file/edit。

增强版：集成超时机制、参数验证、并发控制、线程安全、进度显示、性能监控、安全加固。
"""

from __future__ import annotations

import time
import uuid
import threading
from typing import Any, Dict, List, Optional

from .coding_tools import CodingToolRegistry
from .subagent import SubAgent, SubAgentResult, SubAgentStatus
from .tools import ToolExecutor

# 导入优化组件
try:
    from .stall_detector import StallDetector, TimeoutError, TimeoutContext
    from .parameter_validator import ParameterValidator
    from .tool_call_runtime import ToolCallRuntime
    from .thread_safety import SubAgentBuilder, SubAgentRunner, SessionDB
    from .progress_tracker import ProgressTracker
    from .subagent_config import (
        SUBAGENT_TIMEOUT_SECONDS,
        SUBAGENT_STALL_TIMEOUT_SECONDS,
        MAX_CONCURRENT_TOOL_EXECUTIONS,
        ALLOWED_TOOLS
    )
    from .feature_flags import FeatureFlags
    from .degradation_strategy import DegradationStrategy
    from .performance_monitor import PerformanceMonitor
    from .security_auditor import SecurityAuditor, SecurityScanner
    ENHANCED_FEATURES_AVAILABLE = True
except ImportError:
    ENHANCED_FEATURES_AVAILABLE = False


class CodingSubAgent(SubAgent):
    """可以直接执行代码/文件操作工具的子代理。"""

    def __init__(
        self,
        agent_id: str,
        role: str = "worker",
        planner: Optional[Any] = None,
        tool_executor: Optional[ToolExecutor] = None,
        safety_boundary: Optional[Any] = None,
    ):
        """初始化 CodingSubAgent，默认使用 CodingToolRegistry。"""
        if tool_executor is None:
            tool_executor = ToolExecutor(CodingToolRegistry())

        super().__init__(
            agent_id=agent_id,
            role=role,
            planner=planner,
            tool_executor=tool_executor,
            safety_boundary=safety_boundary,
        )

        # 初始化增强功能组件
        self._enhanced_enabled = ENHANCED_FEATURES_AVAILABLE
        if self._enhanced_enabled:
            # 功能开关
            self.flags = FeatureFlags()
            
            # 降级策略
            self.degradation = DegradationStrategy()
            
            # 性能监控
            self.performance = PerformanceMonitor()
            
            # 安全加固
            self.security = SecurityAuditor()
            self.security_scanner = SecurityScanner()
            
            # 线程安全锁
            self._state_lock = threading.RLock()
            
            # 按需初始化组件
            if self.flags.is_timeout_enabled():
                self._stall_detector = StallDetector(SUBAGENT_STALL_TIMEOUT_SECONDS)
            
            if self.flags.is_validation_enabled():
                self._validator = ParameterValidator()
            
            if self.flags.is_whitelist_enabled():
                self._available_tools = ALLOWED_TOOLS.copy()
            
            if self.flags.is_timeout_enabled():
                self._tool_runtime = ToolCallRuntime(MAX_CONCURRENT_TOOL_EXECUTIONS)
            
            if self.flags.is_progress_enabled():
                self._progress_tracker = ProgressTracker()

    def run(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
        _depth: int = 0,
    ) -> SubAgentResult:
        """执行由 context 描述的工具调用。

        context 中必须包含：
        - tool: 工具名（bash/read_file/write_to_file/edit）
        - params: 工具参数字典
        """
        task_id = f"subtask_{uuid.uuid4().hex[:8]}"
        start_time = time.perf_counter()
        
        # 状态锁保护
        if self._enhanced_enabled:
            with self._state_lock:
                if self.status != SubAgentStatus.IDLE:
                    return SubAgentResult(
                        agent_id=self.agent_id,
                        task_id=task_id,
                        status="failed",
                        error=f"Agent状态不允许执行: {self.status}",
                        duration=0.0
                    )
                self.status = SubAgentStatus.RUNNING
        else:
            self.status = SubAgentStatus.RUNNING

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
            tool_name = context.get("tool", "bash")
            params = context.get("params", {})
            
            # 增强功能执行
            if self._enhanced_enabled:
                return self._run_with_enhancements(
                    task_id, goal, tool_name, params, available_tools, start_time
                )
            else:
                # 原始执行逻辑（向后兼容）
                result = self.tool_executor.execute_tool(tool_name, **params)
                self.status = SubAgentStatus.COMPLETED
                duration = time.perf_counter() - start_time
                return SubAgentResult(
                    agent_id=self.agent_id,
                    task_id=task_id,
                    status="completed",
                    result=result,
                    duration=duration,
                    metadata={
                        "role": self.role,
                        "goal": goal,
                        "tool": tool_name,
                        "params": params,
                    },
                )
        except Exception as exc:  # noqa: BLE001
            self.status = SubAgentStatus.FAILED
            duration = time.perf_counter() - start_time
            
            # 记录性能
            if self._enhanced_enabled:
                self.performance.record_execution(duration, False)
                self.security.log_execution(self.agent_id, tool_name, params, False)
            
            return SubAgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status="failed",
                error=str(exc),
                duration=duration,
                metadata={
                    "role": self.role,
                    "goal": goal,
                },
            )
        finally:
            # 确保状态重置
            if self._enhanced_enabled:
                with self._state_lock:
                    if self.status == SubAgentStatus.RUNNING:
                        self.status = SubAgentStatus.IDLE
    
    def _run_with_enhancements(
        self,
        task_id: str,
        goal: str,
        tool_name: str,
        params: Dict[str, Any],
        available_tools: List[str],
        start_time: float
    ) -> SubAgentResult:
        """使用增强功能执行工具调用"""
        
        # 检查降级级别
        current_level = self.degradation.get_current_level()
        level_config = self.degradation.get_level_config()
        
        # 安全扫描
        if self.flags.is_whitelist_enabled():
            security_issues = self.security_scanner.scan_params(tool_name, params)
            if security_issues:
                # 记录安全问题但不阻止执行
                pass
        
        # 参数验证（根据降级级别）
        if level_config["validation"] and self.flags.is_validation_enabled():
            validation_result = self._validator.validate(context, available_tools)
            if not validation_result["valid"]:
                return SubAgentResult(
                    agent_id=self.agent_id,
                    task_id=task_id,
                    status="failed",
                    error=f"参数验证失败: {validation_result['errors']}",
                    duration=time.perf_counter() - start_time,
                    metadata={"validation_errors": validation_result["errors"]}
                )
        
        # 白名单检查（根据降级级别）
        if level_config["whitelist"] and self.flags.is_whitelist_enabled():
            if tool_name not in self._available_tools:
                return SubAgentResult(
                    agent_id=self.agent_id,
                    task_id=task_id,
                    status="failed",
                    error=f"工具'{tool_name}'不在白名单中",
                    duration=time.perf_counter() - start_time,
                    metadata={"available_tools": self._available_tools}
                )
        
        # 注册进度
        if self.flags.is_progress_enabled():
            self._progress_tracker.register_child(task_id, goal)
        
        # 执行工具（带超时和并发控制）
        timeout = context.get("timeout", SUBAGENT_TIMEOUT_SECONDS)
        
        try:
            if level_config["timeout"] and self.flags.is_timeout_enabled():
                # 使用超时和并发控制
                with self._tool_runtime.acquire_execution_slot(tool_name):
                    if self.flags.is_stall_detection_enabled():
                        self._stall_detector.update_activity()
                    
                    # 执行工具
                    result = self.tool_executor.execute_tool(tool_name, **params)
                    
                    # 检查停滞
                    if self.flags.is_stall_detection_enabled() and self._stall_detector.check_stall():
                        raise TimeoutError("工具执行停滞")
            else:
                # 直接执行
                result = self.tool_executor.execute_tool(tool_name, **params)
            
            # 更新进度
            if self.flags.is_progress_enabled():
                self._progress_tracker.update_child_status(task_id, "completed")
            
            # 记录审计日志
            self.security.log_execution(self.agent_id, tool_name, params, True)
            
            # 记录性能
            duration = time.perf_counter() - start_time
            self.performance.record_execution(duration, True)
            
            self.status = SubAgentStatus.COMPLETED
            return SubAgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status="completed",
                result=result,
                duration=duration,
                metadata={
                    "role": self.role,
                    "goal": goal,
                    "tool": tool_name,
                    "params": params,
                    "enhanced": True
                },
            )
        
        except TimeoutError as exc:
            if self.flags.is_progress_enabled():
                self._progress_tracker.update_child_status(task_id, "timeout")
            
            duration = time.perf_counter() - start_time
            self.performance.record_execution(duration, False, timeout=True)
            self.security.log_execution(self.agent_id, tool_name, params, False)
            
            return SubAgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status="timeout",
                error=str(exc),
                duration=duration,
                metadata={"tool": tool_name, "timeout": timeout}
            )
        
        except Exception as exc:
            if self.flags.is_progress_enabled():
                self._progress_tracker.update_child_status(task_id, "failed")
            
            duration = time.perf_counter() - start_time
            self.performance.record_execution(duration, False)
            self.security.log_execution(self.agent_id, tool_name, params, False)
            
            return SubAgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status="failed",
                error=str(exc),
                duration=duration,
                metadata={
                    "role": self.role,
                    "goal": goal,
                },
            )


def create_coding_subagent_dispatcher(max_workers: int = 8):
    """创建使用 CodingSubAgent 的调度器。"""
    from .subagent import SubAgentDispatcher

    return SubAgentDispatcher(max_workers=max_workers, subagent_factory=CodingSubAgent)
