# -*- coding: utf-8 -*-
"""
L2-L3 Workflow Integration (Phase 2)
Integration between L2 Analysis Layer and L3 Processing Layer for automated workflow execution
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from loguru import logger

if TYPE_CHECKING:
    from core.analysis.l2.enhanced_causal_analyzer import EnhancedCausalAnalyzer
    from core.processing.l3.workflow_engine import WorkflowEngine


class WorkflowTriggerType(Enum):
    """Workflow trigger type"""

    CAUSAL_ANALYSIS = "causal_analysis"
    ANOMALY_DETECTION = "anomaly_detection"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    ALERT = "alert"


class WorkflowStatus(Enum):
    """Workflow execution status"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class WorkflowDefinition:
    """Workflow definition"""

    workflow_id: str
    name: str
    description: str
    trigger_type: WorkflowTriggerType
    trigger_config: Dict[str, Any] = field(default_factory=dict)
    steps: List[Dict[str, Any]] = field(default_factory=list)
    timeout: int = 3600
    retry_policy: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowExecution:
    """Workflow execution instance"""

    execution_id: str
    workflow_id: str
    status: WorkflowStatus = WorkflowStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[Exception] = None
    results: Dict[str, Any] = field(default_factory=dict)
    current_step: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class L2L3WorkflowIntegrator:
    """Integration between L2 Analysis and L3 Processing layers"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize L2-L3 workflow integrator

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Workflow definitions
        self.workflows: Dict[str, WorkflowDefinition] = {}

        # Active executions
        self.active_executions: Dict[str, WorkflowExecution] = {}
        self.execution_history: List[WorkflowExecution] = []

        # L2 Analysis integration
        self.causal_analyzer: Optional["EnhancedCausalAnalyzer"] = None
        self._initialize_causal_analyzer()

        # L3 Processing integration
        self.workflow_engine: Optional["WorkflowEngine"] = None
        self._initialize_workflow_engine()

        # Event handlers
        self.trigger_handlers: Dict[WorkflowTriggerType, List[Callable]] = {}

        # Statistics
        self.total_executions = 0
        self.successful_executions = 0
        self.failed_executions = 0

        logger.info("L2-L3 workflow integrator initialized")

    def _initialize_causal_analyzer(self):
        """Initialize L2 causal analyzer"""
        try:
            from core.analysis.l2.enhanced_causal_analyzer import get_enhanced_causal_analyzer

            self.causal_analyzer = get_enhanced_causal_analyzer(self.config.get("causal_config"))
            logger.info("L2 causal analyzer initialized for workflow integration")
        except ImportError:
            logger.warning(
                "L2 causal analyzer not available, workflows will use simplified analysis"
            )

    def _initialize_workflow_engine(self):
        """Initialize L3 workflow engine"""
        try:
            from core.processing.l3.workflow_engine import get_workflow_engine

            self.workflow_engine = get_workflow_engine()
            logger.info("L3 workflow engine initialized for workflow integration")
        except ImportError:
            logger.warning(
                "L3 workflow engine not available, workflows will use simplified execution"
            )

    def register_workflow(self, workflow: WorkflowDefinition) -> None:
        """
        Register workflow definition

        Args:
            workflow: Workflow definition
        """
        self.workflows[workflow.workflow_id] = workflow
        logger.info(f"Registered workflow: {workflow.workflow_id} - {workflow.name}")

    def register_trigger_handler(
        self, trigger_type: WorkflowTriggerType, handler: Callable
    ) -> None:
        """
        Register trigger handler

        Args:
            trigger_type: Trigger type
            handler: Handler function
        """
        if trigger_type not in self.trigger_handlers:
            self.trigger_handlers[trigger_type] = []
        self.trigger_handlers[trigger_type].append(handler)
        logger.info(f"Registered trigger handler for: {trigger_type.value}")

    async def trigger_workflow(
        self, workflow_id: str, trigger_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Trigger workflow execution

        Args:
            workflow_id: Workflow ID
            trigger_data: Optional trigger data

        Returns:
            Execution ID
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")

        self.workflows[workflow_id]

        # Create execution instance
        execution_id = str(uuid.uuid4())
        execution = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=workflow_id,
            status=WorkflowStatus.PENDING,
            metadata={"trigger_data": trigger_data or {}},
        )

        self.active_executions[execution_id] = execution
        self.total_executions += 1

        logger.info(f"Triggered workflow: {workflow_id}, execution: {execution_id}")

        # Start execution asynchronously
        asyncio.create_task(self._execute_workflow(execution_id))

        return execution_id

    async def _execute_workflow(self, execution_id: str) -> None:
        """
        Execute workflow

        Args:
            execution_id: Execution ID
        """
        if execution_id not in self.active_executions:
            return

        execution = self.active_executions[execution_id]
        workflow = self.workflows[execution.workflow_id]

        try:
            # Update status to running
            execution.status = WorkflowStatus.RUNNING
            execution.started_at = datetime.now(timezone.utc)

            # Execute workflow steps
            for i, step in enumerate(workflow.steps):
                execution.current_step = i

                # Execute step
                result = await self._execute_step(step, execution)
                execution.results[f"step_{i}"] = result

                # Check for cancellation
                if execution.status == WorkflowStatus.CANCELLED:
                    break

            # Update status to completed
            execution.status = WorkflowStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            self.successful_executions += 1

            logger.info(f"Workflow execution completed: {execution_id}")

        except Exception as e:
            # Update status to failed
            execution.status = WorkflowStatus.FAILED
            execution.error = e
            execution.completed_at = datetime.now(timezone.utc)
            self.failed_executions += 1

            logger.error(f"Workflow execution failed: {execution_id}, error: {e}")

        finally:
            # Move to history
            self.execution_history.append(execution)
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]

    async def _execute_step(self, step: Dict[str, Any], execution: WorkflowExecution) -> Any:
        """
        Execute workflow step

        Args:
            step: Step configuration
            execution: Execution instance

        Returns:
            Step result
        """
        step_type = step.get("type", "unknown")
        step_config = step.get("config", {})

        logger.info(f"Executing step: {step_type}")

        if step_type == "causal_analysis":
            return await self._execute_causal_analysis_step(step_config, execution)
        elif step_type == "workflow_execution":
            return await self._execute_workflow_step(step_config, execution)
        elif step_type == "data_processing":
            return await self._execute_data_processing_step(step_config, execution)
        elif step_type == "notification":
            return await self._execute_notification_step(step_config, execution)
        else:
            logger.warning(f"Unknown step type: {step_type}")
            return {"status": "skipped", "reason": "unknown_step_type"}

    async def _execute_causal_analysis_step(
        self, config: Dict[str, Any], execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Execute causal analysis step"""
        if not self.causal_analyzer:
            return {"status": "skipped", "reason": "causal_analyzer_not_available"}

        try:
            # Get trigger data
            trigger_data = execution.metadata.get("trigger_data", {})
            metrics_data = trigger_data.get("metrics_data", {})
            target_variable = trigger_data.get("target_variable", "")

            if not metrics_data or not target_variable:
                return {"status": "skipped", "reason": "missing_required_data"}

            # Perform causal analysis
            analysis_result = await self.causal_analyzer.analyze_causal_relationships(
                metrics_data=metrics_data,
                timestamps=trigger_data.get("timestamps", []),
                target_variable=target_variable,
            )

            return {
                "status": "completed",
                "root_causes": analysis_result.root_causes,
                "confidence": analysis_result.confidence,
                "impact_scores": analysis_result.impact_scores,
            }

        except Exception as e:
            logger.error(f"Causal analysis step failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _execute_workflow_step(
        self, config: Dict[str, Any], execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Execute workflow step"""
        if not self.workflow_engine:
            return {"status": "skipped", "reason": "workflow_engine_not_available"}

        try:
            workflow_name = config.get("workflow_name")
            workflow_params = config.get("params", {})

            # Execute workflow through L3 engine
            # This would integrate with the actual workflow engine
            return {
                "status": "completed",
                "workflow_name": workflow_name,
                "params": workflow_params,
            }

        except Exception as e:
            logger.error(f"Workflow step failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _execute_data_processing_step(
        self, config: Dict[str, Any], execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Execute data processing step"""
        try:
            processing_type = config.get("processing_type")
            data = config.get("data", {})

            # Perform data processing
            # This would integrate with L4 storage layer
            return {
                "status": "completed",
                "processing_type": processing_type,
                "processed_count": len(data) if isinstance(data, (list, dict)) else 0,
            }

        except Exception as e:
            logger.error(f"Data processing step failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def _execute_notification_step(
        self, config: Dict[str, Any], execution: WorkflowExecution
    ) -> Dict[str, Any]:
        """Execute notification step"""
        try:
            notification_type = config.get("notification_type")
            recipients = config.get("recipients", [])
            config.get("message", {})

            # Send notification
            # This would integrate with L7 integration layer
            return {
                "status": "completed",
                "notification_type": notification_type,
                "recipients_count": len(recipients),
            }

        except Exception as e:
            logger.error(f"Notification step failed: {e}")
            return {"status": "failed", "error": str(e)}

    async def handle_causal_analysis_trigger(self, analysis_result: Dict[str, Any]) -> List[str]:
        """
        Handle causal analysis trigger

        Args:
            analysis_result: Causal analysis result

        Returns:
            List of triggered execution IDs
        """
        triggered_executions = []

        # Find workflows triggered by causal analysis
        for workflow_id, workflow in self.workflows.items():
            if workflow.trigger_type == WorkflowTriggerType.CAUSAL_ANALYSIS:
                # Check if trigger conditions are met
                if self._check_trigger_conditions(workflow.trigger_config, analysis_result):
                    execution_id = await self.trigger_workflow(
                        workflow_id, trigger_data={"analysis_result": analysis_result}
                    )
                    triggered_executions.append(execution_id)

        return triggered_executions

    def _check_trigger_conditions(
        self, trigger_config: Dict[str, Any], analysis_result: Dict[str, Any]
    ) -> bool:
        """Check if trigger conditions are met"""
        # Implement trigger condition checking logic
        confidence_threshold = trigger_config.get("confidence_threshold", 0.8)
        min_root_causes = trigger_config.get("min_root_causes", 1)

        if analysis_result.get("confidence", 0) < confidence_threshold:
            return False

        if len(analysis_result.get("root_causes", [])) < min_root_causes:
            return False

        return True

    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """
        Get execution status

        Args:
            execution_id: Execution ID

        Returns:
            Execution status dictionary
        """
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
        else:
            # Check in history
            hist_execution = next(
                (e for e in self.execution_history if e.execution_id == execution_id), None
            )
            if hist_execution is None:
                return {"error": "Execution not found", "execution_id": execution_id}
            execution = hist_execution

        if execution:
            return {
                "execution_id": execution.execution_id,
                "workflow_id": execution.workflow_id,
                "status": execution.status.value,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": (
                    execution.completed_at.isoformat() if execution.completed_at else None
                ),
                "current_step": execution.current_step,
                "results": execution.results,
                "error": str(execution.error) if execution.error else None,
            }

        return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get workflow statistics"""
        return {
            "total_executions": self.total_executions,
            "successful_executions": self.successful_executions,
            "failed_executions": self.failed_executions,
            "active_executions": len(self.active_executions),
            "registered_workflows": len(self.workflows),
            "success_rate": (
                self.successful_executions / self.total_executions
                if self.total_executions > 0
                else 0.0
            ),
        }

    async def cancel_execution(self, execution_id: str) -> bool:
        """
        Cancel workflow execution

        Args:
            execution_id: Execution ID

        Returns:
            Success status
        """
        if execution_id in self.active_executions:
            execution = self.active_executions[execution_id]
            execution.status = WorkflowStatus.CANCELLED
            logger.info(f"Cancelled execution: {execution_id}")
            return True

        return False


def get_l2l3_workflow_integrator(config: Optional[Dict[str, Any]] = None) -> L2L3WorkflowIntegrator:
    """
    Factory function to get L2-L3 workflow integrator instance

    Args:
        config: Optional configuration dictionary

    Returns:
        L2L3WorkflowIntegrator: Integrator instance
    """
    return L2L3WorkflowIntegrator(config)
