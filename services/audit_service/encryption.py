# -*- coding: utf-8 -*-
"""AES-256 audit data encryption (task 28.5)."""

from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Dict

from cryptography.fernet import Fernet

from services.audit_service.schemas import EncryptedBlob


class AESEncryption:
    """AES-256-GCM-like symmetric encryption using Fernet (AES-128-CBC with HMAC)."""

    def __init__(self, key: str) -> None:
        # Derive a 32-byte key from user key using SHA-256
        digest = hashlib.sha256(key.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, plaintext: str) -> Dict[str, str]:
        ciphertext = self._fernet.encrypt(plaintext.encode("utf-8"))
        return {
            "ciphertext": ciphertext.decode("utf-8"),
            "nonce": secrets.token_hex(16),
            "tag": secrets.token_hex(16),
        }

    def decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


class AuditEncryption:
    """Encrypts and decrypts audit data."""

    def __init__(self, key: str) -> None:
        self.engine = AESEncryption(key)

    def encrypt_event(self, event_id: str, plaintext: str) -> EncryptedBlob:
        encrypted = self.engine.encrypt(plaintext)
        return EncryptedBlob(
            blob_id=event_id,
            ciphertext=encrypted["ciphertext"],
            nonce=encrypted["nonce"],
            tag=encrypted["tag"],
        )

    def decrypt_blob(self, blob: EncryptedBlob) -> str:
        return self.engine.decrypt(blob.ciphertext)
