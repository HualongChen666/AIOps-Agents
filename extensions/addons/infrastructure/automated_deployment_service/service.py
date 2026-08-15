# -*- coding: utf-8 -*-
"""Core service logic for the Automated Deployment microservice."""

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
    "implement_cicd_pipeline",
    "integrate_automated_tests",
    "implement_automated_deployment",
    "implement_automated_rollback",
    "implement_automated_monitoring",
    "implement_automated_alerts",
    "implement_log_collection",
    "write_deployment_docs",
    "test_and_optimize_deployment",
    "run_deployment_performance_tests",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "implement_cicd_pipeline": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", ".github/workflows/"],
    },
    "integrate_automated_tests": {
        "executor": "cli",
        "command": ["pytest", "tests"],
    },
    "implement_automated_deployment": {
        "executor": "k8s",
        "command": ["kubectl", "rollout", "status", "deployment/app"],
    },
    "implement_automated_rollback": {
        "executor": "k8s",
        "command": ["kubectl", "rollout", "undo", "deployment/app"],
    },
    "implement_automated_monitoring": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "monitoring/"],
    },
    "implement_automated_alerts": {
        "executor": "k8s",
        "command": ["kubectl", "apply", "-f", "alerts/"],
    },
    "implement_log_collection": {
        "executor": "k8s",
        "command": ["kubectl", "logs", "-l", "app=app"],
    },
    "write_deployment_docs": {
        "executor": "cli",
        "command": ["python", "-m", "mkdocs", "build"],
    },
    "test_and_optimize_deployment": {
        "executor": "k8s",
        "command": ["kubectl", "get", "pods"],
    },
    "run_deployment_performance_tests": {
        "executor": "k8s",
        "command": ["kubectl", "top", "pods"],
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
    """Domain service for Automated Deployment."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "Automated Deployment"
