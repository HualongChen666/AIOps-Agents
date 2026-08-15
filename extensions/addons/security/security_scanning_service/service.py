# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the Security Scanning addon."""

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
    "run_sast_sonarqube",
    "run_dast_zap",
    "run_dependency_snyk",
    "run_container_trivy",
    "manage_vulnerabilities",
    "generate_scan_reports",
    "check_compliance",
    "generate_fix_suggestions",
    "schedule_security_scans",
    "test_and_optimize_security_scanning",
]


class Service:
    """SecurityScanning service dispatcher."""

    @staticmethod
    def execute_operation(name: str, params: Any = None) -> Dict[str, Any]:
        if name not in OPERATIONS and name not in BASE_METHODS:
            raise ValueError(f"Unknown operation: {name}")
        params = params if isinstance(params, dict) else {}
        scanner = SecurityScanner(dry_run=params.get("dry_run"))

        try:
            if name == "run_sast_sonarqube":
                result = scanner.scan_code(
                    params.get("target", "."),
                    params.get("scanners", ["bandit", "semgrep"]),
                )
            elif name == "run_dast_zap":
                result = scanner.scan_api(params.get("target", "http://localhost"))
            elif name == "run_dependency_snyk":
                result = scanner.scan_dependencies(params.get("target", "requirements.txt"))
            elif name == "run_container_trivy":
                result = scanner.scan_container(params.get("image", "alpine:latest"))
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
