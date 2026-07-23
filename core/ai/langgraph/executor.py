# -*- coding: utf-8 -*-
"""
LangGraph Workflow Execution Engine
Manages workflow execution with error recovery and retry
"""

import asyncio
from typing import Any, Dict, Optional

from loguru import logger

from .workflow import Workflow


class WorkflowExecutor:
    """
    Workflow execution engine with error handling and retry
    """

    def __init__(
        self, max_retries: int = 3, retry_delay: float = 1.0, timeout: Optional[float] = None
    ):
        """
        Initialize executor

        Args:
            max_retries: Maximum retry attempts
            retry_delay: Delay between retries (seconds)
            timeout: Execution timeout (seconds)
        """
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    async def execute(
        self, workflow: Workflow, input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute workflow with retry logic

        Args:
            workflow: Workflow to execute
            input_data: Initial input data

        Returns:
            Execution result
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if self.timeout:
                    result = await asyncio.wait_for(
                        workflow.execute(input_data), timeout=self.timeout
                    )
                else:
                    result = await workflow.execute(input_data)

                return result

            except asyncio.TimeoutError:
                last_error = "Workflow execution timeout"
                logger.error(f"Workflow {workflow.name} timed out (attempt {attempt + 1})")

            except Exception as e:
                last_error = str(e)
                logger.error(f"Workflow {workflow.name} failed (attempt {attempt + 1}): {e}")

            # Retry logic
            if attempt < self.max_retries:
                logger.info(f"Retrying workflow {workflow.name} in {self.retry_delay}s")
                await asyncio.sleep(self.retry_delay)

        # All retries failed
        return {
            "status": "failed",
            "error": f"Failed after {self.max_retries} retries",
            "last_error": last_error,
        }


class WorkflowOrchestrator:
    """
    Orchestrates multiple workflows
    """

    def __init__(self):
        """Initialize orchestrator"""
        self.workflows: Dict[str, Workflow] = {}
        self.executor = WorkflowExecutor()

    def register_workflow(self, workflow: Workflow) -> None:
        """
        Register workflow with orchestrator

        Args:
            workflow: Workflow to register
        """
        self.workflows[workflow.name] = workflow
        logger.info(f"Registered workflow: {workflow.name}")

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """
        Get registered workflow

        Args:
            name: Workflow name

        Returns:
            Workflow or None
        """
        return self.workflows.get(name)

    async def execute_workflow(
        self, name: str, input_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute registered workflow

        Args:
            name: Workflow name
            input_data: Input data

        Returns:
            Execution result
        """
        workflow = self.get_workflow(name)
        if not workflow:
            raise ValueError(f"Workflow {name} not found")

        return await self.executor.execute(workflow, input_data)

    def list_workflows(self) -> list[str]:
        """
        List all registered workflows

        Returns:
            List of workflow names
        """
        return list(self.workflows.keys())


__all__ = ["WorkflowExecutor", "WorkflowOrchestrator"]
