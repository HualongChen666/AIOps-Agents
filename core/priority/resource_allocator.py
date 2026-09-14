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
        # 因容量不足而暂时无法满足的任务，供 optimize_allocation 在释放资源后重分配。
        self.pending_tasks: List[Dict] = []

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
        # Resources of the requested type. Keep the full set so that tasks which
        # cannot be satisfied now can still be queued for later reallocation,
        # even when every resource of this type is momentarily exhausted.
        type_resources = [r for r in self.resources.values() if r.type == resource_type]

        if not type_resources:
            logger.warning(f"No available resources of type {resource_type}")
            return []

        available_resources = [r for r in type_resources if r.available > 0]

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

        # 记录本轮因容量不足而未能分配的任务，供后续重分配。
        allocated_task_ids = {a.task_id for a in allocations}
        for task in sorted_tasks:
            required = task.get("resource_requirement", {}).get(resource_type, 0)
            if required <= 0:
                continue
            if task.get("id", "unknown") not in allocated_task_ids and task not in self.pending_tasks:
                self.pending_tasks.append(task)

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

        释放低优先级任务占用的资源，并将这些资源**重分配**给此前因容量不足
        而排队等待的高优先级任务（self.pending_tasks）。
        """
        # Release low-priority allocations
        for allocation in sorted(self.allocations, key=lambda a: a.priority):
            if allocation.priority < 0.5:
                self.release(allocation.task_id)

        # Reallocate the freed capacity to pending higher-priority tasks.
        if self.pending_tasks:
            pending = sorted(
                self.pending_tasks, key=lambda t: t.get("priority", 0), reverse=True
            )
            self.pending_tasks = []
            for resource_type in {r.type for r in self.resources.values()}:
                if pending:
                    self.allocate(pending, resource_type)

        logger.info("Optimized resource allocation")
