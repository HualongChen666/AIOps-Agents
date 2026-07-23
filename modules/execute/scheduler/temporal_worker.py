# -*- coding: utf-8 -*-
"""
Temporal Workflow Engine Integration for AIOps Platform
Provides reliable task scheduling and workflow orchestration using Temporal
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional  # noqa: F401

try:
    from temporalio import activity, worker, workflow
    from temporalio.client import Client
    from temporalio.common import RetryPolicy

    TEMPORAL_AVAILABLE = True
except ImportError:
    TEMPORAL_AVAILABLE = False
    workflow = None
    activity = None
    worker = None
    Client = None
    RetryPolicy = None

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Represents a task execution result"""

    task_id: str
    status: str
    result: Optional[Any] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


# Temporal Activities
@activity.defn
async def detect_anomaly_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity for anomaly detection

    Args:
        input_data: Input data for anomaly detection

    Returns:
        Detection result
    """
    try:
        # Import here to avoid circular dependencies
        from core.anomaly_detection import AnomalyDetector

        detector = AnomalyDetector()
        result = await detector.detect(input_data)

        return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Anomaly detection activity failed: {e}")
        raise


@activity.defn
async def root_cause_analysis_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity for root cause analysis

    Args:
        input_data: Input data for RCA

    Returns:
        RCA result
    """
    try:
        from modules.analyze.root_cause.inference import RootCauseInference

        rca = RootCauseInference()
        result = await rca.analyze(input_data)  # type: ignore[attr-defined]

        return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Root cause analysis activity failed: {e}")
        raise


@activity.defn
async def auto_heal_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity for auto-healing

    Args:
        input_data: Input data for auto-heal

    Returns:
        Heal result
    """
    try:
        from core.auto_heal import AutoHealEngine  # type: ignore[attr-defined]

        healer = AutoHealEngine()
        result = await healer.heal(input_data)

        return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Auto-heal activity failed: {e}")
        raise


@activity.defn
async def runbook_generation_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity for runbook generation

    Args:
        input_data: Input data for runbook generation

    Returns:
        Generated runbook
    """
    try:
        from core.runbook_generator import RunbookGenerator  # type: ignore[attr-defined]

        generator = RunbookGenerator()
        result = await generator.generate(input_data)

        return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Runbook generation activity failed: {e}")
        raise


@activity.defn
async def notify_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Activity for sending notifications

    Args:
        input_data: Notification data

    Returns:
        Notification result
    """
    try:
        from core.notify_engine import NotificationEngine  # type: ignore[attr-defined]

        notifier = NotificationEngine()
        result = await notifier.send(input_data)

        return {"status": "success", "result": result, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Notification activity failed: {e}")
        raise


# Temporal Workflows
@workflow.defn
class AnomalyDetectionWorkflow:
    """
    Workflow for anomaly detection and response
    """

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute anomaly detection workflow

        Args:
            input_data: Workflow input data

        Returns:
            Workflow result
        """
        # Step 1: Detect anomaly
        detection_result = await workflow.execute_activity(
            detect_anomaly_activity,
            input_data,
            start_to_close_timeout=timedelta(seconds=30),
            retry_policy=RetryPolicy(
                maximum_attempts=3, initial_interval=timedelta(seconds=1), backoff_coefficient=2.0
            ),
        )

        if detection_result["status"] != "success":
            return {
                "status": "failed",
                "error": "Anomaly detection failed",
                "detection_result": detection_result,
            }

        # Step 2: If anomaly detected, perform root cause analysis
        if detection_result["result"].get("anomaly_detected", False):
            rca_result = await workflow.execute_activity(
                root_cause_analysis_activity,
                {"anomaly": detection_result["result"], "context": input_data.get("context", {})},
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=2, initial_interval=timedelta(seconds=2)),
            )

            # Step 3: Generate runbook
            runbook_result = await workflow.execute_activity(
                runbook_generation_activity,
                {
                    "anomaly": detection_result["result"],
                    "root_cause": rca_result["result"],
                    "context": input_data.get("context", {}),
                },
                start_to_close_timeout=timedelta(seconds=45),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            # Step 4: Attempt auto-heal if configured
            if input_data.get("auto_heal_enabled", False):
                heal_result = await workflow.execute_activity(
                    auto_heal_activity,
                    {
                        "anomaly": detection_result["result"],
                        "root_cause": rca_result["result"],
                        "runbook": runbook_result["result"],
                    },
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )

                # Step 5: Send notification
                await workflow.execute_activity(
                    notify_activity,
                    {
                        "type": (
                            "anomaly_resolved"
                            if heal_result["result"].get("success")
                            else "anomaly_detected"
                        ),
                        "data": {
                            "anomaly": detection_result["result"],
                            "root_cause": rca_result["result"],
                            "heal_result": heal_result["result"],
                        },
                    },
                    start_to_close_timeout=timedelta(seconds=10),
                )

                return {
                    "status": "completed",
                    "detection": detection_result,
                    "rca": rca_result,
                    "runbook": runbook_result,
                    "heal": heal_result,
                }

            # Send notification without auto-heal
            await workflow.execute_activity(
                notify_activity,
                {
                    "type": "anomaly_detected",
                    "data": {
                        "anomaly": detection_result["result"],
                        "root_cause": rca_result["result"],
                        "runbook": runbook_result["result"],
                    },
                },
                start_to_close_timeout=timedelta(seconds=10),
            )

            return {
                "status": "completed",
                "detection": detection_result,
                "rca": rca_result,
                "runbook": runbook_result,
            }

        return {"status": "no_anomaly", "detection": detection_result}


@workflow.defn
class AutoScalingWorkflow:
    """
    Workflow for auto-scaling operations
    """

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute auto-scaling workflow

        Args:
            input_data: Workflow input data

        Returns:
            Workflow result
        """
        # Auto-scaling logic would be implemented here
        # This is a placeholder for the actual implementation

        return {
            "status": "completed",
            "message": "Auto-scaling workflow executed",
            "timestamp": datetime.utcnow().isoformat(),
        }


@workflow.defn
class BackupWorkflow:
    """
    Workflow for backup operations
    """

    @workflow.run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute backup workflow

        Args:
            input_data: Workflow input data

        Returns:
            Workflow result
        """
        # Backup logic would be implemented here
        # This is a placeholder for the actual implementation

        return {
            "status": "completed",
            "message": "Backup workflow executed",
            "timestamp": datetime.utcnow().isoformat(),
        }


class TemporalWorkflowManager:
    """
    Manager for Temporal workflows
    Handles workflow execution and worker lifecycle
    """

    def __init__(self, temporal_host: str = "localhost:7233", namespace: str = "default"):
        """
        Initialize Temporal Workflow Manager

        Args:
            temporal_host: Temporal server address
            namespace: Temporal namespace
        """
        if not TEMPORAL_AVAILABLE:
            raise ImportError("Temporal SDK not installed. Install with: pip install temporalio")

        self.temporal_host = temporal_host
        self.namespace = namespace
        self.client: Optional[Client] = None
        self.worker: Optional[worker.Worker] = None
        self.is_running = False

        logger.info(f"Temporal Workflow Manager initialized for {temporal_host}")

    async def connect(self) -> bool:
        """
        Connect to Temporal server

        Returns:
            True if connected successfully
        """
        try:
            self.client = await Client.connect(self.temporal_host, namespace=self.namespace)
            logger.info(f"Connected to Temporal server: {self.temporal_host}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Temporal server: {e}")
            return False

    async def start_worker(self, task_queue: str = "aiops-task-queue") -> bool:
        """
        Start Temporal worker

        Args:
            task_queue: Task queue name

        Returns:
            True if worker started successfully
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")

        try:
            self.worker = worker.Worker(
                self.client,
                task_queue=task_queue,
                workflows=[AnomalyDetectionWorkflow, AutoScalingWorkflow, BackupWorkflow],
                activities=[
                    detect_anomaly_activity,
                    root_cause_analysis_activity,
                    auto_heal_activity,
                    runbook_generation_activity,
                    notify_activity,
                ],
            )

            self.is_running = True
            logger.info(f"Temporal worker started for task queue: {task_queue}")
            return True
        except Exception as e:
            logger.error(f"Failed to start Temporal worker: {e}")
            return False

    async def run_worker(self):
        """Run the worker (blocking)"""
        if not self.worker:
            raise RuntimeError("Worker not started. Call start_worker() first.")

        await self.worker.run()

    async def execute_workflow(
        self,
        workflow_class: Any,
        input_data: Dict[str, Any],
        workflow_id: Optional[str] = None,
        task_queue: str = "aiops-task-queue",
    ) -> Any:
        """
        Execute a workflow

        Args:
            workflow_class: Workflow class to execute
            input_data: Input data for workflow
            workflow_id: Optional workflow ID
            task_queue: Task queue name

        Returns:
            Workflow result
        """
        if not self.client:
            raise RuntimeError("Client not connected. Call connect() first.")

        try:
            result = await self.client.execute_workflow(
                workflow_class.run, input_data, id=workflow_id, task_queue=task_queue
            )

            logger.info(f"Workflow executed: {workflow_class.__name__}")
            return result
        except Exception as e:
            logger.error(f"Failed to execute workflow: {e}")
            raise

    async def stop_worker(self):
        """Stop the worker"""
        if self.worker:
            self.worker.shutdown()
            self.is_running = False
            logger.info("Temporal worker stopped")

    async def close(self):
        """Close client connection"""
        if self.client:
            await self.client.close()
            logger.info("Temporal client closed")


def create_temporal_manager(
    temporal_host: str = "localhost:7233", namespace: str = "default"
) -> Optional[TemporalWorkflowManager]:
    """
    Factory function to create Temporal Workflow Manager

    Args:
        temporal_host: Temporal server address
        namespace: Temporal namespace

    Returns:
        TemporalWorkflowManager instance or None if SDK not available
    """
    if not TEMPORAL_AVAILABLE:
        logger.warning("Temporal SDK not available")
        return None

    try:
        return TemporalWorkflowManager(temporal_host, namespace)
    except Exception as e:
        logger.error(f"Failed to create Temporal manager: {e}")
        return None
