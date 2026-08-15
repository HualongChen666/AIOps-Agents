# -*- coding: utf-8 -*-
"""Core service logic for the Automated Operations microservice."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from extensions.addons.engines.infra_executor import BaseInfraService

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]
OPERATIONS: List[str] = [
    "implement_automated_inspection",
    "implement_fault_diagnosis",
    "implement_fault_repair",
    "implement_capacity_planning",
    "implement_automated_backup",
    "implement_automated_recovery",
    "implement_automated_reporting",
    "write_ops_docs",
    "test_and_optimize_ops",
    "run_ops_performance_tests",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "implement_automated_inspection": {
        "executor": "k8s",
        "command": ["kubectl", "get", "pods", "-A"],
    },
    "implement_fault_diagnosis": {
        "executor": "k8s",
        "command": ["kubectl", "describe", "pod"],
    },
    "implement_fault_repair": {
        "executor": "k8s",
        "command": ["kubectl", "delete", "pod"],
    },
    "implement_capacity_planning": {
        "executor": "k8s",
        "command": ["kubectl", "top", "nodes"],
    },
    "implement_automated_backup": {
        "executor": "k8s",
        "command": ["pgbackrest", "backup", "--type=full"],
    },
    "implement_automated_recovery": {
        "executor": "k8s",
        "command": ["velero", "restore", "create", "recovery"],
    },
    "implement_automated_reporting": {
        "executor": "k8s",
        "command": ["kubectl", "logs", "-l", "app=ops"],
    },
    "write_ops_docs": {
        "executor": "cli",
        "command": ["python", "-m", "ops.docs", "build"],
    },
    "test_and_optimize_ops": {
        "executor": "k8s",
        "command": ["kubectl", "get", "all", "-A"],
    },
    "run_ops_performance_tests": {
        "executor": "k8s",
        "command": ["kubectl", "top", "pods", "-A"],
    },
}


def _builder(op: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    spec = _COMMAND_TEMPLATES.get(op)
    if spec:
        return lambda params: spec
    return lambda params: {"executor": "k8s", "command": ["kubectl", "get", "pods"]}


COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    op: _builder(op) for op in OPERATIONS
}


class Service(BaseInfraService):
    """Domain service for Automated Operations."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "Automated Operations"
