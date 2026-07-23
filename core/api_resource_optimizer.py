# -*- coding: utf-8 -*-
"""
API Resource Optimization
Enterprise-grade API resource optimization with monitoring and scheduling
"""

import asyncio
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from loguru import logger


class ResourceType(Enum):
    """Resource type"""

    CPU = "cpu"
    MEMORY = "memory"
    DISK_IO = "disk_io"
    NETWORK_IO = "network_io"
    DATABASE_CONNECTIONS = "database_connections"
    CUSTOM = "custom"


class ResourceLimitType(Enum):
    """Resource limit type"""

    HARD = "hard"
    SOFT = "soft"
    DYNAMIC = "dynamic"


@dataclass
class ResourceUsage:
    """Resource usage data"""

    resource_type: ResourceType
    endpoint: str
    method: str
    current_usage: float
    peak_usage: float
    avg_usage: float
    unit: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceLimit:
    """Resource limit configuration"""

    resource_type: ResourceType
    endpoint: str
    limit_value: float
    limit_type: ResourceLimitType
    unit: str
    action_on_exceed: str = "reject"  # reject, throttle, alert
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ResourceSchedule:
    """Resource schedule configuration"""

    schedule_id: str
    resource_type: ResourceType
    endpoint: str
    start_time: datetime
    end_time: datetime
    max_allocation: float
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


class APIResourceOptimizer:
    """Enterprise-grade API resource optimizer"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize API resource optimizer

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Resource usage history
        self.resource_usage_history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Resource limits
        self.resource_limits: Dict[str, ResourceLimit] = {}

        # Resource schedules
        self.resource_schedules: List[ResourceSchedule] = []

        # Current resource allocations
        self.current_allocations: Dict[str, float] = defaultdict(float)

        # Resource monitoring
        self.resource_metrics: Dict[str, Dict[str, float]] = defaultdict(dict)

        # Configuration
        self.default_cpu_limit = self.config.get("default_cpu_limit", 80.0)
        self.default_memory_limit = self.config.get("default_memory_limit", 80.0)
        self.monitoring_interval_seconds = self.config.get("monitoring_interval_seconds", 5)

        # Statistics
        self.total_resource_checks = 0
        self.total_limit_exceeds = 0
        self.total_schedules_executed = 0

        logger.info("API resource optimizer initialized")

    def track_resource_usage(
        self,
        resource_type: ResourceType,
        endpoint: str,
        method: str,
        usage_value: float,
        unit: str = "percent",
    ) -> None:
        """
        Track resource usage

        Args:
            resource_type: Resource type
            endpoint: API endpoint
            method: HTTP method
            usage_value: Resource usage value
            unit: Usage unit
        """
        key = f"{resource_type.value}:{method}:{endpoint}"

        usage = ResourceUsage(
            resource_type=resource_type,
            endpoint=endpoint,
            method=method,
            current_usage=usage_value,
            peak_usage=usage_value,
            avg_usage=usage_value,
            unit=unit,
        )

        self.resource_usage_history[key].append(usage)

        # Update metrics
        self._update_resource_metrics(key)

        logger.debug(f"Tracked resource usage: {key}, value: {usage_value}{unit}")

    def _update_resource_metrics(self, key: str) -> None:
        """
        Update resource metrics

        Args:
            key: Resource key
        """
        history = self.resource_usage_history[key]

        if not history:
            return

        current_values = [u.current_usage for u in history]

        # Update peak and average
        latest = history[-1]
        latest.peak_usage = max(current_values)
        latest.avg_usage = statistics.mean(current_values)

        # Store in metrics
        self.resource_metrics[key] = {
            "current_usage": latest.current_usage,
            "peak_usage": latest.peak_usage,
            "avg_usage": latest.avg_usage,
            "unit": latest.unit,
            "last_updated": latest.timestamp,
        }

    def set_resource_limit(
        self,
        resource_type: ResourceType,
        endpoint: str,
        limit_value: float,
        limit_type: ResourceLimitType = ResourceLimitType.SOFT,
        unit: str = "percent",
        action_on_exceed: str = "reject",
    ) -> None:
        """
        Set resource limit

        Args:
            resource_type: Resource type
            endpoint: API endpoint
            limit_value: Limit value
            limit_type: Limit type
            unit: Unit
            action_on_exceed: Action when limit exceeded
        """
        key = f"{resource_type.value}:{endpoint}"

        self.resource_limits[key] = ResourceLimit(
            resource_type=resource_type,
            endpoint=endpoint,
            limit_value=limit_value,
            limit_type=limit_type,
            unit=unit,
            action_on_exceed=action_on_exceed,
        )

        logger.info(f"Set resource limit for {key}: {limit_value}{unit} ({limit_type})")

    def check_resource_limit(
        self, resource_type: ResourceType, endpoint: str, method: str
    ) -> Dict[str, Any]:
        """
        Check if resource limit is exceeded

        Args:
            resource_type: Resource type
            endpoint: API endpoint
            method: HTTP method

        Returns:
            Check result
        """
        key = f"{resource_type.value}:{method}:{endpoint}"
        limit_key = f"{resource_type.value}:{endpoint}"

        self.total_resource_checks += 1

        # Get current usage
        metrics = self.resource_metrics.get(key)
        if not metrics:
            return {"allowed": True, "reason": "No metrics available"}

        current_usage = metrics["current_usage"]

        # Check limit
        if limit_key not in self.resource_limits:
            return {"allowed": True, "reason": "No limit configured"}

        limit = self.resource_limits[limit_key]

        if current_usage > limit.limit_value:
            self.total_limit_exceeds += 1

            if limit.action_on_exceed == "reject":
                return {
                    "allowed": False,
                    "reason": "Resource limit exceeded",
                    "current_usage": current_usage,
                    "limit": limit.limit_value,
                    "action": "reject",
                }
            elif limit.action_on_exceed == "throttle":
                return {
                    "allowed": True,
                    "reason": "Resource limit exceeded - throttling",
                    "current_usage": current_usage,
                    "limit": limit.limit_value,
                    "action": "throttle",
                }
            else:  # alert
                return {
                    "allowed": True,
                    "reason": "Resource limit exceeded - alert only",
                    "current_usage": current_usage,
                    "limit": limit.limit_value,
                    "action": "alert",
                }

        return {"allowed": True, "reason": "Within limits"}

    def allocate_resource(self, resource_type: ResourceType, endpoint: str, amount: float) -> bool:
        """
        Allocate resource to endpoint

        Args:
            resource_type: Resource type
            endpoint: API endpoint
            amount: Amount to allocate

        Returns:
            True if allocation successful
        """
        key = f"{resource_type.value}:{endpoint}"
        limit_key = f"{resource_type.value}:{endpoint}"

        # Check limit
        if limit_key in self.resource_limits:
            limit = self.resource_limits[limit_key]
            current_allocation = self.current_allocations[key]

            if current_allocation + amount > limit.limit_value:
                logger.warning(f"Cannot allocate resource: would exceed limit for {key}")
                return False

        self.current_allocations[key] += amount
        logger.debug(f"Allocated {amount} to {key}")

        return True

    def release_resource(self, resource_type: ResourceType, endpoint: str, amount: float) -> None:
        """
        Release resource from endpoint

        Args:
            resource_type: Resource type
            endpoint: API endpoint
            amount: Amount to release
        """
        key = f"{resource_type.value}:{endpoint}"

        if key in self.current_allocations:
            self.current_allocations[key] = max(0, self.current_allocations[key] - amount)
            logger.debug(f"Released {amount} from {key}")

    def add_resource_schedule(
        self,
        resource_type: ResourceType,
        endpoint: str,
        start_time: datetime,
        end_time: datetime,
        max_allocation: float,
        priority: int = 0,
    ) -> None:
        """
        Add resource schedule

        Args:
            resource_type: Resource type
            endpoint: API endpoint
            start_time: Schedule start time
            end_time: Schedule end time
            max_allocation: Maximum allocation
            priority: Schedule priority
        """
        schedule_id = (
            f"{resource_type.value}_{endpoint}_"
            f"{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S_%f')}"
        )

        schedule = ResourceSchedule(
            schedule_id=schedule_id,
            resource_type=resource_type,
            endpoint=endpoint,
            start_time=start_time,
            end_time=end_time,
            max_allocation=max_allocation,
            priority=priority,
        )

        self.resource_schedules.append(schedule)
        logger.info(f"Added resource schedule: {schedule_id}")

    def execute_schedules(self) -> int:
        """
        Execute active resource schedules

        Returns:
            Number of schedules executed
        """
        now = datetime.now(timezone.utc)
        executed = 0

        # Sort by priority
        active_schedules = [s for s in self.resource_schedules if s.start_time <= now <= s.end_time]
        active_schedules.sort(key=lambda x: x.priority, reverse=True)

        for schedule in active_schedules:
            # Check if schedule has already been executed
            if (
                "last_executed" in schedule.metadata
                and schedule.metadata["last_executed"] == now.date()
            ):
                continue

            # Allocate resource
            if self.allocate_resource(
                schedule.resource_type, schedule.endpoint, schedule.max_allocation
            ):
                schedule.metadata["last_executed"] = now.date()
                executed += 1
                self.total_schedules_executed += 1

        return executed

    def get_resource_usage(
        self, resource_type: ResourceType, endpoint: str, method: str
    ) -> Optional[Dict[str, float]]:
        """
        Get resource usage metrics

        Args:
            resource_type: Resource type
            endpoint: API endpoint
            method: HTTP method

        Returns:
            Resource metrics or None
        """
        key = f"{resource_type.value}:{method}:{endpoint}"
        return self.resource_metrics.get(key)

    def get_all_resource_usage(self) -> Dict[str, Dict[str, float]]:
        """Get all resource usage metrics"""
        return self.resource_metrics.copy()

    def optimize_resource_allocation(self, resource_type: ResourceType) -> Dict[str, Any]:
        """
        Optimize resource allocation based on usage patterns

        Args:
            resource_type: Resource type

        Returns:
            Optimization recommendations
        """
        # Get all usage for resource type
        resource_usages = [
            (key, metrics)
            for key, metrics in self.resource_metrics.items()
            if key.startswith(resource_type.value)
        ]

        if not resource_usages:
            return {"error": "No usage data available"}

        recommendations = []

        for key, metrics in resource_usages:
            # Check for over-allocation
            if metrics["avg_usage"] < metrics["peak_usage"] * 0.5:
                recommendations.append(
                    {
                        "endpoint": key,
                        "type": "reduce_allocation",
                        "reason": "Average usage significantly below peak",
                        "current_allocation": metrics["peak_usage"],
                        "recommended_allocation": metrics["avg_usage"] * 1.2,
                    }
                )

            # Check for under-allocation
            elif metrics["avg_usage"] > metrics["peak_usage"] * 0.9:
                recommendations.append(
                    {
                        "endpoint": key,
                        "type": "increase_allocation",
                        "reason": "Average usage close to peak",
                        "current_allocation": metrics["peak_usage"],
                        "recommended_allocation": metrics["peak_usage"] * 1.5,
                    }
                )

        return {
            "resource_type": resource_type.value,
            "total_endpoints": len(resource_usages),
            "recommendations": recommendations,
        }

    def monitor_resources(self) -> Dict[str, Any]:
        """
        Monitor all resources and return status

        Returns:
            Resource monitoring status
        """
        status: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resources": {},
        }

        for key, metrics in self.resource_metrics.items():
            resource_type, method, endpoint = key.split(":", 2)

            # Check limit
            limit_check = self.check_resource_limit(ResourceType(resource_type), endpoint, method)

            status["resources"][key] = {
                "current_usage": metrics["current_usage"],
                "peak_usage": metrics["peak_usage"],
                "avg_usage": metrics["avg_usage"],
                "unit": metrics["unit"],
                "limit_check": limit_check,
            }

        return status

    async def start_monitoring(self) -> None:
        """Start automatic resource monitoring"""

        async def monitoring_loop():
            while True:
                try:
                    # Execute schedules
                    self.execute_schedules()

                    # Monitor resources
                    self.monitor_resources()

                    await asyncio.sleep(self.monitoring_interval_seconds)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Resource monitoring error: {e}")
                    await asyncio.sleep(self.monitoring_interval_seconds)

        asyncio.create_task(monitoring_loop())
        logger.info("Automatic resource monitoring started")

    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics"""
        return {
            "total_resource_checks": self.total_resource_checks,
            "total_limit_exceeds": self.total_limit_exceeds,
            "total_schedules_executed": self.total_schedules_executed,
            "total_resource_limits": len(self.resource_limits),
            "total_resource_schedules": len(self.resource_schedules),
            "total_allocations": len(self.current_allocations),
        }


def get_api_resource_optimizer(config: Optional[Dict[str, Any]] = None) -> APIResourceOptimizer:
    """
    Factory function to get API resource optimizer instance

    Args:
        config: Optional configuration dictionary

    Returns:
        APIResourceOptimizer: Optimizer instance
    """
    return APIResourceOptimizer(config)
