# -*- coding: utf-8 -*-
"""Core service logic for the Backup Recovery Drill microservice."""

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
    "design_drill_plan",
    "run_database_backup_drill",
    "run_config_backup_drill",
    "run_log_backup_drill",
    "write_drill_report",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "design_drill_plan": {
        "executor": "cli",
        "command": ["python", "-c", "print('design drill plan')"],
    },
    "run_database_backup_drill": {
        "executor": "k8s",
        "command": ["pgbackrest", "backup", "--type=full"],
    },
    "run_config_backup_drill": {
        "executor": "k8s",
        "command": ["kubectl", "get", "configmap", "-o", "yaml"],
    },
    "run_log_backup_drill": {
        "executor": "k8s",
        "command": ["kubectl", "logs", "app"],
    },
    "write_drill_report": {
        "executor": "cli",
        "command": ["python", "-c", "print('drill report')"],
    },
}


def _builder(op: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    spec = _COMMAND_TEMPLATES.get(op)
    if spec:
        return lambda params: spec
    return lambda params: {"executor": "cli", "command": ["echo", op]}


COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    op: _builder(op) for op in OPERATIONS
}


class Service(BaseInfraService):
    """Domain service for Backup Recovery Drill."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "Backup Recovery Drill"
