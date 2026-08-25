# -*- coding: utf-8 -*-
"""Configuration for Identity Management Service."""

import os

SERVICE_NAME = "identity_management_service"
VERSION = "1.0.0"

# Server configuration
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
GRPC_PORT = int(os.getenv("GRPC_PORT", "50053"))

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/aiops"
)

# JWT configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "30"))

# MFA configuration
MFA_ISSUER = os.getenv("MFA_ISSUER", "AIOps Identity Management")

# SSO configuration
SSO_ENABLED = os.getenv("SSO_ENABLED", "false").lower() == "true"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
