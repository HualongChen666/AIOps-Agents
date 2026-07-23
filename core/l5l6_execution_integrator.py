# -*- coding: utf-8 -*-
"""
L5-L6 Execution Integration (Phase 3)
Integration between L5 Knowledge Layer and L6 Execution Layer for intelligent execution
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class ExecutionTrigger(Enum):
    """Execution trigger types"""

    KNOWLEDGE_UPDATE = "knowledge_update"
    ANOMALY_DETECTED = "anomaly_detected"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    EVENT_DRIVEN = "event_driven"


class ExecutionPriority(Enum):
    """Execution priority"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExecutionMode(Enum):
    """Execution mode"""

    SYNCHRONOUS = "synchronous"
    ASYNCHRONOUS = "asynchronous"
    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


@dataclass
class KnowledgeBasedAction:
    """Knowledge-based action configuration"""

    action_id: str
    action_name: str
    knowledge_type: str
    execution_trigger: ExecutionTrigger
    execution_priority: ExecutionPriority = ExecutionPriority.MEDIUM
    execution_mode: ExecutionMode = ExecutionMode.ASYNCHRONOUS
    timeout: int = 300
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionRequest:
    """Execution request"""

    request_id: str
    action_id: str
    knowledge_data: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict)
    priority: ExecutionPriority = ExecutionPriority.MEDIUM
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    """Execution result"""

    request_id: str
    action_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class L5L6ExecutionIntegrator:
    """Integration between L5 Knowledge Layer and L6 Execution Layer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize L5-L6 execution integrator

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Knowledge-based actions
        self.actions: Dict[str, KnowledgeBasedAction] = {}

        # Execution queue
        self.execution_queue: Dict[ExecutionPriority, asyncio.Queue] = {
            ExecutionPriority.CRITICAL: asyncio.Queue(maxsize=100),
            ExecutionPriority.HIGH: asyncio.Queue(maxsize=200),
            ExecutionPriority.MEDIUM: asyncio.Queue(maxsize=500),
            ExecutionPriority.LOW: asyncio.Queue(maxsize=1000),
        }

        # Execution history
        self.execution_history: List[ExecutionResult] = []

        # Active executions
        self.active_executions: Dict[str, ExecutionResult] = {}

        # Configuration
        self.max_concurrent_executions = self.config.get("max_concurrent_executions", 10)
        self.default_timeout = self.config.get("default_timeout", 300)

        # Statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0

        logger.info("L5-L6 execution integrator initialized")

    def register_action(self, action: KnowledgeBasedAction) -> None:
        """
        Register knowledge-based action

        Args:
            action: Action configuration
        """
        self.actions[action.action_id] = action
        logger.info(f"Registered action: {action.action_id}")

    async def trigger_execution(self, request: ExecutionRequest) -> str:
        """
        Trigger execution based on knowledge

        Args:
            request: Execution request

        Returns:
            Request ID
        """
        if request.action_id not in self.actions:
            raise ValueError(f"Action not found: {request.action_id}")

        action = self.actions[request.action_id]

        # Add to execution queue
        self.execution_queue[request.priority].put_nowait(request)

        self.total_executions += 1

        logger.info(f"Triggered execution: {request.request_id}, action: {action.action_name}")

        return request.request_id

    async def start_execution_processor(self) -> None:
        """Start execution processor"""

        async def process_queue():
            while True:
                try:
                    # Process queues by priority
                    for priority in [
                        ExecutionPriority.CRITICAL,
                        ExecutionPriority.HIGH,
                        ExecutionPriority.MEDIUM,
                        ExecutionPriority.LOW,
                    ]:
                        queue = self.execution_queue[priority]

                        if not queue.empty():
                            request = await queue.get()
                            await self._execute_request(request)

                    await asyncio.sleep(0.1)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Execution processor error: {e}")
                    await asyncio.sleep(1)

        asyncio.create_task(process_queue())
        logger.info("Execution processor started")

    async def _execute_request(self, request: ExecutionRequest) -> None:
        """
        Execute execution request

        Args:
            request: Execution request
        """
        action = self.actions[request.action_id]

        # Create execution result
        result = ExecutionResult(
            request_id=request.request_id,
            action_id=request.action_id,
            status="pending",
            started_at=datetime.now(timezone.utc),
        )

        self.active_executions[request.request_id] = result

        try:
            # Check conditions
            if not self._check_conditions(action, request.knowledge_data):
                result.status = "skipped"
                result.completed_at = datetime.now(timezone.utc)
                logger.info(f"Execution skipped (conditions not met): {request.request_id}")
                return

            # Execute action
            execution_result = await self._execute_action(action, request)

            # Update result
            result.status = "completed"
            result.result = execution_result
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at is not None:
                result.execution_time = (result.completed_at - result.started_at).total_seconds()

            self.successful_executions += 1

            logger.info(f"Execution completed: {request.request_id}")

        except Exception as e:
            result.status = "failed"
            result.error = str(e)
            result.completed_at = datetime.now(timezone.utc)
            if result.started_at is not None:
                result.execution_time = (result.completed_at - result.started_at).total_seconds()

            self.failed_executions += 1

            logger.error(f"Execution failed: {request.request_id}, error: {e}")

        finally:
            # Move to history
            self.execution_history.append(result)
            if request.request_id in self.active_executions:
                del self.active_executions[request.request_id]

    def _check_conditions(
        self, action: KnowledgeBasedAction, knowledge_data: Dict[str, Any]
    ) -> bool:
        """
        Check if execution conditions are met

        Args:
            action: Action configuration
            knowledge_data: Knowledge data

        Returns:
            True if conditions are met
        """
        # In real implementation, would check actual conditions
        return True

    async def _execute_action(self, action: KnowledgeBasedAction, request: ExecutionRequest) -> Any:
        """
        Execute action

        Args:
            action: Action configuration
            request: Execution request

        Returns:
            Execution result
        """
        # In real implementation, would execute actual action using L6 Execution Layer
        await asyncio.sleep(1)  # Simulate execution

        return {
            "action_id": action.action_id,
            "knowledge_data": request.knowledge_data,
            "status": "success",
        }

    async def get_execution_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution status

        Args:
            request_id: Request ID

        Returns:
            Execution status dictionary
        """
        # Check active executions
        if request_id in self.active_executions:
            result = self.active_executions[request_id]
            return self._result_to_dict(result)

        # Check execution history
        for result in reversed(self.execution_history):
            if result.request_id == request_id:
                return self._result_to_dict(result)

        return None

    def _result_to_dict(self, result: ExecutionResult) -> Dict[str, Any]:
        """Convert execution result to dictionary"""
        return {
            "request_id": result.request_id,
            "action_id": result.action_id,
            "status": result.status,
            "result": result.result,
            "error": result.error,
            "execution_time": result.execution_time,
            "started_at": result.started_at.isoformat() if result.started_at else None,
            "completed_at": result.completed_at.isoformat() if result.completed_at else None,
        }

    async def cancel_execution(self, request_id: str) -> bool:
        """
        Cancel execution

        Args:
            request_id: Request ID

        Returns:
            Success status
        """
        if request_id in self.active_executions:
            result = self.active_executions[request_id]
            result.status = "cancelled"
            result.completed_at = datetime.now(timezone.utc)

            # Move to history
            self.execution_history.append(result)
            del self.active_executions[request_id]

            logger.info(f"Cancelled execution: {request_id}")
            return True

        return False

    def get_action_config(self, action_id: str) -> Optional[Dict[str, Any]]:
        """
        Get action configuration

        Args:
            action_id: Action ID

        Returns:
            Action configuration dictionary
        """
        if action_id not in self.actions:
            return None

        action = self.actions[action_id]

        return {
            "action_id": action.action_id,
            "action_name": action.action_name,
            "knowledge_type": action.knowledge_type,
            "execution_trigger": action.execution_trigger.value,
            "execution_priority": action.execution_priority.value,
            "execution_mode": action.execution_mode.value,
            "timeout": action.timeout,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics"""
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "active_executions": len(self.active_executions),
            "registered_actions": len(self.actions),
            "success_rate": (
                self.successful_executions / self.total_executions
                if self.total_executions > 0
                else 0.0
            ),
        }


def get_l5l6_execution_integrator(
    config: Optional[Dict[str, Any]] = None,
) -> L5L6ExecutionIntegrator:
    """
    Factory function to get L5-L6 execution integrator instance

    Args:
        config: Optional configuration dictionary

    Returns:
        L5L6ExecutionIntegrator: Integrator instance
    """
    return L5L6ExecutionIntegrator(config)
