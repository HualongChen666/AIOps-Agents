# -*- coding: utf-8 -*-
"""Thin wrapper around PolicyEngine for the Data standards addon."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from extensions.addons.engines.doc_policy_engine import PolicyEngine
from extensions.addons.engines.service_contract import BasePolicyService

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "validate_schema",
    "define_data_model_spec",
    "implement_json_schema_validation",
    "implement_data_compliance_check",
]


class DataStandardsService(BasePolicyService):
    """Service wrapper delegating data standards operations to PolicyEngine."""

    ENGINE = PolicyEngine
    OPERATIONS = OPERATIONS
    OP_MAP: Dict[str, Callable[[PolicyEngine, Dict[str, Any]], Any]] = {
        "validate_schema": lambda engine, params: engine.validate_schema(
            params.get("obj"), params.get("schema")
        ),
        "define_data_model_spec": lambda engine, params: engine.validate_schema(
            params.get("obj", {}), params.get("schema", {})
        ),
        "implement_json_schema_validation": lambda engine, params: engine.validate_schema(
            params.get("obj", {}), params.get("schema", {})
        ),
        "implement_data_compliance_check": lambda engine, params: engine.validate_schema(
            params.get("obj", {}), params.get("schema", {})
        ),
    }


Service = DataStandardsService
