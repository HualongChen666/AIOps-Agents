# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the Security Audit addon."""

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
    "run_zap_scan",
    "run_safety_check",
    "run_snyk_scan",
    "run_opa_compliance",
    "write_audit_report",
]


class Service:
    """SecurityAudit service dispatcher."""

    @staticmethod
    def execute_operation(name: str, params: Any = None) -> Dict[str, Any]:
        if name not in OPERATIONS and name not in BASE_METHODS:
            raise ValueError(f"Unknown operation: {name}")
        params = params if isinstance(params, dict) else {}
        scanner = SecurityScanner(dry_run=params.get("dry_run"))

        try:
            if name == "run_zap_scan":
                result = scanner.scan_api(params.get("target", "http://localhost"))
            elif name == "run_safety_check":
                result = scanner.scan_dependencies(params.get("target", "requirements.txt"))
            elif name == "run_snyk_scan":
                result = scanner.scan_dependencies(params.get("target", "requirements.txt"))
            elif name == "run_opa_compliance":
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
