# -*- coding: utf-8 -*-
"""
Workflow Executor
Executes DAG-based workflows with parallel execution, retry, and timeout handling
"""

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from loguru import logger

from .dag import DAG, DAGNode, NodeStatus
from .state_machine import WorkflowEvent, WorkflowState, WorkflowStateMachine


@dataclass
class ExecutionContext:
    """
    Execution context for workflow runs

    Attributes:
        workflow_id: Workflow identifier
        run_id: Execution run identifier
        start_time: Execution start time
        end_time: Execution end time
        status: Current status
        results: Node execution results
        errors: Node execution errors
        metadata: Additional metadata
    """

    workflow_id: str
    run_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    status: WorkflowState = WorkflowState.IDLE
    results: Dict[str, Any] = field(default_factory=dict)
    errors: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary"""
        return {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "status": self.status.value,
            "results": self.results,
            "errors": self.errors,
            "metadata": self.metadata,
        }


class WorkflowExecutor:
    """
    Workflow executor with parallel execution, retry, and timeout support

    Features:
    - Parallel node execution
    - Automatic retry with exponential backoff
    - Timeout handling
    - State machine integration
    - Progress tracking
    """

    def __init__(
        self,
        max_parallel_nodes: int = 5,
        default_timeout: int = 300,
        default_max_retries: int = 3,
        retry_backoff_base: float = 2.0,
    ):
        """
        Initialize executor

        Args:
            max_parallel_nodes: Maximum parallel node executions
            default_timeout: Default timeout in seconds
            default_max_retries: Default maximum retry attempts
            retry_backoff_base: Exponential backoff base
        """
        self.max_parallel_nodes = max_parallel_nodes
        self.default_timeout = default_timeout
        self.default_max_retries = default_max_retries
        self.retry_backoff_base = retry_backoff_base

        # Node execution handlers
        self._handlers: Dict[str, Callable] = {}

        # Running executions
        self._active_executions: Dict[str, ExecutionContext] = {}

    def register_handler(self, node_type: str, handler: Callable) -> None:
        """
        Register execution handler for node type

        Args:
            node_type: Node type identifier
            handler: Handler function (async)
        """
        self._handlers[node_type] = handler
        logger.info(f"Registered handler for node type: {node_type}")

    async def execute(
        self, dag: DAG, context: Optional[ExecutionContext] = None
    ) -> ExecutionContext:
        """
        Execute workflow DAG

        Args:
            dag: DAG to execute
            context: Optional execution context

        Returns:
            Execution context with results
        """
        # Create context if not provided
        if context is None:
            context = ExecutionContext(
                workflow_id=dag.name, run_id=f"{dag.name}-{int(time.time())}"
            )

        # Initialize state machine
        state_machine = WorkflowStateMachine(context.workflow_id)
        self._active_executions[context.run_id] = context

        # Start workflow
        state_machine.transition(WorkflowEvent.START)
        context.status = state_machine.current_state

        try:
            # Execute nodes
            await self._execute_dag(dag, context, state_machine)

            # Complete workflow
            state_machine.transition(WorkflowEvent.COMPLETE)
            context.status = state_machine.current_state

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            state_machine.transition(WorkflowEvent.FAIL)
            context.status = state_machine.current_state
            context.errors["workflow"] = str(e)

        finally:
            context.end_time = datetime.now()
            del self._active_executions[context.run_id]

        return context

    async def _execute_dag(
        self, dag: DAG, context: ExecutionContext, state_machine: WorkflowStateMachine
    ) -> None:
        """
        Execute DAG with parallel execution

        Args:
            dag: DAG to execute
            context: Execution context
            state_machine: State machine for state management
        """
        while True:
            # Check if workflow should stop
            if state_machine.is_terminal():
                break

            # Get ready nodes
            ready_nodes = dag.get_ready_nodes()

            if not ready_nodes:
                # Check if all nodes completed
                all_completed = all(
                    node.status in [NodeStatus.SUCCESS, NodeStatus.FAILED, NodeStatus.SKIPPED]
                    for node in dag.nodes.values()
                )
                if all_completed:
                    break
                # Wait for nodes to complete
                await asyncio.sleep(0.1)
                continue

            # Execute ready nodes in parallel (respecting max_parallel_nodes)
            semaphore = asyncio.Semaphore(self.max_parallel_nodes)
            tasks = [
                self._execute_node(dag.nodes[node_id], dag, context, semaphore)
                for node_id in ready_nodes
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute_node(
        self, node: DAGNode, dag: DAG, context: ExecutionContext, semaphore: asyncio.Semaphore
    ) -> None:
        """
        Execute single node with retry and timeout

        Args:
            node: Node to execute
            dag: DAG
            context: Execution context
            semaphore: Semaphore for parallel execution control
        """
        async with semaphore:
            node.status = NodeStatus.RUNNING

            # Get node configuration
            timeout = node.config.get("timeout", self.default_timeout)
            max_retries = node.config.get("max_retries", self.default_max_retries)

            # Execute with retry
            for attempt in range(max_retries + 1):
                try:
                    # Execute with timeout
                    result = await asyncio.wait_for(
                        self._call_handler(node, context), timeout=timeout
                    )

                    node.status = NodeStatus.SUCCESS
                    node.result = result
                    context.results[node.id] = result

                    logger.info(f"Node {node.id} completed successfully")
                    break

                except asyncio.TimeoutError:
                    error_msg = f"Node {node.id} timed out after {timeout}s"
                    node.error = error_msg
                    logger.warning(error_msg)

                    if attempt < max_retries:
                        await asyncio.sleep(self.retry_backoff_base**attempt)
                    else:
                        node.status = NodeStatus.FAILED
                        context.errors[node.id] = error_msg

                except Exception as e:
                    error_msg = f"Node {node.id} failed: {str(e)}"
                    node.error = error_msg
                    logger.error(error_msg)

                    if attempt < max_retries:
                        await asyncio.sleep(self.retry_backoff_base**attempt)
                    else:
                        node.status = NodeStatus.FAILED
                        context.errors[node.id] = error_msg

    async def _call_handler(self, node: DAGNode, context: ExecutionContext) -> Any:
        """
        Call appropriate handler for node

        Args:
            node: Node to execute
            context: Execution context

        Returns:
            Handler result

        Raises:
            ValueError: If no handler registered for node type
        """
        handler = self._handlers.get(node.type)

        if handler is None:
            raise ValueError(f"No handler registered for node type: {node.type}")

        return await handler(node, context)

    def pause_workflow(self, run_id: str) -> bool:
        """
        Pause running workflow

        Args:
            run_id: Run identifier

        Returns:
            True if paused successfully
        """
        context = self._active_executions.get(run_id)
        if context and context.status == WorkflowState.RUNNING:
            context.status = WorkflowState.PAUSED
            return True
        return False

    def resume_workflow(self, run_id: str) -> bool:
        """
        Resume paused workflow

        Args:
            run_id: Run identifier

        Returns:
            True if resumed successfully
        """
        context = self._active_executions.get(run_id)
        if context and context.status == WorkflowState.PAUSED:
            context.status = WorkflowState.RUNNING
            return True
        return False

    def cancel_workflow(self, run_id: str) -> bool:
        """
        Cancel running workflow

        Args:
            run_id: Run identifier

        Returns:
            True if cancelled successfully
        """
        context = self._active_executions.get(run_id)
        if (
            context
            and context.status != WorkflowState.COMPLETED
            and context.status != WorkflowState.FAILED
            and context.status != WorkflowState.CANCELLED
        ):
            context.status = WorkflowState.CANCELLED
            return True
        return False

    def get_execution_status(self, run_id: str) -> Optional[Dict]:
        """
        Get execution status

        Args:
            run_id: Run identifier

        Returns:
            Execution status dict or None
        """
        context = self._active_executions.get(run_id)
        if context:
            return context.to_dict()
        return None
