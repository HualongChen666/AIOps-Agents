# -*- coding: utf-8 -*-
"""Field-level encryption helpers for sensitive snapshot data."""

from __future__ import annotations

import logging
import base64
import hashlib
import os
from typing import Optional

from loguru import logger

try:
    from cryptography.fernet import Fernet, InvalidToken

    _CRYPTO_AVAILABLE = True
except Exception as e:
    logging.exception("Unexpected exception: %s", e)
    _CRYPTO_AVAILABLE = False

_ENV_PROD = os.getenv("ENVIRONMENT", "development").lower() == "production"
_DEFAULT_ENCRYPTION_KEY = os.getenv("SNAPSHOT_ENCRYPTION_KEY", "").strip()
_PLAINTEXT_PREFIX = "PLAINTEXT::"

_fernet: Optional[Fernet] = None


def _encryption_enabled() -> bool:
    return os.getenv("SNAPSHOT_ENCRYPTION_ENABLED", "true").lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


def _get_fernet() -> Optional[Fernet]:
    """Initialize Fernet lazily from env or derived key."""
    global _fernet
    if _fernet is not None:
        return _fernet

    if not _CRYPTO_AVAILABLE:
        logger.warning("[crypto] cryptography not available, snapshot encryption disabled")
        _fernet = None
        return None

    if not _encryption_enabled():
        logger.info("[crypto] SNAPSHOT_ENCRYPTION_ENABLED=false, encryption disabled")
        _fernet = None
        return None

    raw_key = os.getenv("SNAPSHOT_ENCRYPTION_KEY", "").strip() or _DEFAULT_ENCRYPTION_KEY
    if not raw_key:
        # Derive deterministic key from other secrets if available
        seed = (
            os.getenv("JWT_SECRET_KEY", "").strip()
            or os.getenv("INTERNAL_API_KEY", "").strip()
            or ""
        )
        if seed:
            raw_key = base64.urlsafe_b64encode(
                hashlib.sha256(seed.encode("utf-8")).digest()
            ).decode("ascii")
        else:
            if _ENV_PROD:
                raise RuntimeError(
                    "[crypto] SNAPSHOT_ENCRYPTION_KEY or JWT_SECRET_KEY/INTERNAL_API_KEY "
                    "must be set in production"
                )
            raw_key = Fernet.generate_key().decode("ascii")
            logger.warning(
                "[crypto] SNAPSHOT_ENCRYPTION_KEY not set; generated a random key. "
                "Decryption will fail after process restart unless key is persisted."
            )

    try:
        _fernet = Fernet(raw_key.encode("ascii") if isinstance(raw_key, str) else raw_key)
        logger.info("[crypto] Snapshot encryption initialized")
    except Exception as exc:
        logger.error(f"[crypto] Invalid SNAPSHOT_ENCRYPTION_KEY: {exc}")
        _fernet = None
    return _fernet


def encrypt_snapshot(data: str) -> str:
    """Encrypt a string for snapshot storage.

    Returns the plaintext with a marker if encryption is disabled or fails.
    """
    f = _get_fernet()
    if f is None:
        return f"{_PLAINTEXT_PREFIX}{data}"
    return f.encrypt(data.encode("utf-8")).decode("utf-8")


def decrypt_snapshot(data: str) -> str:
    """Decrypt a snapshot string.

    Transparently handles the plaintext marker and decryption failures.
    """
    if data.startswith(_PLAINTEXT_PREFIX):
        return data[len(_PLAINTEXT_PREFIX) :]
    f = _get_fernet()
    if f is None:
        return data
    try:
        return f.decrypt(data.encode("utf-8")).decode("utf-8")
    except (InvalidToken, Exception) as exc:
        logger.error(f"[crypto] Failed to decrypt snapshot data: {exc}")
        return data
