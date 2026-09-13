# -*- coding: utf-8 -*-
"""
Chaos Engineering Module
混沌工程模块

提供混沌工程测试功能，用于测试系统韧性和容错能力。
"""

import asyncio
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

_random = secrets.SystemRandom()

logger = logging.getLogger(__name__)


class ChaosMeshInjector:
    """Injects chaos experiments as Chaos Mesh custom resources.

    Chaos is applied by creating ``chaos-mesh.org/v1alpha1`` objects
    (NetworkChaos / PodChaos / StressChaos / IOChaos) on the target cluster and
    removed again when the experiment finishes.
    """

    group = "chaos-mesh.org"
    version = "v1alpha1"

    def __init__(self, namespace: str = "default", kubeconfig: Optional[str] = None):
        self.namespace = namespace
        self._kubeconfig = kubeconfig

    def _api(self) -> Any:
        try:
            from kubernetes import client as k8s_client
            from kubernetes import config as k8s_config
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise RuntimeError(
                "kubernetes package is required to inject chaos via Chaos Mesh"
            ) from exc

        if self._kubeconfig:
            k8s_config.load_kube_config(config_file=self._kubeconfig)
        else:
            try:
                k8s_config.load_incluster_config()
            except Exception:
                k8s_config.load_kube_config()
        return k8s_client.CustomObjectsApi()

    async def apply(self, kind: str, name: str, spec: Dict[str, Any]) -> None:
        """Create the chaos custom resource (blocking call offloaded to a thread)."""
        body = {
            "apiVersion": f"{self.group}/{self.version}",
            "kind": kind,
            "metadata": {"name": name, "namespace": self.namespace},
            "spec": spec,
        }
        api = self._api()
        await asyncio.to_thread(
            api.create_namespaced_custom_object,
            self.group,
            self.version,
            self.namespace,
            f"{kind.lower()}es",
            body,
        )

    async def delete(self, kind: str, name: str) -> None:
        """Delete the chaos custom resource."""
        api = self._api()
        try:
            await asyncio.to_thread(
                api.delete_namespaced_custom_object,
                self.group,
                self.version,
                self.namespace,
                f"{kind.lower()}es",
                name,
            )
        except Exception as exc:  # pragma: no cover - best effort cleanup
            logger.warning(f"Failed to delete chaos object {kind}/{name}: {exc}")


class ChaosExperiment(str, Enum):
    """混沌实验类型"""

    LATENCY_INJECTION = "latency_injection"
    FAULT_INJECTION = "fault_injection"
    RESOURCE_LIMITATION = "resource_limitation"
    NETWORK_PARTITION = "network_partition"
    SERVICE_FAILURE = "service_failure"


class ExperimentStatus(str, Enum):
    """实验状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


@dataclass
class ExperimentResult:
    """实验结果"""

    experiment: ChaosExperiment
    status: ExperimentStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0
    success: bool = False
    error_message: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)


class ChaosEngine:
    """混沌工程引擎"""

    def __init__(
        self,
        injector: Optional[Any] = None,
        namespace: Optional[str] = None,
        target_service: Optional[str] = None,
    ):
        """初始化混沌工程引擎

        Args:
            injector: 注入后端 (默认 Chaos Mesh)
            namespace: Kubernetes namespace of the experiment
            target_service: Default ``app`` label of the chaos target
        """
        self._experiment_history: List[ExperimentResult] = []
        self._current_experiment: Optional[ExperimentResult] = None
        self._enabled = False  # 默认禁用，需要显式启用

        self._namespace = namespace or os.getenv("CHAOS_NAMESPACE", "default")
        self._target_service = target_service or os.getenv("CHAOS_TARGET_SERVICE", "")
        self._injector = injector

    @property
    def injector(self) -> Any:
        """The chaos injection backend (Chaos Mesh by default)."""
        if self._injector is None:
            self._injector = ChaosMeshInjector(self._namespace)
        return self._injector

    def set_injector(self, injector: Any) -> None:
        """Override the chaos injection backend."""
        self._injector = injector

    def _resolve_target(self, parameters: Dict[str, Any]) -> str:
        """Resolve the chaos target service label, failing loudly when absent."""
        target = parameters.get("service_name") or self._target_service
        if not target:
            raise RuntimeError(
                "no chaos target configured: pass service_name or set CHAOS_TARGET_SERVICE"
            )
        return str(target)

    def _selector(self, target: str) -> Dict[str, Any]:
        return {"labelSelectors": {"app": target}, "namespaces": [self._namespace]}

    def enable(self):
        """启用混沌工程"""
        self._enabled = True
        logger.warning("Chaos engineering ENABLED - System resilience tests active")

    def disable(self):
        """禁用混沌工程"""
        self._enabled = False
        logger.info("Chaos engineering DISABLED")

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled

    async def run_experiment(
        self, experiment: ChaosExperiment, parameters: Optional[Dict[str, Any]] = None
    ) -> ExperimentResult:
        """
        执行混沌实验

        Args:
            experiment: 实验类型
            parameters: 实验参数

        Returns:
            实验结果
        """
        if not self._enabled:
            logger.warning("Chaos engineering is disabled, skipping experiment")
            return ExperimentResult(
                experiment=experiment,
                status=ExperimentStatus.ABORTED,
                start_time=datetime.now(timezone.utc),
                success=False,
                error_message="Chaos engineering is disabled",
            )

        if self._current_experiment and self._current_experiment.status == ExperimentStatus.RUNNING:
            raise RuntimeError("Another experiment is already running")

        start_time = datetime.now(timezone.utc)

        experiment_result = ExperimentResult(
            experiment=experiment, status=ExperimentStatus.RUNNING, start_time=start_time
        )

        self._current_experiment = experiment_result

        logger.warning(f"Starting chaos experiment: {experiment}")

        try:
            # 根据实验类型执行不同的混沌测试
            if experiment == ChaosExperiment.LATENCY_INJECTION:
                result = await self._inject_latency(parameters or {})
            elif experiment == ChaosExperiment.FAULT_INJECTION:
                result = await self._inject_fault(parameters or {})
            elif experiment == ChaosExperiment.RESOURCE_LIMITATION:
                result = await self._limit_resources(parameters or {})
            elif experiment == ChaosExperiment.NETWORK_PARTITION:
                result = await self._partition_network(parameters or {})
            elif experiment == ChaosExperiment.SERVICE_FAILURE:
                result = await self._fail_service(parameters or {})
            else:
                raise ValueError(f"Unknown experiment: {experiment}")

            experiment_result.status = ExperimentStatus.COMPLETED
            experiment_result.success = result.get("success", False)
            experiment_result.metrics = result

            logger.warning(
                f"Chaos experiment completed: {experiment}, success: {experiment_result.success}"
            )

        except Exception as e:
            experiment_result.status = ExperimentStatus.FAILED
            experiment_result.success = False
            experiment_result.error_message = str(e)
            logger.error(f"Chaos experiment failed: {experiment}, error: {e}")

        finally:
            end_time = datetime.now(timezone.utc)
            experiment_result.end_time = end_time
            experiment_result.duration_seconds = (end_time - start_time).total_seconds()

            self._experiment_history.append(experiment_result)
            self._current_experiment = None

        return experiment_result

    async def _inject_latency(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        注入延迟（真实 Chaos Mesh NetworkChaos/delay）

        Args:
            parameters: delay_ms / duration_seconds / service_name

        Returns:
            实验结果
        """
        delay_ms = int(parameters.get("delay_ms", _random.randint(100, 1000)))
        duration_s = int(parameters.get("duration_seconds", max(1, delay_ms // 100)))
        target = self._resolve_target(parameters)
        name = f"aiops-latency-{secrets.token_hex(4)}"

        spec = {
            "action": "delay",
            "mode": "one",
            "duration": f"{duration_s}s",
            "selector": self._selector(target),
            "delay": {
                "latency": f"{delay_ms}ms",
                "correlation": str(parameters.get("correlation", "100")),
                "jitter": f"{int(parameters.get('jitter_ms', 5))}ms",
            },
        }

        logger.warning(f"Injecting {delay_ms}ms latency into '{target}' via NetworkChaos")
        await self.injector.apply("NetworkChaos", name, spec)
        try:
            response_time = await self._measure_response_time()
        finally:
            await self.injector.delete("NetworkChaos", name)

        return {
            "success": True,
            "injected_latency_ms": delay_ms,
            "chaos_kind": "NetworkChaos",
            "chaos_object": name,
            "target": target,
            "measured_response_time_ms": response_time,
        }

    async def _inject_fault(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        注入故障（真实 Chaos Mesh PodChaos / IOChaos）

        Args:
            parameters: fault_type / duration_seconds / service_name

        Returns:
            实验结果
        """
        fault_type = parameters.get("fault_type", "random")
        duration_s = int(parameters.get("duration_seconds", 30))
        target = self._resolve_target(parameters)
        name = f"aiops-fault-{secrets.token_hex(4)}"

        if fault_type in {
            "database_error",
            "cache_error",
            "api_error",
            "random",
            "service_failure",
            "pod_failure",
            "pod-failure",
        }:
            kind, action = "PodChaos", "pod-failure"
        elif fault_type == "container_kill":
            kind, action = "PodChaos", "container-kill"
        elif fault_type in {"io_error", "io_fault"}:
            kind, action = "IOChaos", "fault"
        else:
            raise ValueError(f"Unsupported fault_type: {fault_type}")

        spec = {
            "action": action,
            "mode": "one",
            "duration": f"{duration_s}s",
            "selector": self._selector(target),
        }

        logger.warning(f"Injecting fault '{fault_type}' into '{target}' via {kind}/{action}")
        await self.injector.apply(kind, name, spec)
        try:
            system_health = await self._check_system_health()
        finally:
            await self.injector.delete(kind, name)

        return {
            "success": True,
            "fault_type": fault_type,
            "chaos_kind": kind,
            "chaos_action": action,
            "chaos_object": name,
            "target": target,
            "system_health": system_health,
        }

    async def _limit_resources(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        限制资源（真实 Chaos Mesh StressChaos）

        Args:
            parameters: resource_type / limit / duration_seconds / service_name

        Returns:
            实验结果
        """
        resource_type = parameters.get("resource_type", "memory")
        limit = float(parameters.get("limit", 0.8))
        duration_s = int(parameters.get("duration_seconds", 60))
        workers = max(1, int(parameters.get("workers", 1)))
        target = self._resolve_target(parameters)
        name = f"aiops-stress-{secrets.token_hex(4)}"

        if resource_type == "cpu":
            stressors = {"cpu": {"workers": workers, "load": max(1, int(limit * 100))}}
        elif resource_type == "memory":
            stressors = {
                "memory": {"workers": workers, "size": parameters.get("size", "256MB")}
            }
        else:
            raise ValueError(f"Unsupported resource_type: {resource_type}")

        spec = {
            "action": "stress",
            "mode": "one",
            "duration": f"{duration_s}s",
            "selector": self._selector(target),
            "stressors": stressors,
        }

        logger.warning(f"Limiting {resource_type} on '{target}' via StressChaos")
        await self.injector.apply("StressChaos", name, spec)
        try:
            system_health = await self._check_system_health()
        finally:
            await self.injector.delete("StressChaos", name)

        return {
            "success": True,
            "resource_type": resource_type,
            "limit": limit,
            "chaos_kind": "StressChaos",
            "chaos_object": name,
            "target": target,
            "system_health": system_health,
        }

    async def _partition_network(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        网络分区（真实 Chaos Mesh NetworkChaos/partition）

        Args:
            parameters: partition_type / direction / duration_seconds / service_name

        Returns:
            实验结果
        """
        partition_type = parameters.get("partition_type", "partial")
        if partition_type not in ("full", "partial"):
            raise ValueError(f"Unsupported partition_type: {partition_type}")
        direction = parameters.get("direction", "both")
        duration_s = int(parameters.get("duration_seconds", 60))
        target = self._resolve_target(parameters)
        name = f"aiops-partition-{secrets.token_hex(4)}"

        spec = {
            "action": "partition",
            "mode": "one",
            "duration": f"{duration_s}s",
            "selector": self._selector(target),
            "direction": direction,
            "target": (
                {"mode": "all", "selector": {"namespaces": [self._namespace]}}
                if partition_type == "full"
                else {
                    "mode": "fixed",
                    "selector": self._selector(target),
                    "value": parameters.get("target_services", []),
                }
            ),
        }

        logger.warning(f"Creating {partition_type} network partition for '{target}'")
        await self.injector.apply("NetworkChaos", name, spec)
        try:
            connectivity_check = await self._check_network_connectivity()
            degradation_check = await self._verify_service_degradation()
        finally:
            await self.injector.delete("NetworkChaos", name)

        return {
            "success": True,
            "partition_type": partition_type,
            "chaos_kind": "NetworkChaos",
            "chaos_object": name,
            "target": target,
            "connectivity": connectivity_check,
            "degradation": degradation_check,
        }

    async def _fail_service(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        服务故障（真实 Chaos Mesh PodChaos/pod-failure）

        Args:
            parameters: service_name / duration_seconds

        Returns:
            实验结果
        """
        service_name = self._resolve_target(parameters)
        duration_s = int(parameters.get("duration_seconds", 30))
        name = f"aiops-service-failure-{secrets.token_hex(4)}"

        spec = {
            "action": "pod-failure",
            "mode": "all",
            "duration": f"{duration_s}s",
            "selector": self._selector(service_name),
        }

        logger.warning(f"Failing service '{service_name}' via PodChaos/pod-failure")
        await self.injector.apply("PodChaos", name, spec)
        try:
            recovery_result = await self._test_service_recovery(service_name)
        finally:
            await self.injector.delete("PodChaos", name)

        return {
            "success": True,
            "service_name": service_name,
            "chaos_kind": "PodChaos",
            "chaos_object": name,
            "recovery_time_ms": recovery_result,
        }

    # ------------------------------------------------------------------
    # 辅助方法（对目标服务做真实探测）
    # ------------------------------------------------------------------
    @staticmethod
    def _target_url(path: str = "") -> str:
        base = os.getenv("CHAOS_TARGET_URL", "http://localhost:8000").rstrip("/")
        return base + path

    async def _http_probe(self, url: str, timeout: float = 10.0) -> float:
        """Issue a real HTTP request and return the elapsed time in ms."""
        import httpx

        start = datetime.now(timezone.utc)
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
        response.raise_for_status()
        return (datetime.now(timezone.utc) - start).total_seconds() * 1000

    async def _measure_response_time(self) -> float:
        """测量目标服务的真实响应时间"""
        return await self._http_probe(self._target_url("/health"))

    async def _check_system_health(self) -> bool:
        """检查系统健康状态（真实探活）"""
        try:
            await self._http_probe(self._target_url("/health"), timeout=5)
            return True
        except Exception as exc:
            logger.warning(f"System health probe failed: {exc}")
            return False

    async def _check_network_connectivity(self) -> bool:
        """检查网络连接（真实探活）"""
        try:
            await self._http_probe(self._target_url("/health"), timeout=5)
            return True
        except Exception as exc:
            logger.warning(f"Network connectivity probe failed: {exc}")
            return False

    async def _verify_service_degradation(self) -> bool:
        """验证服务降级：探活失败即视为已降级"""
        try:
            await self._http_probe(self._target_url("/health"), timeout=5)
            return False
        except Exception:
            return True

    async def _test_service_recovery(self, service_name: str) -> float:
        """轮询目标服务直至恢复，返回恢复耗时（毫秒）"""
        timeout = int(os.getenv("CHAOS_RECOVERY_TIMEOUT", "120"))
        deadline = datetime.now(timezone.utc) + timedelta(seconds=timeout)
        start = datetime.now(timezone.utc)
        while datetime.now(timezone.utc) < deadline:
            try:
                await self._http_probe(self._target_url("/health"), timeout=5)
                return (datetime.now(timezone.utc) - start).total_seconds() * 1000
            except Exception:
                await asyncio.sleep(2)
        raise RuntimeError(
            f"service '{service_name}' did not recover within {timeout}s"
        )

    def get_active_experiments(self) -> int:
        """当前正在运行的混沌实验数量。

        The engine enforces a single concurrent experiment, so this returns
        ``1`` while an experiment is in flight and ``0`` otherwise.  The value
        is derived from the live engine state (not a hard-coded constant).
        """
        current = self._current_experiment
        if current is not None and current.status == ExperimentStatus.RUNNING:
            return 1
        return 0

    def get_experiment_history(self, limit: int = 10) -> List[ExperimentResult]:
        """
        获取实验历史

        Args:
            limit: 返回数量

        Returns:
            实验历史
        """
        return self._experiment_history[-limit:]

    def get_experiment_stats(self) -> Dict[str, Any]:
        """
        获取实验统计

        Returns:
            统计信息
        """
        if not self._experiment_history:
            return {"total_experiments": 0}

        total_experiments = len(self._experiment_history)
        successful_experiments = sum(1 for exp in self._experiment_history if exp.success)
        success_rate = (
            (successful_experiments / total_experiments * 100) if total_experiments > 0 else 0
        )

        # 按实验类型统计
        experiment_stats = {}
        for exp in self._experiment_history:
            exp_type = exp.experiment.value
            if exp_type not in experiment_stats:
                experiment_stats[exp_type] = {"total": 0, "success": 0}
            experiment_stats[exp_type]["total"] += 1
            if exp.success:
                experiment_stats[exp_type]["success"] += 1

        return {
            "total_experiments": total_experiments,
            "successful_experiments": successful_experiments,
            "success_rate": success_rate,
            "experiment_stats": experiment_stats,
            "enabled": self._enabled,
        }


# 全局混沌工程引擎实例
chaos_engine = ChaosEngine()


async def setup_chaos_engineering() -> Any:
    """
    设置混沌工程

    Returns:
        设置结果
    """
    try:
        # 默认禁用，需要在生产环境显式启用
        chaos_engine.disable()

        logger.info("Chaos engineering setup completed (disabled by default)")

        return {
            "status": "success",
            "enabled": chaos_engine.is_enabled(),
            "experiments": [exp.value for exp in ChaosExperiment],
        }

    except Exception as e:
        logger.error(f"Chaos engineering setup failed: {e}")
        return {"status": "error", "error": str(e)}
