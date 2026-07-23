# -*- coding: utf-8 -*-
"""Core tests for workflow microservice."""

from __future__ import annotations

import pytest

from services.workflow_service.grpc.client import WorkflowRPCClient
from services.workflow_service.grpc.server import WorkflowRPCServer
from services.workflow_service.orchestrator import WorkflowOrchestrator
from services.workflow_service.repository import InMemoryWorkflowRepository
from services.workflow_service.retry import RetryEngine
from services.workflow_service.saga import WorkflowSagaOrchestrator
from services.workflow_service.scheduler import WorkflowScheduler
from services.workflow_service.schemas import (
    ScheduledTask,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowTask,
    WorkflowTemplate,
)
from services.workflow_service.state_machine import WorkflowStateMachine
from services.workflow_service.templates import TemplateManager
from services.workflow_service.versioning import WorkflowVersionManager


@pytest.fixture
async def repo():
    return InMemoryWorkflowRepository()


@pytest.mark.asyncio
class TestOrchestrator:
    async def test_create_and_execute(self):
        repo = InMemoryWorkflowRepository()
        await repo.save_definition(
            WorkflowDefinition(
                workflow_id="wf-1",
                name="Test Workflow",
                nodes=[WorkflowNode(node_id="n1", name="Node 1", command="echo hello")],
            )
        )
        orchestrator = WorkflowOrchestrator(repo)
        request = WorkflowRequest(workflow_id="wf-1")
        result = await orchestrator.execute(await orchestrator.create_task(request))
        assert result.success is True

    async def test_node_failure(self):
        repo = InMemoryWorkflowRepository()
        await repo.save_definition(
            WorkflowDefinition(
                workflow_id="wf-fail",
                name="Failing Workflow",
                nodes=[WorkflowNode(node_id="n1", name="Node 1", command="fail")],
            )
        )
        orchestrator = WorkflowOrchestrator(repo)
        request = WorkflowRequest(workflow_id="wf-fail")
        result = await orchestrator.execute(await orchestrator.create_task(request))
        assert result.success is False


@pytest.mark.asyncio
class TestScheduler:
    async def test_enqueue_and_run(self):
        repo = InMemoryWorkflowRepository()
        await repo.save_definition(
            WorkflowDefinition(
                workflow_id="wf-sched",
                name="Scheduled",
                nodes=[WorkflowNode(node_id="n1", name="N1", command="echo")],
            )
        )
        orchestrator = WorkflowOrchestrator(repo)
        scheduler = WorkflowScheduler(poll_interval=0.1)
        scheduler.register_handler(orchestrator.create_task)
        request = WorkflowRequest(workflow_id="wf-sched")
        queued = await scheduler.enqueue(request)
        assert queued.startswith("SCHEDULED-")

    async def test_schedule(self):
        scheduler = WorkflowScheduler(poll_interval=0.1)
        schedule = ScheduledTask(
            schedule_id="sched-1",
            workflow_id="wf-1",
            cron="* * * * *",
        )
        sid = await scheduler.schedule(schedule)
        assert sid == "sched-1"
        results = await scheduler.run_once()
        assert isinstance(results, list)


@pytest.mark.asyncio
class TestStateMachine:
    async def test_transition(self):
        task = WorkflowTask(task_id="t1", workflow_id="wf-1")
        sm = WorkflowStateMachine(task)
        assert sm.transition(WorkflowStatus.RUNNING) is True
        assert sm.transition(WorkflowStatus.SUCCEEDED) is True
        assert sm.transition(WorkflowStatus.COMPLETED) is True
        assert sm.get_state()["status"] == "completed"


@pytest.mark.asyncio
class TestRetry:
    async def test_success_no_retry(self):
        engine = RetryEngine()

        async def success() -> dict:
            return {"ok": True}

        result = await engine.execute(success)
        assert result["ok"] is True

    async def test_retry_then_success(self):
        engine = RetryEngine()
        attempts = {"count": 0}

        async def flaky():
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise RuntimeError("retryable")
            return {"ok": True}

        result = await engine.execute(flaky)
        assert result["ok"] is True

    async def test_non_retryable(self):
        engine = RetryEngine()
        with pytest.raises(RuntimeError):
            await engine.execute(lambda: (_ for _ in ()).throw(RuntimeError("fatal")))

    async def test_policies(self):
        engine = RetryEngine()
        assert "exponential" in engine.policies
        assert "jitter" in engine.policies


@pytest.mark.asyncio
class TestTemplates:
    async def test_render(self):
        manager = TemplateManager()
        template = WorkflowTemplate(
            template_id="tpl-1",
            name="Hello",
            source="Hello {{ name }}",
            default_params={"name": "World"},
        )
        await manager.register(template)
        output = await manager.render("tpl-1")
        assert output == "Hello World"


@pytest.mark.asyncio
class TestVersioning:
    async def test_commit_and_list(self):
        manager = WorkflowVersionManager()
        definition = WorkflowDefinition(workflow_id="wf-1", name="Test")
        version = await manager.commit(definition)
        assert version.version == "v1.0.0"
        versions = await manager.list_versions("wf-1")
        assert len(versions) == 1


@pytest.mark.asyncio
class TestGRPC:
    async def test_server_client(self):
        server = WorkflowRPCServer()

        async def echo(message: str) -> dict:
            return {"message": message}

        server.register("echo", echo)
        client = WorkflowRPCClient(server=server)
        result = await client.call("echo", message="hi")
        assert result["message"] == "hi"


@pytest.mark.asyncio
class TestSaga:
    async def test_successful_saga(self):
        saga = WorkflowSagaOrchestrator()
        from services.workflow_service.schemas import SagaStep

        steps = [SagaStep(step_id="s1", service="svc", action="do", compensation="undo")]
        saga.register("s1", steps, {"do": lambda: {"ok": True}}, {"undo": lambda: {"ok": True}})
        result = await saga.execute("s1")
        assert result["success"] is True

    async def test_failed_saga_compensates(self):
        saga = WorkflowSagaOrchestrator()
        from services.workflow_service.schemas import SagaStep

        steps = [
            SagaStep(step_id="s1", service="svc", action="ok", compensation="undo"),
            SagaStep(step_id="s2", service="svc", action="fail", compensation="undo"),
        ]
        saga.register(
            "s2",
            steps,
            {
                "ok": lambda: {"ok": True},
                "fail": lambda: (_ for _ in ()).throw(RuntimeError("fail")),
            },
            {"undo": lambda: {"ok": True}},
        )
        result = await saga.execute("s2")
        assert result["success"] is False
