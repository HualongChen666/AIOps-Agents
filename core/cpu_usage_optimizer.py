# -*- coding: utf-8 -*-
"""
CPU Usage Optimization
Enterprise-grade CPU usage optimization with monitoring and scheduling
"""

import asyncio
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import psutil
from loguru import logger


class CPUEventType(Enum):
    """CPU event type"""

    SPIKE_DETECTED = "spike_detected"
    HIGH_USAGE_DETECTED = "high_usage_detected"
    LIMIT_EXCEEDED = "limit_exceeded"
    OPTIMIZATION_APPLIED = "optimization_applied"


class CPUOptimizationAction(Enum):
    """CPU optimization action"""

    REDUCE_PRIORITY = "reduce_priority"
    THROTTLE_PROCESSES = "throttle_processes"
    DISTRIBUTE_LOAD = "distribute_load"
    SCALE_WORKERS = "scale_workers"
    ALERT_ONLY = "alert_only"


@dataclass
class CPUSnapshot:
    """CPU snapshot data"""

    snapshot_id: str
    timestamp: datetime
    cpu_percent: float
    cpu_count: int
    per_cpu_percent: List[float]
    load_average: List[float]
    process_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CPULimit:
    """CPU limit configuration"""

    component: str
    max_cpu_percent: float
    warning_threshold_percent: float = 80.0
    critical_threshold_percent: float = 95.0
    action_on_exceed: CPUOptimizationAction = CPUOptimizationAction.REDUCE_PRIORITY
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskPriority:
    """Task priority configuration"""

    task_id: str
    component: str
    priority: int  # 0-100, higher = higher priority
    cpu_affinity: Optional[List[int]] = None
    nice_value: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class CPUUsageOptimizer:
    """Enterprise-grade CPU usage optimizer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CPU usage optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # CPU snapshots history
        self.cpu_snapshots: deque = deque(maxlen=1000)

        # CPU limits
        self.cpu_limits: Dict[str, CPULimit] = {}

        # Task priorities
        self.task_priorities: Dict[str, TaskPriority] = {}

        # CPU event history
        self.cpu_events: deque = deque(maxlen=10000)

        # Component CPU tracking
        self.component_cpu: Dict[str, float] = defaultdict(float)

        # Configuration
        self.monitoring_interval_seconds = self.config.get("monitoring_interval_seconds", 5)
        self.spike_threshold_percent = self.config.get("spike_threshold_percent", 20.0)
        self.high_usage_threshold_percent = self.config.get("high_usage_threshold_percent", 80.0)

        # Statistics
        self.total_optimizations_applied = 0
        self.total_spike_detections = 0
        self.total_high_usage_detections = 0

        logger.info("CPU usage optimizer initialized")

    def take_cpu_snapshot(self, component: str = "system") -> CPUSnapshot:
        """
        Take CPU snapshot

        Args:
            component: Component name

        Returns:
            CPU snapshot
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        per_cpu_percent = psutil.cpu_percent(percpu=True)

        # Get load average (Linux/Unix only)
        try:
            load_avg = list(psutil.getloadavg())
        except (AttributeError, OSError):
            load_avg = [0.0, 0.0, 0.0]

        # Get process count
        process_count = len(psutil.pids())

        snapshot = CPUSnapshot(
            snapshot_id=(
                f"snapshot_{component}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
            ),
            timestamp=datetime.now(timezone.utc),
            cpu_percent=cpu_percent,
            cpu_count=cpu_count,
            per_cpu_percent=per_cpu_percent,
            load_average=load_avg,
            process_count=process_count,
            metadata={"component": component},
        )

        self.cpu_snapshots.append(snapshot)
        self.component_cpu[component] = cpu_percent

        logger.debug(f"CPU snapshot taken for {component}: {cpu_percent:.2f}%")

        return snapshot

    def set_cpu_limit(
        self,
        component: str,
        max_cpu_percent: float,
        warning_threshold_percent: float = 80.0,
        critical_threshold_percent: float = 95.0,
        action_on_exceed: CPUOptimizationAction = CPUOptimizationAction.REDUCE_PRIORITY,
    ) -> None:
        """
        Set CPU limit for component

        Args:
            component: Component name
            max_cpu_percent: Maximum CPU percentage
            warning_threshold_percent: Warning threshold percentage
            critical_threshold_percent: Critical threshold percentage
            action_on_exceed: Action when limit exceeded
        """
        self.cpu_limits[component] = CPULimit(
            component=component,
            max_cpu_percent=max_cpu_percent,
            warning_threshold_percent=warning_threshold_percent,
            critical_threshold_percent=critical_threshold_percent,
            action_on_exceed=action_on_exceed,
        )

        logger.info(f"Set CPU limit for {component}: {max_cpu_percent}%")

    def check_cpu_limit(self, component: str) -> Dict[str, Any]:
        """
        Check if component exceeds CPU limit

        Args:
            component: Component name

        Returns:
            Check result
        """
        if component not in self.cpu_limits:
            return {"status": "no_limit"}

        limit = self.cpu_limits[component]
        current_cpu = self.component_cpu.get(component, 0)

        usage_percent = (current_cpu / limit.max_cpu_percent) * 100

        if usage_percent >= limit.critical_threshold_percent:
            return {
                "status": "critical",
                "component": component,
                "current_cpu_percent": current_cpu,
                "max_cpu_percent": limit.max_cpu_percent,
                "usage_percent": usage_percent,
                "action": limit.action_on_exceed.value,
                "message": f"Critical CPU usage: {usage_percent:.2f}%",
            }
        elif usage_percent >= limit.warning_threshold_percent:
            return {
                "status": "warning",
                "component": component,
                "current_cpu_percent": current_cpu,
                "max_cpu_percent": limit.max_cpu_percent,
                "usage_percent": usage_percent,
                "action": limit.action_on_exceed.value,
                "message": f"Warning CPU usage: {usage_percent:.2f}%",
            }
        else:
            return {
                "status": "normal",
                "component": component,
                "current_cpu_percent": current_cpu,
                "max_cpu_percent": limit.max_cpu_percent,
                "usage_percent": usage_percent,
                "message": "CPU usage within limits",
            }

    def detect_cpu_spike(self, component: str = "system") -> bool:
        """
        Detect CPU spike

        Args:
            component: Component name

        Returns:
            True if spike detected
        """
        # Get recent snapshots
        recent_snapshots = [
            s
            for s in self.cpu_snapshots
            if s.metadata.get("component", "system") == component
            and (datetime.now(timezone.utc) - s.timestamp).total_seconds() <= 60  # Last minute
        ]

        if len(recent_snapshots) < 5:
            return False

        cpu_values = [s.cpu_percent for s in recent_snapshots]

        # Calculate average of first half and second half
        mid_point = len(cpu_values) // 2
        first_half_avg = statistics.mean(cpu_values[:mid_point])
        second_half_avg = statistics.mean(cpu_values[mid_point:])

        # Check if there's a significant increase
        spike_detected: bool = (second_half_avg - first_half_avg) > self.spike_threshold_percent

        if spike_detected:
            self.total_spike_detections += 1

            # Log event
            self.cpu_events.append(
                {
                    "event_type": CPUEventType.SPIKE_DETECTED.value,
                    "timestamp": datetime.now(timezone.utc),
                    "component": component,
                    "before_avg": first_half_avg,
                    "after_avg": second_half_avg,
                    "spike_size": second_half_avg - first_half_avg,
                }
            )

            logger.warning(
                f"CPU spike detected in {component}: {first_half_avg:.2f}% -> {second_half_avg:.2f}%"  # noqa: E501
            )

        return spike_detected

    def detect_high_usage(self, component: str = "system") -> bool:
        """
        Detect high CPU usage

        Args:
            component: Component name

        Returns:
            True if high usage detected
        """
        current_cpu = self.component_cpu.get(component, 0)

        high_usage_detected: bool = current_cpu > self.high_usage_threshold_percent

        if high_usage_detected:
            self.total_high_usage_detections += 1

            # Log event
            self.cpu_events.append(
                {
                    "event_type": CPUEventType.HIGH_USAGE_DETECTED.value,
                    "timestamp": datetime.now(timezone.utc),
                    "component": component,
                    "cpu_percent": current_cpu,
                }
            )

            logger.warning(f"High CPU usage detected in {component}: {current_cpu:.2f}%")

        return high_usage_detected

    def set_task_priority(
        self,
        task_id: str,
        component: str,
        priority: int,
        cpu_affinity: Optional[List[int]] = None,
        nice_value: int = 0,
    ) -> None:
        """
        Set task priority

        Args:
            task_id: Task ID
            component: Component name
            priority: Priority (0-100)
            cpu_affinity: CPU affinity (list of CPU cores)
            nice_value: Nice value for process priority
        """
        self.task_priorities[task_id] = TaskPriority(
            task_id=task_id,
            component=component,
            priority=priority,
            cpu_affinity=cpu_affinity,
            nice_value=nice_value,
        )

        logger.info(f"Set task priority for {task_id}: {priority}")

    def get_task_priority(self, task_id: str) -> Optional[TaskPriority]:
        """
        Get task priority

        Args:
            task_id: Task ID

        Returns:
            Task priority or None
        """
        return self.task_priorities.get(task_id)

    def optimize_cpu(self, component: str) -> Dict[str, Any]:
        """
        Optimize CPU usage for component

        Args:
            component: Component name

        Returns:
            Optimization result
        """
        result: Dict[str, Any] = {
            "component": component,
            "actions_taken": [],
            "optimization_details": [],
        }

        # Check CPU limit
        limit_check = self.check_cpu_limit(component)

        if limit_check["status"] in ["warning", "critical"]:
            limit = self.cpu_limits.get(component)
            if limit:
                action = limit.action_on_exceed

                if action == CPUOptimizationAction.REDUCE_PRIORITY:
                    result["actions_taken"].append("reduce_priority")
                    detail = self._apply_reduce_priority(component)
                    result["optimization_details"].append(detail)
                    if detail["applied"]:
                        self.total_optimizations_applied += 1

                elif action == CPUOptimizationAction.THROTTLE_PROCESSES:
                    result["actions_taken"].append("throttle_processes")
                    detail = self._apply_throttle_processes(component)
                    result["optimization_details"].append(detail)
                    if detail["applied"]:
                        self.total_optimizations_applied += 1

                elif action == CPUOptimizationAction.DISTRIBUTE_LOAD:
                    result["actions_taken"].append("distribute_load")
                    detail = self._apply_distribute_load(component)
                    result["optimization_details"].append(detail)
                    if detail["applied"]:
                        self.total_optimizations_applied += 1

                elif action == CPUOptimizationAction.SCALE_WORKERS:
                    result["actions_taken"].append("scale_workers")
                    detail = self._apply_scale_workers(component)
                    result["optimization_details"].append(detail)
                    if detail["applied"]:
                        self.total_optimizations_applied += 1

                # Log event
                self.cpu_events.append(
                    {
                        "event_type": CPUEventType.OPTIMIZATION_APPLIED.value,
                        "timestamp": datetime.now(timezone.utc),
                        "component": component,
                        "action": action.value,
                    }
                )

        return result

    # -- 真实系统级动作实现 ------------------------------------------------
    def _target_processes(self, component: str) -> List[psutil.Process]:
        """解析组件对应的目标进程。

        通过 ``component_processes`` 配置映射到具体 PID；未配置时作用于
        当前进程（AIOps 服务自优化），而不是仅仅记账。
        """
        processes: List[psutil.Process] = []
        pid_map = self.config.get("component_processes") or {}
        for pid in pid_map.get(component, []) if isinstance(pid_map, dict) else []:
            try:
                processes.append(psutil.Process(int(pid)))
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Invalid target pid {pid} for {component}: {e}")
        if not processes:
            processes.append(psutil.Process())
        return processes

    def _apply_reduce_priority(self, component: str) -> Dict[str, Any]:
        """降低目标进程调度优先级（真实调用 ``nice``）。"""
        step = int(self.config.get("priority_step", 5))
        applied_nice: Dict[str, int] = {}
        try:
            for proc in self._target_processes(component):
                current = proc.nice()
                new_nice = min(19, current + step)
                proc.nice(new_nice)
                applied_nice[str(proc.pid)] = proc.nice()
            return {
                "action": "reduce_priority",
                "description": "Lowered OS scheduling priority of target processes",
                "applied": bool(applied_nice),
                "nice_values": applied_nice,
            }
        except Exception as e:  # noqa: BLE001 - 权限不足等
            logger.warning(f"reduce_priority failed for {component}: {e}")
            return {
                "action": "reduce_priority",
                "description": "Failed to change OS scheduling priority",
                "applied": False,
                "error": str(e),
            }

    def _apply_throttle_processes(self, component: str) -> Dict[str, Any]:
        """把目标进程绑定到单个 CPU 以减少其可用的 CPU 资源（真实 ``cpu_affinity``）。"""
        cpus = list(range(psutil.cpu_count() or 1))
        applied: Dict[str, List[int]] = {}
        try:
            for proc in self._target_processes(component):
                proc.cpu_affinity([cpus[0]])
                applied[str(proc.pid)] = proc.cpu_affinity()
            return {
                "action": "throttle_processes",
                "description": "Restricted target processes to a single CPU",
                "applied": bool(applied),
                "cpu_affinity": applied,
            }
        except Exception as e:  # noqa: BLE001
            logger.warning(f"throttle_processes failed for {component}: {e}")
            return {
                "action": "throttle_processes",
                "description": "Failed to restrict CPU affinity",
                "applied": False,
                "error": str(e),
            }

    def _apply_distribute_load(self, component: str) -> Dict[str, Any]:
        """放开目标进程到全部 CPU，让调度器均衡分配负载。"""
        cpus = list(range(psutil.cpu_count() or 1))
        applied: Dict[str, List[int]] = {}
        try:
            for proc in self._target_processes(component):
                proc.cpu_affinity(cpus)
                applied[str(proc.pid)] = proc.cpu_affinity()
            return {
                "action": "distribute_load",
                "description": "Spread target processes across all available CPUs",
                "applied": bool(applied),
                "cpu_affinity": applied,
            }
        except Exception as e:  # noqa: BLE001
            logger.warning(f"distribute_load failed for {component}: {e}")
            return {
                "action": "distribute_load",
                "description": "Failed to adjust CPU affinity",
                "applied": False,
                "error": str(e),
            }

    def _apply_scale_workers(self, component: str) -> Dict[str, Any]:
        """按当前 CPU 余量调整已注册的 worker 池大小。

        仅当配置中提供了具备 ``resize`` 的 ``worker_pool`` 时才执行，否则如实
        报告未应用（不虚构伸缩结果）。
        """
        pool = self.config.get("worker_pool")
        if pool is None or not hasattr(pool, "resize"):
            return {
                "action": "scale_workers",
                "description": "No configurable worker pool registered (worker_pool)",
                "applied": False,
            }
        try:
            cpu_count = psutil.cpu_count() or 1
            load = self.component_cpu.get(component, 0.0) / 100.0
            target = max(1, min(cpu_count, int(round(cpu_count * (1.0 - load))) or 1))
            pool.resize(target)
            return {
                "action": "scale_workers",
                "description": f"Resized worker pool to {target}",
                "applied": True,
                "worker_count": target,
            }
        except Exception as e:  # noqa: BLE001
            logger.warning(f"scale_workers failed for {component}: {e}")
            return {
                "action": "scale_workers",
                "description": "Failed to resize worker pool",
                "applied": False,
                "error": str(e),
            }

    def get_cpu_statistics(self) -> Dict[str, Any]:
        """Get CPU statistics"""
        if self.cpu_snapshots:
            latest_snapshot = self.cpu_snapshots[-1]
        else:
            latest_snapshot = self.take_cpu_snapshot()

        # Calculate statistics from recent snapshots
        recent_snapshots = [
            s
            for s in self.cpu_snapshots
            if (datetime.now(timezone.utc) - s.timestamp).total_seconds() <= 300  # Last 5 minutes
        ]

        if recent_snapshots:
            cpu_values = [s.cpu_percent for s in recent_snapshots]
            avg_cpu = statistics.mean(cpu_values)
            max_cpu = max(cpu_values)
            min_cpu = min(cpu_values)
        else:
            avg_cpu = latest_snapshot.cpu_percent
            max_cpu = latest_snapshot.cpu_percent
            min_cpu = latest_snapshot.cpu_percent

        return {
            "current_cpu_percent": latest_snapshot.cpu_percent,
            "cpu_count": latest_snapshot.cpu_count,
            "per_cpu_percent": latest_snapshot.per_cpu_percent,
            "load_average": latest_snapshot.load_average,
            "process_count": latest_snapshot.process_count,
            "avg_cpu_percent": avg_cpu,
            "max_cpu_percent": max_cpu,
            "min_cpu_percent": min_cpu,
            "total_optimizations_applied": self.total_optimizations_applied,
            "total_spike_detections": self.total_spike_detections,
            "total_high_usage_detections": self.total_high_usage_detections,
        }

    def get_component_cpu(self, component: str) -> Optional[float]:
        """
        Get component CPU usage

        Args:
            component: Component name

        Returns:
            CPU usage percentage or None
        """
        return self.component_cpu.get(component)

    def get_cpu_efficiency(self, component: str = "system") -> Dict[str, Any]:
        """
        Calculate CPU efficiency metrics

        Args:
            component: Component name

        Returns:
            CPU efficiency metrics
        """
        recent_snapshots = [
            s
            for s in self.cpu_snapshots
            if s.metadata.get("component", "system") == component
            and (datetime.now(timezone.utc) - s.timestamp).total_seconds() <= 3600  # Last hour
        ]

        if len(recent_snapshots) < 10:
            return {"error": "Insufficient data"}

        cpu_values = [s.cpu_percent for s in recent_snapshots]

        # Calculate efficiency metrics
        avg_cpu = statistics.mean(cpu_values)
        std_dev = statistics.stdev(cpu_values) if len(cpu_values) > 1 else 0
        coefficient_of_variation = (std_dev / avg_cpu) if avg_cpu > 0 else 0

        # CPU utilization efficiency (ideal is 70-80%)
        if 70 <= avg_cpu <= 80:
            efficiency = "optimal"
        elif avg_cpu > 80:
            efficiency = "overutilized"
        elif avg_cpu < 50:
            efficiency = "underutilized"
        else:
            efficiency = "acceptable"

        return {
            "component": component,
            "avg_cpu_percent": avg_cpu,
            "std_dev_percent": std_dev,
            "coefficient_of_variation": coefficient_of_variation,
            "efficiency": efficiency,
            "utilization_score": (
                min(100, (avg_cpu / 80) * 100)
                if avg_cpu <= 80
                else 100 - ((avg_cpu - 80) / 20) * 100
            ),
        }

    async def start_monitoring(self) -> None:
        """Start automatic CPU monitoring"""

        async def monitoring_loop():
            while True:
                try:
                    # Take snapshot
                    self.take_cpu_snapshot()

                    # Check all component limits
                    for component in list(self.component_cpu.keys()):
                        limit_check = self.check_cpu_limit(component)

                        if limit_check["status"] in ["warning", "critical"]:
                            # Optimize CPU
                            self.optimize_cpu(component)

                    # Detect spikes and high usage
                    self.detect_cpu_spike()
                    self.detect_high_usage()

                    await asyncio.sleep(self.monitoring_interval_seconds)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"CPU monitoring error: {e}")
                    await asyncio.sleep(self.monitoring_interval_seconds)

        asyncio.create_task(monitoring_loop())
        logger.info("Automatic CPU monitoring started")

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        return {
            "total_optimizations_applied": self.total_optimizations_applied,
            "total_spike_detections": self.total_spike_detections,
            "total_high_usage_detections": self.total_high_usage_detections,
            "total_cpu_limits": len(self.cpu_limits),
            "total_task_priorities": len(self.task_priorities),
            "total_snapshots": len(self.cpu_snapshots),
            "components_tracked": len(self.component_cpu),
        }


def get_cpu_usage_optimizer(config: Optional[Dict[str, Any]] = None) -> CPUUsageOptimizer:
    """
    Factory function to get CPU usage optimizer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        CPUUsageOptimizer: Optimizer instance
    """
    return CPUUsageOptimizer(config)
