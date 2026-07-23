# -*- coding: utf-8 -*-
"""测试L2L3工作流集成器模块"""

import asyncio

import pytest

from core.l2l3_workflow_integrator import (
    L2L3WorkflowIntegrator,
    WorkflowDefinition,
    WorkflowTriggerType,
    get_l2l3_workflow_integrator,
)


@pytest.fixture(autouse=True)
def skip_heavy_initialization(monkeypatch):
    # 避免初始化时加载 heavy ML/分析依赖
    monkeypatch.setattr(
        "core.l2l3_workflow_integrator.L2L3WorkflowIntegrator._initialize_causal_analyzer",
        lambda self: None,
    )
    monkeypatch.setattr(
        "core.l2l3_workflow_integrator.L2L3WorkflowIntegrator._initialize_workflow_engine",
        lambda self: None,
    )


@pytest.fixture
def integrator():
    return L2L3WorkflowIntegrator()


def _wait_for_execution(integrator, execution_id):
    async def wait():
        for _ in range(100):
            if execution_id not in integrator.active_executions:
                return True
            await asyncio.sleep(0.01)
        return False

    asyncio.run(wait())


class TestInitialization:
    def test_get_l2l3_workflow_integrator(self):
        i = get_l2l3_workflow_integrator()
        assert isinstance(i, L2L3WorkflowIntegrator)


class TestWorkflowRegistration:
    def test_register_workflow(self, integrator):
        wf = WorkflowDefinition(
            workflow_id="wf1",
            name="Test Workflow",
            description="desc",
            trigger_type=WorkflowTriggerType.MANUAL,
            steps=[
                {"type": "data_processing", "config": {"processing_type": "count", "data": [1, 2]}},
                {
                    "type": "notification",
                    "config": {"notification_type": "email", "recipients": ["a@b"]},
                },
                {"type": "unknown_type", "config": {}},
            ],
        )
        integrator.register_workflow(wf)
        assert "wf1" in integrator.workflows

    def test_register_trigger_handler(self, integrator):
        calls = []
        integrator.register_trigger_handler(WorkflowTriggerType.MANUAL, lambda d: calls.append(d))
        assert len(integrator.trigger_handlers[WorkflowTriggerType.MANUAL]) == 1


class TestWorkflowExecution:
    def test_trigger_and_execute_manual(self, integrator):
        wf = WorkflowDefinition(
            workflow_id="wf1",
            name="Manual",
            description="desc",
            trigger_type=WorkflowTriggerType.MANUAL,
            steps=[
                {"type": "data_processing", "config": {"processing_type": "count", "data": [1, 2]}}
            ],
        )
        integrator.register_workflow(wf)

        async def run():
            execution_id = await integrator.trigger_workflow("wf1")
            for _ in range(100):
                if execution_id not in integrator.active_executions:
                    break
                await asyncio.sleep(0.01)
            return execution_id

        execution_id = asyncio.run(run())
        status = integrator.get_execution_status(execution_id)
        assert status["status"] == "completed"
        assert integrator.successful_executions == 1

    def test_trigger_workflow_not_found(self, integrator):
        async def run():
            with pytest.raises(ValueError):
                await integrator.trigger_workflow("missing")

        asyncio.run(run())

    def test_cancel_execution(self, integrator):
        wf = WorkflowDefinition(
            workflow_id="wf_cancel",
            name="Cancel",
            description="desc",
            trigger_type=WorkflowTriggerType.MANUAL,
            steps=[],
        )
        integrator.register_workflow(wf)

        async def run():
            execution_id = await integrator.trigger_workflow("wf_cancel")
            # cancel before it finishes (steps empty so it may finish immediately)
            result = await integrator.cancel_execution(execution_id)
            return execution_id, result

        execution_id, cancelled = asyncio.run(run())
        status = integrator.get_execution_status(execution_id)["status"]
        assert cancelled is True or status == "completed"


class TestCausalTrigger:
    def test_check_trigger_conditions(self, integrator):
        result = integrator._check_trigger_conditions({}, {"confidence": 0.9, "root_causes": ["a"]})
        assert result is True
        result = integrator._check_trigger_conditions(
            {"confidence_threshold": 0.95}, {"confidence": 0.9}
        )
        assert result is False

    def test_handle_causal_analysis_trigger(self, integrator):
        wf = WorkflowDefinition(
            workflow_id="wf_causal",
            name="Causal",
            description="desc",
            trigger_type=WorkflowTriggerType.CAUSAL_ANALYSIS,
            trigger_config={"confidence_threshold": 0.8, "min_root_causes": 1},
            steps=[],
        )
        integrator.register_workflow(wf)

        async def run():
            ids = await integrator.handle_causal_analysis_trigger(
                {"confidence": 0.9, "root_causes": ["cpu", "memory"]}
            )
            for eid in ids:
                for _ in range(100):
                    if eid not in integrator.active_executions:
                        break
                    await asyncio.sleep(0.01)
            return ids

        ids = asyncio.run(run())
        assert len(ids) == 1


class TestStatistics:
    def test_get_statistics(self, integrator):
        integrator.total_executions = 10
        integrator.successful_executions = 8
        stats = integrator.get_statistics()
        assert stats["total_executions"] == 10
        assert stats["success_rate"] == 0.8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
