# -*- coding: utf-8 -*-
"""Core service logic for the pgBackRest Backup microservice."""

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
    "postgresql_full_backup",
    "postgresql_incremental_backup",
    "backup_compression",
    "backup_encryption",
    "backup_retention_policy",
    "backup_transfer_s3",
    "backup_validation",
    "point_in_time_recovery",
    "integrate_ops_service",
    "test_and_optimize_pgbackrest_backup",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "postgresql_full_backup": {
        "executor": "k8s",
        "command": ["pgbackrest", "backup", "--type=full"],
    },
    "postgresql_incremental_backup": {
        "executor": "k8s",
        "command": ["pgbackrest", "backup", "--type=incr"],
    },
    "backup_compression": {
        "executor": "k8s",
        "command": ["pgbackrest", "backup", "--compress-level=6"],
    },
    "backup_encryption": {
        "executor": "k8s",
        "command": ["pgbackrest", "backup", "--repo1-cipher-type=aes-256-cbc"],
    },
    "backup_retention_policy": {
        "executor": "k8s",
        "command": ["pgbackrest", "expire"],
    },
    "backup_transfer_s3": {
        "executor": "k8s",
        "command": ["pgbackrest", "repo-ls"],
    },
    "backup_validation": {
        "executor": "k8s",
        "command": ["pgbackrest", "verify"],
    },
    "point_in_time_recovery": {
        "executor": "k8s",
        "command": ["pgbackrest", "restore", "--type=time"],
    },
    "integrate_ops_service": {
        "executor": "k8s",
        "command": ["pgbackrest", "info"],
    },
    "test_and_optimize_pgbackrest_backup": {
        "executor": "k8s",
        "command": ["pgbackrest", "backup", "--type=full"],
    },
}


def _builder(op: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    spec = _COMMAND_TEMPLATES.get(op)
    if spec:
        return lambda params: spec
    return lambda params: {"executor": "k8s", "command": ["pgbackrest", "backup"]}


COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    op: _builder(op) for op in OPERATIONS
}


class Service(BaseInfraService):
    """Domain service for pgBackRest Backup."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "pgBackRest Backup"
