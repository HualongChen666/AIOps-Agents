# -*- coding: utf-8 -*-
"""Configuration for Dependency Management Service."""

import os
from typing import Optional


class Config:
    """Configuration settings for the service."""

    # Service settings
    SERVICE_NAME: str = "dependency_management_service"
    PORT: int = int(os.getenv("PORT", "8003"))
    HOST: str = os.getenv("HOST", "127.0.0.1")

    # gRPC settings
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50053"))
    GRPC_HOST: str = os.getenv("GRPC_HOST", "127.0.0.1")

    # Dependency scanning settings
    SCAN_TIMEOUT: int = int(os.getenv("SCAN_TIMEOUT", "300"))  # 5 minutes
    MAX_CONCURRENT_SCANS: int = int(os.getenv("MAX_CONCURRENT_SCANS", "4"))
    CACHE_DURATION: int = int(os.getenv("CACHE_DURATION", "3600"))  # 1 hour

    # Version check settings
    PYPI_API_URL: str = os.getenv("PYPI_API_URL", "https://pypi.org/pypi")
    SECURITY_DB_URL: str = os.getenv("SECURITY_DB_URL", "https://pypi.org/pypi")
    CHECK_TIMEOUT: int = int(os.getenv("CHECK_TIMEOUT", "60"))  # 1 minute

    # Update settings
    UPDATE_TIMEOUT: int = int(os.getenv("UPDATE_TIMEOUT", "600"))  # 10 minutes
    BACKUP_BEFORE_UPDATE: bool = os.getenv("BACKUP_BEFORE_UPDATE", "true").lower() == "true"
    AUTO_RESOLVE_CONFLICTS: bool = os.getenv("AUTO_RESOLVE_CONFLICTS", "false").lower() == "true"

    # Lock file settings
    LOCK_FILE_DIR: str = os.getenv("LOCK_FILE_DIR", "./locks")
    DEFAULT_LOCK_TYPE: str = os.getenv("DEFAULT_LOCK_TYPE", "requirements.lock")

    # Supported file types
    SUPPORTED_FILE_TYPES: list = ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]

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
        if cls.SCAN_TIMEOUT <= 0:
            raise ValueError(f"Invalid SCAN_TIMEOUT: {cls.SCAN_TIMEOUT}")
        if cls.MAX_CONCURRENT_SCANS <= 0:
            raise ValueError(f"Invalid MAX_CONCURRENT_SCANS: {cls.MAX_CONCURRENT_SCANS}")
        if cls.CHECK_TIMEOUT <= 0:
            raise ValueError(f"Invalid CHECK_TIMEOUT: {cls.CHECK_TIMEOUT}")
        if cls.UPDATE_TIMEOUT <= 0:
            raise ValueError(f"Invalid UPDATE_TIMEOUT: {cls.UPDATE_TIMEOUT}")
