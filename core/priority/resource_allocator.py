# -*- coding: utf-8 -*-
"""
Resource Allocator
Optimizes resource allocation based on priority
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from loguru import logger


@dataclass
class Resource:
    """
    Resource definition

    Attributes:
        id: Resource identifier
        type: Resource type (cpu, memory, etc.)
        capacity: Total capacity
        available: Available capacity
        allocated: Allocated capacity
    """

    id: str
    type: str
    capacity: float
    available: float
    allocated: float = 0.0


@dataclass
class ResourceAllocation:
    """
    Resource allocation result

    Attributes:
        task_id: Task identifier
        resource_id: Resource identifier
        amount: Allocated amount
        priority: Task priority
    """

    task_id: str
    resource_id: str
    amount: float
    priority: float


class ResourceAllocator:
    """
    Resource allocator for priority-based allocation

    Allocates resources to tasks based on priority and availability
    """

    def __init__(self):
        """Initialize resource allocator"""
        self.resources: Dict[str, Resource] = {}
        self.allocations: List[ResourceAllocation] = []

    def add_resource(self, resource: Resource) -> None:
        """
        Add resource to pool

        Args:
            resource: Resource to add
        """
        self.resources[resource.id] = resource
        logger.info(
            f"Added resource {resource.id} (type: {resource.type}, capacity: {resource.capacity})"
        )

    def allocate(self, tasks: List[Dict], resource_type: str) -> List[ResourceAllocation]:
        """
        Allocate resources to tasks based on priority

        Args:
            tasks: List of tasks with priority scores
            resource_type: Type of resource to allocate

        Returns:
            List of resource allocations
        """
        # Filter resources by type
        available_resources = [
            r for r in self.resources.values() if r.type == resource_type and r.available > 0
        ]

        if not available_resources:
            logger.warning(f"No available resources of type {resource_type}")
            return []

        # Sort tasks by priority (descending)
        sorted_tasks = sorted(tasks, key=lambda t: t.get("priority", 0), reverse=True)

        allocations = []

        for task in sorted_tasks:
            required = task.get("resource_requirement", {}).get(resource_type, 0)
            priority = task.get("priority", 0)

            if required == 0:
                continue

            # Find resource with sufficient capacity
            for resource in available_resources:
                if resource.available >= required:
                    # Allocate
                    resource.available -= required
                    resource.allocated += required

                    allocation = ResourceAllocation(
                        task_id=task.get("id", "unknown"),
                        resource_id=resource.id,
                        amount=required,
                        priority=priority,
                    )
                    allocations.append(allocation)

                    logger.info(
                        f"Allocated {required} {resource_type} from {resource.id} "
                        f"to task {task.get('id')} (priority: {priority})"
                    )

                    break

        self.allocations.extend(allocations)

        return allocations

    def release(self, task_id: str) -> None:
        """
        Release resources allocated to a task

        Args:
            task_id: Task identifier
        """
        # Find allocations for this task
        task_allocations = [a for a in self.allocations if a.task_id == task_id]

        for allocation in task_allocations:
            resource = self.resources.get(allocation.resource_id)
            if resource:
                resource.available += allocation.amount
                resource.allocated -= allocation.amount
                logger.info(f"Released {allocation.amount} from {resource.id}")

        # Remove allocations
        self.allocations = [a for a in self.allocations if a.task_id != task_id]

    def get_utilization(self, resource_id: Optional[str] = None) -> Dict:
        """
        Get resource utilization

        Args:
            resource_id: Specific resource ID (optional)

        Returns:
            Utilization statistics
        """
        if resource_id:
            resource = self.resources.get(resource_id)
            if resource:
                utilization = resource.allocated / resource.capacity if resource.capacity > 0 else 0
                return {
                    "resource_id": resource_id,
                    "capacity": resource.capacity,
                    "allocated": resource.allocated,
                    "available": resource.available,
                    "utilization": utilization,
                }
            return {}

        # Overall utilization
        total_capacity = sum(r.capacity for r in self.resources.values())
        total_allocated = sum(r.allocated for r in self.resources.values())
        overall_utilization = total_allocated / total_capacity if total_capacity > 0 else 0

        return {
            "total_capacity": total_capacity,
            "total_allocated": total_allocated,
            "overall_utilization": overall_utilization,
            "resources": {rid: self.get_utilization(rid) for rid in self.resources.keys()},
        }

    def optimize_allocation(self) -> None:
        """
        Optimize resource allocation

        Reallocates resources to improve overall utilization
        """
        # Simplified: release resources from low-priority tasks
        # and reallocate to high-priority tasks

        # Sort allocations by priority (ascending)
        sorted_allocations = sorted(self.allocations, key=lambda a: a.priority)

        # Release low-priority allocations
        for allocation in sorted_allocations:
            if allocation.priority < 0.5:
                self.release(allocation.task_id)

        logger.info("Optimized resource allocation")
