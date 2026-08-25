# -*- coding: utf-8 -*-
"""Configuration for Release Management Service."""

import os
from typing import Optional


class Config:
    """Configuration settings for the service."""

    # Service settings
    SERVICE_NAME: str = "release_management_service"
    PORT: int = int(os.getenv("PORT", "8003"))
    HOST: str = os.getenv("HOST", "127.0.0.1")

    # gRPC settings
    GRPC_PORT: int = int(os.getenv("GRPC_PORT", "50053"))
    GRPC_HOST: str = os.getenv("GRPC_HOST", "127.0.0.1")

    # Release management settings
    RELEASES_DIR: str = os.getenv("RELEASES_DIR", "./releases")
    ARTIFACTS_DIR: str = os.getenv("ARTIFACTS_DIR", "./artifacts")
    BUILD_DIR: str = os.getenv("BUILD_DIR", "./build")
    MAX_RELEASE_HISTORY: int = int(os.getenv("MAX_RELEASE_HISTORY", "1000"))

    # Build settings
    DEFAULT_BUILD_TYPE: str = os.getenv("DEFAULT_BUILD_TYPE", "docker")
    BUILD_TIMEOUT: int = int(os.getenv("BUILD_TIMEOUT", "3600"))  # 1 hour
    MAX_CONCURRENT_BUILDS: int = int(os.getenv("MAX_CONCURRENT_BUILDS", "3"))

    # Deployment settings
    DEPLOYMENT_TIMEOUT: int = int(os.getenv("DEPLOYMENT_TIMEOUT", "1800"))  # 30 minutes
    ROLLBACK_TIMEOUT: int = int(os.getenv("ROLLBACK_TIMEOUT", "900"))  # 15 minutes
    MAX_CONCURRENT_DEPLOYMENTS: int = int(os.getenv("MAX_CONCURRENT_DEPLOYMENTS", "2"))

    # Approval settings
    DEFAULT_APPROVERS: list = ["devops-team", "tech-lead"]
    APPROVAL_TIMEOUT: int = int(os.getenv("APPROVAL_TIMEOUT", "604800"))  # 7 days
    AUTO_APPROVE_DEV: bool = os.getenv("AUTO_APPROVE_DEV", "true").lower() == "true"

    # Version settings
    VERSION_FORMAT: str = os.getenv("VERSION_FORMAT", "semver")  # semver, custom
    DEFAULT_VERSION: str = os.getenv("DEFAULT_VERSION", "0.1.0")

    # Environment settings
    SUPPORTED_ENVIRONMENTS: list = ["dev", "staging", "production"]
    DEFAULT_ENVIRONMENT: str = os.getenv("DEFAULT_ENVIRONMENT", "staging")

    # Storage settings
    STORAGE_TYPE: str = os.getenv("STORAGE_TYPE", "local")  # local, s3, gcs
    STORAGE_PATH: str = os.getenv("STORAGE_PATH", "./storage")

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
        if cls.BUILD_TIMEOUT <= 0:
            raise ValueError(f"Invalid BUILD_TIMEOUT: {cls.BUILD_TIMEOUT}")
        if cls.DEPLOYMENT_TIMEOUT <= 0:
            raise ValueError(f"Invalid DEPLOYMENT_TIMEOUT: {cls.DEPLOYMENT_TIMEOUT}")
        if cls.MAX_CONCURRENT_BUILDS <= 0:
            raise ValueError(f"Invalid MAX_CONCURRENT_BUILDS: {cls.MAX_CONCURRENT_BUILDS}")
        if cls.MAX_CONCURRENT_DEPLOYMENTS <= 0:
            raise ValueError(f"Invalid MAX_CONCURRENT_DEPLOYMENTS: {cls.MAX_CONCURRENT_DEPLOYMENTS}")
        if cls.DEFAULT_ENVIRONMENT not in cls.SUPPORTED_ENVIRONMENTS:
            raise ValueError(f"Unsupported environment: {cls.DEFAULT_ENVIRONMENT}")
        if cls.VERSION_FORMAT not in ["semver", "custom"]:
            raise ValueError(f"Unsupported version format: {cls.VERSION_FORMAT}")
