# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the SQLAlchemy Security addon."""

from __future__ import annotations

from typing import Any, Dict, List

from extensions.addons.engines.security_scanner import SecurityScanner

BASE_METHODS: List[str] = [
    "get_state",
    "backup_state",
    "restore_state",
    "get_stats",
    "list_methods",
]
OPERATIONS: List[str] = [
    "sql_injection_protection",
    "parameterized_queries",
    "data_validation",
    "encrypted_storage",
    "access_control",
    "audit_logging",
    "data_masking",
    "integrate_data_access_layer",
    "test_and_optimize_sqlalchemy_security",
    "write_security_docs",
]


class Service:
    """SQLAlchemySecurity service dispatcher."""

    @staticmethod
    def execute_operation(name: str, params: Any = None) -> Dict[str, Any]:
        if name not in OPERATIONS and name not in BASE_METHODS:
            raise ValueError(f"Unknown operation: {name}")
        params = params if isinstance(params, dict) else {}
        scanner = SecurityScanner(dry_run=params.get("dry_run"))

        try:
            if name == "sql_injection_protection":
                result = scanner.check_sql_injection(params.get("code", ""))
            else:
                return {
                    "success": False,
                    "status": "not_implemented",
                    "result": {},
                    "message": f"{name} is not implemented by the SecurityScanner engine",
                }
        except Exception as exc:
            return {
                "success": False,
                "status": "error",
                "result": {},
                "message": str(exc),
            }

        return {
            "success": True,
            "status": "ok",
            "result": result,
            "message": f"{name} completed",
        }
