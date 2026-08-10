# -*- coding: utf-8 -*-
"""
L3 Processing Layer - Workflow Engine
Provides workflow orchestration and automation for incident response

Phase 4 集成: 完整的 DAG 工作流引擎、状态机、执行引擎、DSL 支持
"""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, cast  # noqa: F401

from loguru import logger


class FallbackWorkflowState(Enum):
    """Fallback workflow execution states"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# Phase 4 集成: 导入完整的工作流引擎组件
try:
    from core.workflow.engine import WorkflowExecutor
    from core.workflow.engine.state_machine import (
        WorkflowState,
        WorkflowStateMachine,
    )

    WORKFLOW_ENGINE_AVAILABLE = True
    logger.info("Phase 4 完整工作流引擎组件已导入")
except ImportError:
    WORKFLOW_ENGINE_AVAILABLE = False
    logger.warning("Phase 4 完整工作流引擎组件不可用，使用简化版本")

# Use the appropriate WorkflowState class based on availability
if WORKFLOW_ENGINE_AVAILABLE:
    WorkflowStateClass: Any = WorkflowState
else:
    WorkflowStateClass = FallbackWorkflowState


class WorkflowStep:
    """Single workflow step"""

    def __init__(
        self,
        name: str,
        handler: Callable,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 300,
    ):
        self.name = name
        self.handler = handler
        self.params = params or {}
        self.timeout = timeout
        self.state = WorkflowStateClass.PENDING  # type: ignore
        self.result = None
        self.error: Optional[str] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None


class Workflow:
    """Workflow definition"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[WorkflowStep] = []
        self.state = WorkflowStateClass.PENDING  # type: ignore
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.context: Dict[str, Any] = {}

    def add_step(self, step: WorkflowStep) -> "Workflow":
        """Add a step to the workflow"""
        self.steps.append(step)
        return self

    def get_step(self, name: str) -> Optional[WorkflowStep]:
        """Get a step by name"""
        for step in self.steps:
            if step.name == name:
                return step
        return None


class WorkflowEngine:
    """
    Workflow Engine for L3 Processing Layer

    Phase 4 集成: 完整的 DAG 工作流引擎支持

    This engine provides:
    - Workflow definition and execution
    - Step-by-step orchestration
    - Error handling and retry
    - Context management
    - DAG-based workflow execution (if available)
    - State machine management (if available)
    - DSL support (if available)
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        config = config or {}
        self.config = config
        self.workflows: Dict[str, Workflow] = {}
        self._is_initialized = True

        # Phase 4 集成: 初始化完整工作流引擎组件
        self._dag_executor: Optional[WorkflowExecutor] = None
        self._state_machine: Optional[WorkflowStateMachine] = None

        if WORKFLOW_ENGINE_AVAILABLE:
            try:
                self._dag_executor = WorkflowExecutor(
                    max_parallel_nodes=config.get("max_parallel_nodes", 5),
                    default_timeout=config.get("default_timeout", 300),
                    default_max_retries=config.get("default_max_retries", 3),
                )
                logger.info("Phase 4 DAG 执行器已初始化")
            except Exception as e:
                logger.warning(f"DAG 执行器初始化失败: {e}")

        logger.info("Workflow Engine initialized for L3 Layer")

    def register_workflow(self, workflow: Workflow) -> None:
        """Register a workflow"""
        self.workflows[workflow.name] = workflow
        logger.info(f"Registered workflow: {workflow.name}")

    def get_workflow(self, name: str) -> Optional[Workflow]:
        """Get a workflow by name"""
        return self.workflows.get(name)

    async def execute_workflow(
        self, workflow_name: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute a workflow

        Args:
            workflow_name: Name of the workflow to execute
            context: Initial context for the workflow

        Returns:
            Execution result
        """
        workflow = self.get_workflow(workflow_name)
        if not workflow:
            return {"error": f"Workflow {workflow_name} not found"}

        workflow.state = WorkflowStateClass.RUNNING
        workflow.started_at = datetime.now()
        workflow.context = context or {}

        logger.info(f"Executing workflow: {workflow_name}")

        try:
            for step in workflow.steps:
                await self._execute_step(step, workflow.context)

                if step.state == WorkflowStateClass.FAILED:
                    workflow.state = WorkflowStateClass.FAILED
                    logger.error(f"Workflow failed at step: {step.name}")
                    return {
                        "workflow": workflow_name,
                        "state": workflow.state.value,
                        "failed_step": step.name,
                        "error": step.error,
                    }

            workflow.state = WorkflowStateClass.COMPLETED
            workflow.completed_at = datetime.now()

            logger.info(f"Workflow completed: {workflow_name}")
            return {
                "workflow": workflow_name,
                "state": workflow.state.value,
                "context": workflow.context,
                "steps_executed": len(workflow.steps),
            }

        except Exception as e:
            workflow.state = WorkflowStateClass.FAILED
            logger.error(f"Workflow execution error: {e}")
            return {"workflow": workflow_name, "state": workflow.state.value, "error": str(e)}

    async def _execute_step(self, step: WorkflowStep, context: Dict[str, Any]) -> None:
        """Execute a single workflow step"""
        step.state = WorkflowStateClass.RUNNING
        step.started_at = datetime.now()

        logger.info(f"Executing step: {step.name}")

        try:
            # Execute the step handler
            result = await step.handler(context, step.params)
            step.result = result
            step.state = WorkflowStateClass.COMPLETED
            step.completed_at = datetime.now()

            # Update context with step result
            context[step.name] = result

            logger.info(f"Step completed: {step.name}")

        except Exception as e:
            step.state = WorkflowStateClass.FAILED
            step.error = str(e)
            step.completed_at = datetime.now()
            logger.error(f"Step failed: {step.name} - {e}")

    def create_incident_response_workflow(self) -> Workflow:
        """Create a standard incident response workflow"""
        workflow = Workflow("incident_response", "Standard incident response workflow")

        # Step 1: Analyze incident
        workflow.add_step(
            WorkflowStep("analyze_incident", self._analyze_incident_handler, {"use_rag": True})
        )

        # Step 2: Determine severity
        workflow.add_step(WorkflowStep("determine_severity", self._determine_severity_handler))

        # Step 3: Generate repair plan
        workflow.add_step(WorkflowStep("generate_repair_plan", self._generate_repair_plan_handler))

        # Step 4: Request approval (if needed)
        workflow.add_step(WorkflowStep("request_approval", self._request_approval_handler))

        # Step 5: Execute repair
        workflow.add_step(WorkflowStep("execute_repair", self._execute_repair_handler))

        # Step 6: Verify fix
        workflow.add_step(WorkflowStep("verify_fix", self._verify_fix_handler))

        self.register_workflow(workflow)
        return workflow

    async def _analyze_incident_handler(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handler for incident analysis step"""
        alert = str(context.get("alert", context.get("message", context.get("title", "")))).lower()
        if any(k in alert for k in ("cpu", "load", "throttle", "processor")):
            root_cause = "CPU resource exhaustion"
        elif any(k in alert for k in ("memory", "mem", "oom", "heap", "ram")):
            root_cause = "Memory exhaustion"
        elif any(k in alert for k in ("disk", "storage", "space", "volume")):
            root_cause = "Disk space issue"
        elif any(k in alert for k in ("network", "connection", "timeout", "latency", "dns")):
            root_cause = "Network connectivity issue"
        elif any(k in alert for k in ("service", "process", "daemon", "restart", "down")):
            root_cause = "Service failure"
        else:
            root_cause = "Unknown root cause"

        return {
            "analysis": "Incident analyzed from alert context",
            "root_cause": root_cause,
            "use_rag": params.get("use_rag", False),
        }

    async def _determine_severity_handler(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handler for severity determination step"""
        analysis = context.get("analyze_incident", {})
        root_cause = str(analysis.get("root_cause", "")).lower()
        if any(k in root_cause for k in ("cpu", "memory", "disk", "network", "service")):
            severity = "high"
            priority = 1
        elif any(k in root_cause for k in ("warning", "degraded")):
            severity = "medium"
            priority = 2
        else:
            severity = "low"
            priority = 3
        return {"severity": severity, "priority": priority}

    async def _generate_repair_plan_handler(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handler for repair plan generation step"""
        analysis = context.get("analyze_incident", {})
        root_cause = str(analysis.get("root_cause", "")).lower()
        severity = context.get("determine_severity", {}).get("severity", "low")
        if "cpu" in root_cause:
            plan = "Scale CPU or restart overloaded processes"
        elif "memory" in root_cause:
            plan = "Free memory or restart leaking service"
        elif "disk" in root_cause:
            plan = "Clean up disk space"
        elif "network" in root_cause:
            plan = "Check network connectivity and DNS"
        elif "service" in root_cause:
            plan = "Restart affected service"
        else:
            plan = "Investigate incident manually"
        estimated_time = "5min" if severity in ("high", "critical") else "15min"
        return {"plan": plan, "estimated_time": estimated_time}

    async def _request_approval_handler(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handler for approval request step"""
        severity = context.get("determine_severity", {}).get("severity", "low")
        auto_approved = severity not in ("critical", "high")
        return {
            "approved": auto_approved,
            "approver": "auto-approver" if auto_approved else "on-call",
            "severity": severity,
        }

    async def _execute_repair_handler(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handler for repair execution step"""
        plan = context.get("generate_repair_plan", {}).get("plan", "Investigate incident manually")
        severity = context.get("determine_severity", {}).get("severity", "low")
        if "restart" in plan.lower():
            action = "Restarted affected service"
        elif "scale" in plan.lower() or "cpu" in plan.lower():
            action = "Scaled CPU resources"
        elif "free" in plan.lower() or "memory" in plan.lower():
            action = "Freed memory and recycled service"
        elif "clean" in plan.lower() or "disk" in plan.lower():
            action = "Cleaned up disk space"
        else:
            action = "Executed remediation: " + plan
        return {"status": "success", "action": action, "severity": severity}

    async def _verify_fix_handler(
        self, context: Dict[str, Any], params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handler for fix verification step"""
        metrics = context.get("metrics", {})
        status = str(context.get("status", context.get("incident_status", ""))).lower()
        if isinstance(metrics, dict) and metrics:
            metrics_normal = all(
                not str(v).lower() in ("critical", "high", "firing", "error", "down")
                for v in metrics.values()
            )
        else:
            metrics_normal = status in ("resolved", "normal", "ok")
        verified = status in ("resolved", "normal", "ok") and metrics_normal
        return {"verified": verified, "metrics_normal": metrics_normal}

    def get_status(self) -> Dict[str, Any]:
        """Get engine status"""
        return {
            "initialized": self._is_initialized,
            "workflow_count": len(self.workflows),
            "workflows": list(self.workflows.keys()),
        }


# Global singleton instance
_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> Optional[WorkflowEngine]:
    """Get global workflow engine instance"""
    return _workflow_engine


def init_workflow_engine(config: Dict[str, Any]) -> WorkflowEngine:
    """Initialize global workflow engine"""
    global _workflow_engine
    _workflow_engine = WorkflowEngine(config)
    return _workflow_engine
