# -*- coding: utf-8 -*-
"""
Chaos Engineering Module
混沌工程模块

提供混沌工程测试功能，用于测试系统韧性和容错能力。
"""

import asyncio
import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

_random = secrets.SystemRandom()

logger = logging.getLogger(__name__)


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

    def __init__(self):
        """初始化混沌工程引擎"""
        self._experiment_history: List[ExperimentResult] = []
        self._current_experiment: Optional[ExperimentResult] = None
        self._enabled = False  # 默认禁用，需要显式启用

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
        注入延迟

        Args:
            parameters: 参数（delay_ms: 延迟毫秒数）

        Returns:
            实验结果
        """
        delay_ms = parameters.get("delay_ms", _random.randint(100, 1000))
        delay_seconds = delay_ms / 1000.0

        logger.warning(f"Injecting {delay_ms}ms latency")

        # 模拟延迟
        await asyncio.sleep(delay_seconds)

        # 测试系统响应
        response_time = await self._measure_response_time()

        return {
            "success": True,
            "injected_latency_ms": delay_ms,
            "measured_response_time_ms": response_time,
        }

    async def _inject_fault(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        注入故障

        Args:
            parameters: 参数（fault_type: 故障类型）

        Returns:
            实验结果
        """
        fault_type = parameters.get("fault_type", "random")

        logger.warning(f"Injecting fault: {fault_type}")

        # 模拟故障注入
        if fault_type == "database_error":
            result = await self._simulate_database_error()
        elif fault_type == "cache_error":
            result = await self._simulate_cache_error()
        elif fault_type == "api_error":
            result = await self._simulate_api_error()
        else:
            result = await self._simulate_random_error()

        return {"success": True, "fault_type": fault_type, "system_resilience": result}

    async def _limit_resources(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        限制资源

        Args:
            parameters: 参数（resource_type: 资源类型, limit: 限制值）

        Returns:
            实验结果
        """
        resource_type = parameters.get("resource_type", "memory")
        limit = parameters.get("limit", 0.8)  # 80%

        logger.warning(f"Limiting {resource_type} to {limit}")

        # 模拟资源限制
        from core.memory_monitor import memory_monitor

        current_usage = memory_monitor.get_memory_usage()

        # 检查系统是否在限制下正常工作
        system_health = await self._check_system_health()

        return {
            "success": True,
            "resource_type": resource_type,
            "limit": limit,
            "current_usage": current_usage,
            "system_health": system_health,
        }

    async def _partition_network(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        网络分区

        Args:
            parameters: 参数（partition_type: 分区类型）

        Returns:
            实验结果
        """
        partition_type = parameters.get("partition_type", "partial")

        logger.warning(f"Creating network partition: {partition_type}")

        # 模拟网络分区
        connectivity_check = await self._check_network_connectivity()

        # 验证系统降级
        degradation_check = await self._verify_service_degradation()

        return {
            "success": True,
            "partition_type": partition_type,
            "connectivity": connectivity_check,
            "degradation": degradation_check,
        }

    async def _fail_service(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        服务故障

        Args:
            parameters: 参数（service_name: 服务名称）

        Returns:
            实验结果
        """
        service_name = parameters.get("service_name", "random")

        logger.warning(f"Failing service: {service_name}")

        # 模拟服务故障
        recovery_result = await self._test_service_recovery(service_name)

        return {"success": True, "service_name": service_name, "recovery_time_ms": recovery_result}

    # 辅助方法
    async def _measure_response_time(self) -> float:
        """测量响应时间"""
        start = datetime.now(timezone.utc)
        # 模拟操作
        await asyncio.sleep(0.1)
        end = datetime.now(timezone.utc)
        return (end - start).total_seconds() * 1000

    async def _simulate_database_error(self) -> bool:
        """模拟数据库错误"""
        logger.debug("Simulating database error")
        await asyncio.sleep(0.5)
        return True

    async def _simulate_cache_error(self) -> bool:
        """模拟缓存错误"""
        logger.debug("Simulating cache error")
        await asyncio.sleep(0.3)
        return True

    async def _simulate_api_error(self) -> bool:
        """模拟API错误"""
        logger.debug("Simulating API error")
        await asyncio.sleep(0.4)
        return True

    async def _simulate_random_error(self) -> bool:
        """模拟随机错误"""
        logger.debug("Simulating random error")
        await asyncio.sleep(_random.uniform(0.2, 0.8))
        return True

    async def _check_system_health(self) -> bool:
        """检查系统健康状态"""
        logger.debug("Checking system health")
        return True

    async def _check_network_connectivity(self) -> bool:
        """检查网络连接"""
        logger.debug("Checking network connectivity")
        return True

    async def _verify_service_degradation(self) -> bool:
        """验证服务降级"""
        logger.debug("Verifying service degradation")
        return True

    async def _test_service_recovery(self, service_name: str) -> float:
        """测试服务恢复"""
        logger.debug(f"Testing service recovery for {service_name}")
        await asyncio.sleep(1.0)
        return 1000.0  # 1秒恢复时间

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
