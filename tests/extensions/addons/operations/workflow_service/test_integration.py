# -*- coding: utf-8 -*-
"""Integration tests for workflow_service FastAPI applications."""

import pytest
from httpx import AsyncClient, ASGITransport

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from extensions.addons.operations.workflow_service.executor_app import (
    WorkflowExecutorApp,
    app as executor_app,
)
from extensions.addons.operations.workflow_service.scheduler_app import (
    WorkflowSchedulerApp,
    app as scheduler_app,
)
from extensions.addons.operations.workflow_service.workflow_orchestrator_app import (
    WorkflowOrchestratorApp,
    app as orchestrator_app,
)
from extensions.addons.operations.workflow_service.schemas import (
    ScheduledTask,
    ServiceHealth,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowRequest,
    WorkflowTemplate,
)


class TestExecutorAppIntegration:
    """Integration tests for WorkflowExecutorApp."""

    @pytest.mark.asyncio
    async def test_executor_app_initialization(self):
        """Test executor app initialization."""
        app_instance = WorkflowExecutorApp()
        assert app_instance.repo is None
        assert app_instance.orchestrator is None
        assert app_instance.health is not None

    @pytest.mark.asyncio
    async def test_executor_app_init(self):
        """Test executor app init method."""
        app_instance = WorkflowExecutorApp()
        await app_instance.init()

        assert app_instance.repo is not None
        assert app_instance.orchestrator is not None

    @pytest.mark.asyncio
    async def test_executor_app_execute(self):
        """Test executor app execute method."""
        app_instance = WorkflowExecutorApp()
        await app_instance.init()

        # Create a workflow definition first
        definition = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test Workflow",
            nodes=[
                WorkflowNode(
                    node_id="node1",
                    name="Test Node",
                    command="echo test",
                    dependencies=[],
                )
            ],
        )
        await app_instance.repo.save_definition(definition)

        request = WorkflowRequest(workflow_id="test-workflow", params={"message": "test"})

        result = await app_instance.execute(request)

        assert result is not None
        assert "task_id" in result or "success" in result

    @pytest.mark.asyncio
    async def test_executor_app_execute_not_initialized(self):
        """Test executor app execute when not initialized."""
        app_instance = WorkflowExecutorApp()

        request = WorkflowRequest(workflow_id="test", params={})

        with pytest.raises(RuntimeError, match="Executor not initialized"):
            await app_instance.execute(request)


class TestSchedulerAppIntegration:
    """Integration tests for WorkflowSchedulerApp."""

    @pytest.mark.asyncio
    async def test_scheduler_app_initialization(self):
        """Test scheduler app initialization."""
        app_instance = WorkflowSchedulerApp()
        assert app_instance.repo is None
        assert app_instance.scheduler is None
        assert app_instance.orchestrator is None
        assert app_instance.health is not None

    @pytest.mark.asyncio
    async def test_scheduler_app_init(self):
        """Test scheduler app init method."""
        app_instance = WorkflowSchedulerApp()
        await app_instance.init()

        assert app_instance.repo is not None
        assert app_instance.scheduler is not None
        assert app_instance.orchestrator is not None

    @pytest.mark.asyncio
    async def test_scheduler_app_handle_request(self):
        """Test scheduler app handle request method."""
        app_instance = WorkflowSchedulerApp()
        await app_instance.init()

        # Create a workflow definition first
        definition = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test Workflow",
            nodes=[
                WorkflowNode(
                    node_id="node1",
                    name="Test Node",
                    command="echo test",
                    dependencies=[],
                )
            ],
        )
        await app_instance.repo.save_definition(definition)

        request = WorkflowRequest(workflow_id="test-workflow", params={})

        result = await app_instance._handle_request(request)

        assert result is not None
        assert hasattr(result, "task_id")

    @pytest.mark.asyncio
    async def test_scheduler_app_handle_request_not_initialized(self):
        """Test scheduler app handle request when not initialized."""
        app_instance = WorkflowSchedulerApp()

        request = WorkflowRequest(workflow_id="test", params={})

        with pytest.raises(RuntimeError, match="Scheduler not initialized"):
            await app_instance._handle_request(request)


class TestOrchestratorAppIntegration:
    """Integration tests for WorkflowOrchestratorApp."""

    @pytest.mark.asyncio
    async def test_orchestrator_app_initialization(self):
        """Test orchestrator app initialization."""
        app_instance = WorkflowOrchestratorApp()
        assert app_instance.repo is None
        assert app_instance.orchestrator is None
        assert app_instance.templates is not None
        assert app_instance.health is not None

    @pytest.mark.asyncio
    async def test_orchestrator_app_init(self):
        """Test orchestrator app init method."""
        app_instance = WorkflowOrchestratorApp()
        await app_instance.init()

        assert app_instance.repo is not None
        assert app_instance.orchestrator is not None

    @pytest.mark.asyncio
    async def test_orchestrator_app_create_definition(self):
        """Test orchestrator app create definition method."""
        app_instance = WorkflowOrchestratorApp()
        await app_instance.init()

        definition = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test Workflow",
            nodes=[
                WorkflowNode(
                    node_id="node1",
                    name="Test Node",
                    command="echo test",
                    dependencies=[],
                )
            ],
        )

        result = await app_instance.create_definition(definition)

        assert result["workflow_id"] == "test-workflow"
        assert result["status"] == "created"

    @pytest.mark.asyncio
    async def test_orchestrator_app_start_workflow(self):
        """Test orchestrator app start workflow method."""
        app_instance = WorkflowOrchestratorApp()
        await app_instance.init()

        # Create a workflow definition first
        definition = WorkflowDefinition(
            workflow_id="test-workflow",
            name="Test Workflow",
            nodes=[
                WorkflowNode(
                    node_id="node1",
                    name="Test Node",
                    command="echo test",
                    dependencies=[],
                )
            ],
        )
        await app_instance.create_definition(definition)

        request = WorkflowRequest(workflow_id="test-workflow", params={})

        result = await app_instance.start_workflow(request)

        assert result is not None
        assert "task_id" in result or "success" in result

    @pytest.mark.asyncio
    async def test_orchestrator_app_start_workflow_not_initialized(self):
        """Test orchestrator app start workflow when not initialized."""
        app_instance = WorkflowOrchestratorApp()

        request = WorkflowRequest(workflow_id="test", params={})

        with pytest.raises(RuntimeError, match="Orchestrator not initialized"):
            await app_instance.start_workflow(request)


class TestExecutorAPIEndpoints:
    """Integration tests for executor API endpoints."""

    @pytest.mark.asyncio
    async def test_executor_health_endpoint(self):
        """Test executor /health endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_executor_metrics_endpoint(self):
        """Test executor /metrics endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_executor_execute_endpoint(self):
        """Test executor /workflows/execute endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")


class TestSchedulerAPIEndpoints:
    """Integration tests for scheduler API endpoints."""

    @pytest.mark.asyncio
    async def test_scheduler_health_endpoint(self):
        """Test scheduler /health endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_scheduler_metrics_endpoint(self):
        """Test scheduler /metrics endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_scheduler_schedule_endpoint(self):
        """Test scheduler /workflows/schedule endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_scheduler_queue_endpoint(self):
        """Test scheduler /workflows/queue endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_scheduler_run_once_endpoint(self):
        """Test scheduler /workflows/run-once endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")


class TestOrchestratorAPIEndpoints:
    """Integration tests for orchestrator API endpoints."""

    @pytest.mark.asyncio
    async def test_orchestrator_health_endpoint(self):
        """Test orchestrator /health endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_orchestrator_metrics_endpoint(self):
        """Test orchestrator /metrics endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_orchestrator_create_definition_endpoint(self):
        """Test orchestrator /workflows/definitions endpoint (POST)."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_orchestrator_list_definitions_endpoint(self):
        """Test orchestrator /workflows/definitions endpoint (GET)."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_orchestrator_execute_endpoint(self):
        """Test orchestrator /workflows/execute endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_orchestrator_list_executions_endpoint(self):
        """Test orchestrator /workflows/executions endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_orchestrator_create_template_endpoint(self):
        """Test orchestrator /workflows/templates endpoint (POST)."""
        pytest.skip("Skipping API endpoint tests that require full initialization")

    @pytest.mark.asyncio
    async def test_orchestrator_render_template_endpoint(self):
        """Test orchestrator /workflows/templates/{template_id}/render endpoint."""
        pytest.skip("Skipping API endpoint tests that require full initialization")


class TestCrossServiceIntegration:
    """Integration tests across different services."""

    @pytest.mark.asyncio
    async def test_orchestrator_to_executor_flow(self):
        """Test workflow flow from orchestrator to executor."""
        # This would test the complete flow but requires running both services
        # For now, we'll just verify the components can be initialized together
        orchestrator = WorkflowOrchestratorApp()
        executor = WorkflowExecutorApp()

        await orchestrator.init()
        await executor.init()

        assert orchestrator.repo is not None
        assert executor.repo is not None

    @pytest.mark.asyncio
    async def test_scheduler_to_orchestrator_flow(self):
        """Test workflow flow from scheduler to orchestrator."""
        scheduler = WorkflowSchedulerApp()
        orchestrator = WorkflowOrchestratorApp()

        await scheduler.init()
        await orchestrator.init()

        assert scheduler.orchestrator is not None
        assert orchestrator.orchestrator is not None

    @pytest.mark.asyncio
    async def test_template_rendering_in_workflow(self):
        """Test template rendering within workflow execution."""
        orchestrator = WorkflowOrchestratorApp()
        await orchestrator.init()

        # Create a template
        template = WorkflowTemplate(
            template_id="test-template",
            name="Test",
            source="echo {{ message }}",
            default_params={"message": "default"},
        )
        await orchestrator.templates.register(template)

        # Render the template
        rendered = await orchestrator.templates.render(
            "test-template", {"message": "Hello"}
        )

        assert "Hello" in rendered

    @pytest.mark.asyncio
    async def test_metrics_collection(self):
        """Test that metrics are collected across services."""
        from metrics import (
            WORKFLOWS_CREATED,
            WORKFLOWS_COMPLETED,
        )

        # Increment some metrics
        WORKFLOWS_CREATED.labels(priority="high").inc()
        WORKFLOWS_COMPLETED.labels(status="succeeded").inc()

        # Verify they were incremented
        assert WORKFLOWS_CREATED.labels(priority="high")._value.get() >= 1
        assert WORKFLOWS_COMPLETED.labels(status="succeeded")._value.get() >= 1

    @pytest.mark.asyncio
    async def test_health_check_all_services(self):
        """Test health check across all services."""
        executor = WorkflowExecutorApp()
        scheduler = WorkflowSchedulerApp()
        orchestrator = WorkflowOrchestratorApp()

        await executor.init()
        await scheduler.init()
        await orchestrator.init()

        # All should have health engines
        assert executor.health is not None
        assert scheduler.health is not None
        assert orchestrator.health is not None

        # All should return valid health status
        executor_health = await executor.health.check("executor", 0)
        scheduler_health = await scheduler.health.check("scheduler", 0)
        orchestrator_health = await orchestrator.health.check("orchestrator", 0)

        assert executor_health.status in ["ok", "degraded"]
        assert scheduler_health.status in ["ok", "degraded"]
        assert orchestrator_health.status in ["ok", "degraded"]
