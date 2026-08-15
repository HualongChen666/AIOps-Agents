# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the Open Source License addon."""

from __future__ import annotations

from typing import List

from extensions.addons.engines.security_scanner import BaseSecurityService


class Service(BaseSecurityService):
    """OpenSourceLicense service delegating all operations to SecurityScanner."""

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
