# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the Security Scanning addon."""

from __future__ import annotations

from typing import List

from extensions.addons.engines.security_scanner import BaseSecurityService


class Service(BaseSecurityService):
    """SecurityScanning service delegating all operations to SecurityScanner."""

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
