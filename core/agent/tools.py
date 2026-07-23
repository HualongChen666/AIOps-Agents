# -*- coding: utf-8 -*-
"""
tools.py
-------
AI Agent 工具生态建设。

功能：
- 工具定义和注册
- 工具执行
- 工具组合和链式调用
- 工具自动选择
- 目标：工具使用准确率 ≥ 90%
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 1️⃣ 工具类别枚举
# ----------------------------------------------------------------------
class ToolCategory(Enum):
    """工具类别"""

    MONITORING = "monitoring"
    ANALYSIS = "analysis"
    EXECUTION = "execution"
    NOTIFICATION = "notification"
    DIAGNOSTIC = "diagnostic"


# ----------------------------------------------------------------------
# 2️⃣ 工具定义
# ----------------------------------------------------------------------
@dataclass
class Tool:
    """工具定义"""

    name: str
    description: str
    category: ToolCategory
    function: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)
    optional_params: List[str] = field(default_factory=list)
    examples: List[Dict[str, Any]] = field(default_factory=list)

    def execute(self, **kwargs) -> Any:
        """执行工具"""
        # 检查必需参数
        missing_params = [p for p in self.required_params if p not in kwargs]
        if missing_params:
            raise ValueError(f"Missing required parameters: {missing_params}")

        # 参数安全验证
        self._validate_parameters(kwargs)

        # 合并默认参数
        params = {**self.parameters, **kwargs}

        # 执行工具函数
        try:
            if asyncio.iscoroutinefunction(self.function):
                # 🔧 性能优化: 检查是否已在异步上下文中
                try:
                    asyncio.get_running_loop()
                    # 已在异步上下文中，创建任务
                    return asyncio.create_task(self.function(**params))
                except RuntimeError:
                    # 不在异步上下文中，使用 asyncio.run
                    return asyncio.run(self.function(**params))
            else:
                return self.function(**params)
        except Exception as e:
            logger.error(f"Tool {self.name} execution failed: {e}")
            raise

    def _validate_parameters(self, params: Dict[str, Any]):
        """验证参数安全性"""
        # 防止命令注入
        for key, value in params.items():
            if isinstance(value, str):
                # 检查危险字符
                dangerous_chars = [";", "|", "&", "$", "`", "\\", "\n", "\r"]
                if any(char in value for char in dangerous_chars):
                    raise ValueError(f"Parameter {key} contains dangerous characters")
                # 检查路径遍历
                if "../" in value or "..\\" in value:
                    raise ValueError(f"Parameter {key} contains path traversal attempt")
            elif isinstance(value, (list, dict)):
                # 递归验证
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            dangerous_chars = [";", "|", "&", "$", "`", "\\", "\n", "\r"]
                            if any(char in item for char in dangerous_chars):
                                raise ValueError(f"Parameter {key} contains dangerous characters")
                            if "../" in item or "..\\" in item:
                                raise ValueError(f"Parameter {key} contains path traversal attempt")

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": self.parameters,
            "required_params": self.required_params,
            "optional_params": self.optional_params,
            "examples": self.examples,
        }


# ----------------------------------------------------------------------
# 3️⃣ 工具注册表
# ----------------------------------------------------------------------
class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._initialize_default_tools()

    def register(self, tool: Tool) -> None:
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"Registered tool: {tool.name}")

    def unregister(self, tool_name: str) -> None:
        """注销工具"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"Unregistered tool: {tool_name}")

    def get_tool(self, tool_name: str) -> Optional[Tool]:
        """获取工具"""
        return self.tools.get(tool_name)

    def list_tools(
        self,
        category: Optional[ToolCategory] = None,
    ) -> List[Tool]:
        """列出工具"""
        if category is None:
            return list(self.tools.values())
        return [tool for tool in self.tools.values() if tool.category == category]

    def search_tools(
        self,
        query: str,
    ) -> List[Tool]:
        """搜索工具"""
        query_lower = query.lower()
        results = []

        for tool in self.tools.values():
            # 搜索名称和描述
            if query_lower in tool.name.lower() or query_lower in tool.description.lower():
                results.append(tool)

        return results

    def _initialize_default_tools(self):
        """初始化默认工具"""
        # 监控工具
        self.register(
            Tool(
                name="collect_metrics",
                description="收集系统指标（CPU、内存、磁盘等）",
                category=ToolCategory.MONITORING,
                function=self._collect_metrics,
                required_params=["target"],
                optional_params=["duration", "interval"],
            )
        )

        self.register(
            Tool(
                name="collect_logs",
                description="收集系统日志",
                category=ToolCategory.MONITORING,
                function=self._collect_logs,
                required_params=["service"],
                optional_params=["level", "lines"],
            )
        )

        # 分析工具
        self.register(
            Tool(
                name="analyze_anomaly",
                description="检测异常",
                category=ToolCategory.ANALYSIS,
                function=self._analyze_anomaly,
                required_params=["data"],
                optional_params=["threshold", "method"],
            )
        )

        self.register(
            Tool(
                name="root_cause_analysis",
                description="根因分析",
                category=ToolCategory.ANALYSIS,
                function=self._root_cause_analysis,
                required_params=["alert_id"],
                optional_params=["method"],
            )
        )

        # 执行工具
        self.register(
            Tool(
                name="restart_service",
                description="重启服务",
                category=ToolCategory.EXECUTION,
                function=self._restart_service,
                required_params=["service_name"],
                optional_params=["timeout"],
            )
        )

        self.register(
            Tool(
                name="scale_service",
                description="扩缩容服务",
                category=ToolCategory.EXECUTION,
                function=self._scale_service,
                required_params=["service_name", "replicas"],
                optional_params=["strategy"],
            )
        )

        # 诊断工具
        self.register(
            Tool(
                name="check_health",
                description="健康检查",
                category=ToolCategory.DIAGNOSTIC,
                function=self._check_health,
                required_params=["target"],
            )
        )

        self.register(
            Tool(
                name="run_diagnostic",
                description="运行诊断",
                category=ToolCategory.DIAGNOSTIC,
                function=self._run_diagnostic,
                required_params=["target"],
                optional_params=["type"],
            )
        )

        # 子代理工具
        self.register(
            Tool(
                name="dispatch_subagent",
                description="将子任务分派给子 Agent 执行",
                category=ToolCategory.EXECUTION,
                function=self._dispatch_subagent,
                required_params=["goal"],
                optional_params=["context", "available_tools", "role", "wait"],
            )
        )

    # 默认工具实现（示例）
    def _collect_metrics(
        self, target: str, duration: int = 60, interval: int = 5
    ) -> Dict[str, Any]:
        """收集指标"""
        logger.info(f"Collecting metrics for {target}")
        # 实际实现应连接到监控系统
        return {
            "target": target,
            "cpu_usage": 75.5,
            "memory_usage": 60.2,
            "disk_usage": 45.8,
            "timestamp": "2024-01-01T00:00:00Z",
        }

    def _collect_logs(self, service: str, level: str = "INFO", lines: int = 100) -> List[str]:
        """收集日志"""
        logger.info(f"Collecting logs for {service}")
        # 实际实现应连接到日志系统
        return [f"[{level}] Service {service} log line {i}" for i in range(lines)]

    def _analyze_anomaly(
        self,
        data: List[float],
        threshold: float = 0.5,
        method: str = "transformer",
    ) -> Dict[str, Any]:
        """异常检测"""
        logger.info(f"Analyzing anomaly with {method}")
        # 实际实现应调用异常检测模型
        return {
            "method": method,
            "is_anomaly": max(data) > threshold,
            "anomaly_score": max(data),
        }

    def _root_cause_analysis(
        self,
        alert_id: str,
        method: str = "causal",
    ) -> Dict[str, Any]:
        """根因分析"""
        logger.info(f"Root cause analysis for {alert_id} using {method}")
        # 实际实现应调用因果分析引擎
        return {
            "alert_id": alert_id,
            "method": method,
            "root_cause": "service_A",
            "confidence": 0.95,
        }

    def _restart_service(self, service_name: str, timeout: int = 30) -> Dict[str, Any]:
        """重启服务"""
        logger.info(f"Restarting service {service_name}")
        # 实际实现应调用服务管理接口
        return {
            "service": service_name,
            "status": "restarted",
            "timeout": timeout,
        }

    def _scale_service(
        self,
        service_name: str,
        replicas: int,
        strategy: str = "rolling",
    ) -> Dict[str, Any]:
        """扩缩容服务"""
        logger.info(f"Scaling service {service_name} to {replicas} replicas")
        # 实际实现应调用扩缩容接口
        return {
            "service": service_name,
            "replicas": replicas,
            "strategy": strategy,
            "status": "scaled",
        }

    def _check_health(self, target: str) -> Dict[str, Any]:
        """健康检查"""
        logger.info(f"Checking health of {target}")
        # 实际实现应调用健康检查接口
        return {
            "target": target,
            "healthy": True,
            "status": "ok",
        }

    def _run_diagnostic(self, target: str, type: str = "basic") -> Dict[str, Any]:
        """运行诊断"""
        logger.info(f"Running {type} diagnostic for {target}")
        # 实际实现应调用诊断工具
        return {
            "target": target,
            "type": type,
            "result": "healthy",
        }

    def _dispatch_subagent(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        available_tools: Optional[Any] = None,
        role: str = "worker",
        wait: bool = True,
    ) -> Dict[str, Any]:
        """分派子 Agent 执行子任务"""
        # 延迟导入，避免循环依赖
        from .subagent import SubAgentDispatcher

        context = context or {}
        tools: List[str] = []
        if available_tools is None:
            tools = []
        elif isinstance(available_tools, str):
            tools = [t.strip() for t in available_tools.split(",") if t.strip()]
        elif isinstance(available_tools, list):
            tools = [str(t) for t in available_tools]

        dispatcher = SubAgentDispatcher(max_workers=2)
        try:
            if wait:
                result = dispatcher.dispatch(
                    goal=goal,
                    context=context,
                    available_tools=tools,
                    role=role,
                    wait=True,
                )
                return result.to_dict()  # type: ignore[union-attr]

            future = dispatcher.dispatch(
                goal=goal,
                context=context,
                available_tools=tools,
                role=role,
                wait=False,
            )
            return {
                "agent_id": "pending",
                "status": "dispatched",
                "goal": goal,
                "role": role,
                "future": future,
            }
        finally:
            # 同步等待模式下关闭调度器；异步模式由调用方持有 future
            if wait:
                dispatcher.shutdown(wait=True)


# ----------------------------------------------------------------------
# 4️⃣ 工具选择器
# ----------------------------------------------------------------------
class ToolSelector:
    """工具选择器"""

    def __init__(self, registry: ToolRegistry):
        """
        Parameters
        ----------
        registry : ToolRegistry
            工具注册表
        """
        self.registry = registry

    def select_tool(
        self,
        task_description: str,
        context: Dict[str, Any],
    ) -> Optional[Tool]:
        """
        自动选择工具

        Parameters
        ----------
        task_description : str
            任务描述
        context : Dict[str, Any]
            上下文信息

        Returns
        -------
        Tool or None
            选择的工具
        """
        # 基于关键词匹配（优先匹配更具体的关键词）
        task_lower = task_description.lower()

        # 收集日志（更具体的关键词优先）
        if any(kw in task_lower for kw in ["日志", "log"]):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if "log" in tool.name.lower():
                    return tool

        # 收集指标
        if any(kw in task_lower for kw in ["收集", "指标", "监控", "metrics", "collect"]):
            tools = self.registry.list_tools(ToolCategory.MONITORING)
            for tool in tools:
                if "metric" in tool.name.lower():
                    return tool

        # 异常检测
        if any(kw in task_lower for kw in ["异常", "检测", "anomaly", "detect"]):
            tools = self.registry.list_tools(ToolCategory.ANALYSIS)
            for tool in tools:
                if "anomaly" in tool.name.lower():
                    return tool

        # 根因分析
        if any(kw in task_lower for kw in ["根因", "分析", "root cause", "analyze"]):
            tools = self.registry.list_tools(ToolCategory.ANALYSIS)
            for tool in tools:
                if "root" in tool.name.lower():
                    return tool

        # 重启服务
        if any(kw in task_lower for kw in ["重启", "restart"]):
            tools = self.registry.list_tools(ToolCategory.EXECUTION)
            for tool in tools:
                if "restart" in tool.name.lower():
                    return tool

        # 扩缩容
        if any(kw in task_lower for kw in ["扩容", "缩容", "scale"]):
            tools = self.registry.list_tools(ToolCategory.EXECUTION)
            for tool in tools:
                if "scale" in tool.name.lower():
                    return tool

        # 健康检查
        if any(kw in task_lower for kw in ["健康", "检查", "health", "check"]):
            tools = self.registry.list_tools(ToolCategory.DIAGNOSTIC)
            for tool in tools:
                if "health" in tool.name.lower():
                    return tool

        # 如果没有匹配，返回 None
        logger.warning(f"No tool matched for task: {task_description}")
        return None

    def select_tools_for_chain(
        self,
        task_chain: List[str],
        context: Dict[str, Any],
    ) -> List[Tool]:
        """
        为任务链选择工具

        Parameters
        ----------
        task_chain : List[str]
            任务链
        context : Dict[str, Any]
            上下文信息

        Returns
        -------
        List[Tool]
            工具列表
        """
        tools = []

        for task in task_chain:
            tool = self.select_tool(task, context)
            if tool:
                tools.append(tool)

        return tools


# ----------------------------------------------------------------------
# 5️⃣ 工具执行器
# ----------------------------------------------------------------------
class ToolExecutor:
    """工具执行器"""

    def __init__(self, registry: ToolRegistry):
        """
        Parameters
        ----------
        registry : ToolRegistry
            工具注册表
        """
        self.registry = registry
        self.selector = ToolSelector(registry)
        self.execution_history: List[Dict[str, Any]] = []

    def execute_tool(
        self,
        tool_name: str,
        **kwargs,
    ) -> Any:
        """
        执行单个工具

        Parameters
        ----------
        tool_name : str
            工具名称
        **kwargs
            工具参数

        Returns
        -------
        Any
            执行结果
        """
        tool = self.registry.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool not found: {tool_name}")

        logger.info(f"Executing tool: {tool_name}")

        try:
            result = tool.execute(**kwargs)

            # 记录执行历史
            self.execution_history.append(
                {
                    "tool": tool_name,
                    "parameters": kwargs,
                    "result": str(result),
                    "success": True,
                }
            )

            return result
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")

            self.execution_history.append(
                {
                    "tool": tool_name,
                    "parameters": kwargs,
                    "result": str(e),
                    "success": False,
                }
            )

            raise

    def execute_chain(
        self,
        tool_chain: List[Tuple[str, Dict[str, Any]]],
    ) -> List[Any]:
        """
        执行工具链

        Parameters
        ----------
        tool_chain : List[Tuple[str, Dict[str, Any]]]
            工具链 [(tool_name, params), ...]

        Returns
        -------
        List[Any]
            执行结果列表
        """
        results = []

        for tool_name, params in tool_chain:
            try:
                result = self.execute_tool(tool_name, **params)
                results.append(result)
            except Exception as e:
                logger.error(f"Chain execution failed at {tool_name}: {e}")
                break

        return results

    def execute_with_auto_selection(
        self,
        task_description: str,
        context: Dict[str, Any],
    ) -> Any:
        """
        自动选择工具并执行

        Parameters
        ----------
        task_description : str
            任务描述
        context : Dict[str, Any]
            上下文信息

        Returns
        -------
        Any
            执行结果
        """
        tool = self.selector.select_tool(task_description, context)
        if tool is None:
            raise ValueError(f"No tool found for task: {task_description}")

        # 从上下文中推断参数
        params = self._infer_parameters(tool, context)

        return self.execute_tool(tool.name, **params)

    def _infer_parameters(
        self,
        tool: Tool,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """从上下文推断工具参数"""
        params = {}

        for param in tool.required_params:
            if param in context:
                params[param] = context[param]
            else:
                # 尝试从上下文中查找相关值
                if param == "target":
                    params[param] = context.get("service", "system")
                elif param == "service":
                    params[param] = context.get("target", "unknown")
                elif param == "data":
                    params[param] = context.get("metrics", [])

        return params

    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计"""
        total = len(self.execution_history)
        successful = sum(1 for h in self.execution_history if h["success"])
        failed = total - successful

        return {
            "total": total,
            "successful": successful,
            "failed": failed,
            "success_rate": successful / total if total > 0 else 0,
        }


# ----------------------------------------------------------------------
# 6️⃣ 工厂函数
# ----------------------------------------------------------------------
def create_tool_registry() -> ToolRegistry:
    """创建工具注册表"""
    return ToolRegistry()


def create_tool_executor(registry: Optional[ToolRegistry] = None) -> ToolExecutor:
    """创建工具执行器"""
    if registry is None:
        registry = create_tool_registry()
    return ToolExecutor(registry)


# ----------------------------------------------------------------------
# 7️⃣ CLI 用于快速测试
# ----------------------------------------------------------------------
if __name__ == "__main__":  # pragma: no cover
    pass

    logging.basicConfig(level=logging.INFO)

    # 测试工具注册表
    logger.info("Testing tool registry")
    registry = create_tool_registry()

    tools = registry.list_tools()
    logger.info(f"Registered {len(tools)} tools:")
    for tool in tools:
        logger.info(f"  - {tool.name}: {tool.description}")

    # 测试工具选择
    logger.info("Testing tool selector")
    selector = ToolSelector(registry)

    selected_tool: Optional[Tool] = selector.select_tool("收集系统指标", {"target": "system"})
    logger.info(f"Selected tool: {selected_tool.name if selected_tool else None}")

    # 测试工具执行
    logger.info("Testing tool executor")
    executor = create_tool_executor(registry)

    result = executor.execute_tool("collect_metrics", target="system")
    logger.info(f"Execution result: {result}")

    # 测试执行统计
    stats = executor.get_execution_statistics()
    logger.info(f"Execution statistics: {stats}")

    logger.info("Test passed!")
