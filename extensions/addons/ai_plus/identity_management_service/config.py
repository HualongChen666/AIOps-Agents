# -*- coding: utf-8 -*-
"""Configuration for Identity Management Service."""

import logging
import os

logger = logging.getLogger(__name__)

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
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_EXPIRE_MINUTES", "30"))


def _resolve_jwt_secret_key() -> str:
    """Resolve JWT secret key from env or K8s secret file mount.

    Strict requirements (no defaults, HS256 entropy >= 256 bits):
    - Primary: env var JWT_SECRET_KEY
    - Fallback: file path in JWT_SECRET_KEY_FILE (e.g., /var/run/secrets/jwt.key)

    Raises:
        RuntimeError: missing env / missing file / read failure / len < 32
    """
    secret = os.getenv("JWT_SECRET_KEY")
    secret_file = os.getenv("JWT_SECRET_KEY_FILE")

    if secret:
        source = "JWT_SECRET_KEY"
    elif secret_file:
        if not os.path.isfile(secret_file):
            raise RuntimeError(
                f"JWT_SECRET_KEY_FILE={secret_file!r} does not exist; "
                "check ConfigMap/Secret mount."
            )
        try:
            with open(secret_file, "r", encoding="utf-8") as f:
                secret = f.read().strip()
            source = f"JWT_SECRET_KEY_FILE={secret_file}"
        except OSError as e:
            raise RuntimeError(
                f"failed to read JWT_SECRET_KEY_FILE={secret_file!r}: {e}"
            ) from e
    else:
        raise RuntimeError(
            "JWT_SECRET_KEY (or JWT_SECRET_KEY_FILE) env var must be set; "
            "production deployments cannot use a hardcoded default."
        )

    if len(secret) < 32:
        raise RuntimeError(
            f"JWT secret from {source} is {len(secret)} chars; "
            "HS256 requires >= 32 chars (>= 256 bits entropy)."
        )

    logger.debug("JWT secret resolved: source=%s length=%d", source, len(secret))
    return secret


JWT_SECRET_KEY = _resolve_jwt_secret_key()

# MFA configuration
MFA_ISSUER = os.getenv("MFA_ISSUER", "AIOps Identity Management")

# SSO configuration
SSO_ENABLED = os.getenv("SSO_ENABLED", "false").lower() == "true"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
