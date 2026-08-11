# -*- coding: utf-8 -*-
"""Unit tests for task execution and scheduling modules."""

from core.execution.l6.fault_tolerant_executor import (
    FaultTolerantExecutor,
    get_fault_tolerant_executor,
)
from core.execution.l6.optimized_executor import init_optimized_executor
from core.task_scheduler import TaskScheduler
from core.workflow_engine import (
    get_valid_workflow_keys,
    get_workflow_definitions,
    is_valid_workflow_key,
)


def test_fault_tolerant_executor():
    executor = get_fault_tolerant_executor()
    assert isinstance(executor, FaultTolerantExecutor)
    assert executor.get_metrics() is not None
    assert executor.get_circuit_breaker_states() is not None


def test_optimized_executor():
    executor = init_optimized_executor({})
    assert executor is not None
    assert executor.get_metrics() is not None
    assert executor.get_status() is not None
    executor.clear_cache()


def test_task_scheduler():
    scheduler = TaskScheduler()
    assert scheduler.list_tasks() is not None


def test_workflow_engine_definitions():
    workflows = get_workflow_definitions()
    assert isinstance(workflows, dict)
    keys = get_valid_workflow_keys()
    assert isinstance(keys, list)
    assert is_valid_workflow_key("nonexistent-key") is False
