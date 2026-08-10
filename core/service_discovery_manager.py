# -*- coding: utf-8 -*-
"""
Service Discovery Manager
Enterprise-grade service discovery and health management
"""

from loguru import logger
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime, timezone
from dataclasses import dataclass, field
from collections import defaultdict
import asyncio
import secrets

_random = secrets.SystemRandom()


class ServiceStatus(Enum):
    """Service status"""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class LoadBalanceStrategy(Enum):
    """Load balance strategy"""

    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"


@dataclass
class ServiceInstance:
    """Service instance"""

    instance_id: str
    service_name: str
    host: str
    port: int
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    weight: int = 1
    active_connections: int = 0


@dataclass
class HealthCheckConfig:
    """Health check configuration"""

    interval_seconds: int = 30
    timeout_seconds: int = 5
    unhealthy_threshold: int = 3
    healthy_threshold: int = 2
    health_check_path: str = "/health"


class ServiceDiscoveryManager:
    """
    Enterprise-grade service discovery manager
    Provides dynamic service discovery, health checking, and load balancing
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize service discovery manager

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

        # Service registry
        self.services: Dict[str, List[ServiceInstance]] = defaultdict(list)
        self.service_metadata: Dict[str, Dict[str, Any]] = {}

        # Health check configuration
        self.health_check_config = HealthCheckConfig(**self.config.get("health_check", {}))

        # Load balancing
        self.load_balance_strategy = LoadBalanceStrategy(
            self.config.get("load_balance_strategy", "round_robin")
        )
        self.round_robin_index: Dict[str, int] = defaultdict(int)

        # Statistics
        self.total_discoveries = 0
        self.total_health_checks = 0
        self.failed_health_checks = 0

        # Background tasks
        self.health_check_task: Optional[asyncio.Task] = None

        logger.info("Service discovery manager initialized")

    def register_service(
        self,
        service_name: str,
        instance_id: str,
        host: str,
        port: int,
        metadata: Optional[Dict[str, Any]] = None,
        weight: int = 1,
    ) -> ServiceInstance:
        """
        Register service instance

        Args:
            service_name: Service name
            instance_id: Instance ID
            host: Host address
            port: Port number
            metadata: Instance metadata
            weight: Instance weight for load balancing

        Returns:
            Service instance
        """
        instance = ServiceInstance(
            instance_id=instance_id,
            service_name=service_name,
            host=host,
            port=port,
            metadata=metadata or {},
            weight=weight,
        )

        # Check if instance already exists
        existing_instances = [
            inst for inst in self.services[service_name] if inst.instance_id == instance_id
        ]

        if existing_instances:
            # Update existing instance
            existing_instance = existing_instances[0]
            existing_instance.host = host
            existing_instance.port = port
            existing_instance.metadata = metadata or {}
            existing_instance.weight = weight
            logger.info(f"Updated service instance: {service_name}/{instance_id}")
        else:
            # Add new instance
            self.services[service_name].append(instance)
            logger.info(f"Registered service instance: {service_name}/{instance_id}")

        self.total_discoveries += 1

        return instance

    def deregister_service(self, service_name: str, instance_id: str) -> bool:
        """
        Deregister service instance

        Args:
            service_name: Service name
            instance_id: Instance ID

        Returns:
            True if deregistered, False otherwise
        """
        instances = self.services[service_name]
        original_count = len(instances)

        self.services[service_name] = [
            inst for inst in instances if inst.instance_id != instance_id
        ]

        if len(self.services[service_name]) < original_count:
            logger.info(f"Deregistered service instance: {service_name}/{instance_id}")
            return True

        return False

    def discover_service(self, service_name: str) -> List[ServiceInstance]:
        """
        Discover service instances

        Args:
            service_name: Service name

        Returns:
            List of service instances
        """
        instances = self.services.get(service_name, [])

        # Filter by status
        healthy_instances = [inst for inst in instances if inst.status == ServiceStatus.HEALTHY]

        self.total_discoveries += 1

        return healthy_instances

    def get_service_instance(
        self, service_name: str, strategy: Optional[LoadBalanceStrategy] = None
    ) -> Optional[ServiceInstance]:
        """
        Get service instance using load balancing

        Args:
            service_name: Service name
            strategy: Load balance strategy

        Returns:
            Service instance or None
        """
        instances = self.discover_service(service_name)

        if not instances:
            return None

        strategy = strategy or self.load_balance_strategy

        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._round_robin_select(service_name, instances)
        elif strategy == LoadBalanceStrategy.RANDOM:
            return self._random_select(instances)
        elif strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(instances)
        elif strategy == LoadBalanceStrategy.WEIGHTED:
            return self._weighted_select(instances)
        else:
            return self._round_robin_select(service_name, instances)

    def _round_robin_select(
        self, service_name: str, instances: List[ServiceInstance]
    ) -> ServiceInstance:
        """
        Round-robin selection

        Args:
            service_name: Service name
            instances: Service instances

        Returns:
            Selected instance
        """
        index = self.round_robin_index[service_name] % len(instances)
        self.round_robin_index[service_name] += 1
        return instances[index]

    def _random_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """
        Random selection

        Args:
            instances: Service instances

        Returns:
            Selected instance
        """
        return _random.choice(instances)

    def _least_connections_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """
        Least connections selection

        Args:
            instances: Service instances

        Returns:
            Selected instance
        """
        return min(instances, key=lambda x: x.active_connections)

    def _weighted_select(self, instances: List[ServiceInstance]) -> ServiceInstance:
        """
        Weighted selection

        Args:
            instances: Service instances

        Returns:
            Selected instance
        """
        total_weight = sum(inst.weight for inst in instances)
        if total_weight == 0:
            return _random.choice(instances)

        rand = _random.uniform(0, total_weight)
        current = 0

        for inst in instances:
            current += inst.weight
            if current >= rand:
                return inst

        return instances[-1]

    async def health_check(self, instance: ServiceInstance) -> bool:
        """
        Perform health check on instance

        Args:
            instance: Service instance

        Returns:
            True if healthy, False otherwise
        """
        self.total_health_checks += 1

        try:
            # Simulate health check (in real implementation, this would make HTTP/gRPC call)
            await asyncio.sleep(0.1)  # Simulate network delay

            # For demonstration, randomly mark as healthy
            is_healthy = _random.random() > 0.1  # 90% chance of being healthy

            instance.last_health_check = datetime.now(timezone.utc)
            instance.status = ServiceStatus.HEALTHY if is_healthy else ServiceStatus.UNHEALTHY

            if not is_healthy:
                self.failed_health_checks += 1

            return is_healthy

        except Exception as e:
            logger.error(f"Health check failed for {instance.instance_id}: {e}")
            instance.status = ServiceStatus.UNHEALTHY
            self.failed_health_checks += 1
            return False

    async def start_health_check_loop(self) -> None:
        """Start health check loop"""
        logger.info("Starting health check loop")

        while True:
            try:
                for service_name, instances in self.services.items():
                    for instance in instances:
                        await self.health_check(instance)

                await asyncio.sleep(self.health_check_config.interval_seconds)

            except asyncio.CancelledError:
                logger.info("Health check loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(5)

    def get_service_summary(self) -> Dict[str, Any]:
        """
        Get service summary

        Returns:
            Service summary
        """
        total_instances = sum(len(instances) for instances in self.services.values())
        healthy_instances = sum(
            len([inst for inst in instances if inst.status == ServiceStatus.HEALTHY])
            for instances in self.services.values()
        )

        return {
            "total_services": len(self.services),
            "total_instances": total_instances,
            "healthy_instances": healthy_instances,
            "unhealthy_instances": total_instances - healthy_instances,
            "total_discoveries": self.total_discoveries,
            "total_health_checks": self.total_health_checks,
            "failed_health_checks": self.failed_health_checks,
            "health_check_success_rate": (
                (self.total_health_checks - self.failed_health_checks) / self.total_health_checks
                if self.total_health_checks > 0
                else 0.0
            ),
            "load_balance_strategy": self.load_balance_strategy.value,
        }

    def get_service_details(self, service_name: str) -> Dict[str, Any]:
        """
        Get service details

        Args:
            service_name: Service name

        Returns:
            Service details
        """
        instances = self.services.get(service_name, [])

        return {
            "service_name": service_name,
            "instance_count": len(instances),
            "healthy_count": len(
                [inst for inst in instances if inst.status == ServiceStatus.HEALTHY]
            ),
            "unhealthy_count": len(
                [inst for inst in instances if inst.status == ServiceStatus.UNHEALTHY]
            ),
            "instances": [
                {
                    "instance_id": inst.instance_id,
                    "host": inst.host,
                    "port": inst.port,
                    "status": inst.status.value,
                    "weight": inst.weight,
                    "active_connections": inst.active_connections,
                    "last_health_check": (
                        inst.last_health_check.isoformat() if inst.last_health_check else None
                    ),
                }
                for inst in instances
            ],
        }


# Global instance
_service_discovery_manager: Optional[ServiceDiscoveryManager] = None


def get_service_discovery_manager() -> ServiceDiscoveryManager:
    """
    Get the global service discovery manager instance

    Returns:
        ServiceDiscoveryManager instance
    """
    global _service_discovery_manager
    if _service_discovery_manager is None:
        _service_discovery_manager = ServiceDiscoveryManager()
    return _service_discovery_manager
