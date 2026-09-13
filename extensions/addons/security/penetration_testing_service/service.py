# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the Penetration Testing addon."""

from __future__ import annotations

from typing import List

from extensions.addons.engines.security_scanner import BaseSecurityService
from extensions.addons.engines.service_contract import ServiceStateContract


class Service(BaseSecurityService, ServiceStateContract):
    """PenetrationTesting service delegating all operations to SecurityScanner."""

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


# --- addon loader compatibility exports (main_app imports) ---
BASE_METHODS: List[str] = list(getattr(Service, "BASE_METHODS", []))
OPERATIONS: List[str] = list(getattr(Service, "OPERATIONS", []))
PenetrationTestingService = Service
