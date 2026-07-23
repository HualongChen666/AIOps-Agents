# -*- coding: utf-8 -*-
"""
planner.py
----------
AI Agent 任务规划引擎 - Chain-of-Thought 推理。

功能：
- 任务分解
- 执行规划
- 动态任务调整
- 思维链推理
- 目标：复杂任务成功率 ≥ 85%
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 任务状态枚举
# ----------------------------------------------------------------------
class TaskStatus(Enum):
    """任务状态"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """任务优先级"""

    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


# ----------------------------------------------------------------------
# 2️⃣ 任务定义
# ----------------------------------------------------------------------
@dataclass
class Task:
    """任务定义"""

    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None
    reasoning: Optional[str] = None  # 思维链推理过程
    estimated_duration: Optional[float] = None  # 预估耗时（秒）
    actual_duration: Optional[float] = None  # 实际耗时

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "dependencies": self.dependencies,
            "parameters": self.parameters,
            "result": str(self.result) if self.result is not None else None,
            "error": self.error,
            "reasoning": self.reasoning,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
        }


# ----------------------------------------------------------------------
# 3️⃣ 思维链推理
# ----------------------------------------------------------------------
class ChainOfThought:
    """思维链推理引擎"""

    def __init__(self, llm_client: Optional[Any] = None):
        """
        Parameters
        ----------
        llm_client : Any, optional
            LLM 客户端（用于生成推理步骤）
        """
        self.llm_client = llm_client
        self.reasoning_steps: List[str] = []

    def reason(
        self,
        goal: str,
        context: Dict[str, Any],
        max_steps: int = 10,
    ) -> List[str]:
        """
        执行思维链推理

        Parameters
        ----------
        goal : str
            目标描述
        context : Dict[str, Any]
            上下文信息
        max_steps : int
            最大推理步骤数

        Returns
        -------
        List[str]
            推理步骤列表
        """
        logger.info(f"Chain-of-Thought reasoning for goal: {goal}")

        if self.llm_client is not None:
            # 使用 LLM 生成推理步骤
            steps = self._llm_reason(goal, context, max_steps)
        else:
            # 使用规则推理（降级方案）
            steps = self._rule_reason(goal, context, max_steps)

        self.reasoning_steps = steps
        return steps

    def _llm_reason(
        self,
        goal: str,
        context: Dict[str, Any],
        max_steps: int,
    ) -> List[str]:
        """使用 LLM 生成推理步骤"""
        # 构造提示词
        prompt = f"""
目标: {goal}

上下文:
{json.dumps(context, indent=2, ensure_ascii=False)}

请生成达成目标的推理步骤，每步应该：
1. 具体可执行
2. 逻辑清晰
3. 逐步推进

输出格式（JSON数组）:
[
  "步骤1: ...",
  "步骤2: ...",
  ...
]
"""

        try:
            # 调用 LLM
            if self.llm_client is None:
                raise RuntimeError("LLM client is not initialized")
            response = self.llm_client.generate(prompt)

            # 解析响应
            steps = json.loads(response)
            if isinstance(steps, list):
                return steps[:max_steps]
            else:
                logger.warning("LLM 返回格式不正确，使用规则推理")
                return self._rule_reason(goal, context, max_steps)
        except Exception as e:
            logger.error(f"LLM 推理失败: {e}，使用规则推理")
            return self._rule_reason(goal, context, max_steps)

    def _rule_reason(
        self,
        goal: str,
        context: Dict[str, Any],
        max_steps: int,
    ) -> List[str]:
        """规则推理（降级方案）"""
        steps = []

        # 根据目标类型生成推理步骤
        goal_lower = goal.lower()

        if "诊断" in goal_lower or "分析" in goal_lower:
            steps = [
                "步骤1: 收集系统指标和日志数据",
                "步骤2: 分析异常模式和趋势",
                "步骤3: 识别可能的根因",
                "步骤4: 验证根因假设",
                "步骤5: 生成诊断报告",
            ]
        elif "修复" in goal_lower or "解决" in goal_lower:
            steps = [
                "步骤1: 定位问题根因",
                "步骤2: 评估修复方案",
                "步骤3: 选择最佳修复策略",
                "步骤4: 执行修复操作",
                "步骤5: 验证修复效果",
            ]
        elif "扩容" in goal_lower or "缩容" in goal_lower:
            steps = [
                "步骤1: 分析当前资源使用情况",
                "步骤2: 预测未来资源需求",
                "步骤3: 计算扩容/缩容规模",
                "步骤4: 执行扩容/缩容操作",
                "步骤5: 监控资源变化",
            ]
        else:
            # 通用推理步骤
            steps = [
                "步骤1: 理解目标和约束",
                "步骤2: 收集必要信息",
                "步骤3: 分析当前状态",
                "步骤4: 制定行动计划",
                "步骤5: 执行并验证",
            ]

        return steps[:max_steps]


# ----------------------------------------------------------------------
# 4️⃣ 任务规划器
# ----------------------------------------------------------------------
class TaskPlanner:
    """任务规划器"""

    def __init__(
        self,
        cot_engine: Optional[ChainOfThought] = None,
    ):
        """
        Parameters
        ----------
        cot_engine : ChainOfThought, optional
            思维链推理引擎
        """
        self.cot_engine = cot_engine or ChainOfThought()
        self.tasks: Dict[str, Task] = {}
        self.task_counter = 0

    def plan(
        self,
        goal: str,
        context: Dict[str, Any],
        available_tools: List[str],
    ) -> List[Task]:
        """
        规划任务

        Parameters
        ----------
        goal : str
            目标描述
        context : Dict[str, Any]
            上下文信息
        available_tools : List[str]
            可用工具列表

        Returns
        -------
        List[Task]
            任务列表
        """
        logger.info(f"Planning tasks for goal: {goal}")

        # 执行思维链推理
        reasoning_steps = self.cot_engine.reason(goal, context)

        # 将推理步骤转换为任务
        tasks = []
        prev_task_id = None

        for i, step in enumerate(reasoning_steps):
            task_id = f"task_{self.task_counter}"
            self.task_counter += 1

            # 提取步骤描述
            description = step.replace(f"步骤{i + 1}: ", "")

            # 确定任务参数
            parameters = self._infer_task_parameters(
                description,
                context,
                available_tools,
            )

            # 确定依赖关系
            dependencies: List[str] = []
            if prev_task_id:
                dependencies.append(prev_task_id)

            # 创建任务
            task = Task(
                id=task_id,
                description=description,
                reasoning=step,
                dependencies=dependencies,
                parameters=parameters,
            )

            tasks.append(task)
            self.tasks[task_id] = task
            prev_task_id = task_id

        logger.info(f"Planned {len(tasks)} tasks")
        return tasks

    def _infer_task_parameters(
        self,
        description: str,
        context: Dict[str, Any],
        available_tools: List[str],
    ) -> Dict[str, Any]:
        """推断任务参数"""
        parameters: Dict[str, Any] = {}

        # 根据描述推断参数
        if "收集" in description or "获取" in description:
            parameters["action"] = "collect"
            parameters["target"] = context.get("target", "system")
        elif "分析" in description:
            parameters["action"] = "analyze"
            parameters["method"] = "statistical"
        elif "识别" in description or "定位" in description:
            parameters["action"] = "identify"
            parameters["algorithm"] = "anomaly_detection"
        elif "验证" in description:
            parameters["action"] = "validate"
            parameters["criteria"] = "success_rate"
        elif "执行" in description:
            parameters["action"] = "execute"
            parameters["mode"] = "safe"
        elif "生成" in description:
            parameters["action"] = "generate"
            parameters["format"] = "report"

        # 添加可用工具信息
        parameters["available_tools"] = available_tools

        return parameters

    def adjust_plan(
        self,
        task_id: str,
        new_status: TaskStatus,
        result: Optional[Any] = None,
        error: Optional[str] = None,
    ) -> List[Task]:
        """
        动态调整计划

        Parameters
        ----------
        task_id : str
            任务 ID
        new_status : TaskStatus
            新状态
        result : Any, optional
            任务结果
        error : str, optional
            错误信息

        Returns
        -------
        List[Task]
            调整后的任务列表
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return list(self.tasks.values())

        task = self.tasks[task_id]
        task.status = new_status
        task.result = result
        task.error = error

        # 如果任务失败，调整后续任务
        if new_status == TaskStatus.FAILED:
            logger.info(f"Task {task_id} failed, adjusting plan")
            self._handle_task_failure(task_id)

        return list(self.tasks.values())

    def _handle_task_failure(self, failed_task_id: str):
        """处理任务失败"""
        # 标记依赖此任务的所有任务为跳过
        for task_id, task in self.tasks.items():
            if failed_task_id in task.dependencies:
                task.status = TaskStatus.SKIPPED
                task.reasoning = f"依赖任务 {failed_task_id} 失败，跳过执行"

    def get_ready_tasks(self) -> List[Task]:
        """获取可执行的任务（依赖已满足）"""
        ready_tasks = []

        for task in self.tasks.values():
            if task.status == TaskStatus.PENDING:
                # 检查依赖是否都已完成
                dependencies_met = all(
                    self.tasks[dep_id].status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                )
                if dependencies_met:
                    ready_tasks.append(task)

        # 按优先级排序
        ready_tasks.sort(key=lambda t: t.priority.value, reverse=True)
        return ready_tasks

    def get_plan_summary(self) -> Dict[str, Any]:
        """获取计划摘要"""
        total = len(self.tasks)
        completed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED)
        failed = sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED)
        skipped = sum(1 for t in self.tasks.values() if t.status == TaskStatus.SKIPPED)
        in_progress = sum(1 for t in self.tasks.values() if t.status == TaskStatus.IN_PROGRESS)
        pending = sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING)

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "skipped": skipped,
            "in_progress": in_progress,
            "pending": pending,
            "progress": completed / total if total > 0 else 0,
        }


# ----------------------------------------------------------------------
# 5️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_planner(llm_client: Optional[Any] = None) -> TaskPlanner:
    """创建任务规划器"""
    cot_engine = ChainOfThought(llm_client)
    return TaskPlanner(cot_engine)


# ----------------------------------------------------------------------
# 6️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    pass

    logging.basicConfig(level=logging.INFO)

    # 测试任务规划
    logger.info("Testing task planner")

    planner = create_planner()

    goal = "诊断系统 CPU 使用率异常高的问题"
    context = {
        "target": "system",
        "metrics": {"cpu_usage": 95.0},
    }
    available_tools = ["collect_metrics", "analyze_logs", "identify_root_cause"]

    tasks = planner.plan(goal, context, available_tools)

    logger.info(f"Planned {len(tasks)} tasks:")
    for task in tasks:
        logger.info(f"  - {task.id}: {task.description}")
        logger.info(f"    Dependencies: {task.dependencies}")
        logger.info(f"    Parameters: {task.parameters}")

    # 测试计划摘要
    summary = planner.get_plan_summary()
    logger.info(f"Plan summary: {summary}")

    logger.info("Test passed!")
