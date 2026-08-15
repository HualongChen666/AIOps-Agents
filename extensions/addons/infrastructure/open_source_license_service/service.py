# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the Open Source License addon."""

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
    "select_osi_license",
    "add_license_file",
    "add_source_headers",
    "write_license_usage_docs",
    "configure_dependency_license_check",
    "generate_license_inventory",
    "write_compliance_docs",
    "review_license_compliance",
    "handle_license_changes",
    "test_and_optimize_licenses",
]


class Service:
    """OpenSourceLicense service dispatcher."""

    @staticmethod
    def execute_operation(name: str, params: Any = None) -> Dict[str, Any]:
        if name not in OPERATIONS and name not in BASE_METHODS:
            raise ValueError(f"Unknown operation: {name}")
        params = params if isinstance(params, dict) else {}
        scanner = SecurityScanner(dry_run=params.get("dry_run"))

        try:
            if name == "review_license_compliance":
                result = scanner.check_license(params.get("dependencies", []))
            elif name == "configure_dependency_license_check":
                result = scanner.check_license(params.get("dependencies", []))
            elif name == "generate_license_inventory":
                result = scanner.check_license(params.get("dependencies", []))
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
