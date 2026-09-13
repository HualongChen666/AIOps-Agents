# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the Security Audit addon."""

from __future__ import annotations

from typing import List

from extensions.addons.engines.security_scanner import BaseSecurityService
from extensions.addons.engines.service_contract import ServiceStateContract


class Service(BaseSecurityService, ServiceStateContract):
    """SecurityAudit service delegating all operations to SecurityScanner."""

    OPERATIONS: List[str] = [
        "run_zap_scan",
        "run_safety_check",
        "run_snyk_scan",
        "run_opa_compliance",
        "write_audit_report",
    ]


# --- addon loader compatibility exports (main_app imports) ---
BASE_METHODS: List[str] = list(getattr(Service, "BASE_METHODS", []))
OPERATIONS: List[str] = list(getattr(Service, "OPERATIONS", []))
SecurityAuditService = Service
