# -*- coding: utf-8 -*-
"""Thin wrapper around DocEngine for the Sphinx documentation addon."""

from __future__ import annotations

from typing import Any, Callable, Dict, List

from extensions.addons.engines.doc_policy_engine import DocEngine
from extensions.addons.engines.service_contract import BasePolicyService

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]

OPERATIONS: List[str] = [
    "build_docs",
    "configure_sphinx",
    "deploy_doc_site",
    "test_and_optimize_sphinx",
]


class SphinxDocumentationService(BasePolicyService):
    """Service wrapper delegating Sphinx documentation operations to DocEngine."""

    ENGINE = DocEngine
    OPERATIONS = OPERATIONS
    OP_MAP: Dict[str, Callable[[DocEngine, Dict[str, Any]], Any]] = {
        "build_docs": lambda engine, params: engine.build_docs(
            params.get("source", "docs"), params.get("output", "_build")
        ),
        "configure_sphinx": lambda engine, params: engine.build_docs(
            params.get("source", "docs"), params.get("output", "_build")
        ),
        "deploy_doc_site": lambda engine, params: engine.build_docs(
            params.get("source", "docs"), params.get("output", "site")
        ),
        "test_and_optimize_sphinx": lambda engine, params: engine.build_docs(
            params.get("source", "docs"), params.get("output", "_build")
        ),
    }


Service = SphinxDocumentationService
