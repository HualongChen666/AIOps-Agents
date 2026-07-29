# -*- coding: utf-8 -*-
"""
Auto-Heal K8s Operator
Kubernetes Operator for automatic healing

功能:
- 监控K8s资源状态
- 检测异常并触发修复
- 协调修复流程
- 状态管理
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from kubernetes import client, config
    from kubernetes.client.rest import ApiException

    KUBERNETES_AVAILABLE = True
except ImportError:
    KUBERNETES_AVAILABLE = False
    client = None
    config = None

logger = logging.getLogger(__name__)


class HealConditionType(Enum):
    """修复条件类型"""

    PodNotReady = "PodNotReady"
    HighCPU = "HighCPU"
    HighMemory = "HighMemory"
    DiskFull = "DiskFull"
    ServiceDown = "ServiceDown"
    CustomAlert = "CustomAlert"


class HealPhase(Enum):
    """修复阶段"""

    Pending = "pending"
    Detecting = "detecting"
    Healing = "healing"
    Verifying = "verifying"
    Completed = "completed"
    Failed = "failed"


class AutoHealOperator:
    """
    自动修复Operator

    监控K8s资源状态，检测异常并触发修复流程。

    参数:
        namespace: 监控的命名空间
        kubeconfig: K8s配置文件路径
        dry_run: 是否只检测不执行
    """

    def __init__(
        self,
        namespace: str = "default",
        kubeconfig: Optional[str] = None,
        dry_run: bool = False,
    ):
        self.namespace = namespace
        self.kubeconfig = kubeconfig
        self.dry_run = dry_run

        self._k8s_client: Optional[client.CoreV1Api] = None
        self._apps_client: Optional[client.AppsV1Api] = None
        self._is_initialized = False

        # 修复任务存储
        self._heal_tasks: Dict[str, Dict[str, Any]] = {}

    def initialize(self) -> None:
        """初始化K8s客户端"""
        if not KUBERNETES_AVAILABLE:
            logger.warning("kubernetes not installed, operator will run in simulation mode")
            return

        try:
            if self.kubeconfig:
                config.load_kube_config(config_file=self.kubeconfig)
            else:
                # 尝试集群内配置
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    # 降级到默认配置
                    config.load_kube_config()

            self._k8s_client = client.CoreV1Api()
            self._apps_client = client.AppsV1Api()
            self._is_initialized = True

            logger.info("K8s operator initialized for namespace: %s", self.namespace)

        except Exception as e:
            logger.error("Failed to initialize K8s client: %s", e)

    async def monitor_resources(self, interval: int = 30) -> None:
        """
        监控资源状态

        参数:
            interval: 监控间隔（秒）
        """
        logger.info("Starting resource monitoring with interval: %ds", interval)

        while True:
            try:
                await self._check_pods()
                await self._check_deployments()
                await self._check_services()

                # 清理已完成的任务
                self._cleanup_completed_tasks()

            except Exception as e:
                logger.error("Error during monitoring: %s", e)

            await asyncio.sleep(interval)

    async def _check_pods(self) -> None:
        """检查Pod状态"""
        if not self._is_initialized:
            logger.debug("K8s client not initialized, skipping pod check")
            return

        try:
            assert self._k8s_client is not None
            pods = self._k8s_client.list_namespaced_pod(self.namespace)

            for pod in pods.items:
                pod_name = pod.metadata.name
                pod_status = pod.status.phase

                # 检查Pod是否处于异常状态
                if pod_status in ["Pending", "Failed", "Unknown"]:
                    await self._trigger_heal(
                        resource_type="Pod",
                        resource_name=pod_name,
                        condition=HealConditionType.PodNotReady,
                        details={
                            "status": pod_status,
                            "reason": pod.status.reason,
                            "message": pod.status.message,
                        },
                    )

                # 检查Pod是否就绪
                elif pod_status == "Running":
                    ready_containers = sum(
                        1 for cs in pod.status.container_statuses or [] if cs.ready
                    )
                    total_containers = len(pod.spec.containers)

                    if ready_containers < total_containers:
                        await self._trigger_heal(
                            resource_type="Pod",
                            resource_name=pod_name,
                            condition=HealConditionType.PodNotReady,
                            details={
                                "ready": ready_containers,
                                "total": total_containers,
                            },
                        )

        except ApiException as e:
            logger.error("K8s API error checking pods: %s", e)

    async def _check_deployments(self) -> None:
        """检查Deployment状态"""
        if not self._is_initialized:
            return

        try:
            assert self._apps_client is not None
            deployments = self._apps_client.list_namespaced_deployment(self.namespace)

            for deploy in deployments.items:
                deploy_name = deploy.metadata.name

                # 检查副本数
                desired = deploy.spec.replicas or 0
                available = deploy.status.available_replicas or 0

                if available < desired:
                    await self._trigger_heal(
                        resource_type="Deployment",
                        resource_name=deploy_name,
                        condition=HealConditionType.PodNotReady,
                        details={
                            "desired": desired,
                            "available": available,
                        },
                    )

        except ApiException as e:
            logger.error("K8s API error checking deployments: %s", e)

    async def _check_services(self) -> None:
        """检查Service状态"""
        if not self._is_initialized:
            return

        try:
            assert self._k8s_client is not None
            services = self._k8s_client.list_namespaced_service(self.namespace)

            for svc in services.items:
                svc_name = svc.metadata.name

                # 检查Service是否有端点
                if svc.spec.type != "ExternalName":
                    # 需要检查Endpoints
                    try:
                        assert self._k8s_client is not None
                        endpoints = self._k8s_client.read_namespaced_endpoints(
                            svc_name, self.namespace
                        )

                        if not endpoints.subsets or not any(
                            subset.addresses for subset in endpoints.subsets
                        ):
                            await self._trigger_heal(
                                resource_type="Service",
                                resource_name=svc_name,
                                condition=HealConditionType.ServiceDown,
                                details={"endpoints": "none"},
                            )
                    except ApiException:
                        pass

        except ApiException as e:
            logger.error("K8s API error checking services: %s", e)

    async def _trigger_heal(
        self,
        resource_type: str,
        resource_name: str,
        condition: HealConditionType,
        details: Dict[str, Any],
    ) -> None:
        """
        触发修复流程

        参数:
            resource_type: 资源类型
            resource_name: 资源名称
            condition: 触发条件
            details: 详细信息
        """
        task_id = f"{resource_type}_{resource_name}_{datetime.now().timestamp()}"

        # 检查是否已有进行中的修复任务
        existing_task = self._get_active_task(resource_type, resource_name)
        if existing_task:
            logger.debug(
                "Heal task already in progress for %s/%s: %s",
                resource_type,
                resource_name,
                existing_task["task_id"],
            )
            return

        # 创建修复任务
        task = {
            "task_id": task_id,
            "resource_type": resource_type,
            "resource_name": resource_name,
            "condition": condition.value,
            "details": details,
            "phase": HealPhase.Pending.value,
            "created_at": datetime.now().isoformat(),
            "namespace": self.namespace,
        }

        self._heal_tasks[task_id] = task

        logger.info(
            "Heal task created: %s for %s/%s (condition: %s)",
            task_id,
            resource_type,
            resource_name,
            condition.value,
        )

        # 执行修复
        if not self.dry_run:
            asyncio.create_task(self._execute_heal(task))

    def _get_active_task(self, resource_type: str, resource_name: str) -> Optional[Dict[str, Any]]:
        """获取进行中的修复任务"""
        for task in self._heal_tasks.values():
            if (
                task["resource_type"] == resource_type
                and task["resource_name"] == resource_name
                and task["phase"] in [HealPhase.Pending.value, HealPhase.Healing.value]
            ):
                return task
        return None

    async def _execute_heal(self, task: Dict[str, Any]) -> None:
        """
        执行修复任务

        参数:
            task: 修复任务
        """
        task_id = task["task_id"]
        task["phase"] = HealPhase.Healing.value

        logger.info("Executing heal task: %s", task_id)

        try:
            # 根据资源类型选择修复策略
            resource_type = task["resource_type"]

            if resource_type == "Pod":
                success = await self._heal_pod(task)
            elif resource_type == "Deployment":
                success = await self._heal_deployment(task)
            elif resource_type == "Service":
                success = await self._heal_service(task)
            else:
                logger.warning("Unknown resource type: %s", resource_type)
                success = False

            if success:
                task["phase"] = HealPhase.Verifying.value
                # 验证修复结果
                verified = await self._verify_heal(task)
                task["phase"] = HealPhase.Completed.value if verified else HealPhase.Failed.value
            else:
                task["phase"] = HealPhase.Failed.value

            task["completed_at"] = datetime.now().isoformat()

            logger.info("Heal task %s completed with phase: %s", task_id, task["phase"])

        except Exception as e:
            logger.error("Error executing heal task %s: %s", task_id, e)
            task["phase"] = HealPhase.Failed.value
            task["error"] = str(e)

    async def _heal_pod(self, task: Dict[str, Any]) -> bool:
        """修复Pod"""
        if not self._is_initialized:
            logger.warning("K8s client not initialized, simulating pod heal")
            return True

        try:
            pod_name = task["resource_name"]

            # 策略1前: 先检查 Pod 是否属于 StatefulSet 或挂载 PVC
            assert self._k8s_client is not None
            pod = self._k8s_client.read_namespaced_pod(name=pod_name, namespace=self.namespace)
            owner_kind = ""
            for ref in pod.metadata.owner_references or []:
                if getattr(ref, "controller", False):
                    owner_kind = getattr(ref, "kind", "")
                    break
            has_pvc = any(
                bool(getattr(vol, "persistent_volume_claim", None))
                for vol in (pod.spec.volumes or [])
            )
            if owner_kind == "StatefulSet" or has_pvc:
                logger.warning(
                    "Refusing to heal stateful/PVC pod %s (owner=%s, has_pvc=%s)",
                    pod_name,
                    owner_kind,
                    has_pvc,
                )
                task["error"] = f"Stateful/PVC pod {pod_name} not eligible for auto-heal"
                return False

            # 策略1: 删除Pod让Deployment重新创建
            self._k8s_client.delete_namespaced_pod(
                name=pod_name, namespace=self.namespace, body=client.V1DeleteOptions()
            )

            logger.info("Deleted pod %s for healing", pod_name)
            return True

        except ApiException as e:
            logger.error("Failed to delete pod %s: %s", pod_name, e)
            return False

    async def _heal_deployment(self, task: Dict[str, Any]) -> bool:
        """修复Deployment"""
        if not self._is_initialized:
            logger.warning("K8s client not initialized, simulating deployment heal")
            return True

        try:
            deploy_name = task["resource_name"]

            # 策略: 重启Deployment
            assert self._apps_client is not None
            self._apps_client.patch_namespaced_deployment(
                name=deploy_name,
                namespace=self.namespace,
                body={
                    "spec": {
                        "template": {
                            "metadata": {
                                "annotations": {
                                    "kubectl.kubernetes.io/restartedAt": datetime.now().isoformat()
                                }
                            }
                        }
                    }
                },
            )

            logger.info("Restarted deployment %s", deploy_name)
            return True

        except ApiException as e:
            logger.error("Failed to restart deployment %s: %s", deploy_name, e)
            return False

    async def _heal_service(self, task: Dict[str, Any]) -> bool:
        """修复Service"""
        if not self._is_initialized:
            logger.warning("K8s client not initialized, simulating service heal")
            return True

        # Service通常不需要主动修复，问题通常在Pod层
        logger.info("Service %s heal skipped (usually heals with pods)", task["resource_name"])
        return True

    async def _verify_heal(self, task: Dict[str, Any]) -> bool:
        """
        验证修复结果

        参数:
            task: 修复任务

        返回:
            是否验证成功
        """
        # 等待一段时间让资源恢复
        await asyncio.sleep(10)

        resource_type = task["resource_type"]
        resource_name = task["resource_name"]

        if resource_type == "Pod":
            return await self._verify_pod(resource_name)
        elif resource_type == "Deployment":
            return await self._verify_deployment(resource_name)
        elif resource_type == "Service":
            return await self._verify_service(resource_name)

        return True

    async def _verify_pod(self, pod_name: str) -> bool:
        """验证Pod状态"""
        if not self._is_initialized:
            return True

        try:
            assert self._k8s_client is not None
            pod = self._k8s_client.read_namespaced_pod(pod_name, self.namespace)
            return pod.status.phase == "Running" if pod.status.phase else False
        except ApiException:
            return False

    async def _verify_deployment(self, deploy_name: str) -> bool:
        """验证Deployment状态"""
        if not self._is_initialized:
            return True

        try:
            assert self._apps_client is not None
            deploy = self._apps_client.read_namespaced_deployment(deploy_name, self.namespace)
            desired = deploy.spec.replicas or 0
            available = deploy.status.available_replicas or 0
            return available >= desired
        except ApiException:
            return False

    async def _verify_service(self, svc_name: str) -> bool:
        """验证Service状态"""
        if not self._is_initialized:
            return True

        try:
            assert self._k8s_client is not None
            endpoints = self._k8s_client.read_namespaced_endpoints(svc_name, self.namespace)
            return bool(endpoints.subsets and any(subset.addresses for subset in endpoints.subsets))
        except ApiException:
            return False

    def _cleanup_completed_tasks(self) -> None:
        """清理已完成的任务"""
        now = datetime.now()
        expired_tasks = []

        for task_id, task in self._heal_tasks.items():
            if task["phase"] in [HealPhase.Completed.value, HealPhase.Failed.value]:
                completed_at = datetime.fromisoformat(task["completed_at"])
                # 保留1小时
                if (now - completed_at).total_seconds() > 3600:
                    expired_tasks.append(task_id)

        for task_id in expired_tasks:
            del self._heal_tasks[task_id]
            logger.debug("Cleaned up expired heal task: %s", task_id)

    def get_heal_tasks(self) -> List[Dict[str, Any]]:
        """获取所有修复任务"""
        return list(self._heal_tasks.values())

    def get_task_stats(self) -> Dict[str, Any]:
        """获取任务统计"""
        total = len(self._heal_tasks)
        by_phase: Dict[str, int] = {}

        for task in self._heal_tasks.values():
            phase = task["phase"]
            by_phase[phase] = by_phase.get(phase, 0) + 1

        return {
            "total": total,
            "by_phase": by_phase,
        }
