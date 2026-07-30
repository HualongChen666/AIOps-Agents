# -*- coding: utf-8 -*-
"""
coding_subagent.py
------------------
用于执行代码/文件操作任务的子代理。

它绕过默认的 AutonomousExecutor/TaskPlanner，直接根据上下文调用工具，
适合被 SubAgentDispatcher 并行分发，执行 bash/read_file/write_to_file/edit。
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from .coding_tools import CodingToolRegistry
from .subagent import SubAgent, SubAgentResult, SubAgentStatus
from .tools import ToolExecutor


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
        self.status = SubAgentStatus.RUNNING
        start_time = time.time()

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
            result = self.tool_executor.execute_tool(tool_name, **params)
            self.status = SubAgentStatus.COMPLETED
            duration = time.time() - start_time
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
            return SubAgentResult(
                agent_id=self.agent_id,
                task_id=task_id,
                status="failed",
                error=str(exc),
                duration=time.time() - start_time,
                metadata={
                    "role": self.role,
                    "goal": goal,
                },
            )


def create_coding_subagent_dispatcher(max_workers: int = 8):
    """创建使用 CodingSubAgent 的调度器。"""
    from .subagent import SubAgentDispatcher

    return SubAgentDispatcher(max_workers=max_workers, subagent_factory=CodingSubAgent)
