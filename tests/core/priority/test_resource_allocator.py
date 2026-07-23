# -*- coding: utf-8 -*-
"""测试资源分配器模块"""

import pytest


class TestResourceAllocatorModule:
    """测试资源分配器模块"""

    def test_resource_allocator_module_exists(self):
        """测试资源分配器模块存在"""
        from core.priority import resource_allocator

        assert resource_allocator is not None

    def test_resource_allocator_has_dataclasses(self):
        """测试资源分配器模块有数据类"""
        from core.priority import resource_allocator

        # 检查模块有数据类
        assert hasattr(resource_allocator, "Resource")
        assert hasattr(resource_allocator, "ResourceAllocation")

    def test_resource_allocator_has_classes(self):
        """测试资源分配器模块有类"""
        from core.priority import resource_allocator

        # 检查模块有类
        assert hasattr(resource_allocator, "ResourceAllocator")


class TestResource:
    """测试资源数据类"""

    def test_resource_creation(self):
        """测试资源创建"""
        from core.priority.resource_allocator import Resource

        resource = Resource(
            id="resource_1",
            type="cpu",
            capacity=100.0,
            available=100.0,
        )

        assert resource.id == "resource_1"
        assert resource.type == "cpu"
        assert resource.capacity == 100.0
        assert resource.available == 100.0
        assert resource.allocated == 0.0


class TestResourceAllocation:
    """测试资源分配数据类"""

    def test_resource_allocation_creation(self):
        """测试资源分配创建"""
        from core.priority.resource_allocator import ResourceAllocation

        allocation = ResourceAllocation(
            task_id="task_1",
            resource_id="resource_1",
            amount=50.0,
            priority=0.8,
        )

        assert allocation.task_id == "task_1"
        assert allocation.resource_id == "resource_1"
        assert allocation.amount == 50.0
        assert allocation.priority == 0.8


class TestResourceAllocator:
    """测试资源分配器类"""

    def test_allocator_initialization(self):
        """测试分配器初始化"""
        from core.priority.resource_allocator import ResourceAllocator

        allocator = ResourceAllocator()

        assert allocator.resources == {}
        assert allocator.allocations == []

    def test_add_resource(self):
        """测试添加资源"""
        from core.priority.resource_allocator import Resource, ResourceAllocator

        allocator = ResourceAllocator()

        resource = Resource(
            id="resource_1",
            type="cpu",
            capacity=100.0,
            available=100.0,
        )

        allocator.add_resource(resource)

        assert "resource_1" in allocator.resources
        assert allocator.resources["resource_1"].capacity == 100.0

    def test_allocate_resources(self):
        """测试分配资源"""
        from core.priority.resource_allocator import Resource, ResourceAllocator

        allocator = ResourceAllocator()

        resource = Resource(
            id="resource_1",
            type="cpu",
            capacity=100.0,
            available=100.0,
        )

        allocator.add_resource(resource)

        tasks = [
            {"id": "task_1", "priority": 0.8, "resource_requirement": {"cpu": 50.0}},
            {"id": "task_2", "priority": 0.6, "resource_requirement": {"cpu": 30.0}},
        ]

        allocations = allocator.allocate(tasks, "cpu")

        assert len(allocations) == 2
        assert allocations[0].task_id == "task_1"
        assert allocations[1].task_id == "task_2"

    def test_allocate_resources_no_available(self):
        """测试分配资源（无可用资源）"""
        from core.priority.resource_allocator import ResourceAllocator

        allocator = ResourceAllocator()

        tasks = [
            {"id": "task_1", "priority": 0.8, "resource_requirement": {"cpu": 50.0}},
        ]

        allocations = allocator.allocate(tasks, "cpu")

        assert len(allocations) == 0

    def test_allocate_resources_insufficient_capacity(self):
        """测试分配资源（容量不足）"""
        from core.priority.resource_allocator import Resource, ResourceAllocator

        allocator = ResourceAllocator()

        resource = Resource(
            id="resource_1",
            type="cpu",
            capacity=50.0,
            available=50.0,
        )

        allocator.add_resource(resource)

        tasks = [
            {"id": "task_1", "priority": 0.8, "resource_requirement": {"cpu": 100.0}},
        ]

        allocations = allocator.allocate(tasks, "cpu")

        assert len(allocations) == 0

    def test_allocate_resources_priority_order(self):
        """测试分配资源（优先级顺序）"""
        from core.priority.resource_allocator import Resource, ResourceAllocator

        allocator = ResourceAllocator()

        resource = Resource(
            id="resource_1",
            type="cpu",
            capacity=100.0,
            available=100.0,
        )

        allocator.add_resource(resource)

        tasks = [
            {"id": "task_1", "priority": 0.4, "resource_requirement": {"cpu": 30.0}},
            {"id": "task_2", "priority": 0.9, "resource_requirement": {"cpu": 50.0}},
        ]

        allocations = allocator.allocate(tasks, "cpu")

        # Higher priority task should be allocated first
        assert allocations[0].task_id == "task_2"
        assert allocations[1].task_id == "task_1"

    def test_release_resources(self):
        """测试释放资源"""
        from core.priority.resource_allocator import Resource, ResourceAllocator

        allocator = ResourceAllocator()

        resource = Resource(
            id="resource_1",
            type="cpu",
            capacity=100.0,
            available=100.0,
        )

        allocator.add_resource(resource)

        tasks = [
            {"id": "task_1", "priority": 0.8, "resource_requirement": {"cpu": 50.0}},
        ]

        allocator.allocate(tasks, "cpu")

        assert resource.available == 50.0
        assert resource.allocated == 50.0

        allocator.release("task_1")

        assert resource.available == 100.0
        assert resource.allocated == 0.0

    def test_release_resources_invalid_task(self):
        """测试释放资源（无效任务）"""
        from core.priority.resource_allocator import ResourceAllocator

        allocator = ResourceAllocator()

        # Should not raise an error
        allocator.release("invalid_task")

    def test_get_utilization_single_resource(self):
        """测试获取利用率（单个资源）"""
        from core.priority.resource_allocator import Resource, ResourceAllocator

        allocator = ResourceAllocator()

        resource = Resource(
            id="resource_1",
            type="cpu",
            capacity=100.0,
            available=100.0,
        )

        allocator.add_resource(resource)

        tasks = [
            {"id": "task_1", "priority": 0.8, "resource_requirement": {"cpu": 50.0}},
        ]

        allocator.allocate(tasks, "cpu")

        utilization = allocator.get_utilization("resource_1")

        assert utilization["resource_id"] == "resource_1"
        assert utilization["allocated"] == 50.0
        assert utilization["available"] == 50.0
        assert utilization["utilization"] == 0.5

    def test_get_utilization_overall(self):
        """测试获取整体利用率"""
        from core.priority.resource_allocator import Resource, ResourceAllocator

        allocator = ResourceAllocator()

        resource1 = Resource(
            id="resource_1",
            type="cpu",
            capacity=100.0,
            available=100.0,
        )

        resource2 = Resource(
            id="resource_2",
            type="memory",
            capacity=200.0,
            available=200.0,
        )

        allocator.add_resource(resource1)
        allocator.add_resource(resource2)

        tasks = [
            {"id": "task_1", "priority": 0.8, "resource_requirement": {"cpu": 50.0}},
        ]

        allocator.allocate(tasks, "cpu")

        utilization = allocator.get_utilization()

        assert utilization["total_capacity"] == 300.0
        assert utilization["total_allocated"] == 50.0
        assert utilization["overall_utilization"] == 50.0 / 300.0

    def test_get_utilization_invalid_resource(self):
        """测试获取利用率（无效资源）"""
        from core.priority.resource_allocator import ResourceAllocator

        allocator = ResourceAllocator()

        utilization = allocator.get_utilization("invalid_resource")

        assert utilization == {}

    def test_optimize_allocation(self):
        """测试优化分配"""
        from core.priority.resource_allocator import Resource, ResourceAllocator

        allocator = ResourceAllocator()

        resource = Resource(
            id="resource_1",
            type="cpu",
            capacity=100.0,
            available=100.0,
        )

        allocator.add_resource(resource)

        tasks = [
            {"id": "task_1", "priority": 0.3, "resource_requirement": {"cpu": 30.0}},
            {"id": "task_2", "priority": 0.8, "resource_requirement": {"cpu": 50.0}},
        ]

        allocator.allocate(tasks, "cpu")

        # Should have 2 allocations
        assert len(allocator.allocations) == 2

        # Optimize - should release low priority tasks
        allocator.optimize_allocation()

        # Should only have high priority allocation
        assert len(allocator.allocations) == 1
        assert allocator.allocations[0].task_id == "task_2"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
