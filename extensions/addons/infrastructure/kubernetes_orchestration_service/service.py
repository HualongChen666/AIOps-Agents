# -*- coding: utf-8 -*-
"""Core service logic for the Kubernetes Orchestration microservice."""

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
    "design_k8s_cluster_architecture",
    "configure_k8s_cluster",
    "container_orchestration_automation",
    "service_discovery",
    "load_balancing",
    "auto_scaling",
    "config_management",
    "storage_management",
    "monitoring_integration_automation",
    "test_and_optimize_kubernetes",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "design_k8s_cluster_architecture": {
        "executor": "k8s",
        "command": ["cluster-info"],
    },
    "configure_k8s_cluster": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "cluster-config.yaml"],
    },
    "container_orchestration_automation": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "workloads/"],
    },
    "service_discovery": {
        "executor": "k8s",
        "command": ["kubectl", "get", "endpoints"],
    },
    "load_balancing": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "ingress.yaml"],
    },
    "auto_scaling": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "hpa.yaml"],
    },
    "config_management": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "configmap.yaml"],
    },
    "storage_management": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "pvc.yaml"],
    },
    "monitoring_integration_automation": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "monitoring.yaml"],
    },
    "test_and_optimize_kubernetes": {
        "executor": "k8s",
        "command": ["kubectl", "get", "pods", "-A"],
    },
}


def _builder(op: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    spec = _COMMAND_TEMPLATES.get(op)
    if spec:
        return lambda params: spec
    return lambda params: {"executor": "k8s", "command": ["kubectl", "apply", "-f", f"{op}.yaml"]}


COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    op: _builder(op) for op in OPERATIONS
}


class Service(BaseInfraService):
    """Domain service for Kubernetes Orchestration."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "Kubernetes Orchestration"
