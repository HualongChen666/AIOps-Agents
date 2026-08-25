# -*- coding: utf-8 -*-
"""Configuration for Secret Management Service."""

import os
from typing import Optional


class Config:
    """Configuration settings for the service."""

    # Service settings
    SERVICE_NAME: str = "secret_management_service"
    PORT: int = int(os.getenv("PORT", "8005"))
    HOST: str = os.getenv("HOST", "127.0.0.1")

    # gRPC settings
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50055"))
    GRPC_HOST: str = os.getenv("GRPC_HOST", "127.0.0.1")

    # Storage settings
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "file")  # file, database
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./secret_storage")
    SECRETS_FILE: str = os.getenv("SECRETS_FILE", "secrets.json")

    # Encryption settings
    ENCRYPTION_ALGORITHM: str = os.getenv("ENCRYPTION_ALGORITHM", "AES-256-GCM")
    ENCRYPTION_KEY_PATH: str = os.getenv("ENCRYPTION_KEY_PATH", "./encryption_keys")
    MASTER_KEY_ENV: str = os.getenv("MASTER_KEY_ENV", "SECRET_MANAGEMENT_MASTER_KEY")

    # Key rotation settings
    DEFAULT_ROTATION_INTERVAL_DAYS: int = int(os.getenv("DEFAULT_ROTATION_INTERVAL_DAYS", "90"))
    OLD_VALUE_RETENTION_HOURS: int = int(os.getenv("OLD_VALUE_RETENTION_HOURS", "24"))
    MAX_VERSIONS: int = int(os.getenv("MAX_VERSIONS", "10"))

    # Access control settings
    ENABLE_ACCESS_CONTROL: bool = os.getenv("ENABLE_ACCESS_CONTROL", "true").lower() == "true"
    DEFAULT_ADMIN_PRINCIPAL: str = os.getenv("DEFAULT_ADMIN_PRINCIPAL", "admin")

    # Audit log settings
    ENABLE_AUDIT_LOG: bool = os.getenv("ENABLE_AUDIT_LOG", "true").lower() == "true"
    AUDIT_LOG_PATH: str = os.getenv("AUDIT_LOG_PATH", "./audit_logs")
    AUDIT_LOG_RETENTION_DAYS: int = int(os.getenv("AUDIT_LOG_RETENTION_DAYS", "90"))

    # Cache settings
    ENABLE_CACHE: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    CACHE_TTL_SECONDS: int = int(os.getenv("CACHE_TTL_SECONDS", "300"))

    # Security settings
    REQUIRE_AUTHENTICATION: bool = os.getenv("REQUIRE_AUTHENTICATION", "true").lower() == "true"
    AUTH_TOKEN_HEADER: str = os.getenv("AUTH_TOKEN_HEADER", "X-Auth-Token")

    # Integration settings
    KEY_MANAGEMENT_SERVICE_BACKEND: str = os.getenv("KEY_MANAGEMENT_SERVICE_BACKEND", "file")

    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    @classmethod
    def validate(cls) -> None:
        """Validate configuration settings."""
        if cls.PORT < 1 or cls.PORT > 65535:
            raise ValueError(f"Invalid PORT: {cls.PORT}")
        if cls.GRPC_PORT < 1 or cls.GRPC_PORT > 65535:
            raise ValueError(f"Invalid GRPC_PORT: {cls.GRPC_PORT}")
        if cls.DEFAULT_ROTATION_INTERVAL_DAYS <= 0:
            raise ValueError(f"Invalid DEFAULT_ROTATION_INTERVAL_DAYS: {cls.DEFAULT_ROTATION_INTERVAL_DAYS}")
        if cls.OLD_VALUE_RETENTION_HOURS <= 0:
            raise ValueError(f"Invalid OLD_VALUE_RETENTION_HOURS: {cls.OLD_VALUE_RETENTION_HOURS}")
        if cls.MAX_VERSIONS <= 0:
            raise ValueError(f"Invalid MAX_VERSIONS: {cls.MAX_VERSIONS}")
        if cls.CACHE_TTL_SECONDS <= 0:
            raise ValueError(f"Invalid CACHE_TTL_SECONDS: {cls.CACHE_TTL_SECONDS}")
        if cls.STORAGE_BACKEND not in ["file", "database"]:
            raise ValueError(f"Unsupported STORAGE_BACKEND: {cls.STORAGE_BACKEND}")
