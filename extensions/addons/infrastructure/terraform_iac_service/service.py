# -*- coding: utf-8 -*-
"""Core service logic for the Terraform IaC microservice."""

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
    "design_terraform_modules",
    "write_terraform_configs",
    "infra_automation_deployment",
    "multi_environment_management",
    "state_management",
    "dependency_management",
    "configure_terraform_cloud",
    "test_integration_automation",
    "monitoring_integration_automation",
    "test_and_optimize_terraform",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "write_terraform_configs": {
        "executor": "terraform",
        "command": ["validate"],
    },
    "infra_automation_deployment": {
        "executor": "terraform",
        "command": ["apply"],
    },
    "multi_environment_management": {
        "executor": "terraform",
        "command": ["workspace", "list"],
    },
    "state_management": {
        "executor": "terraform",
        "command": ["state", "list"],
    },
    "dependency_management": {
        "executor": "terraform",
        "command": ["get"],
    },
    "configure_terraform_cloud": {
        "executor": "terraform",
        "command": ["init"],
    },
}


def _builder(op: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    spec = _COMMAND_TEMPLATES.get(op)
    if spec:
        return lambda params: spec
    return lambda params: {"executor": "terraform", "command": ["plan"]}


COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    op: _builder(op) for op in OPERATIONS
}


class Service(BaseInfraService):
    """Domain service for Terraform IaC."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "Terraform IaC"
