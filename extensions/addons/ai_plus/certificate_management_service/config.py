# -*- coding: utf-8 -*-
"""Configuration for Certificate Management Service."""

import os
from typing import Optional


class Config:
    """Configuration settings for Certificate Management Service."""

    # Service identification
    SERVICE_NAME = "certificate_management_service"
    SERVICE_VERSION = "1.0.0"

    # Server settings
    HOST = os.getenv("CMS_HOST", "0.0.0.0")
    PORT = int(os.getenv("CMS_PORT", "8003"))

    # gRPC settings
    GRPC_HOST = os.getenv("CMS_GRPC_HOST", "0.0.0.0")
    GRPC_PORT = int(os.getenv("CMS_GRPC_PORT", "50053"))

    # Logging settings
    LOG_LEVEL = os.getenv("CMS_LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Certificate storage settings
    CERTIFICATE_STORAGE_PATH = os.getenv(
        "CMS_CERTIFICATE_STORAGE_PATH",
        "data/certificates"
    )
    CERTIFICATE_BACKUP_PATH = os.getenv(
        "CMS_CERTIFICATE_BACKUP_PATH",
        "data/certificates/backups"
    )

    # Certificate validation settings
    DEFAULT_VALIDITY_DAYS = int(os.getenv("CMS_DEFAULT_VALIDITY_DAYS", "365"))
    MIN_VALIDITY_DAYS = int(os.getenv("CMS_MIN_VALIDITY_DAYS", "1"))
    MAX_VALIDITY_DAYS = int(os.getenv("CMS_MAX_VALIDITY_DAYS", "3650"))

    # Key settings
    DEFAULT_KEY_ALGORITHM = os.getenv("CMS_DEFAULT_KEY_ALGORITHM", "RSA")
    DEFAULT_KEY_SIZE = int(os.getenv("CMS_DEFAULT_KEY_SIZE", "2048"))
    ALLOWED_KEY_ALGORITHMS = ["RSA", "ECDSA", "Ed25519"]

    # Certificate types
    CERTIFICATE_TYPES = ["self_signed", "ca_signed", "root_ca", "intermediate_ca"]

    # Revocation settings
    CRL_UPDATE_INTERVAL_HOURS = int(os.getenv("CMS_CRL_UPDATE_INTERVAL_HOURS", "24"))

    # Validation settings
    ENABLE_EXPIRATION_CHECK = os.getenv("CMS_ENABLE_EXPIRATION_CHECK", "true").lower() == "true"
    ENABLE_REVOCATION_CHECK = os.getenv("CMS_ENABLE_REVOCATION_CHECK", "true").lower() == "true"
    EXPIRATION_WARNING_DAYS = int(os.getenv("CMS_EXPIRATION_WARNING_DAYS", "30"))

    @classmethod
    def validate(cls) -> None:
        """Validate configuration settings."""
        # Validate key algorithm
        if cls.DEFAULT_KEY_ALGORITHM not in cls.ALLOWED_KEY_ALGORITHMS:
            raise ValueError(
                f"Invalid key algorithm: {cls.DEFAULT_KEY_ALGORITHM}. "
                f"Must be one of: {cls.ALLOWED_KEY_ALGORITHMS}"
            )

        # Validate key size based on algorithm
        if cls.DEFAULT_KEY_ALGORITHM == "RSA":
            if cls.DEFAULT_KEY_SIZE not in [2048, 4096, 8192]:
                raise ValueError(
                    f"Invalid RSA key size: {cls.DEFAULT_KEY_SIZE}. "
                    f"Must be 2048, 4096, or 8192"
                )
        elif cls.DEFAULT_KEY_ALGORITHM == "ECDSA":
            if cls.DEFAULT_KEY_SIZE not in [256, 384, 521]:
                raise ValueError(
                    f"Invalid ECDSA key size: {cls.DEFAULT_KEY_SIZE}. "
                    f"Must be 256, 384, or 521"
                )

        # Validate validity days
        if cls.DEFAULT_VALIDITY_DAYS < cls.MIN_VALIDITY_DAYS:
            raise ValueError(
                f"Default validity days ({cls.DEFAULT_VALIDITY_DAYS}) "
                f"must be at least {cls.MIN_VALIDITY_DAYS}"
            )
        if cls.DEFAULT_VALIDITY_DAYS > cls.MAX_VALIDITY_DAYS:
            raise ValueError(
                f"Default validity days ({cls.DEFAULT_VALIDITY_DAYS}) "
                f"must not exceed {cls.MAX_VALIDITY_DAYS}"
            )

        # Create storage directories if they don't exist
        os.makedirs(cls.CERTIFICATE_STORAGE_PATH, exist_ok=True)
        os.makedirs(cls.CERTIFICATE_BACKUP_PATH, exist_ok=True)
