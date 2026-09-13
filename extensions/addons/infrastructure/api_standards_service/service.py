# -*- coding: utf-8 -*-
"""Thin wrapper around PolicyEngine for the API standards addon."""

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
    "lint_openapi",
    "follow_openapi3",
    "test_api_with_openapi",
    "generate_api_docs",
]


class APIStandardsService(BasePolicyService):
    """Service wrapper delegating API standards operations to PolicyEngine."""

    ENGINE = PolicyEngine
    OPERATIONS = OPERATIONS
    OP_MAP: Dict[str, Callable[[PolicyEngine, Dict[str, Any]], Any]] = {
        "lint_openapi": lambda engine, params: engine.lint_openapi(params.get("spec")),
        "follow_openapi3": lambda engine, params: engine.lint_openapi(params.get("spec")),
        "test_api_with_openapi": lambda engine, params: engine.lint_openapi(params.get("spec")),
        "generate_api_docs": lambda engine, params: engine.lint_openapi(params.get("spec")),
    }


Service = APIStandardsService
