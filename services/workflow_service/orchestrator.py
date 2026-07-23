# -*- coding: utf-8 -*-
"""Workflow orchestration engine (Airflow abstraction)."""

from __future__ import annotations

import asyncio
import time
import uuid
from typing import Any, Dict, List

from services.workflow_service.metrics import (
    WORKFLOW_EXECUTION_DURATION,
    WORKFLOW_NODE_EXECUTION_DURATION,
    WORKFLOWS_COMPLETED,
    WORKFLOWS_CREATED,
)
from services.workflow_service.repository import WorkflowRepository
from services.workflow_service.retry import RetryEngine
from services.workflow_service.schemas import (
    WorkflowExecutionResult,
    WorkflowNode,
    WorkflowRequest,
    WorkflowStatus,
    WorkflowTask,
)
from services.workflow_service.state_machine import WorkflowStateMachine


class WorkflowOrchestrator:
    """Orchestrate workflow DAG execution with state machine tracking."""

    def __init__(self, repository: WorkflowRepository) -> None:
        self.repo = repository
        self.machines: Dict[str, WorkflowStateMachine] = {}
        self.retry_engine = RetryEngine()

    def _get_machine(self, task: WorkflowTask) -> WorkflowStateMachine:
        if task.task_id not in self.machines:
            self.machines[task.task_id] = WorkflowStateMachine(task)
        return self.machines[task.task_id]

    async def create_task(self, request: WorkflowRequest) -> WorkflowTask:
        task_id = f"WF-{uuid.uuid4().hex[:16].upper()}"
        definition = await self.repo.get_definition(request.workflow_id)
        if not definition:
            raise ValueError(f"Workflow definition {request.workflow_id} not found")
        task = WorkflowTask(
            task_id=task_id,
            workflow_id=request.workflow_id,
            params={**definition.metadata, **request.params},
        )
        WORKFLOWS_CREATED.labels(priority=request.priority.value).inc()
        await self.repo.save_task(task)
        return task

    async def execute(self, task: WorkflowTask) -> WorkflowExecutionResult:
        start = time.perf_counter()
        machine = self._get_machine(task)
        machine.transition(WorkflowStatus.RUNNING)

        definition = await self.repo.get_definition(task.workflow_id)
        if not definition:
            machine.transition(WorkflowStatus.FAILED)
            task.status = WorkflowStatus.FAILED
            await self.repo.save_task(task)
            return WorkflowExecutionResult(
                task_id=task.task_id,
                workflow_id=task.workflow_id,
                success=False,
                duration_seconds=time.perf_counter() - start,
                error="workflow definition not found",
            )

        node_results: Dict[str, Any] = {}
        success = True
        for node in definition.nodes:
            if not self._can_run(node, task.completed_nodes):
                continue
            task.current_node = node.node_id
            await self.repo.save_task(task)
            node_start = time.perf_counter()
            try:
                result = await self.retry_engine.execute(self._run_node, node, task.params)
                node_results[node.node_id] = result
                task.completed_nodes.append(node.node_id)
                machine.transition(WorkflowStatus.RUNNING, f"completed {node.node_id}")
            except Exception as exc:
                task.failed_nodes.append(node.node_id)
                node_results[node.node_id] = {"success": False, "error": str(exc)}
                success = False
                break
            finally:
                WORKFLOW_NODE_EXECUTION_DURATION.labels(node_id=node.node_id).observe(
                    time.perf_counter() - node_start
                )

        duration = time.perf_counter() - start
        WORKFLOW_EXECUTION_DURATION.labels(workflow_id=task.workflow_id).observe(duration)

        if success:
            machine.transition(WorkflowStatus.SUCCEEDED)
            task.status = WorkflowStatus.SUCCEEDED
        else:
            machine.transition(WorkflowStatus.FAILED)
            task.status = WorkflowStatus.FAILED
        task.result = node_results
        await self.repo.save_task(task)
        WORKFLOWS_COMPLETED.labels(status=task.status.value).inc()

        return WorkflowExecutionResult(
            task_id=task.task_id,
            workflow_id=task.workflow_id,
            success=success,
            duration_seconds=duration,
            node_results=node_results,
            error="" if success else "one or more nodes failed",
        )

    def _can_run(self, node: WorkflowNode, completed: List[str]) -> bool:
        return all(dep in completed for dep in node.dependencies)

    async def _run_node(self, node: WorkflowNode, params: Dict[str, Any]) -> Dict[str, Any]:
        await asyncio.sleep(0.001)
        rendered = node.command
        for key, value in params.items():
            rendered = rendered.replace(f"{{{{ {key} }}}}", str(value))
        if "fail" in rendered.lower():
            raise RuntimeError("Simulated node failure")
        return {"success": True, "output": rendered, "node_id": node.node_id}
