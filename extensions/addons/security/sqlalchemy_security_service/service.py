# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the SQLAlchemy Security addon."""

from __future__ import annotations

from typing import List

from extensions.addons.engines.security_scanner import BaseSecurityService


class Service(BaseSecurityService):
    """SQLAlchemySecurity service delegating all operations to SecurityScanner."""

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
