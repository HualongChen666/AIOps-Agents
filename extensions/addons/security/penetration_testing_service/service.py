# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the Penetration Testing addon."""

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
    "design_penetration_plan",
    "execute_penetration_tests",
    "analyze_penetration_results",
    "fix_vulnerabilities",
    "verify_fixes",
    "write_penetration_report",
    "implement_security_hardening",
    "conduct_security_training",
    "schedule_regular_pentests",
    "test_and_optimize_pentesting",
]


class Service:
    """PenetrationTesting service dispatcher."""

    @staticmethod
    def execute_operation(name: str, params: Any = None) -> Dict[str, Any]:
        if name not in OPERATIONS and name not in BASE_METHODS:
            raise ValueError(f"Unknown operation: {name}")
        params = params if isinstance(params, dict) else {}
        scanner = SecurityScanner(dry_run=params.get("dry_run"))

        try:
            if name == "execute_penetration_tests":
                result = scanner.scan_network(params.get("target", "127.0.0.1"))
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
