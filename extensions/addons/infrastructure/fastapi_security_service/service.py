# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the FastAPI Security addon."""

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
    "oauth2_password_auth",
    "jwt_token_auth",
    "api_key_auth",
    "dependency_injection",
    "cors_configuration",
    "security_headers",
    "https_enforcement",
    "rate_limiting",
    "integrate_api_gateway",
    "test_and_optimize_fastapi_security",
]


class Service:
    """FastAPISecurity service dispatcher."""

    @staticmethod
    def execute_operation(name: str, params: Any = None) -> Dict[str, Any]:
        if name not in OPERATIONS and name not in BASE_METHODS:
            raise ValueError(f"Unknown operation: {name}")
        params = params if isinstance(params, dict) else {}
        scanner = SecurityScanner(dry_run=params.get("dry_run"))

        try:
            if name == "api_key_auth":
                result = scanner.check_api_baseline(params.get("spec", {}))
            elif name == "test_and_optimize_fastapi_security":
                result = scanner.check_api_baseline(params.get("spec", {}))
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
