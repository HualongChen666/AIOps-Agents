# -*- coding: utf-8 -*-
"""Thin wrapper around SecurityScanner for the FastAPI Security addon."""

from __future__ import annotations

from typing import List

from extensions.addons.engines.security_scanner import BaseSecurityService


class Service(BaseSecurityService):
    """FastAPISecurity service delegating all operations to SecurityScanner."""

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
