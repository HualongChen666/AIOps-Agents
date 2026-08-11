# -*- coding: utf-8 -*-
"""Tests for core/priority/resource_allocator.py."""

from core.priority.resource_allocator import (
    Resource,
    ResourceAllocator,
)


def test_add_and_allocate():
    allocator = ResourceAllocator()
    allocator.add_resource(Resource(id="r1", type="cpu", capacity=10, available=10))
    tasks = [
        {"id": "t1", "priority": 5, "resource_requirement": {"cpu": 4}},
        {"id": "t2", "priority": 8, "resource_requirement": {"cpu": 6}},
    ]
    allocations = allocator.allocate(tasks, "cpu")
    assert len(allocations) == 2
    assert allocations[0].task_id == "t2"  # higher priority first


def test_release_and_utilization():
    allocator = ResourceAllocator()
    allocator.add_resource(Resource(id="r1", type="cpu", capacity=10, available=10))
    tasks = [{"id": "t1", "priority": 1, "resource_requirement": {"cpu": 3}}]
    allocator.allocate(tasks, "cpu")
    assert allocator.get_utilization("r1")["allocated"] == 3
    allocator.release("t1")
    assert allocator.get_utilization("r1")["allocated"] == 0
    overall = allocator.get_utilization()
    assert overall["total_capacity"] == 10
    assert "resources" in overall


def test_optimize_allocation():
    allocator = ResourceAllocator()
    allocator.add_resource(Resource(id="r1", type="cpu", capacity=10, available=10))
    allocator.optimize_allocation()
    assert allocator.resources["r1"].available == 10
