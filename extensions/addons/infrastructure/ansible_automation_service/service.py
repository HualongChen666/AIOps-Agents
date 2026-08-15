# -*- coding: utf-8 -*-
"""Core service logic for the Ansible Automation microservice."""

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
    "design_ansible_architecture",
    "write_ansible_playbooks",
    "config_management_automation",
    "app_deployment_automation",
    "rolling_update_automation",
    "rollback_automation",
    "configure_ansible_tower",
    "test_integration_automation",
    "monitoring_integration_automation",
    "test_and_optimize_ansible",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "configure_ansible_tower": {
        "executor": "ansible",
        "command": ["tower.yml", "--check"],
    },
}


def _builder(op: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    spec = _COMMAND_TEMPLATES.get(op)
    if spec:
        return lambda params: spec
    return lambda params: {"executor": "ansible", "command": [f"{op}.yml", "--check"]}


COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    op: _builder(op) for op in OPERATIONS
}


class Service(BaseInfraService):
    """Domain service for Ansible Automation."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "Ansible Automation"
