# -*- coding: utf-8 -*-
"""
Custom HPA Controller
Kubernetes自定义指标HPA控制器

功能:
- 自定义指标采集
- 容量预测驱动的伸缩
- 伸缩策略管理
- HPA配置生成
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
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


class ScalingDirection(Enum):
    """伸缩方向"""

    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    NO_ACTION = "no_action"


class ScalingPolicy:
    """
    伸缩策略

    参数:
        min_replicas: 最小副本数
        max_replicas: 最大副本数
        target_cpu_utilization: 目标CPU利用率
        target_memory_utilization: 目标内存利用率
        scale_up_threshold: 扩容阈值
        scale_down_threshold: 缩容阈值
        cooldown_period: 冷却期（秒）
    """

    def __init__(
        self,
        min_replicas: int = 1,
        max_replicas: int = 10,
        target_cpu_utilization: float = 70.0,
        target_memory_utilization: float = 80.0,
        scale_up_threshold: float = 80.0,
        scale_down_threshold: float = 30.0,
        cooldown_period: int = 300,
    ):
        self.min_replicas = min_replicas
        self.max_replicas = max_replicas
        self.target_cpu_utilization = target_cpu_utilization
        self.target_memory_utilization = target_memory_utilization
        self.scale_up_threshold = scale_up_threshold
        self.scale_down_threshold = scale_down_threshold
        self.cooldown_period = cooldown_period

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "min_replicas": self.min_replicas,
            "max_replicas": self.max_replicas,
            "target_cpu_utilization": self.target_cpu_utilization,
            "target_memory_utilization": self.target_memory_utilization,
            "scale_up_threshold": self.scale_up_threshold,
            "scale_down_threshold": self.scale_down_threshold,
            "cooldown_period": self.cooldown_period,
        }


class CustomHPAController:
    """
    自定义HPA控制器

    基于容量预测和自定义指标的弹性伸缩控制器。

    参数:
        namespace: 命名空间
        kubeconfig: K8s配置文件路径
        dry_run: 是否只模拟不执行
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

        self._k8s_client: Optional[client.AppsV1Api] = None
        self._autoscaling_client: Optional[client.AutoscalingV2Api] = None
        self._metrics_client: Optional[client.CustomMetricsApi] = None
        self._is_initialized = False

        # 伸缩策略存储
        self._policies: Dict[str, ScalingPolicy] = {}

        # 伸缩历史
        self._scaling_history: List[Dict[str, Any]] = []

        # 冷却期记录
        self._cooldowns: Dict[str, datetime] = {}

    def initialize(self) -> None:
        """初始化K8s客户端"""
        if not KUBERNETES_AVAILABLE:
            logger.warning("kubernetes not installed, controller will run in simulation mode")
            return

        try:
            if self.kubeconfig:
                config.load_kube_config(config_file=self.kubeconfig)
            else:
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config()

            self._k8s_client = client.AppsV1Api()
            self._autoscaling_client = client.AutoscalingV2Api()
            self._metrics_client = client.CustomMetricsApi()
            self._is_initialized = True

            logger.info("Custom HPA controller initialized for namespace: %s", self.namespace)

        except Exception as e:
            logger.error("Failed to initialize K8s client: %s", e)

    def register_policy(
        self,
        deployment_name: str,
        policy: ScalingPolicy,
    ) -> None:
        """
        注册伸缩策略

        参数:
            deployment_name: Deployment名称
            policy: 伸缩策略
        """
        self._policies[deployment_name] = policy
        logger.info("Registered scaling policy for deployment: %s", deployment_name)

    def get_policy(self, deployment_name: str) -> Optional[ScalingPolicy]:
        """获取伸缩策略"""
        return self._policies.get(deployment_name)

    async def monitor_and_scale(self, interval: int = 60) -> None:
        """
        监控并执行伸缩

        参数:
            interval: 监控间隔（秒）
        """
        logger.info("Starting HPA monitoring with interval: %ds", interval)

        while True:
            try:
                for deployment_name, policy in self._policies.items():
                    await self._evaluate_scaling(deployment_name, policy)

                # 清理过期的冷却期
                self._cleanup_cooldowns()

            except Exception as e:
                logger.error("Error during HPA monitoring: %s", e)

            await asyncio.sleep(interval)

    async def _evaluate_scaling(
        self,
        deployment_name: str,
        policy: ScalingPolicy,
    ) -> None:
        """
        评估是否需要伸缩

        参数:
            deployment_name: Deployment名称
            policy: 伸缩策略
        """
        # 检查冷却期
        if self._is_in_cooldown(deployment_name):
            logger.debug("Deployment %s is in cooldown period", deployment_name)
            return

        # 获取当前指标
        metrics = await self._get_deployment_metrics(deployment_name)

        if not metrics:
            logger.warning("Failed to get metrics for deployment: %s", deployment_name)
            return

        # 评估伸缩方向
        direction = self._evaluate_scaling_direction(metrics, policy)

        if direction == ScalingDirection.NO_ACTION:
            return

        # 计算目标副本数
        current_replicas = metrics.get("current_replicas", 1)
        target_replicas = self._calculate_target_replicas(
            current_replicas,
            metrics,
            policy,
            direction,
        )

        # 应用限制
        target_replicas = max(policy.min_replicas, min(policy.max_replicas, target_replicas))

        if target_replicas == current_replicas:
            return

        # 执行伸缩
        success = await self._scale_deployment(deployment_name, target_replicas)

        if success:
            # 记录冷却期
            self._cooldowns[deployment_name] = datetime.now() + timedelta(
                seconds=policy.cooldown_period
            )

            # 记录历史
            self._scaling_history.append(
                {
                    "deployment_name": deployment_name,
                    "from_replicas": current_replicas,
                    "to_replicas": target_replicas,
                    "direction": direction.value,
                    "metrics": metrics,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            logger.info(
                "Scaled deployment %s from %d to %d replicas (direction: %s)",
                deployment_name,
                current_replicas,
                target_replicas,
                direction.value,
            )

    @staticmethod
    def _parse_cpu_quantity(value: Optional[str]) -> float:
        """把 K8s CPU 资源量字符串解析为核数（"100m" -> 0.1，"2" -> 2.0）。"""
        if not value:
            return 0.0
        value = str(value).strip()
        try:
            if value.endswith("m"):
                return float(value[:-1]) / 1000.0
            if value.endswith("n"):
                return float(value[:-1]) / 1_000_000_000.0
            if value.endswith("u"):
                return float(value[:-1]) / 1_000_000.0
            return float(value)
        except ValueError:
            return 0.0

    @staticmethod
    def _parse_memory_quantity(value: Optional[str]) -> float:
        """把 K8s 内存资源量字符串解析为字节数（"128Mi" -> 134217728）。"""
        if not value:
            return 0.0
        value = str(value).strip()
        suffixes = {
            "Ki": 1024,
            "Mi": 1024**2,
            "Gi": 1024**3,
            "Ti": 1024**4,
            "Pi": 1024**5,
            "K": 1000,
            "M": 1000**2,
            "G": 1000**3,
            "T": 1000**4,
            "k": 1000,
        }
        for suffix, factor in suffixes.items():
            if value.endswith(suffix):
                try:
                    return float(value[: -len(suffix)]) * factor
                except ValueError:
                    return 0.0
        try:
            return float(value)
        except ValueError:
            return 0.0

    async def _get_deployment_metrics(self, deployment_name: str) -> Optional[Dict[str, Any]]:
        """
        获取Deployment指标

        从 K8s API 读取 Deployment 当前副本数、Pod 资源 requests，
        并通过 metrics-server（``metrics.k8s.io/v1beta1``）读取**真实** Pod 使用量，
        据此计算 CPU/内存利用率。无 metrics-server 或客户端未初始化时返回 ``None``
        （诚实失败，绝不返回占位常量）。

        参数:
            deployment_name: Deployment名称

        返回:
            指标字典；无法获取时返回 None
        """
        if not self._is_initialized or self._k8s_client is None:
            logger.error(
                "K8s client not initialized; cannot read metrics for deployment %s",
                deployment_name,
            )
            return None

        try:
            # 获取Deployment
            deploy = self._k8s_client.read_namespaced_deployment(deployment_name, self.namespace)

            current_replicas = deploy.spec.replicas or 0

            # 获取Pod
            pods = self._k8s_client.list_namespaced_pod(
                self.namespace, label_selector=f"app={deployment_name}"
            )

            if not pods.items:
                return {
                    "current_replicas": current_replicas,
                    "cpu_utilization": 0.0,
                    "memory_utilization": 0.0,
                }

            # 汇总每个容器的资源 requests 作为利用率分母
            requested_cpu = 0.0
            requested_memory = 0.0
            running_pods = 0
            for pod in pods.items:
                if pod.status.phase != "Running":
                    continue
                running_pods += 1
                for container in pod.spec.containers or []:
                    requests = getattr(container.resources, "requests", None) or {}
                    requested_cpu += self._parse_cpu_quantity(requests.get("cpu"))
                    requested_memory += self._parse_memory_quantity(requests.get("memory"))

            if running_pods == 0:
                return {
                    "current_replicas": current_replicas,
                    "cpu_utilization": 0.0,
                    "memory_utilization": 0.0,
                }

            # 从 metrics-server 读取真实使用量
            custom_api = client.CustomObjectsApi()
            metrics_obj = custom_api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace=self.namespace,
                plural="pods",
                label_selector=f"app={deployment_name}",
            )

            used_cpu = 0.0
            used_memory = 0.0
            for item in metrics_obj.get("items", []):
                for container in item.get("containers", []):
                    usage = container.get("usage", {}) or {}
                    used_cpu += self._parse_cpu_quantity(usage.get("cpu"))
                    used_memory += self._parse_memory_quantity(usage.get("memory"))

            cpu_utilization = (used_cpu / requested_cpu * 100.0) if requested_cpu > 0 else 0.0
            memory_utilization = (
                (used_memory / requested_memory * 100.0) if requested_memory > 0 else 0.0
            )

            return {
                "current_replicas": current_replicas,
                "cpu_utilization": round(cpu_utilization, 2),
                "memory_utilization": round(memory_utilization, 2),
                "used_cpu_cores": round(used_cpu, 4),
                "used_memory_bytes": int(used_memory),
            }

        except ApiException as e:
            logger.error("Failed to get metrics for deployment %s: %s", deployment_name, e)
            return None

    def _evaluate_scaling_direction(
        self,
        metrics: Dict[str, Any],
        policy: ScalingPolicy,
    ) -> ScalingDirection:
        """
        评估伸缩方向

        参数:
            metrics: 指标
            policy: 伸缩策略

        返回:
            伸缩方向
        """
        cpu_util = metrics.get("cpu_utilization", 0.0)
        mem_util = metrics.get("memory_utilization", 0.0)

        # 扩容条件
        if cpu_util >= policy.scale_up_threshold or mem_util >= policy.scale_up_threshold:
            return ScalingDirection.SCALE_UP

        # 缩容条件
        if cpu_util <= policy.scale_down_threshold and mem_util <= policy.scale_down_threshold:
            return ScalingDirection.SCALE_DOWN

        return ScalingDirection.NO_ACTION

    def _calculate_target_replicas(
        self,
        current_replicas: int,
        metrics: Dict[str, Any],
        policy: ScalingPolicy,
        direction: ScalingDirection,
    ) -> int:
        """
        计算目标副本数

        参数:
            current_replicas: 当前副本数
            metrics: 指标
            policy: 伸缩策略
            direction: 伸缩方向

        返回:
            目标副本数
        """
        if direction == ScalingDirection.SCALE_UP:
            # 基于CPU利用率计算
            cpu_util = metrics.get("cpu_utilization", 0.0)
            if cpu_util > 0:
                target = int(current_replicas * (cpu_util / policy.target_cpu_utilization))
                return max(current_replicas + 1, target)
            return current_replicas + 1

        elif direction == ScalingDirection.SCALE_DOWN:
            # 缩容时每次减少1个副本
            return max(1, current_replicas - 1)

        return current_replicas

    async def _scale_deployment(
        self,
        deployment_name: str,
        target_replicas: int,
    ) -> bool:
        """
        执行伸缩

        参数:
            deployment_name: Deployment名称
            target_replicas: 目标副本数

        返回:
            是否成功
        """
        if self.dry_run:
            logger.info(
                "Dry-run: would scale deployment %s to %d replicas",
                deployment_name,
                target_replicas,
            )
            return True

        if not self._is_initialized or self._k8s_client is None:
            logger.error(
                "K8s client not initialized; cannot scale deployment %s to %d replicas",
                deployment_name,
                target_replicas,
            )
            return False

        try:
            self._k8s_client.patch_namespaced_deployment_scale(
                name=deployment_name,
                namespace=self.namespace,
                body={"spec": {"replicas": target_replicas}},
            )
            logger.info("Scaled deployment %s to %d replicas", deployment_name, target_replicas)
            return True

        except ApiException as e:
            logger.error("Failed to scale deployment %s: %s", deployment_name, e)
            return False

    def _is_in_cooldown(self, deployment_name: str) -> bool:
        """检查是否在冷却期"""
        if deployment_name not in self._cooldowns:
            return False
        return datetime.now() < self._cooldowns[deployment_name]

    def _cleanup_cooldowns(self) -> None:
        """清理过期的冷却期"""
        now = datetime.now()
        expired = [name for name, expiry in self._cooldowns.items() if now >= expiry]
        for name in expired:
            del self._cooldowns[name]

    def get_scaling_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取伸缩历史

        参数:
            limit: 返回数量限制

        返回:
            伸缩历史列表
        """
        return self._scaling_history[-limit:]

    def get_scaling_stats(self) -> Dict[str, Any]:
        """获取伸缩统计"""
        if not self._scaling_history:
            return {
                "total_scalings": 0,
                "scale_up_count": 0,
                "scale_down_count": 0,
            }

        scale_up_count = sum(
            1 for h in self._scaling_history if h["direction"] == ScalingDirection.SCALE_UP.value
        )
        scale_down_count = sum(
            1 for h in self._scaling_history if h["direction"] == ScalingDirection.SCALE_DOWN.value
        )

        return {
            "total_scalings": len(self._scaling_history),
            "scale_up_count": scale_up_count,
            "scale_down_count": scale_down_count,
        }

    def create_hpa_manifest(
        self,
        deployment_name: str,
        policy: ScalingPolicy,
    ) -> Dict[str, Any]:
        """
        创建HPA YAML清单

        参数:
            deployment_name: Deployment名称
            policy: 伸缩策略

        返回:
            HPA清单字典
        """
        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {
                "name": f"{deployment_name}-hpa",
                "namespace": self.namespace,
            },
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": deployment_name,
                },
                "minReplicas": policy.min_replicas,
                "maxReplicas": policy.max_replicas,
                "metrics": [
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "cpu",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": int(policy.target_cpu_utilization),
                            },
                        },
                    },
                    {
                        "type": "Resource",
                        "resource": {
                            "name": "memory",
                            "target": {
                                "type": "Utilization",
                                "averageUtilization": int(policy.target_memory_utilization),
                            },
                        },
                    },
                ],
            },
        }
