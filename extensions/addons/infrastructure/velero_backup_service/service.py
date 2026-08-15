# -*- coding: utf-8 -*-
"""Core service logic for the Velero Backup microservice."""

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
    "k8s_resource_backup",
    "persistent_volume_backup",
    "scheduled_backup_policy",
    "backup_retention_policy",
    "backup_encryption",
    "backup_compression",
    "backup_transfer_s3",
    "backup_validation",
    "integrate_ops_service",
    "test_and_optimize_velero_backup",
]

_COMMAND_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "k8s_resource_backup": {
        "executor": "k8s",
        "command": ["velero", "backup", "create", "k8s-backup"],
    },
    "persistent_volume_backup": {
        "executor": "k8s",
        "command": ["velero", "backup", "create", "pv-backup", "--include-volumes"],
    },
    "scheduled_backup_policy": {
        "executor": "k8s",
        "command": ["velero", "schedule", "create", "daily", "--schedule=@daily"],
    },
    "backup_retention_policy": {
        "executor": "k8s",
        "command": ["velero", "backup", "delete", "old-backup"],
    },
    "backup_encryption": {
        "executor": "k8s",
        "command": ["velero", "backup", "create", "enc-backup", "--snapshot-volumes"],
    },
    "backup_compression": {
        "executor": "k8s",
        "command": ["velero", "backup", "create", "comp-backup", "--compressed"],
    },
    "backup_transfer_s3": {
        "executor": "k8s",
        "command": ["velero", "backup-location", "get"],
    },
    "backup_validation": {
        "executor": "k8s",
        "command": ["velero", "backup", "describe", "backup"],
    },
    "integrate_ops_service": {
        "executor": "k8s",
        "command": ["velero", "backup-location", "get"],
    },
    "test_and_optimize_velero_backup": {
        "executor": "k8s",
        "command": ["velero", "backup", "create", "test-backup"],
    },
}


def _builder(op: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    spec = _COMMAND_TEMPLATES.get(op)
    if spec:
        return lambda params: spec
    return lambda params: {"executor": "k8s", "command": ["velero", "backup", "create", op]}


COMMAND_MAP: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    op: _builder(op) for op in OPERATIONS
}


class Service(BaseInfraService):
    """Domain service for Velero Backup."""

    OPERATIONS = OPERATIONS
    COMMAND_MAP = COMMAND_MAP
    display_name = "Velero Backup"
