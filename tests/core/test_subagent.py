# -*- coding: utf-8 -*-
"""子代理调度器测试"""

from __future__ import annotations

import pytest

from core.agent.subagent import (
    SubAgent,
    SubAgentResult,
    SubAgentStatus,
    create_subagent_dispatcher,
    dispatch_task,
)
from core.agent.tools import ToolRegistry


class TestSubAgent:
    """SubAgent 单元测试"""

    def test_subagent_creation(self):
        agent = SubAgent(agent_id="test-001", role="analyzer")
        assert agent.agent_id == "test-001"
        assert agent.role == "analyzer"
        assert agent.status == SubAgentStatus.IDLE

    def test_subagent_run(self):
        agent = SubAgent(agent_id="test-002")
        result = agent.run(
            goal="收集系统指标",
            context={"target": "system"},
            available_tools=["collect_metrics"],
        )
        assert isinstance(result, SubAgentResult)
        assert result.agent_id == "test-002"
        assert result.status == "completed"
        assert result.result is not None
        assert result.duration >= 0

    def test_subagent_terminate(self):
        agent = SubAgent(agent_id="test-003")
        agent.terminate()
        assert agent.is_terminated() is True
        result = agent.run(
            goal="健康检查",
            context={"target": "system"},
            available_tools=["check_health"],
        )
        assert result.status == "terminated"


class TestSubAgentDispatcher:
    """SubAgentDispatcher 单元测试"""

    def test_create_subagent(self):
        dispatcher = create_subagent_dispatcher(max_workers=2)
        try:
            agent = dispatcher.create_subagent(role="worker")
            assert agent.agent_id.startswith("subagent_")
            assert agent.role == "worker"
            assert agent in dispatcher.list_subagents()
        finally:
            dispatcher.shutdown(wait=True)

    def test_dispatch_sync(self):
        dispatcher = create_subagent_dispatcher(max_workers=2)
        try:
            result = dispatcher.dispatch(
                goal="收集系统日志",
                context={"service": "aiops"},
                available_tools=["collect_logs"],
                role="worker",
                wait=True,
            )
            assert isinstance(result, SubAgentResult)
            assert result.status == "completed"
            assert result.result is not None
        finally:
            dispatcher.shutdown(wait=True)

    def test_dispatch_batch(self):
        dispatcher = create_subagent_dispatcher(max_workers=3)
        try:
            tasks = [
                {
                    "goal": "收集系统指标",
                    "context": {"target": "system"},
                    "available_tools": ["collect_metrics"],
                    "role": "collector",
                },
                {
                    "goal": "异常检测",
                    "context": {"data": [0.1, 0.9, 0.8]},
                    "available_tools": ["analyze_anomaly"],
                    "role": "analyzer",
                },
            ]
            results = dispatcher.dispatch_batch(tasks)
            assert len(results) == len(tasks)
            for result in results:
                assert result.status == "completed"
            summary = dispatcher.get_summary()
            assert summary["total"] == 2
            assert summary["completed"] == 2
            assert summary["success_rate"] == 1.0
        finally:
            dispatcher.shutdown(wait=True)

    def test_dispatch_async_future(self):
        dispatcher = create_subagent_dispatcher(max_workers=2)
        try:
            future = dispatcher.dispatch(
                goal="健康检查",
                context={"target": "system"},
                available_tools=["check_health"],
                wait=False,
            )
            result = future.result()
            assert result.status == "completed"
        finally:
            dispatcher.shutdown(wait=True)

    def test_get_result(self):
        dispatcher = create_subagent_dispatcher(max_workers=2)
        try:
            result = dispatcher.dispatch(
                goal="运行诊断",
                context={"target": "system"},
                available_tools=["run_diagnostic"],
                wait=True,
            )
            fetched = dispatcher.get_result(result.agent_id)
            assert fetched is result
        finally:
            dispatcher.shutdown(wait=True)

    def test_terminate(self):
        dispatcher = create_subagent_dispatcher(max_workers=2)
        try:
            agent = dispatcher.create_subagent(role="worker")
            assert dispatcher.terminate(agent.agent_id) is True
        finally:
            dispatcher.shutdown(wait=True)

    def test_shutdown_idempotent(self):
        dispatcher = create_subagent_dispatcher(max_workers=2)
        dispatcher.shutdown(wait=True)


class TestDispatchTask:
    """便捷函数测试"""

    def test_dispatch_task(self):
        result = dispatch_task(
            goal="健康检查",
            context={"target": "system"},
            available_tools=["check_health"],
            role="worker",
        )
        assert isinstance(result, SubAgentResult)
        assert result.status == "completed"


class TestSubAgentTool:
    """dispatch_subagent 工具集成测试"""

    def test_dispatch_subagent_tool(self):
        registry = ToolRegistry()
        tool = registry.get_tool("dispatch_subagent")
        assert tool is not None

        result = tool.execute(
            goal="收集系统指标",
            context={"target": "system"},
            available_tools=["collect_metrics"],
            role="collector",
            wait=True,
        )
        assert result["status"] == "completed"
        assert result["result"] is not None

    def test_dispatch_subagent_tool_string_tools(self):
        registry = ToolRegistry()
        tool = registry.get_tool("dispatch_subagent")
        result = tool.execute(
            goal="运行诊断",
            context={"target": "system"},
            available_tools="run_diagnostic",
            wait=True,
        )
        assert result["status"] == "completed"


class TestAutonomousExecutorSubagent:
    """AutonomousExecutor 子代理集成测试"""

    def test_execute_plan_with_subagents(self):
        from core.agent.executor import create_autonomous_executor

        executor = create_autonomous_executor()
        result = executor.execute_plan_with_subagents(
            goal="诊断系统 CPU 使用率异常",
            context={"target": "system", "metrics": {"cpu_usage": 95.0}},
            available_tools=["collect_metrics", "analyze_anomaly", "check_health"],
            max_subagents=3,
        )
        assert "subagent_results" in result
        assert "summary" in result
        assert result["summary"]["total"] > 0
        assert result["summary"]["completed"] > 0

    def test_set_subagent_dispatcher(self):
        from core.agent.executor import AutonomousExecutor
        from core.agent.planner import create_planner
        from core.agent.tools import create_tool_executor

        executor = AutonomousExecutor(
            planner=create_planner(),
            tool_executor=create_tool_executor(),
        )
        dispatcher = create_subagent_dispatcher(max_workers=2)
        executor.set_subagent_dispatcher(dispatcher)
        assert executor.subagent_dispatcher is dispatcher


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
