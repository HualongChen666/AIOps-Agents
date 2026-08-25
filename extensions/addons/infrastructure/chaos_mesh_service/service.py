# -*- coding: utf-8 -*-
"""Core service logic for the Chaos Mesh microservice."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from extensions.addons.engines.infra_executor import BaseInfraService

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]
OPERATIONS: List[str] = [
    "pod_fault_injection",
    "network_fault_injection",
    "disk_fault_injection",
    "resource_fault_injection",
    "fault_orchestration",
    "fault_monitoring",
    "fault_recovery",
    "drill_report",
    "integrate_ops_service",
    "test_and_optimize_chaos_mesh",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "pod_fault_injection": {
        "executor": "k8s",
        "command": ["chaosctl", "create", "pod-chaos"],
    },
    "network_fault_injection": {
        "executor": "k8s",
        "command": ["chaosctl", "create", "network-chaos"],
    },
    "disk_fault_injection": {
        "executor": "k8s",
        "command": ["chaosctl", "create", "disk-chaos"],
    },
    "resource_fault_injection": {
        "executor": "k8s",
        "command": ["chaosctl", "create", "stress-chaos"],
    },
    "fault_orchestration": {
        "executor": "k8s",
        "command": ["chaosctl", "list"],
    },
    "fault_monitoring": {
        "executor": "k8s",
        "command": ["kubectl", "get", "chaos"],
    },
    "fault_recovery": {
        "executor": "k8s",
        "command": ["kubectl", "delete", "chaos"],
    },
    "drill_report": {
        "executor": "cli",
        "command": ["python", "-c", "print('chaos report')"],
    },
    "integrate_ops_service": {
        "executor": "k8s",
        "command": ["kubectl", "get", "pods"],
    },
    "test_and_optimize_chaos_mesh": {
        "executor": "k8s",
        "command": ["chaosctl", "create", "test"],
    },
}


def _builder(op: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    spec = _COMMAND_TEMPLATES.get(op)
    if spec:
        return lambda params: spec
    return lambda params: {"executor": "k8s", "command": ["chaosctl", "create", op]}


COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    op: _builder(op) for op in OPERATIONS
}


class Service(BaseInfraService):
    """Domain service for Chaos Mesh."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "Chaos Mesh"
