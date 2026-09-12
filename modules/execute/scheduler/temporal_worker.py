# -*- coding: utf-8 -*-
"""
Temporal Workflow Engine Integration for AIOps Platform
Provides reliable task scheduling and workflow orchestration using Temporal

本模块把 AIOps 平台既有的真实能力（异常检测 / 根因推断 / 自动修复 / Runbook 生成 /
通知 / 弹性伸缩 / 备份）封装为 Temporal Activity 与 Workflow。

设计要点（真实实现，非桩）：
- Temporal SDK 缺失时，模块仍可被安全导入：装饰器降级为恒等装饰器，
  仅 `TemporalWorkflowManager` 在真正使用时才要求 SDK 存在。
- 每个 Activity 都调用平台内**真实**的下层实现：
    * 异常检测 -> ``core.advanced_ai_capabilities.predict_anomalies``（独立/序列两种形态）
    * 根因推断 -> ``modules.analyze.root_cause.inference.RootCauseInference.infer_root_cause``
    * 自动修复 -> ``core.auto_heal.try_auto_heal``
    * Runbook  -> ``core.runbook_generator.generate_repair_runbook``
    * 通知     -> ``core.notify_engine.send_alert_notification``
    * 弹性伸缩 -> ``modules.execute.autoscaler.custom_hpa_controller.CustomHPAController``
    * 备份     -> ``core.backup_manager.backup_database``
  不存在的方法/占位返回值一律移除；数据不足时 Activity 明确抛错，绝不伪造成功。
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from temporalio import activity, worker, workflow
    from temporalio.client import Client
    from temporalio.common import RetryPolicy

    TEMPORAL_AVAILABLE = True
except ImportError:  # pragma: no cover - exercised only when SDK absent
    TEMPORAL_AVAILABLE = False
    workflow = None
    activity = None
    worker = None
    Client = None
    RetryPolicy = None

logger = logging.getLogger(__name__)


# ----------------------------------------------------------------------
# 装饰器降级：Temporal SDK 缺失时模块仍可导入，避免 import 期 AttributeError
# ----------------------------------------------------------------------
if TEMPORAL_AVAILABLE:
    activity_defn = activity.defn
    workflow_defn = workflow.defn
    workflow_run = workflow.run
else:  # pragma: no cover - only without temporalio installed

    def activity_defn(fn):
        return fn

    def workflow_defn(cls):
        return cls

    def workflow_run(fn):
        return fn


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


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
            self.timestamp = datetime.now(timezone.utc)


# ----------------------------------------------------------------------
# Temporal Activities（全部调用真实下层实现）
# ----------------------------------------------------------------------
@activity_defn
async def detect_anomaly_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    异常检测 Activity。

    ``input_data`` 需携带真实被检数据：
      * ``current_data``: ``{metric_name: current_value}``
      * ``historical_baseline``: ``{metric_name: [历史值, ...]}``
      * ``threshold_std``（可选，默认 2.0）

    调用 ``core.advanced_ai_capabilities.predict_anomalies`` 进行真实 z-score 检测。
    数据缺失时抛 ``ValueError``（Activity 失败），不返回伪造结果。
    """
    try:
        from core.advanced_ai_capabilities import AdvancedAICapabilities

        current_data = input_data.get("current_data") or input_data.get("metrics")
        baseline = input_data.get("historical_baseline") or input_data.get("baseline")
        if not current_data or not baseline:
            raise ValueError(
                "detect_anomaly_activity requires 'current_data' and 'historical_baseline'"
            )

        engine = AdvancedAICapabilities()
        prediction = await engine.predict_anomalies(
            current_data={k: float(v) for k, v in current_data.items()},
            historical_baseline={k: [float(x) for x in v] for k, v in baseline.items()},
            threshold_std=float(input_data.get("threshold_std", 2.0)),
        )

        anomalies = prediction.metadata.get("anomalies", [])
        anomaly_count = len(anomalies)

        return {
            "status": "success",
            "result": {
                "anomaly_detected": anomaly_count > 0,
                "anomaly_count": anomaly_count,
                "anomalies": anomalies,
                "confidence": prediction.confidence,
                "method": prediction.model_used,
            },
            "timestamp": _utcnow_iso(),
        }
    except Exception as e:
        logger.error(f"Anomaly detection activity failed: {e}")
        raise


@activity_defn
async def root_cause_analysis_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    根因分析 Activity。

    ``input_data`` 需携带真实拓扑数据：``alerts`` / ``services`` / ``metrics`` /
    ``dependencies``（均可选，但 ``alerts`` 至少一条）。先用
    ``RootCauseInference.build_graph_from_alerts`` 构建图，再对首个告警调用
    ``infer_root_cause`` 做真实推断（GNN 不可用时自动降级 pagerank 启发式）。
    """
    try:
        from modules.analyze.root_cause.inference import RootCauseInference

        alerts = input_data.get("alerts") or []
        if not alerts:
            raise ValueError("root_cause_analysis_activity requires at least one alert")

        rca = RootCauseInference()
        rca.build_graph_from_alerts(
            alerts=alerts,
            services=input_data.get("services") or [],
            metrics=input_data.get("metrics") or [],
            dependencies=input_data.get("dependencies") or [],
        )

        hops = int(input_data.get("hops", 3))
        results: List[Dict[str, Any]] = []
        for alert in alerts:
            alert_id = alert.get("id")
            if not alert_id:
                continue
            results.append(rca.infer_root_cause(alert_id=alert_id, hops=hops))

        return {
            "status": "success",
            "result": {
                "results": results,
                "primary": results[0] if results else None,
            },
            "timestamp": _utcnow_iso(),
        }
    except Exception as e:
        logger.error(f"Root cause analysis activity failed: {e}")
        raise


@activity_defn
async def auto_heal_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    自动修复 Activity —— 调用 ``core.auto_heal.try_auto_heal`` 执行真实修复流程
    （风险评估 -> 修复 -> 验证 -> 审批队列）。
    """
    try:
        from core.auto_heal import try_auto_heal

        alert = input_data.get("alert") or input_data.get("anomaly")
        if not alert:
            raise ValueError("auto_heal_activity requires 'alert' input")

        result = await try_auto_heal(alert)

        return {
            "status": "success",
            "result": result,
            "timestamp": _utcnow_iso(),
        }
    except Exception as e:
        logger.error(f"Auto-heal activity failed: {e}")
        raise


@activity_defn
async def runbook_generation_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Runbook 生成 Activity —— 调用 ``core.runbook_generator.generate_repair_runbook``
    生成真实修复 Runbook（含护栏审查与审批入队）。
    """
    try:
        from core.runbook_generator import generate_repair_runbook

        alert = input_data.get("alert") or input_data.get("anomaly")
        if not alert:
            raise ValueError("runbook_generation_activity requires 'alert' input")

        result = await generate_repair_runbook(alert, rich_context=input_data.get("context"))

        return {
            "status": "success",
            "result": result,
            "timestamp": _utcnow_iso(),
        }
    except Exception as e:
        logger.error(f"Runbook generation activity failed: {e}")
        raise


@activity_defn
async def notify_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    通知 Activity —— 调用 ``core.notify_engine.send_alert_notification``
    经真实渠道（企业微信/钉钉/飞书/Slack/邮件）派发告警通知。
    """
    try:
        from core.notify_engine import send_alert_notification

        alert = input_data.get("alert") or input_data.get("data")
        if not alert:
            raise ValueError("notify_activity requires 'alert' input")

        result = await send_alert_notification(alert)

        return {
            "status": "success",
            "result": result,
            "timestamp": _utcnow_iso(),
        }
    except Exception as e:
        logger.error(f"Notification activity failed: {e}")
        raise


@activity_defn
async def auto_scaling_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    弹性伸缩 Activity —— 调用 ``CustomHPAController`` 的真实伸缩评估/执行逻辑。

    ``input_data``：
      * ``deployment_name``（必填）
      * ``namespace``（可选，默认 default）
      * ``policy``（可选字典，映射 ScalingPolicy 字段）
      * ``metrics``（可选：外部提供的真实指标；缺省则从 K8s metrics-server 读取）
      * ``dry_run``（可选，默认 True —— 只评估不落地，符合"安全执行默认"）
    """
    try:
        from modules.execute.autoscaler.custom_hpa_controller import (
            CustomHPAController,
            ScalingDirection,
            ScalingPolicy,
        )

        deployment = input_data.get("deployment_name") or input_data.get("deployment")
        if not deployment:
            raise ValueError("auto_scaling_activity requires 'deployment_name'")

        policy_cfg = input_data.get("policy") or {}
        policy = ScalingPolicy(**policy_cfg) if policy_cfg else ScalingPolicy()

        controller = CustomHPAController(
            namespace=input_data.get("namespace", "default"),
            kubeconfig=input_data.get("kubeconfig"),
            dry_run=bool(input_data.get("dry_run", True)),
        )
        controller.initialize()

        metrics = input_data.get("metrics")
        if not metrics:
            metrics = await controller._get_deployment_metrics(deployment)
        if not metrics:
            raise RuntimeError(f"no metrics available for deployment {deployment}")

        direction = controller._evaluate_scaling_direction(metrics, policy)
        current_replicas = int(metrics.get("current_replicas", 1))
        target_replicas = current_replicas
        scaled = False

        if direction != ScalingDirection.NO_ACTION:
            target_replicas = controller._calculate_target_replicas(
                current_replicas, metrics, policy, direction
            )
            target_replicas = max(policy.min_replicas, min(policy.max_replicas, target_replicas))
            if target_replicas != current_replicas:
                scaled = await controller._scale_deployment(deployment, target_replicas)

        return {
            "status": "success",
            "result": {
                "deployment_name": deployment,
                "direction": direction.value,
                "current_replicas": current_replicas,
                "target_replicas": target_replicas,
                "scaled": scaled,
                "dry_run": controller.dry_run,
                "metrics": metrics,
            },
            "timestamp": _utcnow_iso(),
        }
    except Exception as e:
        logger.error(f"Auto-scaling activity failed: {e}")
        raise


@activity_defn
async def backup_activity(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    备份 Activity —— 调用 ``core.backup_manager.backup_database`` 执行真实数据库备份
    （wal-g / pg_dump 视配置而定）。
    """
    try:
        from core.backup_manager import backup_database, list_backups

        success = backup_database()
        backups = list_backups()

        return {
            "status": "success" if success else "failed",
            "result": {
                "success": success,
                "backups": backups,
                "label": input_data.get("label"),
            },
            "timestamp": _utcnow_iso(),
        }
    except Exception as e:
        logger.error(f"Backup activity failed: {e}")
        raise


# ----------------------------------------------------------------------
# Temporal Workflows
# ----------------------------------------------------------------------
@workflow_defn
class AnomalyDetectionWorkflow:
    """
    Workflow for anomaly detection and response
    """

    @workflow_run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute anomaly detection workflow

        Args:
            input_data: Workflow input data (含 series/points 等真实被检数据)

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
            context = input_data.get("context", {})
            rca_result = await workflow.execute_activity(
                root_cause_analysis_activity,
                {
                    "alerts": context.get("alerts", input_data.get("alerts", [])),
                    "services": context.get("services", input_data.get("services", [])),
                    "metrics": context.get("metrics", input_data.get("metrics", [])),
                    "dependencies": context.get(
                        "dependencies", input_data.get("dependencies", [])
                    ),
                },
                start_to_close_timeout=timedelta(seconds=60),
                retry_policy=RetryPolicy(maximum_attempts=2, initial_interval=timedelta(seconds=2)),
            )

            primary_alert = (context.get("alerts") or input_data.get("alerts") or [{}])[0]

            # Step 3: Generate runbook
            runbook_result = await workflow.execute_activity(
                runbook_generation_activity,
                {
                    "alert": primary_alert,
                    "context": context,
                },
                start_to_close_timeout=timedelta(seconds=45),
                retry_policy=RetryPolicy(maximum_attempts=2),
            )

            # Step 4: Attempt auto-heal if configured
            if input_data.get("auto_heal_enabled", False):
                heal_result = await workflow.execute_activity(
                    auto_heal_activity,
                    {"alert": primary_alert},
                    start_to_close_timeout=timedelta(seconds=120),
                    retry_policy=RetryPolicy(maximum_attempts=1),
                )

                # Step 5: Send notification
                await workflow.execute_activity(
                    notify_activity,
                    {
                        "alert": {
                            "type": (
                                "anomaly_resolved"
                                if heal_result["result"].get("success")
                                else "anomaly_detected"
                            ),
                            "id": primary_alert.get("id"),
                            "title": primary_alert.get("title", "Anomaly detected"),
                            "data": {
                                "anomaly": detection_result["result"],
                                "root_cause": rca_result["result"],
                                "heal_result": heal_result["result"],
                            },
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
                    "alert": {
                        "type": "anomaly_detected",
                        "id": primary_alert.get("id"),
                        "title": primary_alert.get("title", "Anomaly detected"),
                        "data": {
                            "anomaly": detection_result["result"],
                            "root_cause": rca_result["result"],
                            "runbook": runbook_result["result"],
                        },
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


@workflow_defn
class AutoScalingWorkflow:
    """
    Workflow for auto-scaling operations

    通过 ``auto_scaling_activity`` 调用真实 HPA 控制器评估并（在非 dry-run 时）执行伸缩。
    """

    @workflow_run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute auto-scaling workflow

        Args:
            input_data: Workflow input data

        Returns:
            Workflow result
        """
        scaling_result = await workflow.execute_activity(
            auto_scaling_activity,
            input_data,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(maximum_attempts=2),
        )

        return {
            "status": scaling_result["status"],
            "scaling": scaling_result["result"],
            "timestamp": _utcnow_iso(),
        }


@workflow_defn
class BackupWorkflow:
    """
    Workflow for backup operations

    通过 ``backup_activity`` 调用真实数据库备份。
    """

    @workflow_run
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute backup workflow

        Args:
            input_data: Workflow input data

        Returns:
            Workflow result
        """
        backup_result = await workflow.execute_activity(
            backup_activity,
            input_data,
            start_to_close_timeout=timedelta(seconds=1800),
            retry_policy=RetryPolicy(maximum_attempts=1),
        )

        return {
            "status": backup_result["status"],
            "backup": backup_result["result"],
            "timestamp": _utcnow_iso(),
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
                    auto_scaling_activity,
                    backup_activity,
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
